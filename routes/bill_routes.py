# ============================================================
#  routes/bill_routes.py
#  Flow steps 3-4: upload a bill photo/SMS screenshot → OCR
#  extraction → user reviews on 06_upload_confirm.html → saved
#  bill shows up on the dashboard.
#
#  POST /bill/upload   → runs OCR, returns extracted fields
#                         (nothing saved to the DB yet)
#  POST /bill/confirm  → saves the (possibly user-edited) values
#  GET  /bill/         → recent bills, used by 05_upload_bill.html's
#                         "Recent uploads" table
# ============================================================

import os
import uuid

from flask import Blueprint, current_app, jsonify, request, session
from werkzeug.utils import secure_filename

from database.db import db
from models import Bill
from utils.login_utils import api_login_required
from utils.ocr_utils import extract_bill_data

bill_bp = Blueprint('bill', __name__)

VALID_SOURCES = ('photo', 'sms')
VALID_CONFIDENCE = ('High', 'Medium', 'Low')
MAX_REASONABLE_KWH = 9999


def _allowed_file(filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    return ext in current_app.config['ALLOWED_UPLOAD_EXTENSIONS']


# ── upload + OCR ─────────────────────────────────────────────
@bill_bp.route('/upload', methods=['POST'])
@api_login_required
def upload_bill():
    if 'file' not in request.files or request.files['file'].filename == '':
        return jsonify(success=False, message='Please select a bill image or SMS screenshot first.'), 400

    file = request.files['file']
    source = request.form.get('source', 'photo')
    if source not in VALID_SOURCES:
        source = 'photo'

    if not _allowed_file(file.filename):
        return jsonify(success=False, message='Unsupported file type. Please upload a JPEG, PNG, or PDF file.'), 400

    upload_folder = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_folder, exist_ok=True)

    safe_name = secure_filename(file.filename)
    temp_path = os.path.join(upload_folder, f'{uuid.uuid4().hex}_{safe_name}')
    file.save(temp_path)

    try:
        result = extract_bill_data(temp_path)
    finally:
        # Matches the privacy note on 05_upload_bill.html — the
        # image is only used to read the figures, then removed.
        if current_app.config.get('DELETE_UPLOAD_AFTER_OCR', True) and os.path.exists(temp_path):
            os.remove(temp_path)

    # Stored server-side (not just returned to the client) for two
    # reasons: (1) page_routes.py's ocr_pending_required guard on
    # 06_upload_confirm.html checks session['pending_ocr'] — without
    # setting it here, a successful upload would still bounce the
    # user straight back to the upload page; (2) it lets confirm.js
    # fetch the values via GET /bill/pending on page load instead of
    # relying on sessionStorage surviving the navigation.
    session['pending_ocr'] = {
        'extracted':      result['extracted'],
        'ocr_confidence': result['ocr_confidence'],
        'source':         source,
        'filename':       safe_name,
    }

    return jsonify(
        success=True,
        extracted=result['extracted'],
        ocr_confidence=result['ocr_confidence'],
        source=source,
        filename=safe_name,
    )


# ── pending OCR result (for the confirm page to load) ────────
@bill_bp.route('/pending', methods=['GET'])
@api_login_required
def get_pending_ocr():
    pending = session.get('pending_ocr')
    if not pending:
        return jsonify(success=False, message='No pending upload to review. Please upload a bill first.'), 404
    return jsonify(success=True, **pending)


# ── confirm + save ───────────────────────────────────────────
@bill_bp.route('/confirm', methods=['POST'])
@api_login_required
def confirm_bill():
    data = request.get_json(silent=True) or {}

    billing_period = (data.get('billing_period') or '').strip()
    source = data.get('source') if data.get('source') in VALID_SOURCES else 'photo'
    ocr_confidence = data.get('ocr_confidence') if data.get('ocr_confidence') in VALID_CONFIDENCE else None

    units_consumed = data.get('units_consumed')
    if units_consumed is None:
        return jsonify(success=False, message='Units consumed (kWh) is required.'), 400
    try:
        units_consumed = float(units_consumed)
    except (TypeError, ValueError):
        return jsonify(success=False, message='Units consumed must be a number.'), 400

    # 0 is a legitimate value (e.g. a net-metering month fully offset
    # by solar export — see the sample CEB bill this was tested
    # against). Only reject negative or unreasonably large values.
    if units_consumed < 0:
        return jsonify(success=False, message='Units consumed cannot be negative.'), 400
    if units_consumed > MAX_REASONABLE_KWH:
        return jsonify(success=False, message='Units consumed value seems too high. Please check and correct it.'), 400

    bill_amount_lkr = data.get('bill_amount_lkr')
    if bill_amount_lkr is not None and bill_amount_lkr != '':
        try:
            bill_amount_lkr = float(bill_amount_lkr)
        except (TypeError, ValueError):
            return jsonify(success=False, message='Bill amount must be a number.'), 400
        if bill_amount_lkr < 0:
            return jsonify(success=False, message='Bill amount cannot be negative.'), 400
    else:
        bill_amount_lkr = None

    if not billing_period:
        return jsonify(success=False, message='Billing period is required.'), 400

    bill = Bill(
        user_id=session['user_id'],
        billing_period=billing_period,
        units_consumed=units_consumed,
        bill_amount_lkr=bill_amount_lkr,
        source=source,
        ocr_confidence=ocr_confidence,
    )
    db.session.add(bill)
    db.session.commit()

    # Confirmed and saved — the pending upload no longer needs
    # reviewing, and clearing this also means the ocr_pending_required
    # guard will correctly bounce a stale reload of the confirm page
    # back to the upload page rather than re-showing old data.
    session.pop('pending_ocr', None)

    return jsonify(success=True, redirect='/07_dashboard.html')


# ── recent bills ─────────────────────────────────────────────
@bill_bp.route('/', methods=['GET'])
@api_login_required
def list_bills():
    bills = (
        Bill.query.filter_by(user_id=session['user_id'])
        .order_by(Bill.confirmed_at.desc())
        .all()
    )
    return jsonify(success=True, bills=[b.to_dict() for b in bills])
