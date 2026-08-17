# ============================================================
#  routes/report_routes.py
#  Powers 10_reports.html — a summary table + per-bill "vs your
#  average" comparison, optionally filtered by calendar year.
#
#  GET /reports/?year=YYYY → summary stats + bill list for that
#                             year (year omitted = all-time).
#
#  Note: the actual CSV/PDF "Download report" button is handled
#  entirely client-side (Blob download / window.print()) against
#  whatever this endpoint already returned — there's no separate
#  server-side export endpoint. This route's only job is to
#  supply the data.
#
#  Unlike predict_routes.py's billing_period text matching,
#  filtering by year here uses Bill.confirmed_at (a real
#  DateTime column), so it's reliable regardless of how
#  billing_period text happens to be formatted.
# ============================================================

from flask import Blueprint, jsonify, request, session

from models import Bill
from utils.login_utils import api_login_required

report_bp = Blueprint('report', __name__)


@report_bp.route('/', methods=['GET'])
@api_login_required
def get_report():
    user_id = session['user_id']
    all_bills = (
        Bill.query.filter_by(user_id=user_id)
        .order_by(Bill.confirmed_at.desc())
        .all()
    )

    year_param = request.args.get('year')
    if year_param:
        try:
            year = int(year_param)
        except ValueError:
            return jsonify(success=False, message='Invalid year.'), 400
        bills = [b for b in all_bills if b.confirmed_at.year == year]
    else:
        bills = all_bills

    summary = _build_summary(bills)
    avg_kwh = summary['monthly_avg_kwh']

    return jsonify(
        success=True,
        summary=summary,
        bills=_bills_with_vs_avg(bills, avg_kwh),
    )


# ── helpers ──────────────────────────────────────────────────
def _build_summary(bills):
    if not bills:
        return {
            'total_kwh': 0, 'total_lkr': 0, 'monthly_avg_kwh': None,
            'peak_month': None, 'bills_confirmed': 0,
        }

    kwh_values = [float(b.units_consumed) for b in bills]
    lkr_values = [float(b.bill_amount_lkr) for b in bills if b.bill_amount_lkr is not None]

    total_kwh = round(sum(kwh_values), 2)
    peak_bill = max(bills, key=lambda b: float(b.units_consumed))

    return {
        'total_kwh':        total_kwh,
        'total_lkr':        round(sum(lkr_values), 2) if lkr_values else None,
        'monthly_avg_kwh':  round(total_kwh / len(bills), 1),
        'peak_month':       peak_bill.billing_period,
        'bills_confirmed':  len(bills),
    }


def _bills_with_vs_avg(bills, avg_kwh):
    """
    Each row's "vs average" compares against the average of ALL
    bills in the current (possibly year-filtered) view — including
    itself — matching how the frontend prototype computed this
    (AppData.personalAverageKwh(false) equivalent). This answers
    "how does this bill compare to my overall pattern", a
    different question from dashboard_routes.py's vs_avg_percent
    (which deliberately excludes the latest bill).
    """
    rows = []
    for b in bills:
        row = b.to_dict()
        kwh = float(b.units_consumed)
        row['vs_avg_pct'] = round(((kwh - avg_kwh) / avg_kwh) * 100) if avg_kwh else None
        rows.append(row)
    return rows
