# ============================================================
#  models/__init__.py
#  Re-exports every model so app.py / routes can do:
#     from models import User, Otp, Appliance, Bill, ...
#  instead of importing from each submodule individually. Also
#  ensures every model class is registered on `db.metadata`
#  before db.create_all() or Flask-Migrate runs — SQLAlchemy
#  only picks up models that have actually been imported.
# ============================================================

from models.user import User, LoginLog
from models.otp import Otp
from models.appliance import Appliance, ApplianceProfile, APPLIANCE_CATALOG, HOUSEHOLD_SIZES
from models.bill import Bill, Prediction

__all__ = [
    'User', 'LoginLog',
    'Otp',
    'Appliance', 'ApplianceProfile', 'APPLIANCE_CATALOG', 'HOUSEHOLD_SIZES',
    'Bill', 'Prediction',
]
