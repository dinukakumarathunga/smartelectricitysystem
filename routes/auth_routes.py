# ============================================================
#  routes/auth_routes.py
#  Flow step 1: register → login → OTP → (appliance onboarding
#  or dashboard, decided by user.first_login_done).
#
#  Endpoints match what the frontend JS will call once it's
#  rewritten off localStorage (see app-data.js note): POST
#  /auth/register, /auth/login, /auth/verify-otp,
#  /auth/resend-otp, /auth/logout. All return
#  {success, message?, redirect?} JSON, same shape login.js /
#  otp.js / register.js already expect from their old fetch()
#  calls.
#
#  Session keys set here are exactly what page_routes.py's
#  guards check:
#    pending_otp, otp_user_id  → required to reach 03_otp_login.html
#    user_id, otp_verified     → required for every logged-in page
# ============================================================

from flask import Blueprint, current_app, jsonify, request, session

from database.db import db
from models import Appliance, Otp, User
from utils.login_utils import record_login, send_otp_code

auth_bp = Blueprint('auth', __name__)


# ── register ─────────────────────────────────────────────────
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}

    full_name        = (data.get('full_name') or '').strip()
    username         = (data.get('username') or '').strip()
    account_number   = (data.get('account_number') or '').strip()
    email            = (data.get('email') or '').strip().lower()
    mobile           = (data.get('mobile') or '').strip()
    password         = data.get('password') or ''
    confirm_password = data.get('confirm_password') or ''

    error = _validate_registration(full_name, username, account_number, email, password, confirm_password)
    if error:
        return jsonify(success=False, message=error), 400

    if User.query.filter_by(username=username).first():
        return jsonify(success=False, message='That username is already taken.'), 409
    if User.query.filter_by(email=email).first():
        return jsonify(success=False, message='An account with that email already exists.'), 409
    if User.query.filter_by(account_number=account_number).first():
        return jsonify(success=False, message='An account is already registered to that electricity account number.'), 409

    user = User(full_name=full_name, username=username, account_number=account_number,
                email=email, mobile=mobile)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    # Seed the fixed appliance catalog (unowned) so 04_appliance_onboarding.html
    # has rows to toggle rather than needing to create them lazily.
    Appliance.seed_catalog_for_user(user.id)

    _issue_otp(user, purpose='register')
    return jsonify(success=True)


# ── login ────────────────────────────────────────────────────
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    identifier = (data.get('username') or '').strip()
    password   = data.get('password') or ''

    if not identifier or not password:
        return jsonify(success=False, message='Username/account number and password are required.'), 400

    user = User.query.filter(
        (User.username == identifier) | (User.account_number == identifier)
    ).first()

    if not user or not user.check_password(password):
        if user:
            record_login(user.id, 'Failed')
        return jsonify(success=False, message='Incorrect username/account number or password.'), 401

    _issue_otp(user, purpose='login')
    return jsonify(success=True)


# ── OTP verify ───────────────────────────────────────────────
@auth_bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.get_json(silent=True) or {}
    code = (data.get('otp') or '').strip()

    user_id = session.get('otp_user_id')
    purpose = session.get('pending_otp')

    if not user_id or not purpose:
        return jsonify(success=False, message='No verification in progress. Please log in again.'), 400

    max_attempts = current_app.config['OTP_MAX_ATTEMPTS']
    attempts = session.get('otp_attempts', 0)
    if attempts >= max_attempts:
        _clear_otp_session()
        return jsonify(success=False, message='Too many incorrect attempts. Please log in again to request a new code.'), 429

    otp = (
        Otp.query.filter_by(user_id=user_id, purpose=purpose, used_at=None)
        .order_by(Otp.created_at.desc())
        .first()
    )

    if not otp or not otp.verify(code):
        session['otp_attempts'] = attempts + 1
        user = User.query.get(user_id)
        if user:
            record_login(user.id, 'Failed')
        remaining = max_attempts - (attempts + 1)
        message = 'Incorrect or expired code. Please try again.'
        if remaining <= 0:
            _clear_otp_session()
            message = 'Too many incorrect attempts. Please log in again to request a new code.'
        return jsonify(success=False, message=message), 400

    user = User.query.get(user_id)

    _clear_otp_session()
    session['user_id'] = user.id
    session['otp_verified'] = True
    session.permanent = True

    record_login(user.id, 'Success')

    redirect_url = '/07_dashboard.html' if user.first_login_done else '/04_appliance_onboarding.html'
    return jsonify(success=True, redirect=redirect_url)


# ── OTP resend ───────────────────────────────────────────────
@auth_bp.route('/resend-otp', methods=['POST'])
def resend_otp():
    user_id = session.get('otp_user_id')
    purpose = session.get('pending_otp')

    if not user_id or not purpose:
        return jsonify(success=False, message='No verification in progress. Please log in again.'), 400

    user = User.query.get(user_id)
    if not user:
        _clear_otp_session()
        return jsonify(success=False, message='Account not found. Please log in again.'), 404

    session.pop('otp_attempts', None)   # fresh code, fresh attempt count
    _issue_otp(user, purpose=purpose)
    return jsonify(success=True)


# ── logout ───────────────────────────────────────────────────
@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify(success=True, redirect='/02_login.html')


# ── helpers ──────────────────────────────────────────────────
def _issue_otp(user, purpose):
    otp, code = Otp.create_for_user(
        user_id=user.id,
        purpose=purpose,
        length=current_app.config['OTP_LENGTH'],
        expiry_minutes=current_app.config['OTP_EXPIRY_MINUTES'],
    )
    send_otp_code(user, code, purpose)

    session['pending_otp'] = purpose
    session['otp_user_id'] = user.id
    session.pop('otp_attempts', None)


def _clear_otp_session():
    session.pop('pending_otp', None)
    session.pop('otp_user_id', None)
    session.pop('otp_attempts', None)


def _validate_registration(full_name, username, account_number, email, password, confirm_password):
    if not full_name:
        return 'Full name is required.'
    if not username or len(username) < 3:
        return 'Username must be at least 3 characters.'
    if not account_number:
        return 'Electricity account number is required.'
    if not email or '@' not in email:
        return 'A valid email address is required.'
    if not password or len(password) < 8:
        return 'Password must be at least 8 characters.'
    if password != confirm_password:
        return 'Passwords do not match.'
    return None
