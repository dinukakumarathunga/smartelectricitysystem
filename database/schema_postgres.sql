-- ============================================================
--  schema_postgres.sql
--  SmartElec — PostgreSQL version, for Render's free database.
--  Converted from the original MySQL schema.sql. Table names,
--  column names, and relationships are unchanged — only the
--  syntax differs (no ENGINE/AUTO_INCREMENT/UNSIGNED in Postgres,
--  ENUM handled via CHECK constraints instead).
-- ============================================================

-- ── users ───────────────────────────────────────────────────
DROP TABLE IF EXISTS login_log CASCADE;
DROP TABLE IF EXISTS predictions CASCADE;
DROP TABLE IF EXISTS bills CASCADE;
DROP TABLE IF EXISTS appliances CASCADE;
DROP TABLE IF EXISTS appliance_profile CASCADE;
DROP TABLE IF EXISTS otps CASCADE;
DROP TABLE IF EXISTS users CASCADE;

CREATE TABLE users (
  id               SERIAL PRIMARY KEY,
  full_name        VARCHAR(120)  NOT NULL,
  username         VARCHAR(60)   NOT NULL UNIQUE,
  account_number   VARCHAR(40)   NOT NULL UNIQUE,
  email            VARCHAR(160)  NOT NULL UNIQUE,
  mobile           VARCHAR(20),
  password_hash    VARCHAR(255)  NOT NULL,
  first_login_done BOOLEAN       NOT NULL DEFAULT FALSE,
  created_at       TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ── otps ────────────────────────────────────────────────────
CREATE TABLE otps (
  id          SERIAL PRIMARY KEY,
  user_id     INTEGER      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  code_hash   VARCHAR(255) NOT NULL,
  purpose     VARCHAR(20)  NOT NULL CHECK (purpose IN ('register','login')),
  expires_at  TIMESTAMP    NOT NULL,
  used_at     TIMESTAMP,
  created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_otps_user_purpose ON otps (user_id, purpose);

-- ── appliance_profile ───────────────────────────────────────
CREATE TABLE appliance_profile (
  user_id         INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  household_size  VARCHAR(10) CHECK (household_size IN ('1-2','3-4','5+')),
  updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ── appliances ──────────────────────────────────────────────
CREATE TABLE appliances (
  id      SERIAL PRIMARY KEY,
  user_id INTEGER      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name    VARCHAR(60)  NOT NULL,
  owned   BOOLEAN      NOT NULL DEFAULT FALSE,
  UNIQUE (user_id, name)
);

-- ── bills ───────────────────────────────────────────────────
CREATE TABLE bills (
  id               SERIAL PRIMARY KEY,
  user_id          INTEGER        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  billing_period   VARCHAR(60),
  units_consumed   DECIMAL(10,2)  NOT NULL,
  units_exported   DECIMAL(10,2),
  bill_amount_lkr  DECIMAL(12,2),
  source           VARCHAR(10)    NOT NULL DEFAULT 'photo' CHECK (source IN ('photo','sms')),
  ocr_confidence   VARCHAR(10)    CHECK (ocr_confidence IN ('High','Medium','Low')),
  image_path       VARCHAR(255),
  confirmed_at     TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_bills_user_confirmed ON bills (user_id, confirmed_at);

-- ── predictions ─────────────────────────────────────────────
CREATE TABLE predictions (
  id               SERIAL PRIMARY KEY,
  user_id          INTEGER        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  for_period       VARCHAR(60)    NOT NULL,
  predicted_kwh    DECIMAL(10,2)  NOT NULL,
  actual_bill_id   INTEGER        REFERENCES bills(id) ON DELETE SET NULL,
  accuracy_pct     DECIMAL(5,2),
  created_at       TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_predictions_user ON predictions (user_id);

-- ── login_log ───────────────────────────────────────────────
CREATE TABLE login_log (
  id          SERIAL PRIMARY KEY,
  user_id     INTEGER      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  at          TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  device      VARCHAR(120),
  ip_address  VARCHAR(45),
  result      VARCHAR(10)  NOT NULL CHECK (result IN ('Success','Failed'))
);
CREATE INDEX idx_login_log_user_at ON login_log (user_id, at);
