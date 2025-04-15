# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from .models import db
from .routes import user_bp

def create_app():
    app = Flask(__name__)

    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI="postgresql://postgres:postgres@postgres-userdb:5432/users",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY="super-secret"  # you can load from .env later
    )

    db.init_app(app)
    Migrate(app, db)

    app.register_blueprint(user_bp)

    return app
