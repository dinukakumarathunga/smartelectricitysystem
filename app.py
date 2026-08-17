# ============================================================
#  app.py
#  Flask application factory. Run with:
#     flask run          (reads FLASK_APP=app.py from .env)
#  or:
#     python app.py
#
#  All blueprints are wired up: page rendering (page_routes.py)
#  plus one blueprint per flow step — auth, appliances, bill
#  upload/confirm, dashboard, AI prediction, reports, and
#  profile/security. See each routes/*.py file for what it does.
# ============================================================

import os

from flask import Flask
from flask_wtf import CSRFProtect

from config.config import get_config
from database.db import init_db
from page_routes import page_bp

csrf = CSRFProtect()


def create_app():
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.config.from_object(get_config())

    init_db(app)
    csrf.init_app(app)

    # uploads/temp/ is where bill images sit only long enough for
    # OCR to run (see DELETE_UPLOAD_AFTER_OCR in config.py) —
    # create it if this is a fresh checkout.
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['SAMPLE_BILLS_FOLDER'], exist_ok=True)

    app.register_blueprint(page_bp)

    from routes.auth_routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from routes.appliance_routes import appliance_bp
    app.register_blueprint(appliance_bp, url_prefix='/appliances')

    from routes.bill_routes import bill_bp
    app.register_blueprint(bill_bp, url_prefix='/bill')

    from routes.dashboard_routes import dashboard_bp
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')

    from routes.predict_routes import predict_bp
    app.register_blueprint(predict_bp, url_prefix='/predict')

    from routes.report_routes import report_bp
    app.register_blueprint(report_bp, url_prefix='/reports')

    from routes.profile_routes import profile_bp
    app.register_blueprint(profile_bp, url_prefix='/profile')

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=app.config.get('DEBUG', False))
