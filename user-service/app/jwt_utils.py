import jwt
import datetime
import os
from flask import current_app, request, jsonify # Import current_app to access config
from functools import wraps
from .config import JWT_SECRET_KEY  # Ensure the secret key is imported

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

def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"message": "Token is missing"}), 401

        try:
            token = token.split(" ")[1]  # Extract the token from "Bearer <token>"
            decoded_token = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
            user_id = decoded_token.get("sub")
            if not user_id:
                return jsonify({"message": "Invalid token"}), 401

            kwargs['user_id'] = user_id
            kwargs['token'] = token
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"message": "Invalid token"}), 401

        return f(*args, **kwargs)
    return decorated_function

# ... potentially other utility functions ...
