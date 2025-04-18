from flask import Blueprint, request, jsonify, current_app
from .models import db, Reservation
from .jwt_utils import token_required, get_user_details, get_room_details # Import token_required and validation helpers
from .kafka_producer import send_reservation_event # Import Kafka producer function
from datetime import datetime
from sqlalchemy import or_, and_

reservation_bp = Blueprint('reservation_bp', __name__)

# Helper function to check for overlapping reservations
def check_overlap(room_id, start_time, end_time, exclude_reservation_id=None):
    query = Reservation.query.filter(
        Reservation.room_id == room_id,
        Reservation.id != exclude_reservation_id, # Exclude self when updating
        or_(
            # Existing reservation starts during the new one
            and_(Reservation.start_time >= start_time, Reservation.start_time < end_time),
            # Existing reservation ends during the new one
            and_(Reservation.end_time > start_time, Reservation.end_time <= end_time),
            # Existing reservation completely contains the new one
            and_(Reservation.start_time <= start_time, Reservation.end_time >= end_time)
        )
    )
    return query.first()

# Create a new reservation
@reservation_bp.route('/', methods=['POST'])
@token_required
def create_reservation(user_id, token):
    data = request.get_json()
    required_fields = ['room_id', 'start_time', 'end_time']
    if not data or not all(field in data for field in required_fields):
        return jsonify({"message": "Missing required fields: room_id, start_time, end_time"}), 400

    try:
        room_id = int(data['room_id'])
        start_time = datetime.fromisoformat(data['start_time'])
        end_time = datetime.fromisoformat(data['end_time'])
    except (ValueError, TypeError) as e:
        return jsonify({"message": "Invalid data format for room_id, start_time, or end_time", "error": str(e)}), 400

    if end_time <= start_time:
        return jsonify({"message": "End time must be after start time"}), 400

    # --- Inter-service communication/validation ---
    # 1. Validate Room exists (optional but recommended)
    room_details = get_room_details(room_id, token)
    if not room_details:
         # Logged in get_room_details
         return jsonify({"message": f"Room with ID {room_id} not found or room service unavailable"}), 404 # Or 400 Bad Request

    # 2. Validate User exists (less critical if user_id from token is trusted)
    # user_details = get_user_details(user_id, token)
    # if not user_details:
    #     return jsonify({"message": "User validation failed or user service unavailable"}), 400

    # --- Check for overlaps ---
    existing_reservation = check_overlap(room_id, start_time, end_time)
    if existing_reservation:
        return jsonify({"message": "Time slot conflict with an existing reservation"}), 409 # Conflict

    try:
        new_reservation = Reservation(
            user_id=user_id, # Use user_id from token
            room_id=room_id,
            start_time=start_time,
            end_time=end_time,
            purpose=data.get('purpose')
        )
        db.session.add(new_reservation)
        db.session.commit()
        reservation_dict = new_reservation.to_dict() # Get dict before potential session closure

        # --- Publish Kafka Event ---
        send_reservation_event("RESERVATION_CREATED", reservation_dict)
        # --- End Kafka Event ---

        return jsonify(reservation_dict), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to create reservation: {e}")
        return jsonify({"message": "Failed to create reservation", "error": str(e)}), 500


# Get all reservations (maybe filter by user or room?)
@reservation_bp.route('/', methods=['GET'])
@token_required
def get_reservations(user_id, token):
    # Add query parameters for filtering, e.g., ?user_id=self or ?room_id=123
    filter_user = request.args.get('user_id')
    filter_room = request.args.get('room_id')

    query = Reservation.query

    if filter_user == 'self':
        query = query.filter_by(user_id=user_id)
    # Add admin check if allowing filtering by arbitrary user_id

    if filter_room:
        try:
            query = query.filter_by(room_id=int(filter_room))
        except ValueError:
            return jsonify({"message": "Invalid room_id format"}), 400

    reservations = query.order_by(Reservation.start_time).all()
    return jsonify([res.to_dict() for res in reservations])

# Get a specific reservation by ID
@reservation_bp.route('/<int:reservation_id>', methods=['GET'])
@token_required
def get_reservation(user_id, token, reservation_id):
    reservation = Reservation.query.get(reservation_id)
    if not reservation:
        return jsonify({"message": "Reservation not found"}), 404

    # Optional: Check if the user owns the reservation or is an admin
    # user_details = get_user_details(user_id, token)
    # if reservation.user_id != user_id and (not user_details or user_details.get('role') != 'admin'):
    #    return jsonify({"message": "Forbidden"}), 403

    return jsonify(reservation.to_dict())

# Update a reservation (only owner or admin?)
@reservation_bp.route('/<int:reservation_id>', methods=['PUT'])
@token_required
def update_reservation(user_id, token, reservation_id):
    reservation = Reservation.query.get(reservation_id)
    if not reservation:
        return jsonify({"message": "Reservation not found"}), 404

    # --- Authorization Check ---
    # Allow only the user who made the reservation or an admin to update
    user_details = get_user_details(user_id, token) # Fetch user details to check role
    is_admin = user_details and user_details.get('role') == 'admin'

    if reservation.user_id != user_id and not is_admin:
       return jsonify({"message": "Forbidden: You can only update your own reservations"}), 403

    data = request.get_json()
    if not data:
        return jsonify({"message": "No input data provided"}), 400

    try:
        new_start_time = datetime.fromisoformat(data['start_time']) if 'start_time' in data else reservation.start_time
        new_end_time = datetime.fromisoformat(data['end_time']) if 'end_time' in data else reservation.end_time
        new_room_id = int(data['room_id']) if 'room_id' in data else reservation.room_id
    except (ValueError, TypeError) as e:
        return jsonify({"message": "Invalid data format for time or room_id", "error": str(e)}), 400

    if new_end_time <= new_start_time:
        return jsonify({"message": "End time must be after start time"}), 400

    # --- Check for overlaps (excluding the current reservation) ---
    if 'start_time' in data or 'end_time' in data or 'room_id' in data:
        # Validate Room exists if changed
        if new_room_id != reservation.room_id:
             room_details = get_room_details(new_room_id, token)
             if not room_details:
                 return jsonify({"message": f"Room with ID {new_room_id} not found or room service unavailable"}), 404 # Or 400

        existing_reservation = check_overlap(new_room_id, new_start_time, new_end_time, exclude_reservation_id=reservation_id)
        if existing_reservation:
            return jsonify({"message": "Time slot conflict with an existing reservation"}), 409 # Conflict

    try:
        reservation.room_id = new_room_id
        reservation.start_time = new_start_time
        reservation.end_time = new_end_time
        reservation.purpose = data.get('purpose', reservation.purpose)
        # user_id should generally not be changed during an update

        db.session.commit()
        reservation_dict = reservation.to_dict() # Get dict before potential session closure

        # --- Publish Kafka Event ---
        send_reservation_event("RESERVATION_UPDATED", reservation_dict)
        # --- End Kafka Event ---

        return jsonify(reservation_dict)
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to update reservation {reservation_id}: {e}")
        return jsonify({"message": "Failed to update reservation", "error": str(e)}), 500


# Delete a reservation (only owner or admin?)
@reservation_bp.route('/<int:reservation_id>', methods=['DELETE'])
@token_required
def delete_reservation(user_id, token, reservation_id):
    reservation = Reservation.query.get(reservation_id)
    if not reservation:
        return jsonify({"message": "Reservation not found"}), 404

    # --- Authorization Check ---
    user_details = get_user_details(user_id, token) # Fetch user details to check role
    is_admin = user_details and user_details.get('role') == 'admin'

    if reservation.user_id != user_id and not is_admin:
       return jsonify({"message": "Forbidden: You can only delete your own reservations"}), 403

    try:
        reservation_dict = reservation.to_dict() # Capture state before deleting
        db.session.delete(reservation)
        db.session.commit()

        # --- Publish Kafka Event ---
        # Send the state *before* deletion
        send_reservation_event("RESERVATION_DELETED", reservation_dict)
        # --- End Kafka Event ---

        return jsonify({"message": "Reservation deleted successfully"})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to delete reservation {reservation_id}: {e}")
        return jsonify({"message": "Failed to delete reservation", "error": str(e)}), 500

