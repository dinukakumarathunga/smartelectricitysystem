# ============================================================
#  models/appliance.py
#  Matches the `appliances` and `appliance_profile` tables in
#  schema.sql. Powers 04_appliance_onboarding.html (flow step 2)
#  and 11_appliance_profile.html.
# ============================================================

from datetime import datetime, timezone

from database.db import db

# Keep this in sync with APPLIANCE_CATALOG in static/js/app-data.js —
# it's the fixed list of tiles shown on the onboarding/profile grid.
APPLIANCE_CATALOG = [
    'Air conditioner', 'Water heater', 'Electric stove', 'Television',
    'Washing machine', 'Refrigerator', 'Electric water pump', 'Home office setup'
]

HOUSEHOLD_SIZES = ('1-2', '3-4', '5+')


class ApplianceProfile(db.Model):
    __tablename__ = 'appliance_profile'

    user_id        = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    household_size = db.Column(db.Enum(*HOUSEHOLD_SIZES, name='household_size'))
    updated_at     = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def to_dict(self):
        return {
            'household_size': self.household_size,
            'updated_at':     self.updated_at.isoformat(),
        }


class Appliance(db.Model):
    __tablename__ = 'appliances'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'name', name='uq_appliances_user_name'),
    )

    id      = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    name    = db.Column(db.String(60), nullable=False)
    owned   = db.Column(db.Boolean, nullable=False, default=False)

    @classmethod
    def seed_catalog_for_user(cls, user_id):
        """
        Creates one row per APPLIANCE_CATALOG entry for a brand
        new user, all unowned by default — mirrors how app-data.js
        seeds APPLIANCE_CATALOG.map(name => ({name, owned:false}))
        the first time getAppliances() is called.
        """
        rows = [cls(user_id=user_id, name=name, owned=False) for name in APPLIANCE_CATALOG]
        db.session.bulk_save_objects(rows)
        db.session.commit()

    def to_dict(self):
        return {'name': self.name, 'owned': self.owned}

    def __repr__(self):
        return f'<Appliance {self.name} owned={self.owned}>'
