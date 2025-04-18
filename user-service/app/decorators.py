from functools import wraps
from flask import request, jsonify
from .jwt_utils import decode_token # Use relative import

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

        # Pass the user_id obtained from the token to the decorated function
        return f(user_id, *args, **kwargs)

    return decorated
