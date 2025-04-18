# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS # Import CORS
from .models import db
from .routes import user_bp
from .auth import auth_bp # Import auth_bp
import os
# from dotenv import load_dotenv # dotenv loaded in run.py

# load_dotenv() # Load environment variables from .env file

def create_app():
    app = Flask(__name__)
    CORS(app) # Enable CORS for all routes

    # Load configuration from environment variables
    app.config.from_mapping(
        # Use DATABASE_URL from environment for flexibility
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/users_db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        # Flask's SECRET_KEY for session management, flash messages etc.
        SECRET_KEY=os.getenv("SECRET_KEY", "a-different-super-secret"),
        # JWT Secret Key
        JWT_SECRET_KEY=os.getenv("JWT_SECRET_KEY", "super-secret-key"),

        # Google OAuth Config (can also be set directly in make_google_blueprint)
        # Ensure these are set in your environment (.env file or system env)
        GOOGLE_CLIENT_ID=os.getenv("GOOGLE_CLIENT_ID"),
        GOOGLE_CLIENT_SECRET=os.getenv("GOOGLE_CLIENT_SECRET"),
    )

    db.init_app(app)
    Migrate(app, db)

    app.register_blueprint(user_bp, url_prefix='/users') # Add prefix to user routes
    app.register_blueprint(auth_bp) # Register auth blueprint (prefix defined in auth.py)

    # Simple health check endpoint
    @app.route('/health')
    def health():
        return {"status": "healthy"}

    return app
