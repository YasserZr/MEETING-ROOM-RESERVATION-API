import json
import logging
import threading
import time
import os
from kafka import KafkaConsumer
from kafka.errors import KafkaError
from flask import current_app, jsonify
from .models import db, User  # Assuming you need db and User model

logger = logging.getLogger(__name__)
consumer_thread = None
stop_event = threading.Event()

# Define Kafka configuration using environment variables
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
RESERVATIONS_TOPIC = os.getenv('KAFKA_RESERVATIONS_TOPIC', 'reservations-topic')
GROUP_ID = 'user-service-group' # Define a consumer group ID

def process_message(message):
    """Placeholder function to process received Kafka messages."""
    try:
        event = json.loads(message.value.decode('utf-8'))
        event_type = event.get("type")
        payload = event.get("payload")
        logger.info(f"Received Kafka Event Type: {event_type}, Payload ID: {payload.get('id') if payload else 'N/A'}")
        # Add actual processing logic here based on event_type
        # e.g., update user data, send notification, etc.
        if event_type == "RESERVATION_CREATED":
            logger.info(f"Processing RESERVATION_CREATED for user {payload.get('user_id')}")
        elif event_type == "RESERVATION_UPDATED":
             logger.info(f"Processing RESERVATION_UPDATED for user {payload.get('user_id')}")
        elif event_type == "RESERVATION_DELETED":
             logger.info(f"Processing RESERVATION_DELETED for user {payload.get('user_id')}")

    except json.JSONDecodeError:
        logger.error(f"Failed to decode Kafka message value: {message.value}")
    except Exception as e:
        logger.error(f"Error processing Kafka message: {e}", exc_info=True)


def consume_messages(app):
    """Runs the Kafka consumer loop."""
    # Need app context to access config
    with app.app_context():
        bootstrap_servers = current_app.config.get('KAFKA_BOOTSTRAP_SERVERS')
        topic = current_app.config.get('KAFKA_RESERVATIONS_TOPIC')
        group_id = current_app.config.get('KAFKA_CONSUMER_GROUP')

        if not all([bootstrap_servers, topic, group_id]):
            logger.error("Kafka consumer configuration missing (servers, topic, or group_id). Consumer not starting.")
            return

        logger.info(f"Starting Kafka consumer thread for topic '{topic}', group '{group_id}'...")
        consumer = None
        while not stop_event.is_set():
            try:
                if consumer is None:
                    logger.info(f"Attempting to connect Kafka consumer to {bootstrap_servers}...")
                    consumer = KafkaConsumer(
                        topic,
                        bootstrap_servers=bootstrap_servers.split(','),
                        group_id=group_id,
                        auto_offset_reset='earliest', # Start reading at the earliest message if no offset found
                        # value_deserializer=lambda m: json.loads(m.decode('utf-8')), # Can deserialize here
                        consumer_timeout_ms=1000, # Timeout to allow checking stop_event
                        enable_auto_commit=True, # Auto commit offsets
                        security_protocol='PLAINTEXT' # Explicitly set, adjust if using SSL/SASL
                    )
                    logger.info(f"Kafka consumer connected to topic '{topic}'.")

                for message in consumer:
                    if stop_event.is_set():
                        break
                    process_message(message)
                    # Manual commit if enable_auto_commit=False
                    # consumer.commit()

            except KafkaError as e:
                logger.error(f"Kafka error in consumer loop: {e}. Retrying in 10 seconds...")
                if consumer:
                    consumer.close()
                consumer = None
                time.sleep(10) # Wait before retrying connection
            except Exception as e:
                 logger.error(f"Unexpected error in consumer loop: {e}. Retrying in 10 seconds...", exc_info=True)
                 if consumer:
                     consumer.close()
                 consumer = None
                 time.sleep(10) # Wait before retrying

        if consumer:
            consumer.close()
        logger.info("Kafka consumer thread stopped.")


def start_consumer_thread(app):
    """Starts the Kafka consumer in a background thread."""
    global consumer_thread
    if consumer_thread is None or not consumer_thread.is_alive():
        stop_event.clear()
        # Pass the app instance itself, not just current_app proxy
        consumer_thread = threading.Thread(target=consume_messages, args=(app,), daemon=True)
        consumer_thread.start()
        logger.info("Kafka consumer background thread initiated.")
    else:
        logger.info("Kafka consumer thread already running.")

def stop_consumer_thread():
    """Signals the consumer thread to stop."""
    global consumer_thread
    if consumer_thread and consumer_thread.is_alive():
        logger.info("Stopping Kafka consumer thread...")
        stop_event.set()
        consumer_thread.join(timeout=10) # Wait for thread to finish
        if consumer_thread.is_alive():
             logger.warning("Kafka consumer thread did not stop gracefully.")
        consumer_thread = None
    else:
        logger.info("Kafka consumer thread not running or already stopped.")

def consume_reservations(app):
    """
    Kafka consumer function that runs in a background thread.
    Needs the Flask app instance to work within the application context.
    """
    consumer = None # Initialize consumer to None
    try:
        with app.app_context(): # Create an application context
            current_app.logger.info(f"Attempting to connect Kafka consumer to {KAFKA_BOOTSTRAP_SERVERS}...")
            consumer = KafkaConsumer(
                RESERVATIONS_TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS.split(','),
                auto_offset_reset='earliest',
                group_id=GROUP_ID,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                consumer_timeout_ms=1000
            )
            current_app.logger.info(f"Kafka consumer connected to topic '{RESERVATIONS_TOPIC}'.")

            while True: # Keep consuming messages
                # Check for stop signal if you implement one
                # if stop_event.is_set():
                #    break

                for message in consumer:
                    try:
                        reservation_data = message.value
                        current_app.logger.info(f"Received reservation message: {reservation_data}")

                        # --- Process the message ---
                        user_id = reservation_data.get('user_id')
                        status = reservation_data.get('status')

                        if user_id and status == 'cancelled':
                            user = User.query.get(user_id)
                            if user:
                                current_app.logger.info(f"Processing cancellation for user {user_id}")
                                # db.session.commit() # Commit if changes were made
                            else:
                                current_app.logger.warning(f"User {user_id} not found for cancellation.")

                    except json.JSONDecodeError:
                        current_app.logger.error(f"Failed to decode JSON message: {message.value}")
                    except Exception as e:
                        # This exception handling is now INSIDE the app context
                        current_app.logger.error(f"Error processing Kafka message: {e}", exc_info=True)

                # Optional sleep if consumer_timeout_ms is not used or is long
                # time.sleep(0.1)

    except Exception as e:
        # Log general consumer errors (like connection issues)
        # Use the passed 'app' object's logger if current_app is unavailable
        logger_instance = current_app.logger if current_app else app.logger
        logger_instance.error(f"Kafka consumer error: {e}", exc_info=True)
    finally:
        if consumer:
            consumer.close()
            logger_instance = current_app.logger if current_app else app.logger
            logger_instance.info("Kafka consumer closed.")


def start_kafka_consumer_thread(app):
    """Starts the Kafka consumer in a background daemon thread."""
    current_app.logger.info(f"Starting Kafka consumer thread for topic '{RESERVATIONS_TOPIC}', group '{GROUP_ID}'...")
    # Pass the app instance to the target function
    thread = threading.Thread(target=consume_reservations, args=(app,), daemon=True)
    thread.start()
    current_app.logger.info("Kafka consumer background thread initiated.")
    return thread

