from functools import wraps
from flask import request, jsonify, current_app

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get("Authorization")
        if (auth_header):
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({"message": "Bearer token malformed"}), 401

        if not token:
            return jsonify({"message": "Token is missing"}), 401

        # Simulate decoding the token to extract user_id
        user_id = 1  # Replace with actual token decoding logic if needed
        kwargs['user_id'] = user_id
        kwargs['token'] = token
        return f(*args, **kwargs)

    return decorated

def role_required(required_roles):
    def decorator(f):
        @wraps(f)
        def decorated(user_id, *args, **kwargs):
            # Validate roles using headers
            user_role = request.headers.get('X-User-Role')  # Example: Pass role in headers
            current_app.logger.debug(f"User ID: {user_id}, Role: {user_role}, Required Roles: {required_roles}")
            if not user_role:
                current_app.logger.warning("X-User-Role header is missing.")
                return jsonify({"message": "Access denied: Role header missing"}), 403
            if user_role not in required_roles:
                current_app.logger.warning(f"Access denied: User role '{user_role}' not in {required_roles}")
                return jsonify({"message": "Access denied"}), 403
            return f(user_id, *args, **kwargs)
        return decorated
    return decorator
