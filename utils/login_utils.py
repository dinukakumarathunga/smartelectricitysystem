# ============================================================
#  utils/login_utils.py
#  OTP delivery dispatch (email or SMS, per config.OTP_CHANNEL),
#  login activity logging for 12_security.html's "Recent login
#  activity" table, and a login guard for JSON API routes.
# ============================================================

from functools import wraps

from flask import current_app, jsonify, request, session

from database.db import db
from models import LoginLog
from utils.email_utils import send_email


def api_login_required(view):
    """
    Same session check as page_routes.py's login_required, but for
    JSON endpoints (appliance_routes.py, bill_routes.py, etc.) —
    returns a 401 JSON body instead of redirecting, since a fetch()
    call can't follow a redirect to a login page usefully.
    """
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not (session.get('user_id') and session.get('otp_verified')):
            return jsonify(success=False, message='Please log in to continue.'), 401
        return view(*args, **kwargs)
    return wrapped


def send_otp_code(user, code, purpose):
    """Delivers a one-time code to the user via whichever channel is configured."""
    channel = current_app.config.get('OTP_CHANNEL', 'email')
    expiry_minutes = current_app.config['OTP_EXPIRY_MINUTES']

    if channel == 'sms':
        message = f'Your SmartElec verification code is {code}. It expires in {expiry_minutes} minutes.'
        _send_sms(user.mobile, message)
    else:
        subject = 'Your SmartElec verification code'
        body = (
            f'Your one-time verification code is: {code}\n'
            f'It expires in {expiry_minutes} minutes.\n\n'
            f"If you didn't request this, you can safely ignore this email."
        )
        send_email(user.email, subject, body)


def _send_sms(to_number, message):
    cfg = current_app.config
    sid, token, from_number = (
        cfg.get('TWILIO_ACCOUNT_SID'), cfg.get('TWILIO_AUTH_TOKEN'), cfg.get('TWILIO_FROM_NUMBER')
    )

    if not (sid and token and from_number and to_number):
        current_app.logger.info(f'[DEV SMS — Twilio not configured]\nTo: {to_number}\n{message}')
        return

    try:
        from twilio.rest import Client
    except ImportError:
        current_app.logger.warning('twilio package not installed — falling back to console log.')
        current_app.logger.info(f'[DEV SMS]\nTo: {to_number}\n{message}')
        return

    Client(sid, token).messages.create(body=message, from_=from_number, to=to_number)


def record_login(user_id, result):
    """
    Logs a login attempt (success or failure) for the security
    page's activity table. Device string is a best-effort parse
    of the User-Agent header — good enough for display, not meant
    to be a precise fingerprint.
    """
    ua = request.user_agent
    device = ua.browser.capitalize() if ua.browser else 'Unknown browser'
    if ua.platform:
        device = f'{device} on {ua.platform.capitalize()}'

    entry = LoginLog(
        user_id=user_id,
        device=device,
        ip_address=request.remote_addr,
        result=result,
    )
    db.session.add(entry)
    db.session.commit()
