from flask import Blueprint, request, jsonify, current_app
from .models import db, Reservation
from .jwt_utils import token_required, get_user_details, get_room_details # Import token_required and validation helpers
from .kafka_producer import send_reservation_event # Import Kafka producer function
from datetime import datetime, timedelta
from sqlalchemy import or_, and_
from .email_utils import send_email  # Import the email utility
import pytz  # For timezone handling
from email.utils import formatdate  # For RFC 2822 date formatting
import os  # Import os to read environment variables
from sqlalchemy.sql import func  # Import for aggregation

reservation_bp = Blueprint('reservation_bp', __name__)

MODIFICATION_TIME_LIMIT = timedelta(hours=1)  # Allow modifications/cancellations up to 1 hour before the start time

# Define booking policies
BOOKING_POLICIES = {
    "department_head": {"max_days_in_advance": 90},  # Department heads can book up to 90 days in advance
    "staff": {"max_days_in_advance": 30},           # Staff can book up to 30 days in advance
    "guest": {"max_days_in_advance": 7}             # Guests can book up to 7 days in advance
}

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

def generate_calendar_invitation(room_name, room_description, start_time, end_time, attendees, purpose):
    """Generate an iCalendar (.ics) file for the meeting."""
    start_time_utc = start_time.astimezone(pytz.utc).strftime('%Y%m%dT%H%M%SZ')
    end_time_utc = end_time.astimezone(pytz.utc).strftime('%Y%m%dT%H%M%SZ')
    now_utc = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')

    attendees_emails = "\n".join([f"ATTENDEE;CN={attendee}:mailto:{attendee}" for attendee in attendees])

    ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Meeting Room Reservation//EN
CALSCALE:GREGORIAN
METHOD:REQUEST
BEGIN:VEVENT
UID:{start_time_utc}-{room_name}@meeting-room-reservation
DTSTAMP:{now_utc}
DTSTART:{start_time_utc}
DTEND:{end_time_utc}
SUMMARY:{purpose}
DESCRIPTION:{room_description}
LOCATION:{room_name}
{attendees_emails}
END:VEVENT
END:VCALENDAR
"""
    return ics_content.encode('utf-8')

def check_blackout_periods(room_id, start_time, end_time, token):
    """Check if the reservation conflicts with any blackout periods."""
    room_service_url = current_app.config.get("ROOM_SERVICE_URL", "http://room-service:5001")
    try:
        response = requests.get(
            f"{room_service_url}/{room_id}/blackout",
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        blackout_periods = response.json()
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Failed to fetch blackout periods: {e}")
        return False, "Failed to fetch blackout periods from room-service"

    for bp in blackout_periods:
        bp_start = datetime.fromisoformat(bp['start_time'])
        bp_end = datetime.fromisoformat(bp['end_time'])
        if not (end_time <= bp_start or start_time >= bp_end):
            return False, f"Reservation conflicts with a blackout period: {bp.get('reason', 'No reason provided')}"

    return True, None

def send_to_external_calendar(user_email, ics_content):
    """Send the calendar event to an external calendar system."""
    # Placeholder for integration with external calendar APIs (e.g., Google Calendar, Microsoft Outlook)
    # For now, this function will log the event and simulate success.
    current_app.logger.info(f"Sending calendar event for {user_email} to external calendar system.")
    # Simulate success
    return True

def is_email_notifications_enabled():
    """Check if email notifications are enabled."""
    return os.getenv('ENABLE_EMAIL_NOTIFICATIONS', 'true').lower() == 'true'

def get_booking_lead_time():
    """Get the minimum booking lead time in hours from environment variables."""
    return int(os.getenv('BOOKING_LEAD_TIME_HOURS', 1))  # Default to 1 hour

def get_cancellation_deadline():
    """Get the cancellation deadline in hours from environment variables."""
    return int(os.getenv('CANCELLATION_DEADLINE_HOURS', 1))  # Default to 1 hour

def get_operating_hours():
    """Get the operating hours from environment variables."""
    start_hour = int(os.getenv('OPERATING_HOURS_START', 8))  # Default to 8 AM
    end_hour = int(os.getenv('OPERATING_HOURS_END', 18))  # Default to 6 PM
    return start_hour, end_hour

# Create a new reservation
@reservation_bp.route('/', methods=['POST'])
@token_required
def create_reservation(user_id, token):
    data = request.get_json()
    required_fields = ['room_id', 'start_time', 'duration', 'num_attendees']
    if not data or not all(field in data for field in required_fields):
        return jsonify({"message": "Missing required fields: room_id, start_time, duration, num_attendees"}), 400

    try:
        room_id = int(data['room_id'])
        start_time = datetime.fromisoformat(data['start_time'])
        duration = int(data['duration'])  # Duration in minutes
        num_attendees = int(data['num_attendees'])
        end_time = start_time + timedelta(minutes=duration)
        recurrence = data.get('recurrence')  # Optional recurrence pattern (e.g., "weekly", "monthly")
        occurrences = int(data.get('occurrences', 1))  # Number of occurrences for the recurrence
    except (ValueError, TypeError) as e:
        return jsonify({"message": "Invalid data format for room_id, start_time, duration, or num_attendees", "error": str(e)}), 400

    if end_time <= start_time:
        return jsonify({"message": "End time must be after start time"}), 400

    if num_attendees <= 0:
        return jsonify({"message": "Number of attendees must be greater than zero"}), 400

    if recurrence and occurrences <= 0:
        return jsonify({"message": "Occurrences must be greater than zero for recurring meetings"}), 400

    # --- Enforce Booking Lead Time ---
    booking_lead_time = get_booking_lead_time()
    if (start_time - datetime.utcnow()).total_seconds() / 3600 < booking_lead_time:
        return jsonify({"message": f"Reservations must be made at least {booking_lead_time} hours in advance"}), 403

    # --- Enforce Operating Hours ---
    operating_start, operating_end = get_operating_hours()
    if not (operating_start <= start_time.hour < operating_end and operating_start < end_time.hour <= operating_end):
        return jsonify({"message": f"Reservations must be within operating hours: {operating_start}:00 to {operating_end}:00"}), 403

    # --- Inter-service communication/validation ---
    # 1. Validate Room exists and check capacity
    room_details = get_room_details(room_id, token)
    if not room_details:
        return jsonify({"message": f"Room with ID {room_id} not found or room service unavailable"}), 404

    if room_details.get('capacity', 0) < num_attendees:
        return jsonify({"message": f"Room capacity ({room_details.get('capacity')}) is insufficient for {num_attendees} attendees"}), 400

    # 2. Validate User Role and Booking Policy
    user_details = get_user_details(user_id, token)
    if not user_details or not user_details.get('role'):
        return jsonify({"message": "User role information is missing or user service unavailable"}), 403

    user_role = user_details['role']
    booking_policy = BOOKING_POLICIES.get(user_role, BOOKING_POLICIES['guest'])  # Default to guest policy if role is unknown
    max_days_in_advance = booking_policy['max_days_in_advance']

    if (start_time - datetime.utcnow()).days > max_days_in_advance:
        return jsonify({"message": f"Users with role '{user_role}' can only book up to {max_days_in_advance} days in advance"}), 403

    # --- Check for blackout periods ---
    is_valid, error_message = check_blackout_periods(room_id, start_time, end_time, token)
    if not is_valid:
        return jsonify({"message": error_message}), 403

    reservations = []
    try:
        attendees = data.get('attendees', [])  # Get attendees from the request
        for i in range(occurrences):
            # Calculate the start and end times for each occurrence
            if recurrence == "weekly":
                occurrence_start_time = start_time + timedelta(weeks=i)
            elif recurrence == "monthly":
                occurrence_start_time = start_time + timedelta(days=30 * i)
            else:
                occurrence_start_time = start_time

            occurrence_end_time = occurrence_start_time + timedelta(minutes=duration)

            # --- Check for overlaps ---
            existing_reservation = check_overlap(room_id, occurrence_start_time, occurrence_end_time)
            if existing_reservation:
                return jsonify({"message": f"Time slot conflict for occurrence {i + 1} with an existing reservation"}), 409

            # Create the reservation
            new_reservation = Reservation(
                user_id=user_id,
                room_id=room_id,
                start_time=occurrence_start_time,
                end_time=occurrence_end_time,
                purpose=data.get('purpose'),
                num_attendees=num_attendees,
                description=data.get('description'),  # Add description
                attendees=attendees  # Add attendees
            )
            db.session.add(new_reservation)
            reservations.append(new_reservation)

        db.session.commit()

        # Send confirmation email for the first occurrence
        if is_email_notifications_enabled():
            user_details = get_user_details(user_id, token)
            if user_details and user_details.get('email'):
                email_body = (
                    f"Dear {user_details.get('full_name', 'User')},\n\n"
                    f"Your recurring reservation has been confirmed with the following details:\n"
                    f"Room: {room_details.get('name')}\n"
                    f"Start Time (First Occurrence): {start_time}\n"
                    f"End Time (First Occurrence): {end_time}\n"
                    f"Number of Attendees: {num_attendees}\n"
                    f"Purpose: {data.get('purpose', 'N/A')}\n"
                    f"Recurrence: {recurrence if recurrence else 'None'}\n"
                    f"Occurrences: {occurrences}\n\n"
                    f"Thank you for using our service!"
                )

                # Generate the .ics file
                ics_content = generate_calendar_invitation(
                    room_name=room_details.get('name'),
                    room_description=room_details.get('description', 'N/A'),
                    start_time=start_time,
                    end_time=end_time,
                    attendees=[user_details['email']],  # Add more attendees if needed
                    purpose=data.get('purpose', 'Meeting')
                )

                send_email(
                    to_email=user_details['email'],
                    subject="Meeting Room Reservation Confirmation",
                    body=email_body,
                    attachment=ics_content,
                    attachment_name="meeting-invitation.ics"
                )

                # Send to external calendar system
                send_to_external_calendar(user_details['email'], ics_content)

        # Send Email Invitations
        if is_email_notifications_enabled() and attendees:
            email_body = (
                f"Dear Attendee,\n\n"
                f"You have been invited to the following meeting:\n"
                f"Room: {room_details.get('name')}\n"
                f"Location: {room_details.get('description', 'N/A')}\n"
                f"Start Time: {start_time}\n"
                f"End Time: {end_time}\n"
                f"Purpose: {data.get('purpose', 'N/A')}\n"
                f"Description: {data.get('description', 'N/A')}\n\n"
                f"Thank you!"
            )

            # Generate the .ics file
            ics_content = generate_calendar_invitation(
                room_name=room_details.get('name'),
                room_description=room_details.get('description', 'N/A'),
                start_time=start_time,
                end_time=end_time,
                attendees=attendees,
                purpose=data.get('purpose', 'Meeting')
            )

            for attendee_email in attendees:
                send_email(
                    to_email=attendee_email,
                    subject="Meeting Invitation",
                    body=email_body,
                    attachment=ics_content,
                    attachment_name="meeting-invitation.ics"
                )

        # Publish Kafka events for all reservations
        for reservation in reservations:
            send_reservation_event("RESERVATION_CREATED", reservation.to_dict())

        return jsonify([reservation.to_dict() for reservation in reservations]), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to create recurring reservations: {e}")
        return jsonify({"message": "Failed to create recurring reservations", "error": str(e)}), 500


# Get all reservations (maybe filter by user or room?)
@reservation_bp.route('/', methods=['GET'])
@token_required
def get_reservations(user_id, token):
    # Add query parameters for filtering, e.g., ?user_id=self or ?room_id=123
    filter_user = request.args.get('user_id')
    filter_room = request.args.get('room_id')
    start_time = request.args.get('start_time')
    end_time = request.args.get('end_time')

    query = Reservation.query

    if filter_user == 'self':
        query = query.filter_by(user_id=user_id)

    if filter_room:
        try:
            query = query.filter_by(room_id=int(filter_room))
        except ValueError:
            return jsonify({"message": "Invalid room_id format"}), 400

    if start_time and end_time:
        try:
            start_time = datetime.fromisoformat(start_time)
            end_time = datetime.fromisoformat(end_time)
            query = query.filter(
                or_(
                    and_(Reservation.start_time >= start_time, Reservation.start_time < end_time),
                    and_(Reservation.end_time > start_time, Reservation.end_time <= end_time),
                    and_(Reservation.start_time <= start_time, Reservation.end_time >= end_time)
                )
            )
        except ValueError:
            return jsonify({"message": "Invalid date format. Use ISO 8601 format."}), 400

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

    # --- Time Limit Check ---
    if datetime.utcnow() > reservation.start_time - MODIFICATION_TIME_LIMIT:
        return jsonify({"message": "Modifications are not allowed within 1 hour of the reservation start time"}), 403

    # --- Authorization Check ---
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
        reservation.num_attendees = data.get('num_attendees', reservation.num_attendees)
        reservation.description = data.get('description', reservation.description)  # Update description
        db.session.commit()
        reservation_dict = reservation.to_dict()  # Get dict before potential session closure

        # --- Send Notification Email ---
        if is_email_notifications_enabled():
            user_details = get_user_details(user_id, token)
            if user_details and user_details.get('email'):
                email_body = (
                    f"Dear {user_details.get('full_name', 'User')},\n\n"
                    f"The following reservation has been updated:\n"
                    f"Room: {reservation_dict['room_id']}\n"
                    f"Start Time: {reservation_dict['start_time']}\n"
                    f"End Time: {reservation_dict['end_time']}\n"
                    f"Purpose: {reservation_dict['purpose']}\n\n"
                    f"Please check your schedule for the updated details.\n\n"
                    f"Thank you!"
                )
                send_email(
                    to_email=user_details['email'],
                    subject="Meeting Room Reservation Updated",
                    body=email_body
                )
        # --- End Email Sending ---

        # --- Publish Kafka Event ---
        send_reservation_event("RESERVATION_UPDATED", reservation_dict)
        # --- End Kafka Event ---

        return jsonify(reservation_dict)
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to update reservation {reservation_id}: {e}")
        return jsonify({"message": "Failed to update reservation", "error": str(e)}), 500

# Delete a reservation (only owner or admin?)
@reservation_bp.route('/<int:reservation_id>', methods=['DELETE'])  # Fix typo: methods['DELETE'] -> methods=['DELETE']
@token_required
def delete_reservation(user_id, token, reservation_id):
    reservation = Reservation.query.get(reservation_id)
    if not reservation:
        return jsonify({"message": "Reservation not found"}), 404

    # --- Enforce Cancellation Deadline ---
    cancellation_deadline = get_cancellation_deadline()
    if (reservation.start_time - datetime.utcnow()).total_seconds() / 3600 < cancellation_deadline:
        return jsonify({"message": f"Cancellations must be made at least {cancellation_deadline} hours before the reservation start time"}), 403

    # --- Authorization Check ---
    user_details = get_user_details(user_id, token) # Fetch user details to check role
    is_admin = user_details and user_details.get('role') == 'admin'

    if reservation.user_id != user_id and not is_admin:
       return jsonify({"message": "Forbidden: You can only delete your own reservations"}), 403

    try:
        reservation_dict = reservation.to_dict()  # Capture state before deleting
        db.session.delete(reservation)
        db.session.commit()

        # --- Send Notification Email ---
        if is_email_notifications_enabled():
            user_details = get_user_details(user_id, token)
            if user_details and user_details.get('email'):
                email_body = (
                    f"Dear {user_details.get('full_name', 'User')},\n\n"
                    f"The following reservation has been canceled:\n"
                    f"Room: {reservation_dict['room_id']}\n"
                    f"Start Time: {reservation_dict['start_time']}\n"
                    f"End Time: {reservation_dict['end_time']}\n"
                    f"Purpose: {reservation_dict['purpose']}\n\n"
                    f"Please update your schedule accordingly.\n\n"
                    f"Thank you!"
                )
                send_email(
                    to_email=user_details['email'],
                    subject="Meeting Room Reservation Canceled",
                    body=email_body
                )
        # --- End Email Sending ---

        # --- Publish Kafka Event ---
        send_reservation_event("RESERVATION_DELETED", reservation_dict)
        # --- End Kafka Event ---

        return jsonify({"message": "Reservation deleted successfully"})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to delete reservation {reservation_id}: {e}")
        return jsonify({"message": "Failed to delete reservation", "error": str(e)}), 500

@reservation_bp.route('/reports/usage', methods=['GET'])
@token_required
def generate_usage_report(user_id, token):
    """
    Generate a report on meeting room usage.
    Query parameters:
    - start_time: Start of the time range (ISO 8601 format, optional)
    - end_time: End of the time range (ISO 8601 format, optional)
    """
    start_time = request.args.get('start_time')
    end_time = request.args.get('end_time')

    query = db.session.query(
        Reservation.room_id,
        func.count(Reservation.id).label('total_bookings'),
        func.sum(func.extract('epoch', Reservation.end_time - Reservation.start_time) / 3600).label('total_hours')
    ).group_by(Reservation.room_id)

    if start_time:
        try:
            start_time = datetime.fromisoformat(start_time)
            query = query.filter(Reservation.start_time >= start_time)
        except ValueError:
            return jsonify({"message": "Invalid start_time format. Use ISO 8601 format."}), 400

    if end_time:
        try:
            end_time = datetime.fromisoformat(end_time)
            query = query.filter(Reservation.end_time <= end_time)
        except ValueError:
            return jsonify({"message": "Invalid end_time format. Use ISO 8601 format."}), 400

    results = query.all()

    # Fetch room details from room-service
    room_service_url = current_app.config.get("ROOM_SERVICE_URL", "http://room-service:5001")
    try:
        response = requests.get(f"{room_service_url}/rooms", headers={"Authorization": f"Bearer {token}"})
        response.raise_for_status()
        rooms = {room['id']: room for room in response.json()}
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Failed to fetch room details: {e}")
        return jsonify({"message": "Failed to fetch room details from room-service"}), 500

    # Build the report
    report = []
    for result in results:
        room_id = result.room_id
        room_details = rooms.get(room_id, {})
        report.append({
            "room_id": room_id,
            "room_name": room_details.get('name', 'Unknown'),
            "total_bookings": result.total_bookings,
            "total_hours": round(result.total_hours, 2),
            "capacity": room_details.get('capacity', 'Unknown')
        })

    return jsonify(report), 200

