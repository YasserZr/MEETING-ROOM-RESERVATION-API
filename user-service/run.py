from app import create_app
import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000) # Changed port to 5000
