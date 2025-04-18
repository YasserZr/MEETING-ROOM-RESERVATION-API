# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS # Import CORS
from .models import db
from .routes import user_bp
from .auth import auth_bp # Import auth_bp
import os
import logging # Import logging
# from dotenv import load_dotenv # dotenv loaded in run.py

# Import Kafka consumer start function (create this file next)
# from .kafka_consumer import start_consumer_thread

# load_dotenv() # Load environment variables from .env file

def create_app():
    app = Flask(__name__)
    CORS(app) # Enable CORS for all routes

    # Configure logging
    logging.basicConfig(level=logging.INFO)
    app.logger.setLevel(logging.INFO) # Ensure Flask logger level is set

    # Load configuration from environment variables
    app.config.from_mapping(
        # Use DATABASE_URL from environment for flexibility
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/users_db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        # Flask's SECRET_KEY for session management, flash messages etc.
        SECRET_KEY=os.getenv("SECRET_KEY", "a_default_secret_key_for_dev"), # Provide a default for safety
        # JWT Secret Key
        JWT_SECRET_KEY=os.getenv("JWT_SECRET_KEY", "a_default_jwt_secret_key_for_dev"), # Also load JWT key here if needed globally

        # Google OAuth Config (can also be set directly in make_google_blueprint)
        # Ensure these are set in your environment (.env file or system env)
        GOOGLE_CLIENT_ID=os.getenv("GOOGLE_CLIENT_ID"),
        GOOGLE_CLIENT_SECRET=os.getenv("GOOGLE_CLIENT_SECRET"),

        # Kafka Configuration
        KAFKA_BOOTSTRAP_SERVERS=os.getenv("KAFKA_BOOTSTRAP_SERVERS"),
        KAFKA_RESERVATIONS_TOPIC=os.getenv("KAFKA_RESERVATIONS_TOPIC"),
        KAFKA_CONSUMER_GROUP="user-service-group", # Example consumer group ID
    )

    db.init_app(app)
    Migrate(app, db)

    app.register_blueprint(user_bp, url_prefix='/users') # Add prefix to user routes
    app.register_blueprint(auth_bp) # Register auth blueprint (prefix defined in auth.py)

    # Simple health check endpoint
    @app.route('/health')
    def health():
        return {"status": "healthy"}

    # Start Kafka consumer in a background thread AFTER app context is available
    # but before running the app. Use app.before_first_request or similar,
    # or manage thread lifecycle carefully. Starting in run.py might be simpler.
    # with app.app_context():
    #    start_consumer_thread(app)

    app.logger.info("User service application created successfully.")

    return app
