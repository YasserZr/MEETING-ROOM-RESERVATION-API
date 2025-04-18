from dotenv import load_dotenv
import os
import atexit # Import atexit for cleanup

# Load environment variables from .env file located in the parent directory
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env') # Adjust path if .env is elsewhere
load_dotenv(dotenv_path=dotenv_path)

from app import create_app
# Import consumer start/stop functions
from app.kafka_consumer import start_consumer_thread, stop_consumer_thread

app = create_app()

# Start Kafka consumer thread in the main process after app creation
# Ensure this runs only once, e.g., not in Flask's reloader process
if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    start_consumer_thread(app)
    # Register cleanup function
    atexit.register(stop_consumer_thread)


if __name__ == '__main__':
    # Use host='0.0.0.0' to be accessible externally/within Docker
    app.run(host='0.0.0.0', port=5000, debug=os.getenv('FLASK_ENV') == 'development')
