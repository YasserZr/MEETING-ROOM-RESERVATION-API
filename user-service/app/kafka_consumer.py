import json
import logging
import threading
import time
from kafka import KafkaConsumer
from kafka.errors import KafkaError
from flask import current_app

logger = logging.getLogger(__name__)
consumer_thread = None
stop_event = threading.Event()

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

