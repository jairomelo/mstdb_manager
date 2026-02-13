#!/bin/bash

# Import PostgreSQL Data Script
# Loads Django fixtures into PostgreSQL database

set -e

echo "========================================"
echo "PostgreSQL Data Import Script"
echo "========================================"
echo ""

if [ -z "$1" ]; then
    echo "Usage: $0 <path-to-fixture-file.json>"
    echo ""
    echo "Example:"
    echo "  $0 backups/mysql_dump_20260212_120000.json"
    exit 1
fi

FIXTURE_FILE="$1"

if [ ! -f "$FIXTURE_FILE" ]; then
    echo "Error: Fixture file not found: $FIXTURE_FILE"
    exit 1
fi

echo "Fixture file: $FIXTURE_FILE"
echo "File size: $(du -h "$FIXTURE_FILE" | cut -f1)"
echo ""

# Check if we're in a container or host
if [ -f "/.dockerenv" ]; then
    # We're inside a container
    echo "Running inside Docker container..."
    MANAGE_PY="python manage.py"
else
    # We're on the host, use docker-compose
    echo "Running from host, using docker-compose..."
    MANAGE_PY="docker-compose exec web python manage.py"
fi

echo ""
echo "Step 1: Loading fixtures into PostgreSQL..."
echo "-----------------------------------------------------"

$MANAGE_PY loaddata "$FIXTURE_FILE"

if [ $? -eq 0 ]; then
    echo "✓ Fixtures loaded successfully!"
else
    echo "✗ Failed to load fixtures!"
    exit 1
fi

echo ""
echo "Step 2: Resetting database sequences..."
echo "-----------------------------------------------------"

# Reset sequences for custom primary keys
if [ -f "/.dockerenv" ]; then
    python manage.py sqlsequencereset dbgestor cataloguers api | psql $DATABASE_URL
else
    docker-compose exec web python manage.py sqlsequencereset dbgestor cataloguers api | docker-compose exec -T postgres psql $DATABASE_URL
fi

if [ $? -eq 0 ]; then
    echo "✓ Sequences reset successfully!"
else
    echo "✗ Failed to reset sequences!"
    echo "  You may need to run this manually."
fi

echo ""
echo "Step 3: Verifying data..."
echo "-----------------------------------------------------"

# Count records in key models
echo "Record counts:"
$MANAGE_PY shell -c "
from dbgestor.models import Documento, PersonaEsclavizada, PersonaNoEsclavizada, Lugar, Corporacion
print(f'  Documentos: {Documento.objects.count()}')
print(f'  Personas Esclavizadas: {PersonaEsclavizada.objects.count()}')
print(f'  Personas No Esclavizadas: {PersonaNoEsclavizada.objects.count()}')
print(f'  Lugares: {Lugar.objects.count()}')
print(f'  Corporaciones: {Corporacion.objects.count()}')
"

echo ""
echo "========================================"
echo "Migration complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Verify data integrity by spot-checking records"
echo "2. Test search functionality"
echo "3. Test API endpoints"
echo "4. Run full application tests"
echo ""
