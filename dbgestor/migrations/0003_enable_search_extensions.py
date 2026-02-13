# Generated migration for PostgreSQL search extensions
# Enables pg_trgm and unaccent extensions for full-text search

from django.contrib.postgres.operations import TrigramExtension, UnaccentExtension
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dbgestor', '0002_corporacion_is_published_documento_is_published_and_more'),
    ]

    operations = [
        # Enable PostgreSQL extensions for full-text search
        TrigramExtension(),  # Fuzzy string matching (trigram similarity)
        UnaccentExtension(),  # Remove accents for better Spanish text search
    ]
