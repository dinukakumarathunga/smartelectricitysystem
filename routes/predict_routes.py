# ============================================================
#  routes/predict_routes.py
#  Flow step 5: full AI prediction page (08_ai_prediction.html).
#  Reuses predict_next_month() from ml_utils.py (same regression
#  dashboard_routes.py uses), and adds two things the dashboard's
#  quick preview doesn't need:
#    - a "next_month" label (best-effort, parsed from the latest
#      billing_period text)
#    - an accuracy_log: once a predicted month's real bill later
#      gets confirmed, this shows how close the prediction was
#
#  GET /predict/ → everything the prediction page needs in one call.
# ============================================================

import re
from datetime import datetime

from flask import Blueprint, jsonify, session

from database.db import db
from models import Bill, Prediction
from utils.login_utils import api_login_required
from utils.ml_utils import predict_next_month

predict_bp = Blueprint('predict', __name__)

ACCURACY_LOG_LIMIT = 6


@predict_bp.route('/', methods=['GET'])
@api_login_required
def get_prediction():
    user_id = session['user_id']
    bills = (
        Bill.query.filter_by(user_id=user_id)
        .order_by(Bill.confirmed_at.desc())
        .all()
    )  # newest first

    # Before computing anything new, see if any earlier prediction's
    # target month has since been confirmed as a real bill — if so,
    # score that prediction now so the accuracy log stays current.
    _backfill_prediction_accuracy(user_id, bills)

    prediction = predict_next_month(bills)
    if not prediction['success']:
        return jsonify(success=False, message=prediction['message'])

    next_month = _next_month_label(bills[0].billing_period) if bills else None
    _record_prediction_if_new(user_id, next_month or 'next billing period', prediction['predicted_kwh'])

    return jsonify(
        success=True,
        predicted_kwh=prediction['predicted_kwh'],
        predicted_lkr=prediction['predicted_lkr'],
        next_month=next_month,
        high_usage_alert=prediction['high_usage_alert'],
        confidence_pct=prediction['confidence_pct'],
        months_of_data=prediction['months_of_data'],
        personal_avg_kwh=prediction['personal_avg_kwh'],
        peak_month=prediction['peak_month'],
        trend_data=prediction['trend_data'],
        accuracy_log=_get_accuracy_log(user_id),
    )


# ── helpers ──────────────────────────────────────────────────
def _record_prediction_if_new(user_id, for_period, predicted_kwh):
    """One Prediction row per (user, for_period) — repeat GETs for
    the same target month don't pile up duplicate rows."""
    existing = Prediction.query.filter_by(user_id=user_id, for_period=for_period).first()
    if existing:
        return existing
    pred = Prediction(user_id=user_id, for_period=for_period, predicted_kwh=predicted_kwh)
    db.session.add(pred)
    db.session.commit()
    return pred


def _backfill_prediction_accuracy(user_id, bills):
    """
    Best-effort match: an earlier prediction's for_period is plain
    text (e.g. "Aug 2024"), matched against a since-confirmed bill's
    billing_period text. This only works when formatting stays
    consistent between when the prediction was made and when the
    real bill was confirmed — billing_period is free text (OCR or
    user-edited), so this is a known limitation, not a bug: it will
    simply fail to match (and quietly skip scoring) rather than
    scoring something incorrectly.
    """
    unmatched = [p for p in Prediction.query.filter_by(user_id=user_id).all() if p.actual_bill_id is None]
    if not unmatched:
        return

    bills_by_period = {b.billing_period: b for b in bills if b.billing_period}

    for pred in unmatched:
        matching_bill = bills_by_period.get(pred.for_period)
        if matching_bill:
            pred.actual_bill_id = matching_bill.id
            db.session.commit()
            pred.compute_accuracy(actual_bill=matching_bill)


def _get_accuracy_log(user_id):
    rows = Prediction.query.filter_by(user_id=user_id).all()
    matched = [r for r in rows if r.actual_bill_id is not None]
    matched.sort(key=lambda r: r.created_at, reverse=True)
    return [r.to_dict() for r in matched[:ACCURACY_LOG_LIMIT]]


def _next_month_label(billing_period_text):
    """
    Best-effort: finds the last "<Month> <Year>" token in the
    billing period text (the end of the range) and returns the
    following calendar month as "<Mon> <Year>". Returns None if
    nothing parseable is found — the frontend falls back to a
    generic "next billing period" label in that case.
    """
    if not billing_period_text:
        return None

    matches = re.findall(r'([A-Za-z]{3,9})\s+(\d{4})', billing_period_text)
    if not matches:
        return None

    month_str, year_str = matches[-1]
    parsed = None
    for fmt in ('%b %Y', '%B %Y'):
        try:
            parsed = datetime.strptime(f'{month_str} {year_str}', fmt)
            break
        except ValueError:
            continue
    if parsed is None:
        return None

    year, month = parsed.year, parsed.month + 1
    if month > 12:
        month = 1
        year += 1
    return datetime(year, month, 1).strftime('%b %Y')
