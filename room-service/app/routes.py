from flask import Blueprint, request, jsonify
from .models import db, Room
from .jwt_utils import token_required, admin_required # Import decorators

room_bp = Blueprint('room_bp', __name__)

# Create a new room (Admin only)
@room_bp.route('', methods=['POST']) # No trailing slash here
@admin_required
def create_room(user_id, token): # user_id and token passed by decorator
    data = request.get_json()
    if not data or not data.get('name') or data.get('capacity') is None:
        return jsonify({"error": "Missing name or capacity"}), 400

    if Room.query.filter_by(name=data['name']).first():
        return jsonify({"message": f"Room with name '{data['name']}' already exists"}), 409

    try:
        new_room = Room(
            name=data['name'],
            capacity=data['capacity'],
            description=data.get('description')
        )
        db.session.add(new_room)
        db.session.commit()
        return jsonify(new_room.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Failed to create room", "error": str(e)}), 500


# Get all rooms (All authenticated users)
@room_bp.route('/', methods=['GET'])
@token_required
def get_rooms(user_id, token): # user_id and token passed by decorator
    rooms = Room.query.all()
    return jsonify([room.to_dict() for room in rooms])

# Get a specific room by ID (All authenticated users)
@room_bp.route('/<int:room_id>', methods=['GET'])
@token_required
def get_room(user_id, token, room_id): # user_id and token passed by decorator
    room = Room.query.get(room_id)
    if not room:
        return jsonify({"message": "Room not found"}), 404
    return jsonify(room.to_dict())

# Update a room (Admin only)
@room_bp.route('/<int:room_id>', methods=['PUT'])
@admin_required
def update_room(user_id, token, room_id): # user_id and token passed by decorator
    room = Room.query.get(room_id)
    if not room:
        return jsonify({"message": "Room not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"message": "No input data provided"}), 400

    # Check for duplicate name if name is being changed
    new_name = data.get('name')
    if new_name and new_name != room.name and Room.query.filter_by(name=new_name).first():
         return jsonify({"message": f"Room with name '{new_name}' already exists"}), 409

    try:
        room.name = data.get('name', room.name)
        room.capacity = data.get('capacity', room.capacity)
        room.description = data.get('description', room.description)
        db.session.commit()
        return jsonify(room.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Failed to update room", "error": str(e)}), 500

# Delete a room (Admin only)
@room_bp.route('/<int:room_id>', methods=['DELETE'])
@admin_required
def delete_room(user_id, token, room_id): # user_id and token passed by decorator
    room = Room.query.get(room_id)
    if not room:
        return jsonify({"message": "Room not found"}), 404

    try:
        db.session.delete(room)
        db.session.commit()
        return jsonify({"message": "Room deleted successfully"})
    except Exception as e:
        db.session.rollback()
        # Consider checking for FK constraints if reservations depend on rooms
        return jsonify({"message": "Failed to delete room", "error": str(e)}), 500
