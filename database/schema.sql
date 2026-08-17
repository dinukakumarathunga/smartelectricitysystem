-- ============================================================
--  schema.sql
--  SmartElec — Secure Smart Electricity Consumption Analysis
--
--  Mirrors the data shape already used by static/js/app-data.js
--  (currently a localStorage prototype) so the Flask routes can
--  be wired up with the same field names on both sides.
--
--  Dialect: MySQL 8 / InnoDB. Swap AUTO_INCREMENT -> SERIAL and
--  drop the ENGINE line if moving to Postgres.
-- ============================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ── users ───────────────────────────────────────────────────
-- One row per registered account. Password is never stored in
-- plain text here (the JS prototype does — see security note in
-- app-data.js — this schema assumes Werkzeug's generate_password_hash).
DROP TABLE IF EXISTS users;
CREATE TABLE users (
  id               INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  full_name        VARCHAR(120)  NOT NULL,
  username         VARCHAR(60)   NOT NULL,
  account_number   VARCHAR(40)   NOT NULL,   -- CEB/LECO account number, e.g. printed on the bill
  email            VARCHAR(160)  NOT NULL,
  mobile           VARCHAR(20)   NULL,
  password_hash    VARCHAR(255)  NOT NULL,
  first_login_done TINYINT(1)    NOT NULL DEFAULT 0,  -- drives the onboarding redirect (flow step 2)
  created_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

  UNIQUE KEY uq_users_username        (username),
  UNIQUE KEY uq_users_email           (email),
  UNIQUE KEY uq_users_account_number  (account_number)
) ENGINE=InnoDB;

-- ── otps ────────────────────────────────────────────────────
-- Short-lived one-time codes for the login flow (flow step 1).
-- One active row per (user, purpose) at a time in practice;
-- old rows can be swept by a periodic job or left to expire.
DROP TABLE IF EXISTS otps;
CREATE TABLE otps (
  id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id     INT UNSIGNED  NOT NULL,
  code_hash   VARCHAR(255)  NOT NULL,        -- hash the code, don't store it raw
  purpose     ENUM('register','login')  NOT NULL,
  expires_at  DATETIME      NOT NULL,
  used_at     DATETIME      NULL,
  created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT fk_otps_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  KEY idx_otps_user_purpose (user_id, purpose)
) ENGINE=InnoDB;

-- ── appliance_profile ───────────────────────────────────────
-- One row per user for the household-level fields collected
-- alongside the appliance grid (flow step 2).
DROP TABLE IF EXISTS appliance_profile;
CREATE TABLE appliance_profile (
  user_id         INT UNSIGNED PRIMARY KEY,
  household_size  ENUM('1-2','3-4','5+')  NULL,
  updated_at      DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  CONSTRAINT fk_appliance_profile_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ── appliances ──────────────────────────────────────────────
-- One row per (user, appliance name) — matches the fixed
-- APPLIANCE_CATALOG list in app-data.js. `owned` is a simple
-- boolean toggle, same as the tile grid on the onboarding and
-- profile pages.
DROP TABLE IF EXISTS appliances;
CREATE TABLE appliances (
  id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id     INT UNSIGNED  NOT NULL,
  name        VARCHAR(60)   NOT NULL,   -- e.g. 'Air conditioner', 'Water heater'
  owned       TINYINT(1)    NOT NULL DEFAULT 0,

  CONSTRAINT fk_appliances_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  UNIQUE KEY uq_appliances_user_name (user_id, name)
) ENGINE=InnoDB;

-- ── bills ───────────────────────────────────────────────────
-- One row per confirmed bill/SMS upload (flow steps 3 + 4).
-- units_consumed of 0 is valid (e.g. a net-metering month fully
-- offset by export) — see the confirm.js validation fix, keep
-- that in mind when writing the route/model layer too.
DROP TABLE IF EXISTS bills;
CREATE TABLE bills (
  id               INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id          INT UNSIGNED   NOT NULL,
  billing_period   VARCHAR(60)    NULL,     -- free-text as extracted/edited, e.g. "22 Jun 2024 - 23 Jul 2024"
  units_consumed   DECIMAL(10,2)  NOT NULL,
  units_exported   DECIMAL(10,2)  NULL,     -- for net-metering/solar accounts
  bill_amount_lkr  DECIMAL(12,2)  NULL,
  source           ENUM('photo','sms')  NOT NULL DEFAULT 'photo',
  ocr_confidence   ENUM('High','Medium','Low')  NULL,
  image_path       VARCHAR(255)   NULL,     -- path under uploads/, if the original image is kept
  confirmed_at     DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT fk_bills_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  KEY idx_bills_user_confirmed (user_id, confirmed_at)
) ENGINE=InnoDB;

-- ── predictions ─────────────────────────────────────────────
-- Optional but recommended: logs each prediction the ml_models/
-- .pkl model makes, so the "model accuracy so far" stat on
-- 08_ai_prediction.html can be computed from real history instead
-- of left as "not tracked yet" (current state in app-data.js).
DROP TABLE IF EXISTS predictions;
CREATE TABLE predictions (
  id               INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id          INT UNSIGNED   NOT NULL,
  for_period       VARCHAR(60)    NOT NULL,   -- the month being predicted, e.g. "Aug 2024"
  predicted_kwh    DECIMAL(10,2)  NOT NULL,
  actual_bill_id   INT UNSIGNED   NULL,       -- filled in once that month's real bill is confirmed
  accuracy_pct     DECIMAL(5,2)   NULL,       -- computed once actual_bill_id is set
  created_at       DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT fk_predictions_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_predictions_bill FOREIGN KEY (actual_bill_id) REFERENCES bills(id) ON DELETE SET NULL,
  KEY idx_predictions_user (user_id)
) ENGINE=InnoDB;

-- ── login_log ───────────────────────────────────────────────
-- Recent login activity shown on 12_security.html.
DROP TABLE IF EXISTS login_log;
CREATE TABLE login_log (
  id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id     INT UNSIGNED  NOT NULL,
  at          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  device      VARCHAR(120)  NULL,
  ip_address  VARCHAR(45)   NULL,   -- long enough for IPv6
  result      ENUM('Success','Failed')  NOT NULL,

  CONSTRAINT fk_login_log_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  KEY idx_login_log_user_at (user_id, at)
) ENGINE=InnoDB;

SET FOREIGN_KEY_CHECKS = 1;
