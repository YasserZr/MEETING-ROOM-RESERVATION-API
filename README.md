# MEETING-ROOM-RESERVATION-API

A microservices-based API for managing meeting room reservations, using Kafka for inter-service communication.

## Services

### 1. User Service (`/user-service`)

*   Handles user registration, authentication, profile management, and JWT generation.
*   Manages user data (email, name, role).
*   **Consumes Kafka events** from the `reservations-topic` (currently logs them).
*   Port: 5000
*   Database: `users_db` (PostgreSQL)
*   Endpoints:
    *   `/auth/login/google/authorized`: Placeholder for Google OAuth callback (logic removed).
    *   `/users/me` (GET): Get current user's profile (requires JWT).
    *   `/users` (GET): List all users (potentially admin only).
    *   `/users` (POST): Create a new user (potentially admin only or internal).
    *   `/users` (GET): List all users (Admin only).
    *   `/users/<id>` (PUT): Update a user's role (Admin only).
        *   **Request Body:**
            ```json
            {
                "role": "staff"
            }
            ```
        *   **Response:**
            ```json
            {
                "id": 1,
                "email": "user@example.com",
                "role": "staff",
                "created_at": "2025-04-18T12:00:00"
            }
            ```
    *   `/users/<id>` (DELETE): Delete a user (Admin only).

### 2. Room Service (`/room-service`)

*   Manages meeting room information (name, capacity, description).
*   Provides CRUD operations for rooms. Requires admin privileges for CUD operations.
*   Port: 5001
*   Database: `rooms_db` (PostgreSQL)
*   Endpoints (require JWT):
    *   `/rooms/` (POST): Create a new room (Admin only).
        *   **Request Body:**
            ```json
            {
                "name": "Conference Room B",
                "capacity": 15,
                "description": "A medium-sized conference room with a whiteboard.",
                "amenities": {
                    "projector": false,
                    "whiteboard": true,
                    "video_conferencing": false
                }
            }
            ```
        *   **Response:**
            ```json
            {
                "id": 2,
                "name": "Conference Room B",
                "capacity": 15,
                "description": "A medium-sized conference room with a whiteboard.",
                "amenities": {
                    "projector": false,
                    "whiteboard": true,
                    "video_conferencing": false
                },
                "created_at": "2025-04-18T12:00:00"
            }
            ```
    *   `/rooms/` (GET): Get a list of all rooms.
    *   `/rooms/<id>` (GET): Get details of a specific room.
    *   `/rooms/<id>` (PUT): Update a room (Admin only).
        *   **Request Body:**
            ```json
            {
                "name": "Conference Room C",
                "capacity": 25,
                "description": "A large conference room with advanced video conferencing capabilities.",
                "amenities": {
                    "projector": true,
                    "whiteboard": true,
                    "video_conferencing": true
                }
            }
            ```
        *   **Response:**
            ```json
            {
                "id": 3,
                "name": "Conference Room C",
                "capacity": 25,
                "description": "A large conference room with advanced video conferencing capabilities.",
                "amenities": {
                    "projector": true,
                    "whiteboard": true,
                    "video_conferencing": true
                },
                "created_at": "2025-04-18T12:00:00"
            }
            ```
    *   `/rooms/<id>` (DELETE): Delete a room (Admin only).
    *   `/rooms/<id>/blackout` (POST): Add a blackout period for a room (Admin only).
        *   **Request Body:**
            ```json
            {
                "start_time": "2025-04-20T08:00:00",
                "end_time": "2025-04-20T18:00:00",
                "reason": "Maintenance"
            }
            ```
        *   **Response:**
            ```json
            {
                "id": 1,
                "room_id": 2,
                "start_time": "2025-04-20T08:00:00",
                "end_time": "2025-04-20T18:00:00",
                "reason": "Maintenance"
            }
            ```
    *   `/rooms/<id>/blackout` (GET): Get all blackout periods for a room.
    *   `/rooms/search` (GET): Search for meeting rooms based on specific criteria.
        *   **Query Parameters:**
            *   `capacity` (optional): Minimum capacity required.
            *   `amenities` (optional): Comma-separated list of required amenities (e.g., `projector,whiteboard`).
            *   `start_time` (optional): Start time for availability check (ISO 8601 format).
            *   `end_time` (optional): End time for availability check (ISO 8601 format).
        *   **Response:**
            ```json
            [
                {
                    "id": 1,
                    "name": "Conference Room A",
                    "capacity": 20,
                    "description": "A spacious conference room with natural light.",
                    "amenities": {
                        "projector": true,
                        "whiteboard": true,
                        "video_conferencing": true
                    },
                    "created_at": "2025-04-18T12:00:00"
                },
                {
                    "id": 2,
                    "name": "Conference Room B",
                    "capacity": 15,
                    "description": "A medium-sized conference room with a whiteboard.",
                    "amenities": {
                        "projector": false,
                        "whiteboard": true,
                        "video_conferencing": false
                    },
                    "created_at": "2025-04-18T12:00:00"
                }
            ]
            ```

### 3. Reservation Service (`/reservation-service`)

*   Handles the creation, retrieval, updating, and deletion of room reservations.
*   Connects users and rooms for specific time slots.
*   Includes logic to prevent overlapping reservations for the same room.
*   **Publishes Kafka events** (RESERVATION_CREATED, RESERVATION_UPDATED, RESERVATION_DELETED) to the `reservations-topic`.
*   Requires JWT for all operations. Users can manage their own reservations; Admins might have broader access (TBD).
*   **Booking Policies:**
    *   Different user roles have different booking policies:
        *   **Department Head:** Can book up to 90 days in advance.
        *   **Staff:** Can book up to 30 days in advance.
        *   **Guest:** Can book up to 7 days in advance.
*   **Blackout Period Enforcement:**
    *   Reservations cannot be made during blackout periods defined for a room.
*   **Calendar Integration:**
    *   Reservations are sent to external calendar systems (e.g., Google Calendar, Microsoft Outlook) as `.ics` events.
    *   Users will receive calendar invitations in their email inbox and can add them to their calendars.
*   **Booking and Cancellation Rules:**
    *   Reservations must be made at least `BOOKING_LEAD_TIME_HOURS` hours in advance (default: 1 hour).
    *   Cancellations must be made at least `CANCELLATION_DEADLINE_HOURS` hours before the reservation start time (default: 1 hour).
*   **Operating Hours:**
    *   Reservations must be made within the operating hours defined by `OPERATING_HOURS_START` and `OPERATING_HOURS_END` (default: 8:00 AM to 6:00 PM).
*   Port: 5002
*   Database: `reservations_db` (PostgreSQL)
*   Endpoints (require JWT):
    *   `/reservations/` (POST): Create a new reservation.
        *   **Request Body:**
            ```json
            {
                "room_id": 1,
                "start_time": "2025-04-19T10:00:00",
                "duration": 60,  // Duration in minutes
                "num_attendees": 10,  // Number of attendees
                "purpose": "Team meeting",  // Optional
                "description": "Discuss project milestones and deliverables",  // Optional
                "attendees": ["attendee1@example.com", "attendee2@example.com"],  // Optional
                "recurrence": "weekly",  // Optional: "weekly" or "monthly"
                "occurrences": 5  // Optional: Number of occurrences for the recurrence
            }
            ```
        *   **Response:**
            ```json
            [
                {
                    "id": 1,
                    "user_id": 2,
                    "room_id": 1,
                    "start_time": "2025-04-19T10:00:00",
                    "end_time": "2025-04-19T11:00:00",
                    "purpose": "Team meeting",
                    "description": "Discuss project milestones and deliverables",
                    "num_attendees": 10,
                    "attendees": ["attendee1@example.com", "attendee2@example.com"],
                    "created_at": "2025-04-18T12:00:00"
                },
                {
                    "id": 2,
                    "user_id": 2,
                    "room_id": 1,
                    "start_time": "2025-04-26T10:00:00",
                    "end_time": "2025-04-26T11:00:00",
                    "purpose": "Team meeting",
                    "description": "Discuss project milestones and deliverables",
                    "num_attendees": 10,
                    "created_at": "2025-04-18T12:00:00"
                }
            ]
            ```
    *   `/reservations/` (GET): Get reservations (can filter by `?user_id=self` or `?room_id=<id>`).
    *   `/reservations/<id>` (GET): Get details of a specific reservation.
    *   `/reservations/<id>` (PUT): Update a reservation (Owner or Admin).
        *   **Note:** Modifications are allowed only up to 1 hour before the reservation's start time.
        *   **Notification:** Attendees will receive an email notification if the reservation is updated.
    *   `/reservations/<id>` (DELETE): Delete a reservation (Owner or Admin).
        *   **Note:** Cancellations are allowed only up to 1 hour before the reservation's start time.
        *   **Notification:** Attendees will receive an email notification if the reservation is canceled.
    *   `/reports/usage` (GET): Generate a report on meeting room usage.
        *   **Query Parameters:**
            *   `start_time` (optional): Start of the time range (ISO 8601 format).
            *   `end_time` (optional): End of the time range (ISO 8601 format).
        *   **Response:**
            ```json
            [
                {
                    "room_id": 1,
                    "room_name": "Conference Room A",
                    "total_bookings": 15,
                    "total_hours": 45.5,
                    "capacity": 20
                },
                {
                    "room_id": 2,
                    "room_name": "Conference Room B",
                    "total_bookings": 10,
                    "total_hours": 30.0,
                    "capacity": 15
                }
            ]
            ```

### 4. Kafka & Zookeeper

*   Apache Kafka is used for asynchronous communication between services.
*   Zookeeper is required by Kafka for cluster management.
*   Kafka Port (Internal): `kafka:9092`
*   Kafka Port (External): `localhost:9092` (if mapped in docker-compose)
*   Zookeeper Port: `2181`

## Setup and Running

1.  **Prerequisites:** Docker, Docker Compose.
2.  **Environment Variables:**
    *   Create a `.env` file in the root directory (`/home/hadoop/MEETING-ROOM-RESERVATION-API`).
    *   Add your Google OAuth credentials:
        ```env
        GOOGLE_CLIENT_ID=YOUR_GOOGLE_CLIENT_ID
        GOOGLE_CLIENT_SECRET=YOUR_GOOGLE_CLIENT_SECRET

        # Optional: Override default Kafka topic name
        # KAFKA_RESERVATIONS_TOPIC=my-reservations
        ```
    *   Ensure `JWT_SECRET_KEY` and `SECRET_KEY` are set (defaults provided in `docker-compose.yml` for dev).
    *   **Email Notifications:**
        *   Email notifications for reservations, modifications, and cancellations can be enabled or disabled using the `ENABLE_EMAIL_NOTIFICATIONS` environment variable.
            *   `ENABLE_EMAIL_NOTIFICATIONS=true` (default): Email notifications are enabled.
            *   `ENABLE_EMAIL_NOTIFICATIONS=false`: Email notifications are disabled.
3.  **Build and Run:**
    ```bash
    docker-compose up --build -d
    ```
    Wait for all services, including Kafka and Zookeeper, to become healthy. Check logs: `docker-compose logs -f`
4.  **Database Migrations:**
    (Run these after services are up if needed)
    ```bash
    # For user-service
    docker-compose exec user-service flask db init # Only first time ever
    docker-compose exec user-service flask db migrate -m "Initial user migration"
    docker-compose exec user-service flask db upgrade

    # For room-service
    docker-compose exec room-service flask db init # Only first time ever
    docker-compose exec room-service flask db migrate -m "Initial room migration"
    docker-compose exec room-service flask db upgrade

    # For reservation-service
    docker-compose exec reservation-service flask db init # Only first time ever
    docker-compose exec reservation-service flask db migrate -m "Initial reservation migration"
    docker-compose exec reservation-service flask db upgrade
    ```
5.  **Access Services:**
    *   User Service: `http://localhost:5000`
    *   Room Service: `http://localhost:5001`
    *   Reservation Service: `http://localhost:5002`
6.  **Check Kafka Events:**
    *   Create/Update/Delete a reservation via the Reservation Service API.
    *   Check the logs of the `user-service` container for messages indicating received Kafka events:
        ```bash
        docker-compose logs -f user-service
        ```

## Teardown

```bash
docker-compose down -v # -v removes volumes (database data, kafka data if volumes defined)
```
