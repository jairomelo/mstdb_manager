#!/bin/bash
set -e

echo "======================================"
echo "TrayectoriasAfro Docker Entrypoint"
echo "======================================"

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
while ! pg_isready -h "${DATABASE_HOST:-postgres}" -p "${DATABASE_PORT:-5432}" -U "${POSTGRES_USER:-trayectorias_user}" > /dev/null 2>&1; do
    echo "PostgreSQL is unavailable - sleeping"
    sleep 2
done
echo "✓ PostgreSQL is ready"

# Enable PostgreSQL extensions
echo "Enabling PostgreSQL extensions..."
psql $DATABASE_URL -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;" 2>/dev/null || echo "pg_trgm extension already exists or cannot be created (may need superuser)"
psql $DATABASE_URL -c "CREATE EXTENSION IF NOT EXISTS unaccent;" 2>/dev/null || echo "unaccent extension already exists or cannot be created (may need superuser)"
echo "✓ Extensions configured"

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput
echo "✓ Migrations complete"

# Create cache table if needed
echo "Setting up cache table..."
python manage.py createcachetable 2>/dev/null || echo "Cache table already exists"

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput
echo "✓ Static files collected"

echo "======================================"
echo "Starting application..."
echo "======================================"

# Execute the main container command
exec "$@"
