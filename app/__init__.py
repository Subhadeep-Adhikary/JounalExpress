import os
from flask import Flask
from dotenv import load_dotenv
from .extensions import db

load_dotenv()


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "My_secret_key")
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "change-this-in-production")
    app.config["MONGO_URI"] = os.getenv("MONGO_URI", "mongodb://localhost:27017/JournalExpress")
    app.config['MONGO_TRACK_MODIFICATION'] = False

    db.init_app(app)

    from app.models import init_db_collections
    init_db_collections()

    from app.routes.auth import auth_bp
    from app.routes.connection import connection_bp
    from app.routes.tasks import tasks_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(connection_bp)
    app.register_blueprint(tasks_bp)

    return app

