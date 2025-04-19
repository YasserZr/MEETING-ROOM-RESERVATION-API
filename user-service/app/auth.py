# auth.py

from flask import Blueprint, redirect, url_for, jsonify, current_app, request
from flask import session
from flask_dance.contrib.google import make_google_blueprint, google
from .models import db, User # Corrected import
from .jwt_utils import generate_token # Corrected import
import os

# Use a distinct name for the auth blueprint if user_bp is already used for user routes
auth_bp = Blueprint("auth_bp", __name__, url_prefix='/auth') # Added url_prefix

# Consider loading secrets more securely in production
google_bp = make_google_blueprint(
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    scope=["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"],
    # redirect_to is preferred over redirect_url for dynamic resolution
    # redirect_to="auth_bp.google_login_authorized" # Use the endpoint name
    # Or keep redirect_url if frontend handles the redirect explicitly
    redirect_url="/auth/login/google/authorized" # Ensure this matches Google Cloud Console config
)
# Register google_bp under auth_bp
auth_bp.register_blueprint(google_bp, url_prefix="/login")


#@auth_bp.route("/login/google")
#def google_login_entry():
    # Redirect to Google's OAuth consent screen
    # Use the prefixed endpoint name because google_bp is registered under auth_bp
#    return redirect(url_for("auth_bp.google.login"))

# Renamed function to avoid conflict and match potential redirect_to usage
@auth_bp.route("/login/google/authorized")
def google_login_authorized():
    # --- Add Logging ---
    current_app.logger.info(f"Callback received. google.authorized = {google.authorized}")
    current_app.logger.info(f"Session contents: {dict(session)}")
    # --- End Logging ---

    if not google.authorized:
        current_app.logger.warning("Google not authorized, redirecting back to login entry.")
        # --- FIX: Use the correct endpoint name provided by Flask-Dance ---
        return redirect(url_for("auth_bp.google.login"))
        # --- END FIX ---

    try:
        resp = google.get("/oauth2/v2/userinfo")
        resp.raise_for_status() # Raise exception for bad status codes
    except Exception as e:
        current_app.logger.error(f"Failed to fetch user info from Google: {e}")
        return jsonify({"error": "Failed to fetch user info from Google"}), 500

    user_info = resp.json()
    email = user_info.get("email")
    full_name = user_info.get("name") # Get full name from Google profile

    if not email:
        return jsonify({"error": "Email not provided by Google"}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        # Use full_name from Google if available
        user = User(email=email, full_name=full_name if full_name else email.split('@')[0])
        db.session.add(user)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to create user: {e}")
            return jsonify({"error": "Failed to create user profile"}), 500

    token = generate_token(user.id)
    # Consider redirecting to a frontend URL with the token
    # For API-only, returning the token is fine
    return jsonify({"access_token": token})

# Example simple username/password login (requires password handling in User model)
# @auth_bp.route('/login', methods=['POST'])
# def login():
#     data = request.get_json()
#     email = data.get('email')
#     password = data.get('password') # Need to implement password hashing/checking
#     user = User.query.filter_by(email=email).first()
#     # Add password check logic here
#     if user: # and check_password(user.password_hash, password):
#         token = generate_token(user.id)
#         return jsonify({"access_token": token})
#     return jsonify({"message": "Invalid credentials"}), 401
