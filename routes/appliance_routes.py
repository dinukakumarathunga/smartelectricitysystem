# ============================================================
#  routes/appliance_routes.py
#  Flow step 2: appliance onboarding (04_appliance_onboarding.html)
#  and later editing (11_appliance_profile.html) share the same
#  two endpoints — the frontend distinguishes "first time" vs
#  "editing" purely by which page it's on, not by anything the
#  backend needs to know.
#
#  GET  /appliances/       → current selections + household size
#  POST /appliances/save   → persist selections, flips
#                             user.first_login_done to True
#
#  IMPORTANT: this is the only place first_login_done gets set.
#  Without it, auth_routes.py's verify_otp() would send every
#  returning user back to onboarding forever — see the redirect
#  logic there.
# ============================================================

from flask import Blueprint, jsonify, request, session

from database.db import db
from models import APPLIANCE_CATALOG, Appliance, ApplianceProfile, HOUSEHOLD_SIZES, User
from utils.login_utils import api_login_required

appliance_bp = Blueprint('appliances', __name__)


@appliance_bp.route('/', methods=['GET'])
@api_login_required
def get_appliances():
    user_id = session['user_id']

    rows = Appliance.query.filter_by(user_id=user_id).all()
    if not rows:
        # Defensive fallback — every new user is seeded via
        # Appliance.seed_catalog_for_user() at registration, but
        # this covers any account created before that was wired in.
        Appliance.seed_catalog_for_user(user_id)
        rows = Appliance.query.filter_by(user_id=user_id).all()

    profile = ApplianceProfile.query.get(user_id)

    return jsonify(
        success=True,
        appliances=[a.to_dict() for a in rows],
        household_size=profile.household_size if profile else None,
    )


@appliance_bp.route('/save', methods=['POST'])
@api_login_required
def save_appliances():
    data = request.get_json(silent=True) or {}
    incoming = data.get('appliances') or []
    household_size = data.get('household_size') or None

    if household_size and household_size not in HOUSEHOLD_SIZES:
        return jsonify(success=False, message='Invalid household size.'), 400

    # Only accept names from the fixed catalog — ignore anything
    # else rather than erroring, since a stale client sending an
    # unrecognised name shouldn't block saving the rest.
    incoming_by_name = {}
    for item in incoming:
        name = (item.get('name') or '').strip()
        if name in APPLIANCE_CATALOG:
            incoming_by_name[name] = bool(item.get('owned'))

    user_id = session['user_id']
    existing = {a.name: a for a in Appliance.query.filter_by(user_id=user_id).all()}

    for name in APPLIANCE_CATALOG:
        owned = incoming_by_name.get(name, False)
        if name in existing:
            existing[name].owned = owned
        else:
            db.session.add(Appliance(user_id=user_id, name=name, owned=owned))

    profile = ApplianceProfile.query.get(user_id)
    if profile is None:
        profile = ApplianceProfile(user_id=user_id)
        db.session.add(profile)
    profile.household_size = household_size

    # Flow step 2 complete — every subsequent login goes straight
    # to the dashboard instead of back through onboarding.
    user = User.query.get(user_id)
    if user:
        user.first_login_done = True

    db.session.commit()
    return jsonify(success=True)
