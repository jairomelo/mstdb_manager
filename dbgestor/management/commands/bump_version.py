from django.core.management.base import BaseCommand
from datetime import datetime
import re

class Command(BaseCommand):
    help = 'Bump version number. Use --target to choose code (default) or schema versioning.'

    def add_arguments(self, parser):
        parser.add_argument('part', type=str, choices=['major', 'minor', 'patch'])
        parser.add_argument(
            '--target',
            type=str,
            choices=['code', 'schema'],
            default='code',
            help='Which version to bump: code (default) or schema (deposit CSV structure).',
        )

    def handle(self, *args, **kwargs):
        version_file_path = 'dbgestor/version.py'
        with open(version_file_path, 'r') as f:
            content = f.read()

        part = kwargs['part']
        target = kwargs['target']
        today = datetime.now().strftime('%Y-%m-%d')

        if target == 'schema':
            match = re.search(r'SCHEMA_VERSION = \((\d+), (\d+), (\d+)\)', content)
            if not match:
                raise ValueError("Could not find SCHEMA_VERSION tuple in version.py")
            major, minor, patch = map(int, match.groups())
            major, minor, patch = self._bump(part, major, minor, patch)
            content = re.sub(
                r'SCHEMA_VERSION = \(\d+, \d+, \d+\)',
                f'SCHEMA_VERSION = ({major}, {minor}, {patch})',
                content,
            )
            content = re.sub(r"SCHEMA_VERSION_DATE = '[0-9-]+'", f"SCHEMA_VERSION_DATE = '{today}'", content)
        else:
            match = re.search(r'^VERSION = \((\d+), (\d+), (\d+)\)', content, re.MULTILINE)
            if not match:
                raise ValueError("Could not find VERSION tuple in version.py")
            major, minor, patch = map(int, match.groups())
            major, minor, patch = self._bump(part, major, minor, patch)
            content = re.sub(
                r'^VERSION = \(\d+, \d+, \d+\)',
                f'VERSION = ({major}, {minor}, {patch})',
                content,
                flags=re.MULTILINE,
            )
            content = re.sub(r"VERSION_DATE = '[0-9-]+'", f"VERSION_DATE = '{today}'", content)

        with open(version_file_path, 'w') as f:
            f.write(content)

        label = 'Schema version' if target == 'schema' else 'Version'
        self.stdout.write(self.style.SUCCESS(f'{label} bumped to {major}.{minor}.{patch}'))

    def _bump(self, part, major, minor, patch):
        if part == 'major':
            return major + 1, 0, 0
        elif part == 'minor':
            return major, minor + 1, 0
        else:
            return major, minor, patch + 1 