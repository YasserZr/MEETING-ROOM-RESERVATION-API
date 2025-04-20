from flask import Blueprint, request, jsonify, current_app
from .models import db, Room
from .jwt_utils import token_required, admin_required # Import decorators
import requests
from datetime import datetime
from sqlalchemy import and_

room_bp = Blueprint('room_bp', __name__)

# Create a new room (Admin only)
@room_bp.route('', methods=['POST']) # No trailing slash here
@admin_required
def create_room(user_id, token): # user_id and token passed by decorator
    data = request.get_json()
    if not data or not data.get('name') or data.get('capacity') is None:
        return jsonify({"message": "Missing required fields: name or capacity"}), 400

    if Room.query.filter_by(name=data['name']).first():
        return jsonify({"message": f"Room with name '{data['name']}' already exists"}), 409

    try:
        new_room = Room(
            name=data['name'],
            capacity=data['capacity'],
            description=data.get('description'),
            amenities=data.get('amenities')  # Optional amenities
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
        room.amenities = data.get('amenities', room.amenities)  # Update amenities
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

# Check room availability (All authenticated users)
@room_bp.route('/availability', methods=['GET'])
@token_required
def check_room_availability(user_id, token):
    start_time = request.args.get('start_time')
    end_time = request.args.get('end_time')

    if not start_time or not end_time:
        return jsonify({"message": "start_time and end_time are required"}), 400

    try:
        start_time = datetime.fromisoformat(start_time)
        end_time = datetime.fromisoformat(end_time)
    except ValueError:
        return jsonify({"message": "Invalid date format. Use ISO 8601 format."}), 400

    if end_time <= start_time:
        return jsonify({"message": "end_time must be after start_time"}), 400

    # Fetch reservations from reservation-service
    reservation_service_url = current_app.config.get("RESERVATION_SERVICE_URL", "http://reservation-service:5002")
    try:
        response = requests.get(
            f"{reservation_service_url}/reservations",
            params={"start_time": start_time.isoformat(), "end_time": end_time.isoformat()},
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        reservations = response.json()
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Failed to fetch reservations: {e}")
        return jsonify({"message": "Failed to fetch reservations from reservation-service"}), 500

    # Get all rooms
    rooms = Room.query.all()
    reserved_room_ids = {res['room_id'] for res in reservations}

    # Find available rooms
    available_rooms = [room.to_dict() for room in rooms if room.id not in reserved_room_ids]

    return jsonify(available_rooms)

# Add a blackout period (Admin only)
@room_bp.route('/<int:room_id>/blackout', methods=['POST'])
@admin_required
def add_blackout_period(user_id, token, room_id):
    room = Room.query.get(room_id)
    if not room:
        return jsonify({"message": "Room not found"}), 404

    data = request.get_json()
    if not data or not data.get('start_time') or not data.get('end_time'):
        return jsonify({"message": "Missing required fields: start_time or end_time"}), 400

    try:
        start_time = datetime.fromisoformat(data['start_time'])
        end_time = datetime.fromisoformat(data['end_time'])
        if end_time <= start_time:
            return jsonify({"message": "End time must be after start time"}), 400
    except ValueError:
        return jsonify({"message": "Invalid date format. Use ISO 8601 format."}), 400

    blackout_period = BlackoutPeriod(
        room_id=room_id,
        start_time=start_time,
        end_time=end_time,
        reason=data.get('reason')
    )
    try:
        db.session.add(blackout_period)
        db.session.commit()
        return jsonify(blackout_period.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Failed to add blackout period", "error": str(e)}), 500

# Get blackout periods for a room
@room_bp.route('/<int:room_id>/blackout', methods=['GET'])
@token_required
def get_blackout_periods(user_id, token, room_id):
    room = Room.query.get(room_id)
    if not room:
        return jsonify({"message": "Room not found"}), 404

    blackout_periods = BlackoutPeriod.query.filter_by(room_id=room_id).all()
    return jsonify([bp.to_dict() for bp in blackout_periods])

@room_bp.route('/search', methods=['GET'])
def search_rooms():
    """
    Search for meeting rooms based on specific criteria.
    Query parameters:
    - capacity: Minimum capacity required (optional)
    - amenities: Comma-separated list of required amenities (optional)
    - start_time: Start time for availability check (ISO 8601 format, optional)
    - end_time: End time for availability check (ISO 8601 format, optional)
    """
    capacity = request.args.get('capacity', type=int)
    amenities = request.args.get('amenities', type=str)
    start_time = request.args.get('start_time')
    end_time = request.args.get('end_time')

    query = Room.query

    # Filter by capacity
    if capacity:
        query = query.filter(Room.capacity >= capacity)

    # Filter by amenities
    if amenities:
        required_amenities = amenities.split(',')
        query = query.filter(
            and_(
                *(Room.amenities[key].astext == 'true' for key in required_amenities)
            )
        )

    # Filter by availability
    if start_time and end_time:
        try:
            start_time = datetime.fromisoformat(start_time)
            end_time = datetime.fromisoformat(end_time)
            query = query.filter(
                ~Room.reservations.any(
                    and_(
                        Reservation.start_time < end_time,
                        Reservation.end_time > start_time
                    )
                )
            )
        except ValueError:
            return jsonify({"message": "Invalid date format. Use ISO 8601 format for start_time and end_time."}), 400

    rooms = query.all()
    return jsonify([room.to_dict() for room in rooms]), 200
