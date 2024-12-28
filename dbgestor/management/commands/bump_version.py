from django.core.management.base import BaseCommand
from datetime import datetime
import re

class Command(BaseCommand):
    help = 'Bump version number'

    def add_arguments(self, parser):
        parser.add_argument('part', type=str, choices=['major', 'minor', 'patch'])

    def handle(self, *args, **kwargs):
        version_file_path = 'dbgestor/version.py'
        with open(version_file_path, 'r') as f:
            content = f.read()

        # Extract current version
        version_match = re.search(r'VERSION = \((\d+), (\d+), (\d+)\)', content)
        if not version_match:
            raise ValueError("Could not find version tuple in version.py")

        major, minor, patch = map(int, version_match.groups())

        # Update version based on argument
        part = kwargs['part']
        if part == 'major':
            major += 1
            minor = 0
            patch = 0
        elif part == 'minor':
            minor += 1
            patch = 0
        else:  # patch
            patch += 1

        # Update version file
        new_version = f'VERSION = ({major}, {minor}, {patch})'
        new_date = f"VERSION_DATE = '{datetime.now().strftime('%Y-%m-%d')}'"
        
        content = re.sub(r'VERSION = \(\d+, \d+, \d+\)', new_version, content)
        content = re.sub(r"VERSION_DATE = '[0-9-]+'", new_date, content)

        with open(version_file_path, 'w') as f:
            f.write(content)

        self.stdout.write(self.style.SUCCESS(f'Version bumped to {major}.{minor}.{patch}')) 