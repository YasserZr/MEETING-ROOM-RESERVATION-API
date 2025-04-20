from flask import Blueprint, request, jsonify, redirect, url_for, current_app
import os
# Assuming you use a library like Flask-Dance or requests-oauthlib
# from flask_dance.contrib.google import make_google_blueprint, google # Example
# Or using requests_oauthlib
# from requests_oauthlib import OAuth2Session # This is likely handled in auth.py
import json

# Change db import
from . import db # Import db from __init__.py
from .models import User # Import User model separately
from .decorators import token_required, role_required  # Import both token_required and role_required

from functools import wraps
from .jwt_utils import token_required  # Import token_required for base authentication

import logging
logging.basicConfig(level=logging.DEBUG)

# Define admin_required decorator
def admin_required(f):
    @wraps(f)
    @token_required  # <== Automatically apply token_required inside
    def decorated_function(user_id, token, *args, **kwargs):
        user = User.query.get(user_id)
        if not user or user.role != 'admin':
            return jsonify({"message": "Admin access required"}), 403
        return f(user_id, token, *args, **kwargs)
    return decorated_function


user_bp = Blueprint('user_bp', __name__)  # Keep blueprint name simple

@user_bp.route("/me", methods=["GET"])  # Route relative to blueprint prefix '/users'
@token_required
def get_profile(user_id, token):  # Add 'token' parameter
    current_app.logger.debug(f"Fetching profile for user_id: {user_id}")
    user = User.query.get(user_id)
    if not user:
        current_app.logger.error("User not found")
        return jsonify({"message": "User not found"}), 404
    # Return more user details if needed, ensure sensitive info is not exposed
    return jsonify({"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role})

from werkzeug.security import generate_password_hash  # Import for password hashing

@user_bp.route('', methods=['GET'])  # Route relative to blueprint prefix '/users'
@token_required
@role_required(['admin'])  # Only admins can access this route
def get_users(user_id, token):  # Add 'token' parameter
    users = User.query.all()
    return jsonify([{'id': u.id, 'email': u.email, 'full_name': u.full_name, 'role': u.role} for u in users])

# Update a user's role (Admin only)
@user_bp.route('/<int:user_id>', methods=['PUT'])
@token_required
@role_required(['admin']) 
def update_user_role(user_id,token):
    """Update the role of a user by their ID."""
    current_app.logger.debug(f"Admin attempting to update role for user ID: {user_id}")
    user = User.query.get(user_id)
    if not user:
        current_app.logger.error(f"User with ID {user_id} not found.")
        return jsonify({"message": "User not found"}), 404

    data = request.get_json()
    if not data or 'role' not in data:
        current_app.logger.error("Role is missing in the request payload.")
        return jsonify({"message": "Role is required"}), 400

    new_role = data['role']
    current_app.logger.debug(f"New role for user ID {user_id}: {new_role}")

    try:
        user.role = new_role
        db.session.commit()
        current_app.logger.info(f"User ID {user_id} role updated to {new_role}.")
        return jsonify({"message": "User role updated successfully", "user": user.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating role for user ID {user_id}: {e}")
        return jsonify({"message": "Failed to update user role", "error": str(e)}), 500

# Delete a user (Admin only)
@user_bp.route('/<int:user_id>', methods=['DELETE'])
@token_required
@role_required(['admin']) 
def delete_user(user_id, token):
    """Delete a user by their ID."""
    current_app.logger.debug(f"Admin attempting to delete user ID: {user_id}")
    user = User.query.get(user_id)
    if not user:
        current_app.logger.error(f"User with ID {user_id} not found.")
        return jsonify({"message": "User not found"}), 404

    try:
        db.session.delete(user)
        db.session.commit()
        current_app.logger.info(f"User ID {user_id} deleted successfully.")
        return jsonify({"message": "User deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting user ID {user_id}: {e}")
        return jsonify({"message": "Failed to delete user", "error": str(e)}), 500





# Remove the duplicated auth blueprint and routes from this file
# The auth logic (Google OAuth) should reside in auth.py
# bp = Blueprint('auth', __name__, url_prefix='/auth')
# ... remove all @bp.route definitions ...
