# auth.py

from flask import Blueprint, jsonify, current_app, request, session
# Removed Flask-Dance imports
# from flask_dance.contrib.google import make_google_blueprint, google
from .models import db, User
from .jwt_utils import generate_token
import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

auth_bp = Blueprint("auth_bp", __name__, url_prefix='/auth')

# Removed Flask-Dance blueprint registration
# google_bp = make_google_blueprint(...)
# auth_bp.register_blueprint(google_bp, url_prefix="/login")

@auth_bp.route("/login/google/authorized")
def google_login_authorized():
    # Simulate fetching user from the database (replace with actual logic)
    user = User.query.first()  # Replace with actual user lookup logic
    if not user:
        return jsonify({"message": "User not found"}), 404

    token = generate_token(user.id)
    if not token:
        return jsonify({"message": "Failed to generate token"}), 500
    return jsonify({"message": "Login successful", "token": token})


@auth_bp.route("/logout")
def logout():
    session.clear()
    current_app.logger.info("User logged out, session cleared.")
    return jsonify({"message": "Logged out successfully"})


@auth_bp.route("/debug-session")
def debug_session():
    return jsonify({"message": "Debugging session logic removed"})