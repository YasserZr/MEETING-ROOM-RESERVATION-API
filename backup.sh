#!/bin/bash

# Database Backup Script for Meeting Room Reservation System
# This script backs up all PostgreSQL databases and uploads them to AWS S3

# Set variables
BACKUP_DIR="/tmp/database_backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="/var/log/db_backup.log"
S3_BUCKET="meeting-room-backups"  # Replace with your S3 bucket name
S3_PREFIX="daily-backups"
RETENTION_DAYS=30  # Number of days to keep backups in S3

# AWS S3 bucket lifecycle policy should be configured separately in AWS console
# for automatic deletion of old backups

# Database connection details
declare -A DB_CONFIGS=(
  ["user-db"]="host=localhost port=5433 user=postgres password=postgres dbname=users_db"
  ["room-db"]="host=localhost port=5434 user=postgres password=postgres dbname=rooms_db"
  ["reservation-db"]="host=localhost port=5435 user=postgres password=postgres dbname=reservations_db"
  ["sonarqube-db"]="host=localhost port=5436 user=sonar password=sonar dbname=sonar"
)

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Log function
log_message() {
  echo "$(date +"%Y-%m-%d %H:%M:%S") - $1" >> $LOG_FILE
  echo "$(date +"%Y-%m-%d %H:%M:%S") - $1"
}

# Start backup process
log_message "Starting database backup process"

# Loop through databases and create backups
for db_name in "${!DB_CONFIGS[@]}"; do
  log_message "Backing up $db_name database"
  
  # Get connection details
  conn_details="${DB_CONFIGS[$db_name]}"
  
  # Extract connection parameters
  db_host=$(echo $conn_details | grep -oP 'host=\K[^ ]+')
  db_port=$(echo $conn_details | grep -oP 'port=\K[^ ]+')
  db_user=$(echo $conn_details | grep -oP 'user=\K[^ ]+')
  db_pass=$(echo $conn_details | grep -oP 'password=\K[^ ]+')
  db_name_actual=$(echo $conn_details | grep -oP 'dbname=\K[^ ]+')
  
  # Set backup file name
  BACKUP_FILE="$BACKUP_DIR/${db_name}_${TIMESTAMP}.sql.gz"
  
  # Export database using pg_dump and compress
  PGPASSWORD=$db_pass pg_dump -h $db_host -p $db_port -U $db_user -d $db_name_actual -F c | gzip > $BACKUP_FILE
  
  # Check if backup was successful
  if [ $? -eq 0 ]; then
    log_message "Successfully created backup of $db_name at $BACKUP_FILE"
    
    # Upload to S3
    aws s3 cp $BACKUP_FILE s3://$S3_BUCKET/$S3_PREFIX/$db_name/$(basename $BACKUP_FILE)
    
    if [ $? -eq 0 ]; then
      log_message "Successfully uploaded $db_name backup to S3"
    else
      log_message "ERROR: Failed to upload $db_name backup to S3"
    fi
  else
    log_message "ERROR: Failed to create backup of $db_name"
  fi
done

# Cleanup local backups
log_message "Cleaning up local backup files"
rm -f $BACKUP_DIR/*.sql.gz

log_message "Database backup process completed"

# Optional: Delete old backups from S3 (if not using S3 lifecycle policies)
# aws s3 ls s3://$S3_BUCKET/$S3_PREFIX/ --recursive | grep -v -E "($(date +"%Y%m%d" --date="$RETENTION_DAYS days ago"))" | awk '{print $4}' | xargs -I {} aws s3 rm s3://$S3_BUCKET/{}

exit 0