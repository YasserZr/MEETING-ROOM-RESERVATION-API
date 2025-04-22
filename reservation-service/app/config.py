import os

# JWT secret key
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'default_jwt_secret_key')

# Flask secret key
SECRET_KEY = os.getenv('SECRET_KEY', 'default_flask_secret_key')

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
KAFKA_RESERVATIONS_TOPIC = os.getenv('KAFKA_RESERVATIONS_TOPIC', 'reservations-topic')

# User service URL
USER_SERVICE_URL = os.getenv('USER_SERVICE_URL', 'http://user-service:5000')

# Room service URL
ROOM_SERVICE_URL = os.getenv('ROOM_SERVICE_URL', 'http://room-service:5001')
