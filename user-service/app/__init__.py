from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from dotenv import load_dotenv
import os

db = SQLAlchemy()
jwt = JWTManager()

def create_app():
    load_dotenv()
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
    app.config['JWT_SECRET_KEY'] = os.getenv("JWT_SECRET_KEY")

    db.init_app(app)
    jwt.init_app(app)
    CORS(app)

    from .routes import user_bp
    app.register_blueprint(user_bp)

    return app
