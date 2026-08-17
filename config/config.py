# ============================================================
#  config/config.py
#  Central Flask configuration, loaded from environment
#  variables (see .env.example). Values here are deliberately
#  kept in sync with what the frontend already assumes:
#    - OTP_EXPIRY_MINUTES  = 5   → matches the 05:00 countdown in otp.js
#    - OTP_LENGTH          = 6   → matches the 6 otp-box inputs in 03_otp_login.html
#    - MAX_CONTENT_LENGTH  = 10MB → matches the 10 MB check in upload.js
#    - ALLOWED_UPLOAD_EXTENSIONS → matches the accept=".jpg,.jpeg,.png,.pdf" on 05_upload_bill.html
# ============================================================

import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


class Config:
    """Base config — shared by every environment."""

    # ── Core Flask ──────────────────────────────────────────
    SECRET_KEY = os.environ.get('SECRET_KEY', 'change-me-in-.env')
    DEBUG = False
    TESTING = False

    # ── Database ────────────────────────────────────────────
    # e.g. mysql+pymysql://user:password@localhost:3306/smartelec
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'mysql+pymysql://root:root@localhost:3306/smartelec'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,   # avoids "MySQL server has gone away" on idle connections
        'pool_recycle': 280,
    }

    # ── Session / auth ──────────────────────────────────────
    # Session-based auth to match the fetch() calls in the JS
    # (login.js / otp.js expect the server to track the pending
    # OTP + logged-in state between requests).
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False') == 'True'
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)   # "remember this device" on 02_login.html

    # ── CSRF (Flask-WTF) ─────────────────────────────────────
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None   # tokens don't expire mid-session; rely on SECRET_KEY rotation instead

    # ── OTP ──────────────────────────────────────────────────
    OTP_LENGTH = 6
    OTP_EXPIRY_MINUTES = 5
    OTP_MAX_ATTEMPTS = 5          # lock out after N wrong codes, per otp.js's "shake the boxes" flow
    OTP_CHANNEL = os.environ.get('OTP_CHANNEL', 'email')   # 'email' or 'sms'

    # ── Email (used if OTP_CHANNEL == 'email') ──────────────
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', MAIL_USERNAME)

    # ── SMS (used if OTP_CHANNEL == 'sms') ──────────────────
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
    TWILIO_FROM_NUMBER = os.environ.get('TWILIO_FROM_NUMBER')

    # ── File uploads (bill photo / SMS screenshot) ──────────
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join(BASE_DIR, 'uploads', 'temp'))
    SAMPLE_BILLS_FOLDER = os.path.join(BASE_DIR, 'uploads', 'sample_bills')
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024   # 10 MB, matches upload.js
    ALLOWED_UPLOAD_EXTENSIONS = {'jpg', 'jpeg', 'png', 'pdf'}
    DELETE_UPLOAD_AFTER_OCR = True   # matches the privacy note on 05_upload_bill.html

    # ── OCR ──────────────────────────────────────────────────
    TESSERACT_CMD = os.environ.get('TESSERACT_CMD')   # e.g. /usr/bin/tesseract — leave unset to use system PATH
    OCR_LOW_CONFIDENCE_THRESHOLD = 60   # pytesseract confidence % below which ocr_confidence is 'Low'

    # ── ML prediction models ────────────────────────────────
    ML_MODELS_DIR = os.environ.get('ML_MODELS_DIR', os.path.join(BASE_DIR, 'ml_models'))
    PREDICTION_MIN_MONTHS = 2   # matches AppData.predict()'s "need at least 2 confirmed bills" rule


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'mysql+pymysql://root:root@localhost:3306/smartelec_dev'
    )


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False   # simplifies posting test payloads without a CSRF token
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'TEST_DATABASE_URL',
        'sqlite:///' + os.path.join(BASE_DIR, 'test.db')
    )


class ProductionConfig(Config):
    SESSION_COOKIE_SECURE = True


config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
}


def get_config():
    env = os.environ.get('FLASK_ENV', 'development')
    cfg = config_by_name.get(env, DevelopmentConfig)

    # app.config.from_object() is normally passed a class, not an
    # instance, so this check has to live here rather than in
    # ProductionConfig.__init__ (which would never run in that case).
    if cfg is ProductionConfig and Config.SECRET_KEY == 'change-me-in-.env':
        raise RuntimeError('SECRET_KEY must be set via environment in production.')

    return cfg
