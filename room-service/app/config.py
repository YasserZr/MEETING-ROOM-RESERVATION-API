import os

# JWT secret key
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'default_jwt_secret_key')

# Flask secret key
SECRET_KEY = os.getenv('SECRET_KEY', 'default_flask_secret_key')
