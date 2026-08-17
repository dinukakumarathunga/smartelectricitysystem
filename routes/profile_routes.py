# ============================================================
#  routes/profile_routes.py
#  Powers 12_security.html: account info + recent login activity,
#  password change, and the "Download my data" export.
#
#  Note: appliance profile editing (11_appliance_profile.html)
#  is NOT here — it reuses the same GET/POST /appliances/
#  endpoints as onboarding (see appliance_routes.py), since the
#  frontend distinguishes "first time" vs "editing" purely by
#  which page it's on, not by anything the backend needs a
#  separate endpoint for.
#
#  GET  /profile/            → account info + recent login log
#  POST /profile/change-password
#  GET  /profile/export      → full data dump for "Download my data"
# ============================================================

from flask import Blueprint, jsonify, request, session

from database.db import db
from models import Appliance, ApplianceProfile, Bill, LoginLog, User
from utils.login_utils import api_login_required

profile_bp = Blueprint('profile', __name__)

LOGIN_LOG_LIMIT = 10
MIN_PASSWORD_LENGTH = 8


@profile_bp.route('/', methods=['GET'])
@api_login_required
def get_profile():
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify(success=False, message='Account not found.'), 404

    logs = (
        LoginLog.query.filter_by(user_id=user.id)
        .order_by(LoginLog.at.desc())
        .all()[:LOGIN_LOG_LIMIT]
    )

    return jsonify(success=True, user=user.to_public_dict(), login_log=[l.to_dict() for l in logs])


@profile_bp.route('/change-password', methods=['POST'])
@api_login_required
def change_password():
    data = request.get_json(silent=True) or {}
    current  = data.get('current_password') or ''
    new      = data.get('new_password') or ''
    confirm  = data.get('confirm_password') or ''

    user = User.query.get(session['user_id'])
    if not user:
        return jsonify(success=False, message='Account not found.'), 404

    if not current or not user.check_password(current):
        return jsonify(success=False, message='Current password is incorrect.'), 400
    if not new or len(new) < MIN_PASSWORD_LENGTH:
        return jsonify(success=False, message=f'New password must be at least {MIN_PASSWORD_LENGTH} characters.'), 400
    if new != confirm:
        return jsonify(success=False, message='New passwords do not match.'), 400
    if current == new:
        return jsonify(success=False, message='New password must be different from your current password.'), 400

    user.set_password(new)
    db.session.commit()
    return jsonify(success=True)


@profile_bp.route('/export', methods=['GET'])
@api_login_required
def export_data():
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify(success=False, message='Account not found.'), 404

    appliances = Appliance.query.filter_by(user_id=user.id).all()
    profile = ApplianceProfile.query.get(user.id)
    bills = Bill.query.filter_by(user_id=user.id).order_by(Bill.confirmed_at.desc()).all()
    logs = LoginLog.query.filter_by(user_id=user.id).order_by(LoginLog.at.desc()).all()

    return jsonify(
        success=True,
        data={
            # to_public_dict() already excludes password_hash — never
            # include it in an export.
            'user':            user.to_public_dict(),
            'appliances':      [a.to_dict() for a in appliances],
            'household_size':  profile.household_size if profile else None,
            'bills':           [b.to_dict() for b in bills],
            'login_history':   [l.to_dict() for l in logs],
        },
    )
