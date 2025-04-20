# auth.py

from flask import Blueprint, jsonify, current_app, request, session, redirect, url_for
import requests
from .jwt_utils import generate_token
import os
import sys
from dotenv import load_dotenv
from werkzeug.security import check_password_hash  # Import for password verification
from werkzeug.security import generate_password_hash  # Import for password hashing
from .models import db, User  # Import db and User at the top

# Load environment variables from .env file
load_dotenv()

auth_bp = Blueprint("auth_bp", __name__, url_prefix='/auth')

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:5000/auth/login/google/callback")
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

@auth_bp.route("/login/google")
def google_login():
    """Redirect the user to Google's OAuth 2.0 authorization endpoint."""
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent"
    }
    auth_url = f"{GOOGLE_AUTH_URL}?{requests.compat.urlencode(params)}"
    return redirect(auth_url)

@auth_bp.route("/login/google/callback")
def google_callback():
    """Handle the callback from Google's OAuth 2.0 server."""

    code = request.args.get("code")
    if not code:
        return jsonify({"message": "Authorization code not provided"}), 400

    # Exchange the authorization code for an access token
    token_data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code"
    }
    token_response = requests.post(GOOGLE_TOKEN_URL, data=token_data)
    if not token_response.ok:
        return jsonify({"message": "Failed to fetch access token"}), 400

    access_token = token_response.json().get("access_token")
    if not access_token:
        return jsonify({"message": "Access token not provided"}), 400

    # Fetch user info from Google
    userinfo_response = requests.get(GOOGLE_USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"})
    if not userinfo_response.ok:
        return jsonify({"message": "Failed to fetch user info from Google"}), 400

    user_info = userinfo_response.json()
    email = user_info.get("email")
    full_name = user_info.get("name")

    if not email:
        return jsonify({"message": "Google account does not have an email"}), 400

    # Check if the user exists in the database
    user = User.query.filter_by(email=email).first()
    if user:
        # User exists, generate a JWT token
        token = generate_token(user.id)
        if not token:
            return jsonify({"message": "Failed to generate token"}), 500

        return jsonify({"message": "Login successful", "token": token, "user": {"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role}})

    # User does not exist, create a new user
    user = User(
        email=email,
        full_name=full_name,
        role="attendee"  # Assign default role for Google users
    )
    db.session.add(user)
    db.session.commit()

    # Generate JWT token for the new user
    token = generate_token(user.id)
    if not token:
        return jsonify({"message": "Failed to generate token"}), 500

    return jsonify({"message": "User created and login successful", "token": token, "user": {"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role}})


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
    if not data or "username" not in data or "password" not in data or "email" not in data:
        return jsonify({"message": "Username, email, and password are required"}), 400

    username = data["username"][:128]  # Limit username to 128 characters
    email = data["email"][:128]        # Limit email to 128 characters
    password = data["password"]        # Password length is hashed, no need to truncate
    full_name = data.get("full_name", "")[:128]  # Limit full_name to 128 characters
    role = data.get("role", "user")[:128]  # Default role is "user", limit to 128 characters

    # Log truncated data for debugging (optional)
    current_app.logger.debug(f"Truncated data: username={username}, email={email}, full_name={full_name}, role={role}")

    # Check if the user already exists
    if User.query.filter((User.username == username) | (User.email == email)).first():
        return jsonify({"message": "User with this username or email already exists"}), 409

    # Create a new user with a hashed password
    hashed_password = generate_password_hash(password)
    new_user = User(username=username, email=email, password=hashed_password, full_name=full_name, role=role)

    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"message": "User registered successfully", "role": role}), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error registering user: {e}")
        return jsonify({"message": "Failed to register user", "error": str(e)}), 500


@auth_bp.route("/logout")
def logout():
    session.clear()
    current_app.logger.info("User logged out, session cleared.")
    return jsonify({"message": "Logged out successfully"})


@auth_bp.route("/debug-session")
def debug_session():
    return jsonify({"message": "Debugging session logic removed"})