from app import create_app
import os
from dotenv import load_dotenv
import argparse # Import argparse

# Load environment variables from .env file located in the parent directory
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env') # Adjust path to root .env
load_dotenv(dotenv_path=dotenv_path)

app = create_app()

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Run Room Service')
    parser.add_argument('--port', type=int, default=5001, help='Port to run the service on')
    args = parser.parse_args()

    port = args.port
    app.run(host="0.0.0.0", port=port)
    app.logger.info(f"Room service running on port {port}")
