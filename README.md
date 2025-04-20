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

### 2. Room Service (`/room-service`)

*   Manages meeting room information (name, capacity, description).
*   Provides CRUD operations for rooms. Requires admin privileges for CUD operations.
*   Port: 5001
*   Database: `rooms_db` (PostgreSQL)
*   Endpoints (require JWT):
    *   `/rooms/` (POST): Create a new room (Admin only).
    *   `/rooms/` (GET): Get a list of all rooms.
    *   `/rooms/<id>` (GET): Get details of a specific room.
    *   `/rooms/<id>` (PUT): Update a room (Admin only).
    *   `/rooms/<id>` (DELETE): Delete a room (Admin only).

### 3. Reservation Service (`/reservation-service`)

*   Handles the creation, retrieval, updating, and deletion of room reservations.
*   Connects users and rooms for specific time slots.
*   Includes logic to prevent overlapping reservations for the same room.
*   **Publishes Kafka events** (RESERVATION_CREATED, RESERVATION_UPDATED, RESERVATION_DELETED) to the `reservations-topic`.
*   Requires JWT for all operations. Users can manage their own reservations; Admins might have broader access (TBD).
*   Port: 5002
*   Database: `reservations_db` (PostgreSQL)
*   Endpoints (require JWT):
    *   `/reservations/` (POST): Create a new reservation.
    *   `/reservations/` (GET): Get reservations (can filter by `?user_id=self` or `?room_id=<id>`).
    *   `/reservations/<id>` (GET): Get details of a specific reservation.
    *   `/reservations/<id>` (PUT): Update a reservation (Owner or Admin).
    *   `/reservations/<id>` (DELETE): Delete a reservation (Owner or Admin).

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
