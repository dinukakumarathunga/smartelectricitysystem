# ============================================================
#  models/user.py
#  Matches the `users` and `login_log` tables in schema.sql.
# ============================================================

from datetime import datetime, timezone

from werkzeug.security import generate_password_hash, check_password_hash

from database.db import db


class User(db.Model):
    __tablename__ = 'users'

    id               = db.Column(db.Integer, primary_key=True)
    full_name        = db.Column(db.String(120), nullable=False)
    username         = db.Column(db.String(60), unique=True, nullable=False)
    account_number   = db.Column(db.String(40), unique=True, nullable=False)
    email            = db.Column(db.String(160), unique=True, nullable=False)
    mobile           = db.Column(db.String(20))
    password_hash    = db.Column(db.String(255), nullable=False)
    first_login_done = db.Column(db.Boolean, nullable=False, default=False)
    created_at       = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # ── relationships ────────────────────────────────────────
    otps = db.relationship(
        'Otp', backref='user', cascade='all, delete-orphan', lazy='dynamic'
    )
    appliances = db.relationship(
        'Appliance', backref='user', cascade='all, delete-orphan', lazy='dynamic'
    )
    appliance_profile = db.relationship(
        'ApplianceProfile', backref='user', uselist=False, cascade='all, delete-orphan'
    )
    bills = db.relationship(
        'Bill', backref='user', cascade='all, delete-orphan',
        order_by='Bill.confirmed_at.desc()', lazy='dynamic'
    )
    predictions = db.relationship(
        'Prediction', backref='user', cascade='all, delete-orphan', lazy='dynamic'
    )
    login_logs = db.relationship(
        'LoginLog', backref='user', cascade='all, delete-orphan',
        order_by='LoginLog.at.desc()', lazy='dynamic'
    )

    # ── password helpers ─────────────────────────────────────
    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    # ── login lookup ─────────────────────────────────────────
    def matches_identifier(self, identifier):
        """
        login.js lets the user log in with either their username
        OR their electricity account number — see the "e.g.
        kumara_h or CEB-XXXXXXX" placeholder on 02_login.html.
        """
        return identifier == self.username or identifier == self.account_number

    # ── serialisation ────────────────────────────────────────
    def to_public_dict(self):
        """Never include password_hash in anything sent to the client."""
        return {
            'id':              self.id,
            'full_name':       self.full_name,
            'username':        self.username,
            'account_number':  self.account_number,
            'email':           self.email,
            'mobile':          self.mobile,
            'first_login_done': self.first_login_done,
            'created_at':      self.created_at.isoformat(),
        }

    def __repr__(self):
        return f'<User {self.username}>'


class LoginLog(db.Model):
    __tablename__ = 'login_log'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    at         = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    device     = db.Column(db.String(120))
    ip_address = db.Column(db.String(45))
    result     = db.Column(db.Enum('Success', 'Failed', name='login_result'), nullable=False)

    def to_dict(self):
        return {
            'at':     self.at.isoformat(),
            'device': self.device,
            'result': self.result,
        }
