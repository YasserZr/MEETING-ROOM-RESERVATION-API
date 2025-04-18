import json
import logging
from kafka import KafkaProducer
from kafka.errors import KafkaError
from flask import current_app

logger = logging.getLogger(__name__)
producer = None

def get_kafka_producer():
    """Initializes and returns a KafkaProducer instance."""
    global producer
    if producer is None:
        bootstrap_servers = current_app.config.get('KAFKA_BOOTSTRAP_SERVERS')
        if not bootstrap_servers:
            logger.error("KAFKA_BOOTSTRAP_SERVERS not configured.")
            return None
        try:
            producer = KafkaProducer(
                bootstrap_servers=bootstrap_servers.split(','), # Handle comma-separated list
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: str(k).encode('utf-8') if k else None,
                retries=5, # Retry sending messages on failure
                acks='all' # Wait for all replicas to acknowledge
            )
            logger.info(f"KafkaProducer initialized for servers: {bootstrap_servers}")
        except KafkaError as e:
            logger.error(f"Failed to initialize KafkaProducer: {e}")
            producer = None # Ensure producer remains None on failure
    return producer

def send_reservation_event(event_type, reservation_data):
    """Sends a reservation event to the configured Kafka topic."""
    kafka_producer = get_kafka_producer()
    topic = current_app.config.get('KAFKA_RESERVATIONS_TOPIC')

    if not kafka_producer or not topic:
        logger.error("Kafka producer or topic not available. Cannot send event.")
        return

    event = {
        "type": event_type,
        "payload": reservation_data # reservation_data should be a dict (e.g., from reservation.to_dict())
    }
    reservation_id = reservation_data.get('id')

    try:
        logger.info(f"Sending event to Kafka topic '{topic}': {event}")
        future = kafka_producer.send(topic, key=reservation_id, value=event)
        # Optional: Block for synchronous send or add callbacks for async handling
        # result = future.get(timeout=10)
        # logger.info(f"Event sent successfully: {result}")
        # Add callbacks for better async handling
        future.add_callback(on_send_success)
        future.add_errback(on_send_error)
    except KafkaError as e:
        logger.error(f"Failed to send event to Kafka topic '{topic}': {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while sending Kafka event: {e}")

# Optional callbacks for async send
def on_send_success(record_metadata):
    logger.info(f"Message sent successfully to topic '{record_metadata.topic}' partition {record_metadata.partition} offset {record_metadata.offset}")

def on_send_error(excp):
    logger.error('Error sending message to Kafka', exc_info=excp)

# Optional: Function to close producer on app shutdown
# def close_kafka_producer(app=None):
#     global producer
#     if producer:
#         producer.flush()
#         producer.close()
#         producer = None
#         logger.info("KafkaProducer closed.")
