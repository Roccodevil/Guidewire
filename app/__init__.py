from flask import Flask
from sqlalchemy import text

from app.config import Config
from app.db_models import db


def _ensure_schema_updates():
    # create_all creates missing tables but does not add new columns to existing ones.
    db.session.execute(
        text("ALTER TABLE delivery_orders ADD COLUMN IF NOT EXISTS distance_km DOUBLE PRECISION")
    )
    db.session.commit()


def create_app():
    app = Flask(__name__, template_folder="../templates")
    app.config.from_object(Config)

    db.init_app(app)

    with app.app_context():
        db.create_all()
        _ensure_schema_updates()

    from app.routes import main_bp

    app.register_blueprint(main_bp)

    return app
