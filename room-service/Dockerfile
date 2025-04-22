# Base image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=run.py
ENV LOG_LEVEL=INFO

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Create and set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt && pip install prometheus-flask-exporter

# Copy application code
COPY . .

# Create log directory
RUN mkdir -p /var/log/room-service

# Set volume for logs
VOLUME ["/var/log/room-service"]

# Expose default port (can be overridden by docker-compose command)
EXPOSE 5001
# Expose metrics port for Prometheus
EXPOSE 9090

# Default command (can be overridden by docker-compose command)
CMD ["python", "run.py", "--port=5001"]
