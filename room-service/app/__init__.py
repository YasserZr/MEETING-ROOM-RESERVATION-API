from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from .models import db
from .routes import room_bp
import os
import logging # Import logging

def create_app():
    app = Flask(__name__)
    CORS(app) # Enable CORS for all routes

    # Load configuration from environment variables
    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "postgresql://postgres:postgres@room-db:5432/rooms_db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY=os.getenv("SECRET_KEY", "another-super-secret"),
        JWT_SECRET_KEY=os.getenv("JWT_SECRET_KEY", "super-secret-key"), # Use the same JWT key as user-service
        RESERVATION_SERVICE_URL=os.getenv("RESERVATION_SERVICE_URL", "http://reservation-service:5002") # Add this line
    )

    # Setup structured logging
    from .config import setup_logging
    logger = setup_logging()
    app.logger.handlers = []
    for handler in logger.handlers:
        app.logger.addHandler(handler)
    app.logger.setLevel(logger.level)

    # Reduce verbosity of third-party logs
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)

    db.init_app(app)
    Migrate(app, db)

    app.register_blueprint(room_bp, url_prefix='/rooms') # Add prefix

    # Simple health check endpoint
    @app.route('/health')
    def health():
        # Add database connectivity check?
        return {"status": "healthy"}

    app.logger.info({"message": "Room service application created successfully", "service": "room-service"})

    return app
