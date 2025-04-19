# app/__init__.py
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS # Import CORS
import os
import logging # Import logging
from dotenv import load_dotenv # dotenv loaded in run.py

#Import Kafka consumer start function (create this file next)
#from .kafka_consumer import start_consumer_thread

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

    # Initialize extensions
    db.init_app(app) # Use the db defined above
    migrate.init_app(app, db)
    CORS(app) # Enable CORS for all routes

    # Configure logging
    logging.basicConfig(level=logging.INFO)
    app.logger.setLevel(logging.INFO)
    app.logger.info("User service application created successfully.")

    with app.app_context():
        # Import models here AFTER db is initialized with app
        from . import models
        # Import and register blueprints
        from . import routes # Import routes module here
        from . import auth   # Import auth module here

        app.register_blueprint(routes.user_bp, url_prefix='/users') # Register the user blueprint with prefix
        app.register_blueprint(auth.auth_bp)   # Register the auth blueprint (prefix is defined in auth.py)

        # Create database tables if they don't exist
        # Consider using Flask-Migrate for production environments
        # db.create_all() # Uncomment if you want Flask to create tables on startup

        # Start Kafka consumer in a background thread
        from .kafka_consumer import start_kafka_consumer_thread
        start_kafka_consumer_thread(app)

    # Simple health check endpoint
    @app.route('/health')
    def health_check():
        return jsonify({"status": "healthy"}), 200

    return app