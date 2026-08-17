# ============================================================
#  database/db.py
#  Shared SQLAlchemy instance. Every model imports `db` from
#  here (not from app.py) to avoid circular imports between
#  app.py, routes/*.py, and models/*.py.
# ============================================================

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def init_db(app):
    """Attach SQLAlchemy to the Flask app. Call once from app.py."""
    db.init_app(app)


def create_all_dev_only(app):
    """
    Convenience helper for local development/testing ONLY.

    database/schema.sql is the source of truth for the real
    database (run it directly with `mysql ... < schema.sql`).
    This just lets db.create_all() build the same tables from
    the SQLAlchemy models for quick local iteration or for the
    SQLite test database defined in TestingConfig, without
    needing a MySQL server running.

    Do not call this against a production database — it can
    silently diverge from schema.sql over time if only one of
    the two is kept up to date.
    """
    with app.app_context():
        db.create_all()
