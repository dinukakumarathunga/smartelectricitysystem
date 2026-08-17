# ============================================================
#  models/bill.py
#  Matches the `bills` and `predictions` tables in schema.sql.
#  Powers the upload/confirm flow (steps 3-4), the dashboard,
#  reports, and AI prediction pages (step 5).
# ============================================================

from datetime import datetime, timezone

from database.db import db


class Bill(db.Model):
    __tablename__ = 'bills'

    id              = db.Column(db.Integer, primary_key=True)
    user_id         = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    billing_period  = db.Column(db.String(60))
    # NOTE: units_consumed of 0 is a valid, real value (e.g. a
    # net-metering month fully offset by solar export — see the
    # sample CEB bill this project was tested against). Don't add
    # a "must be positive" validator anywhere in the route layer;
    # only reject negative or missing values. This bit us once
    # already in confirm.js's original validation — see that
    # file's history.
    units_consumed  = db.Column(db.Numeric(10, 2), nullable=False)
    units_exported  = db.Column(db.Numeric(10, 2))
    bill_amount_lkr = db.Column(db.Numeric(12, 2))
    source          = db.Column(db.Enum('photo', 'sms', name='bill_source'), nullable=False, default='photo')
    ocr_confidence  = db.Column(db.Enum('High', 'Medium', 'Low', name='ocr_confidence'))
    image_path      = db.Column(db.String(255))
    confirmed_at    = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self):
        return {
            'id':              self.id,
            'billing_period':  self.billing_period,
            'units_consumed':  float(self.units_consumed),
            'units_exported':  float(self.units_exported) if self.units_exported is not None else None,
            'bill_amount_lkr': float(self.bill_amount_lkr) if self.bill_amount_lkr is not None else None,
            'source':          self.source,
            'ocr_confidence':  self.ocr_confidence,
            'confirmed_at':    self.confirmed_at.isoformat(),
        }

    def __repr__(self):
        return f'<Bill {self.billing_period} {self.units_consumed}kWh>'


class Prediction(db.Model):
    __tablename__ = 'predictions'

    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    for_period     = db.Column(db.String(60), nullable=False)
    predicted_kwh  = db.Column(db.Numeric(10, 2), nullable=False)
    actual_bill_id = db.Column(db.Integer, db.ForeignKey('bills.id', ondelete='SET NULL'))
    accuracy_pct   = db.Column(db.Numeric(5, 2))
    created_at     = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    actual_bill = db.relationship('Bill', foreign_keys=[actual_bill_id])

    def compute_accuracy(self, actual_bill=None):
        """
        Call once the real bill for for_period has been confirmed,
        to fill in accuracy_pct. This is what lets
        08_ai_prediction.html show a real "model accuracy so far"
        figure instead of an untracked placeholder.

        Pass actual_bill explicitly when you've just set
        self.actual_bill_id in the same request (see
        predict_routes.py's backfill logic) — relying on the
        self.actual_bill relationship immediately after setting the
        FK can require a session refresh first; passing the object
        directly sidesteps that.
        """
        bill = actual_bill or self.actual_bill
        if bill is None:
            return None
        actual = float(bill.units_consumed)
        predicted = float(self.predicted_kwh)
        if actual == 0:
            # Avoid divide-by-zero for a net-metering month; treat
            # an exact match as 100% and anything else as 0%.
            self.accuracy_pct = 100.0 if predicted == 0 else 0.0
        else:
            error_pct = abs(actual - predicted) / actual * 100
            self.accuracy_pct = max(0.0, round(100 - error_pct, 2))
        db.session.commit()
        return self.accuracy_pct

    def to_dict(self):
        return {
            'for_period':     self.for_period,
            'predicted_kwh':  float(self.predicted_kwh),
            'actual_kwh':     float(self.actual_bill.units_consumed) if self.actual_bill else None,
            'accuracy_pct':   float(self.accuracy_pct) if self.accuracy_pct is not None else None,
        }

    def __repr__(self):
        return f'<Prediction {self.for_period} {self.predicted_kwh}kWh>'
