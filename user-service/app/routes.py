from flask import Blueprint, request, jsonify, redirect, url_for, current_app
import os
# Assuming you use a library like Flask-Dance or requests-oauthlib
# from flask_dance.contrib.google import make_google_blueprint, google # Example
# Or using requests_oauthlib
from requests_oauthlib import OAuth2Session
import json

from .models import db, User
from .decorators import token_required # Import token_required from decorators

user_bp = Blueprint('user_bp', __name__)

@user_bp.route("/me", methods=["GET"]) # Changed from @app.route to @user_bp.route
@token_required
def get_profile(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404
    # Return more user details if needed, ensure sensitive info is not exposed
    return jsonify({"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role})

@user_bp.route('/users', methods=['POST'])
def create_user():
    data = request.get_json()
    user = User(
        email=data['email'],
        full_name=data['full_name'],
        role=data.get('role', 'user')
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({'message': 'User created', 'user_id': user.id})

@user_bp.route('/users', methods=['GET'])
def get_users():
    users = User.query.all()
    # Corrected key name from 'name' to 'full_name' to match model
    return jsonify([{'id': u.id, 'email': u.email, 'full_name': u.full_name, 'role': u.role} for u in users])

# Example using requests_oauthlib - adapt based on your actual implementation
bp = Blueprint('auth', __name__, url_prefix='/auth')

# Ensure these are loaded from environment variables
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
# You'll need to define these redirect URIs in your Google Cloud Console
# and potentially load them from config/env as well
REDIRECT_URI = 'http://localhost:5000/auth/google/callback' # Example callback URL

# Google OAuth endpoints
AUTHORIZATION_BASE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://www.googleapis.com/oauth2/v4/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v1/userinfo"
SCOPE = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid" # Request 'openid' scope for ID token
]

@bp.route('/google/login')
def google_login():
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
         return jsonify({"error": "Google OAuth credentials not configured"}), 500

    google = OAuth2Session(GOOGLE_CLIENT_ID, scope=SCOPE, redirect_uri=REDIRECT_URI)
    authorization_url, state = google.authorization_url(
        AUTHORIZATION_BASE_URL,
        access_type="offline", prompt="select_account")

    # Store state in session? Or handle stateless
    # session['oauth_state'] = state
    return redirect(authorization_url)

@bp.route('/google/callback')
def google_callback():
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
         return jsonify({"error": "Google OAuth credentials not configured"}), 500

    # Handle state validation if used
    google = OAuth2Session(GOOGLE_CLIENT_ID, redirect_uri=REDIRECT_URI) # state=session['oauth_state']
    try:
        token = google.fetch_token(
            TOKEN_URL,
            client_secret=GOOGLE_CLIENT_SECRET,
            authorization_response=request.url)

        # Fetch user info
        user_info_response = google.get(USERINFO_URL)
        if user_info_response.ok:
            user_info = user_info_response.json()
            # Process user_info: find/create user in your DB, generate JWT, etc.
            # Example:
            email = user_info.get('email')
            google_id = user_info.get('id')
            name = user_info.get('name')
            # ... find or create user ...
            # user = find_or_create_user(google_id, email, name)
            # jwt_token = generate_token(user.id) # Assuming generate_token exists
            # return jsonify({"token": jwt_token})
            return jsonify(user_info) # Placeholder
        else:
            return jsonify({"error": "Failed to fetch user info"}), 500

    except Exception as e:
        # Log error e
        return jsonify({"error": "OAuth callback failed", "details": str(e)}), 500

# ... other routes ...

# Make sure to register this blueprint in app/__init__.py
# from . import routes
# app.register_blueprint(routes.bp)
