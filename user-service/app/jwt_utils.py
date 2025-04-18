import jwt
import datetime
import os
from flask import current_app # Import current_app to access config

# Function to generate JWT token
def generate_token(user_id):
    try:
        payload = {
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1), # Token expiration time
            'iat': datetime.datetime.utcnow(),
            'sub': user_id
        }
        # Use JWT_SECRET_KEY from Flask app config or environment variable
        secret_key = current_app.config.get('JWT_SECRET_KEY') or os.getenv('JWT_SECRET_KEY')
        if not secret_key:
            raise ValueError("JWT_SECRET_KEY is not configured")

        return jwt.encode(
            payload,
            secret_key,
            algorithm='HS256'
        )
    except Exception as e:
        # Log the exception e
        return None

# Function to decode JWT token
def decode_token(token):
    try:
        # Use JWT_SECRET_KEY from Flask app config or environment variable
        secret_key = current_app.config.get('JWT_SECRET_KEY') or os.getenv('JWT_SECRET_KEY')
        if not secret_key:
            raise ValueError("JWT_SECRET_KEY is not configured")

        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        return payload['sub'] # Return user_id (subject)
    except jwt.ExpiredSignatureError:
        # Handle expired token
        return None
    except jwt.InvalidTokenError:
        # Handle invalid token
        return None
    except Exception as e:
        # Log the exception e
        return None

# ... potentially other utility functions ...
