#!/bin/bash

# PostgreSQL Database Backup Script for TrayectoriasAfro
# Updated for containerized PostgreSQL deployment

set -e

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/backups}"
DB_NAME="${POSTGRES_DB:-trayectorias}"
DB_USER="${POSTGRES_USER:-trayectorias_user}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-30}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/trayectorias_${TIMESTAMP}.sql"
LOG_FILE="/app/appslogs/backup.log"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"
mkdir -p "$(dirname "$LOG_FILE")"

echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting PostgreSQL backup" | tee -a "$LOG_FILE"

# Perform backup
if pg_dump -U "$DB_USER" "$DB_NAME" > "$BACKUP_FILE" 2>&1; then
    # Compress backup
    gzip "$BACKUP_FILE"
    
    BACKUP_SIZE=$(du -h "${BACKUP_FILE}.gz" | cut -f1)
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Backup completed successfully: ${BACKUP_FILE}.gz (Size: $BACKUP_SIZE)" | tee -a "$LOG_FILE"
    
    # Delete old backups
    DELETED=$(find "$BACKUP_DIR" -name "trayectorias_*.sql.gz" -type f -mtime +$KEEP_DAYS -delete -print | wc -l)
    if [ "$DELETED" -gt 0 ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Removed $DELETED old backup(s) (>${KEEP_DAYS} days)" | tee -a "$LOG_FILE"
    fi
    
    exit 0
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Backup failed for $DB_NAME" | tee -a "$LOG_FILE"
    exit 1
fi
