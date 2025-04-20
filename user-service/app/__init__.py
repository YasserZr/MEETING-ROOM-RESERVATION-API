# app/__init__.py
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS # Import CORS
import os
import logging # Import logging
import sys # Import sys
from dotenv import load_dotenv # dotenv loaded in run.py
from logging.handlers import RotatingFileHandler # Import RotatingFileHandler

# Load environment variables from .env file
load_dotenv()

# Define db instance here
db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)

    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'a_default_secret_key')
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'a_default_jwt_secret_key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    # Initialize extensions
    db.init_app(app) # Use the db defined above
    migrate.init_app(app, db)
    CORS(app) # Enable CORS for all routes

    # Logging configuration
    logging.basicConfig(
        level=logging.DEBUG,
        stream=sys.stdout,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logging.getLogger("oauthlib").setLevel(logging.DEBUG)
    logging.getLogger("requests").setLevel(logging.DEBUG)
    logging.getLogger("urllib3").setLevel(logging.DEBUG)
    logging.getLogger("werkzeug").setLevel(logging.INFO)

    # Reduce verbosity of Kafka logs
    logging.getLogger("kafka").setLevel(logging.WARNING)
    logging.getLogger("kafka.conn").setLevel(logging.WARNING)
    logging.getLogger("kafka.client").setLevel(logging.WARNING)
    logging.getLogger("kafka.metrics").setLevel(logging.WARNING)
    logging.getLogger("kafka.protocol").setLevel(logging.WARNING)

    app.logger.info("Logging configured. Kafka logs set to WARNING level.")

    # Configure logging to a file
    if not app.debug:
        log_file = '/home/hadoop/MEETING-ROOM-RESERVATION-API/user-service/app.log'
        log_dir = os.path.dirname(log_file)

        # Ensure the directory exists
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        file_handler = RotatingFileHandler(log_file, maxBytes=10240, backupCount=10)
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        app.logger.addHandler(file_handler)

    with app.app_context():
        # Import models here AFTER db is initialized with app
        from . import models
        # Import and register blueprints
        from . import routes # Import routes module here

        app.register_blueprint(routes.user_bp, url_prefix='/users') # Register the user blueprint with prefix

        # Start Kafka consumer in a background thread
        from .kafka_consumer import start_kafka_consumer_thread
        start_kafka_consumer_thread(app)

    # Delay the import to avoid circular import issues
    from . import auth

    app.register_blueprint(auth.auth_bp)   # Register the auth blueprint (prefix is defined in auth.py)

    # Delay the import to avoid circular import issues
    from .kafka_consumer import start_kafka_consumer

    # Start Kafka consumer
    start_kafka_consumer(app)

    # Simple health check endpoint
    @app.route('/health')
    def health_check():
        return jsonify({"status": "healthy"}), 200

    return app