# auth.py

from flask import Blueprint, redirect, url_for, jsonify, current_app, request, session # Add request, session
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
    redirect_url="/auth/login/google/authorized" # Absolute path from root
)
# Register google_bp under auth_bp
auth_bp.register_blueprint(google_bp, url_prefix="/login")


@auth_bp.route("/login/google/authorized") # Matches redirect_url
def google_login_authorized():
    """Callback route for Google OAuth."""
    current_app.logger.info("Callback received.")
    current_app.logger.info("Session contents before check: %s", dict(session.items()))
    current_app.logger.info("Request args received from Google: %s", request.args)

    # Check if Google returned an error parameter explicitly
    if request.args.get('error'):
        error = request.args.get('error')
        error_description = request.args.get('error_description')
        current_app.logger.error(f"Google OAuth Error received: {error} - {error_description}")
        return jsonify({"error": "Google authentication failed", "details": error_description or error}), 401

    # Now check Flask-Dance's authorized status
    current_app.logger.info("Checking google.authorized status...")
    is_authorized = google.authorized
    current_app.logger.info(f"google.authorized = {is_authorized}")

    if not is_authorized:
        current_app.logger.warning("Google not authorized (token exchange likely failed or session issue). Redirecting back to login entry.")
        # It's hard to get the exact error from Flask-Dance here easily if token exchange failed silently
        # Correct the endpoint name for the nested blueprint
        return redirect(url_for("auth_bp.google.login")) # Redirects to /auth/login/google

    # If authorized, proceed to fetch user info
    current_app.logger.info("Authorization successful, attempting to fetch user info...")
    try:
        resp = google.get("/oauth2/v2/userinfo") # Use the google session object provided by Flask-Dance
        resp.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        user_info = resp.json()
        email = user_info.get("email")
        full_name = user_info.get("name")

        current_app.logger.info(f"Google user info fetched: Email={email}, Name={full_name}")

        if not email:
            current_app.logger.error("Email not found in Google user info.")
            return jsonify({"error": "Email not provided by Google"}), 400

        # Find or create user
        user = User.query.filter_by(email=email).first()
        if user:
            current_app.logger.info(f"User found: {email} (ID: {user.id})")
        else:
            current_app.logger.info(f"User not found, creating new user: {email}")
            user = User(email=email, full_name=full_name or 'Unknown Name') # Handle missing name
            db.session.add(user)
            db.session.commit()
            current_app.logger.info(f"New user created with ID: {user.id}")

        # Generate JWT token
        token = generate_token(user.id)
        current_app.logger.info(f"JWT token generated for user ID: {user.id}")
        return jsonify({"access_token": token})

    except Exception as e:
        db.session.rollback() # Rollback potential db changes on error
        current_app.logger.error(f"Error during Google callback processing after authorization: {e}", exc_info=True)
        return jsonify({"error": "An error occurred during authentication processing after authorization."}), 500

# Add a simple logout route for testing if needed
@auth_bp.route("/logout")
def logout():
    # Clear the Flask session
    session.clear()
    # Clear Flask-Dance token if stored in session (it usually is)
    # You might need more specific logic depending on storage backend if not default session
    if 'google_oauth_token' in session:
         del session['google_oauth_token']
    current_app.logger.info("User logged out, session cleared.")
    return jsonify({"message": "Logged out successfully"})
