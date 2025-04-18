from flask import Blueprint, request, jsonify
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
