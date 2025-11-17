"""
Patch: Fix NULL persona_idno records
Date: 2025-11-16
Issue: MultipleObjectsReturned error caused by records with persona_idno=NULL
Solution: Generate proper persona_idno values based on persona_id

Run with: python manage.py shell < maintenance/patches/16112025-repair-null-records.py
"""

import os
import django
from datetime import datetime

try:
    from django.conf import settings
    if not settings.configured:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mdb.settings')
        django.setup()
except ImportError:
    pass

from dbgestor.models import Persona

import logging

logger = logging.getLogger("dbgestor")

def main():
    logger.info(f'FIXING NULL PERSONA_IDNO RECORDS - {datetime.now()}')
    
    # Get NULL records
    null_records = Persona.objects.filter(persona_idno__isnull=True)
    
    if not null_records.exists():
        logger.info('No records with NULL persona_idno found. Database is clean.')
        return

    logger.info(f'Found {null_records.count()} records to fix:')

    
    # Create backup record of what we're about to fix
    backup_info = []
    for record in null_records:
        backup_info.append({
            'pk': record.persona_id,
            'name': record.nombre_normalizado,
            'created_at': str(record.created_at) if hasattr(record, 'created_at') else 'N/A'
        })
    
    print('\nRecords to be updated:')
    for info in backup_info:
        print(f"  PK: {info['pk']}, Name: \"{info['name']}\", Created: {info['created_at']}")
    
    print(f'\nAbout to update {len(backup_info)} records. Continue? (y/N): ', end='')
    try:
        confirmation = input().lower().strip()
        if confirmation != 'y':
            logger.warning('Operation cancelled by user.')
            return
    except (EOFError, KeyboardInterrupt):
        # For non-interactive execution
        logger.warning('Running in non-interactive mode, proceeding with fix...')

    print('\nApplying fixes...')
    fixed_count = 0
    
    for record in null_records:
        try:
            old_idno = record.persona_idno
            expected_idno = f'mx-sv-per-{str(record.persona_id).zfill(6)}'
            
            print(f'  PK: {record.persona_id} -> IDNO: {expected_idno}')
            
            # Update the record
            record.persona_idno = expected_idno
            record.save(update_fields=['persona_idno'])
            fixed_count += 1
            
        except Exception as e:
            logger.error(f'ERROR fixing PK {record.persona_id}: {e}')

    # Verification
    print(f'\Report:')
    print(f'  Records fixed: {fixed_count}')
    
    remaining_nulls = Persona.objects.filter(persona_idno__isnull=True).count()
    logger.warning(f'  Remaining NULL records: {remaining_nulls}')
    
    # Test that the fix worked
    try:
        result = Persona.objects.get(persona_idno=None)
        logger.error('ERROR: Still found records with None persona_idno!')
        return False
    except Persona.DoesNotExist:
        logger.info('SUCCESS: No more records with None persona_idno')
        return True
    except Persona.MultipleObjectsReturned as e:
        logger.error(f'ERROR: Still have multiple records: {e}')
        return False

if __name__ == '__main__':
    success = main()
    if success:
        logger.info('Patch completed successfully!')
    else:
        logger.error('Patch failed - manual intervention required!')
else:
    # When run via manage.py shell
    main()