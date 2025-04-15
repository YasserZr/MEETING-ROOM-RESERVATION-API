from flask import Blueprint, request, jsonify
from .models import db, User

user_bp = Blueprint('user_bp', __name__)

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
    return jsonify([{'id': u.id, 'email': u.email, 'name': u.full_name, 'role': u.role} for u in users])
