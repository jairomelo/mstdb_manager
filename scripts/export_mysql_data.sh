#!/bin/bash

# Database Migration: MySQL to PostgreSQL
# This script helps migrate data from MySQL to PostgreSQL for TrayectoriasAfro

set -e

echo "====================================="
echo "MySQL to PostgreSQL Migration Script"
echo "====================================="
echo ""

# Configuration
MYSQL_HOST="${MYSQL_HOST:-localhost}"
MYSQL_PORT="${MYSQL_PORT:-3306}"
MYSQL_USER="${MYSQL_USER:-root}"
MYSQL_DB="${MYSQL_DB:-trayectorias}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo "Step 1: Export data from MySQL using Django dumpdata"
echo "-----------------------------------------------------"

# Check if we're in the correct directory
if [ ! -f "manage.py" ]; then
    echo "Error: manage.py not found. Please run this script from the mstdb_manager directory."
    exit 1
fi

# Export all data as JSON fixtures
echo "Exporting data to JSON fixtures..."
OUTPUT_FILE="$BACKUP_DIR/mysql_dump_${TIMESTAMP}.json"

python manage.py dumpdata \
    --natural-foreign \
    --natural-primary \
    --indent 2 \
    --exclude auth.permission \
    --exclude contenttypes \
    --exclude admin.logentry \
    --exclude sessions.session \
    --output "$OUTPUT_FILE"

if [ $? -eq 0 ]; then
    echo "✓ Data exported successfully to: $OUTPUT_FILE"
    echo "  File size: $(du -h "$OUTPUT_FILE" | cut -f1)"
else
    echo "✗ Export failed!"
    exit 1
fi

echo ""
echo "Step 2: Backup complete!"
echo "-----------------------------------------------------"
echo ""
echo "Next steps:"
echo "1. Update your .env file with PostgreSQL connection details"
echo "2. Start the PostgreSQL container:"
echo"   docker-compose up -d postgres"
echo "3. Run migrations on PostgreSQL:"
echo "   docker-compose exec web python manage.py migrate"
echo "4. Load the data into PostgreSQL:"
echo "   docker-compose exec web python manage.py loaddata $OUTPUT_FILE"
echo "5. Reset sequences for auto-increment fields:"
echo "   docker-compose exec web python manage.py sqlsequencereset dbgestor | docker-compose exec -T postgres psql \$DATABASE_URL"
echo ""
echo "For detailed instructions, see DOCKER.md"
echo "====================================="
