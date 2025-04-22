from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from .models import db
from .routes import reservation_bp
import os
import logging # Import logging

# Import Kafka Producer (create this file next)
# from .kafka_producer import init_kafka_producer

def create_app():
    app = Flask(__name__)
    CORS(app) # Enable CORS for all routes

    # Load configuration from environment variables
    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "postgresql://postgres:postgres@reservation-db:5432/reservations_db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY=os.getenv("SECRET_KEY", "yet-another-super-secret"),
        JWT_SECRET_KEY=os.getenv("JWT_SECRET_KEY", "super-secret-key"), # Use the same JWT key
        # Kafka Configuration
        KAFKA_BOOTSTRAP_SERVERS=os.getenv("KAFKA_BOOTSTRAP_SERVERS"),
        KAFKA_RESERVATIONS_TOPIC=os.getenv("KAFKA_RESERVATIONS_TOPIC"),
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

    # Initialize Kafka Producer (implementation in kafka_producer.py)
    # init_kafka_producer(app) # We will initialize producer on demand in routes for simplicity now

    db.init_app(app)
    Migrate(app, db)

    app.register_blueprint(reservation_bp, url_prefix='/reservations') # Add prefix

    # Simple health check endpoint
    @app.route('/health')
    def health():
        # Add Kafka connection check?
        # try:
        #    get_kafka_producer().bootstrap_connected()
        #    kafka_status = "connected"
        # except Exception:
        #    kafka_status = "disconnected"
        return {"status": "healthy"} #, "kafka": kafka_status}

    app.logger.info({"message": "Reservation service application created successfully", "service": "reservation-service"})

    return app
