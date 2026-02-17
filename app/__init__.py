from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config
import os

db = SQLAlchemy()
login_manager = LoginManager()


@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    upload_path = os.path.join(app.root_path, "uploads")
    os.makedirs(upload_path, exist_ok=True)
    app.config["UPLOAD_FOLDER"] = upload_path

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    from app.routes import main
    from app.auth import auth
    from app.leaderboard import leaderboard

    app.register_blueprint(main)
    app.register_blueprint(auth)
    app.register_blueprint(leaderboard)

    with app.app_context():
        db.drop_all()
        db.create_all()

    return app

