from flask import Flask

from app.config import Config
from app.db_models import db


def create_app():
    app = Flask(__name__, template_folder="../templates")
    app.config.from_object(Config)

    db.init_app(app)

    with app.app_context():
        db.create_all()

    from app.routes import main_bp

    app.register_blueprint(main_bp)

    return app
