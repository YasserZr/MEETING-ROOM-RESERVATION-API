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

# Define admin_required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_details = request.user  # Assume user details are added to the request by token_required
        if not user_details or user_details.get('role') != 'admin':
            return jsonify({"message": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated_function

user_bp = Blueprint('user_bp', __name__) # Keep blueprint name simple

@user_bp.route("/me", methods=["GET"]) # Route relative to blueprint prefix '/users'
@token_required
def get_profile(user_id): # Assuming token_required injects user_id or user object
    # If token_required injects the user object directly:
    # user = current_user # Or however token_required provides it
    # If it only provides user_id:
    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404
    # Return more user details if needed, ensure sensitive info is not exposed
    return jsonify({"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role})

@user_bp.route('', methods=['POST']) # Route relative to blueprint prefix '/users'
def create_user():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('full_name'):
        return jsonify({"error": "Missing email or full_name"}), 400

    # Check if user already exists
    if User.query.filter_by(email=data['email']).first():
        return jsonify({"error": "User with this email already exists"}), 409

    user = User(
        email=data['email'],
        full_name=data['full_name'],
        role=data.get('role', 'user') # Default role to 'user'
    )
    db.session.add(user)
    db.session.commit()
    # Return the created user details (excluding sensitive info if any)
    return jsonify({'message': 'User created', 'user': {"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role}}), 201

@user_bp.route('', methods=['GET'])  # Route relative to blueprint prefix '/users'
@token_required
@role_required(['admin'])  # Only admins can access this route
def get_users(user_id):
    users = User.query.all()
    return jsonify([{'id': u.id, 'email': u.email, 'full_name': u.full_name, 'role': u.role} for u in users])

# List all users (Admin only)
@user_bp.route('/users', methods=['GET'])
@admin_required
def list_users(user_id, token):
    users = User.query.all()
    return jsonify([user.to_dict() for user in users]), 200

# Update a user's role (Admin only)
@user_bp.route('/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user_role(admin_id, token, user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404

    data = request.get_json()
    new_role = data.get('role')
    if not new_role:
        return jsonify({"message": "Role is required"}), 400

    try:
        user.role = new_role
        db.session.commit()
        return jsonify(user.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Failed to update user role", "error": str(e)}), 500

# Delete a user (Admin only)
@user_bp.route('/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(admin_id, token, user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404

    try:
        db.session.delete(user)
        db.session.commit()
        return jsonify({"message": "User deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Failed to delete user", "error": str(e)}), 500

# Remove the duplicated auth blueprint and routes from this file
# The auth logic (Google OAuth) should reside in auth.py
# bp = Blueprint('auth', __name__, url_prefix='/auth')
# ... remove all @bp.route definitions ...
