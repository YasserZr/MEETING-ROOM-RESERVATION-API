# Base image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Create and set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy application code
COPY . .

# Expose Flask port
EXPOSE 5000

# Create log directory
RUN mkdir -p /var/log/user-service

# Set volume for logs
VOLUME ["/var/log/user-service"]

# Run the app using host 0.0.0.0
CMD ["python", "run.py"]
