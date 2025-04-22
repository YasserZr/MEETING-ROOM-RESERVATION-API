import jwt
from datetime import datetime, timedelta
from flask import current_app, jsonify, request
import requests
import os
from functools import wraps  # Add this import

# Define JWT secret key directly instead of importing
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'default_jwt_secret_key')

# Function to generate JWT token
def generate_token(user_id):
    try:
        payload = {
            'exp': datetime.utcnow() + timedelta(days=1), # Token expiration time
            'iat': datetime.utcnow(),
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
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
        return payload['sub'] # Return user_id
    except jwt.ExpiredSignatureError:
        current_app.logger.warning("Token expired.")
        return None
    except jwt.InvalidTokenError:
        current_app.logger.warning("Invalid token.")
        return None

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get("Authorization")
        if auth_header:
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({"message": "Bearer token malformed"}), 401

        if not token:
            return jsonify({"message": "Token is missing"}), 401

        user_id = decode_token(token)
        if not user_id:
            return jsonify({"message": "Token is invalid or expired"}), 401

        # Pass user_id and token to the decorated function
        return f(user_id, token, *args, **kwargs)

    return decorated

# Function to fetch user details (optional, could be used for validation)
def get_user_details(user_id, token):
    user_service_url = os.getenv("USER_SERVICE_URL", "http://user-service:5000")
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{user_service_url}/users/me", headers=headers)
        response.raise_for_status()
        details = response.json()
        # Ensure the ID from the token matches the ID returned by the service
        if details.get('id') == user_id:
            return details
        else:
            current_app.logger.error(f"User ID mismatch: token({user_id}) != service({details.get('id')})")
            return None
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Failed to fetch user details from user-service: {e}")
        return None
    except Exception as e:
        current_app.logger.error(f"Error processing user details response: {e}")
        return None

# Function to fetch room details (optional, could be used for validation)
def get_room_details(room_id, token):
    room_service_url = os.getenv("ROOM_SERVICE_URL", "http://room-service:5001")
    headers = {"Authorization": f"Bearer {token}"} # Pass token to room service
    try:
        response = requests.get(f"{room_service_url}/rooms/{room_id}", headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Failed to fetch room details from room-service: {e}")
        return None

# ... potentially other utility functions ...
