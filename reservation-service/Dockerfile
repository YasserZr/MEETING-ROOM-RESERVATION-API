# Base image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=run.py

# Install curl for health checks (if needed, already present in base image usually)
# RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Create and set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
# Consider installing build dependencies if needed by kafka-python-ng, though unlikely for -ng
# RUN apt-get update && apt-get install -y gcc libffi-dev && \
RUN pip install --upgrade pip && pip install -r requirements.txt
# && apt-get remove -y gcc libffi-dev && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . .

# Expose default port (can be overridden by docker-compose command)
EXPOSE 5002

# Default command (can be overridden by docker-compose command)
CMD ["python", "run.py", "--port=5002"]
