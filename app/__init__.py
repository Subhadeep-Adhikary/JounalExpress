import os
from flask import Flask
from .extensions import db


def load_dotenv(dotenv_path=None):
    """Load simple KEY=VALUE entries from an optional environment file."""
    path = dotenv_path or os.path.join(os.getcwd(), ".env")
    if not os.path.isfile(path):
        return False

    with open(path, encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if key:
                os.environ.setdefault(key, value.strip().strip('"').strip("'"))
    return True

# Prefer a project-level .env, while also supporting the app-local file used by
# existing installations of this project.
load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


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
