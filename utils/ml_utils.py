# ============================================================
#  utils/ml_utils.py
#  Prediction logic shared by dashboard_routes.py (the "predicted
#  next month" stat card) and predict_routes.py (the full AI
#  prediction page).
#
#  predict_next_month() is a direct Python port of the simple
#  linear-regression approach the frontend prototype used
#  (AppData.predict() in the old app-data.js) — same math, same
#  thresholds — so backend and the prototype agree while there's
#  no trained model yet.
#
#  load_pretrained_model() is a hook for the 9 .pkl files this
#  project's file structure expects from a Colab notebook. Their
#  exact input/output contract isn't known yet, so nothing calls
#  this function until that's defined — predict_next_month() is
#  what's actually used today.
# ============================================================

import os

MIN_MONTHS_FOR_PREDICTION = 2


def linear_regression(xs, ys):
    """Ordinary least squares for a single feature. Returns (slope, intercept)."""
    n = len(xs)
    sum_x = sum(xs)
    sum_y = sum(ys)
    sum_xy = sum(x * y for x, y in zip(xs, ys))
    sum_xx = sum(x * x for x in xs)
    denominator = (n * sum_xx - sum_x * sum_x) or 1   # avoid div-by-zero when all xs are equal
    slope = (n * sum_xy - sum_x * sum_y) / denominator
    intercept = (sum_y - slope * sum_x) / n
    return slope, intercept


def predict_next_month(bills_newest_first, min_months=MIN_MONTHS_FOR_PREDICTION):
    """
    bills_newest_first: list of Bill-like objects (needs .units_consumed,
    .billing_period, .bill_amount_lkr), ordered newest-first — i.e.
    exactly what Bill.query.order_by(Bill.confirmed_at.desc()).all()
    returns. Internally reversed to oldest-first for the regression.
    """
    bills = list(reversed(bills_newest_first))
    n = len(bills)

    if n < min_months:
        message = (
            'Upload at least one bill to generate predictions.' if n == 0
            else f'Upload {min_months - n} more bill(s) to enable predictions — '
                 f'at least {min_months} confirmed months are needed.'
        )
        return {'success': False, 'message': message}

    ys = [float(b.units_consumed) for b in bills]
    xs = list(range(n))

    slope, intercept = linear_regression(xs, ys)
    predicted_kwh = max(0, round(slope * n + intercept))

    avg = sum(ys) / n
    latest_kwh = ys[-1]
    latest = bills[-1]
    high_usage = latest_kwh > avg * 1.1

    predicted_lkr = None
    if getattr(latest, 'bill_amount_lkr', None) and latest_kwh:
        predicted_lkr = round((float(latest.bill_amount_lkr) / latest_kwh) * predicted_kwh)

    peak_index = ys.index(max(ys))
    peak_month = bills[peak_index].billing_period

    trend_data = [
        {'period': b.billing_period, 'actual': ys[i], 'predicted': predicted_kwh if i == n - 1 else None}
        for i, b in enumerate(bills)
    ]

    return {
        'success':          True,
        'predicted_kwh':    predicted_kwh,
        'predicted_lkr':    predicted_lkr,
        'months_of_data':   n,
        'personal_avg_kwh': round(avg, 1),
        'peak_month':       peak_month,
        'confidence_pct':   min(90, 40 + n * 10),
        'high_usage_alert': 'Yes' if high_usage else 'No',
        'trend_data':       trend_data,
    }


def load_pretrained_model(filename):
    """
    Loads a .pkl file from ML_MODELS_DIR if it exists. Returns None
    if not found — callers should fall back to predict_next_month()
    rather than erroring, since the trained models aren't wired in
    yet. joblib is imported lazily here (not at module level) so
    this file can still be imported in environments where joblib
    isn't installed and only the regression path is being used.
    """
    from flask import current_app

    path = os.path.join(current_app.config['ML_MODELS_DIR'], filename)
    if not os.path.exists(path):
        return None

    import joblib
    return joblib.load(path)
