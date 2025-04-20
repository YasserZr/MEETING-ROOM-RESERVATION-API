# auth.py

from flask import Blueprint, jsonify, current_app, request, session
# Removed Flask-Dance imports
# from flask_dance.contrib.google import make_google_blueprint, google
from .models import db, User
from .jwt_utils import generate_token
import os
import sys
from dotenv import load_dotenv
from werkzeug.security import check_password_hash  # Import for password verification
from werkzeug.security import generate_password_hash  # Import for password hashing

# Load environment variables from .env file
load_dotenv()

auth_bp = Blueprint("auth_bp", __name__, url_prefix='/auth')

# Removed Flask-Dance blueprint registration
# google_bp = make_google_blueprint(...)
# auth_bp.register_blueprint(google_bp, url_prefix="/login")

@auth_bp.route("/login/google/authorized")
def google_login_authorized():
    if not google.authorized:
        return redirect(url_for("google.login"))

    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        return jsonify({"message": "Failed to fetch user info from Google"}), 400

    user_info = resp.json()
    email = user_info.get("email")
    full_name = user_info.get("name")

    if not email:
        return jsonify({"message": "Google account does not have an email"}), 400

    # Check if user exists, otherwise create a new user
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(
            email=email,
            full_name=full_name,
            role="attendee"  # Assign default role for Google users
        )
        db.session.add(user)
        db.session.commit()

    # Generate JWT token
    token = generate_token(user.id)
    if not token:
        return jsonify({"message": "Failed to generate token"}), 500

    return jsonify({"message": "Login successful", "token": token})


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data or "username" not in data or "password" not in data:
        return jsonify({"message": "Username and password are required"}), 400

    username = data["username"]
    password = data["password"]

    # Fetch user from the database
    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password, password):
        return jsonify({"message": "Invalid username or password"}), 401

    token = generate_token(user.id)
    if not token:
        return jsonify({"message": "Failed to generate token"}), 500

    return jsonify({"message": "Login successful", "token": token})


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    if not data or "username" not in data or "password" not in data:
        return jsonify({"message": "Username and password are required"}), 400

    username = data["username"]
    password = data["password"]

    # Check if the user already exists
    if User.query.filter_by(username=username).first():
        return jsonify({"message": "User already exists"}), 409

    # Create a new user with a hashed password
    hashed_password = generate_password_hash(password)
    new_user = User(username=username, password=hashed_password)

    # Add the user to the database
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully"}), 201


@auth_bp.route("/logout")
def logout():
    session.clear()
    current_app.logger.info("User logged out, session cleared.")
    return jsonify({"message": "Logged out successfully"})


@auth_bp.route("/debug-session")
def debug_session():
    return jsonify({"message": "Debugging session logic removed"})