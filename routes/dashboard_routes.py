# ============================================================
#  routes/dashboard_routes.py
#  Flow step 4: shows the analysed data from confirmed bills —
#  stat cards, chart, recent uploads, alert banner on
#  07_dashboard.html.
#
#  GET /dashboard/ → everything the dashboard page needs in one
#                     call, matching what the old dashboard.js
#                     prototype already expected from this route.
# ============================================================

from flask import Blueprint, jsonify, session

from models import Bill
from utils.login_utils import api_login_required
from utils.ml_utils import predict_next_month

dashboard_bp = Blueprint('dashboard', __name__)

CHART_MONTHS = 6           # how many months the bar chart shows
HIGH_USAGE_MARGIN = 1.1    # >10% above the prior average counts as "high usage"


@dashboard_bp.route('/', methods=['GET'])
@api_login_required
def get_dashboard():
    bills = (
        Bill.query.filter_by(user_id=session['user_id'])
        .order_by(Bill.confirmed_at.desc())
        .all()
    )  # newest first

    if not bills:
        return jsonify(
            success=True,
            current_bill=None,
            vs_avg_percent=None,
            chart_data=[],
            recent_bills=[],
        )

    latest = bills[0]
    latest_kwh = float(latest.units_consumed)

    # "vs your average" deliberately excludes the latest bill itself —
    # this answers "how does this month compare to your history",
    # which is a different question from predict_next_month()'s
    # internal average (which includes every month, for regression
    # stability). Two averages, two purposes — see ml_utils.py.
    prior_kwh = [float(b.units_consumed) for b in bills[1:]]
    prior_avg = sum(prior_kwh) / len(prior_kwh) if prior_kwh else None

    vs_avg_percent = round(((latest_kwh - prior_avg) / prior_avg) * 100) if prior_avg else None
    high_usage_alert = 'Yes' if (prior_avg is not None and latest_kwh > prior_avg * HIGH_USAGE_MARGIN) else 'No'

    prediction = predict_next_month(bills)

    ordered_for_chart = list(reversed(bills[:CHART_MONTHS]))   # oldest → newest, capped
    chart_data = [{'period': b.billing_period, 'kwh': float(b.units_consumed)} for b in ordered_for_chart]

    current_bill = {
        'units_consumed':     latest_kwh,
        'bill_amount_lkr':    float(latest.bill_amount_lkr) if latest.bill_amount_lkr is not None else None,
        'billing_period':     latest.billing_period,
        'predicted_next_kwh': prediction.get('predicted_kwh') if prediction['success'] else None,
        'high_usage_alert':   high_usage_alert,
    }

    return jsonify(
        success=True,
        current_bill=current_bill,
        vs_avg_percent=vs_avg_percent,
        personal_avg_kwh=round(prior_avg, 1) if prior_avg is not None else None,
        chart_data=chart_data,
        recent_bills=[b.to_dict() for b in bills[:CHART_MONTHS]],
    )
