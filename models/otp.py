# ============================================================
#  models/otp.py
#  Matches the `otps` table in schema.sql.
#  Handles the login-flow OTP step (register/login on
#  03_otp_login.html) — codes are hashed at rest, never stored
#  or logged raw.
# ============================================================

import random
from datetime import datetime, timedelta, timezone

from werkzeug.security import generate_password_hash, check_password_hash

from database.db import db


class Otp(db.Model):
    __tablename__ = 'otps'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    code_hash  = db.Column(db.String(255), nullable=False)
    purpose    = db.Column(db.Enum('register', 'login', name='otp_purpose'), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at    = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # ── creation ─────────────────────────────────────────────
    @staticmethod
    def generate_code(length):
        return ''.join(str(random.randint(0, 9)) for _ in range(length))

    @classmethod
    def create_for_user(cls, user_id, purpose, length, expiry_minutes):
        """
        Creates and persists a new OTP row, and returns the RAW
        code separately (it is never stored in plain text) so the
        caller (auth_routes.py) can hand it to email/SMS_utils
        for delivery. Any previous unused OTP for this user +
        purpose is invalidated first, so only one code is ever
        valid at a time — otherwise "Resend code" on
        03_otp_login.html could leave several codes simultaneously
        valid.
        """
        cls.query.filter_by(user_id=user_id, purpose=purpose, used_at=None).delete()

        code = cls.generate_code(length)
        otp = cls(
            user_id=user_id,
            code_hash=generate_password_hash(code),
            purpose=purpose,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes),
        )
        db.session.add(otp)
        db.session.commit()
        return otp, code

    # ── verification ─────────────────────────────────────────
    def is_expired(self):
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > expires_at

    def verify(self, raw_code):
        """Returns True and marks the OTP used on success; False otherwise."""
        if self.used_at is not None or self.is_expired():
            return False
        if not check_password_hash(self.code_hash, raw_code):
            return False
        self.used_at = datetime.now(timezone.utc)
        db.session.commit()
        return True

    def __repr__(self):
        return f'<Otp user_id={self.user_id} purpose={self.purpose}>'
