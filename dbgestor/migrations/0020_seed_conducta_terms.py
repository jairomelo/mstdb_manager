from django.db import migrations

# Seed inicial del vocabulario canónico de conducta. La lista definitiva de
# aliases se acordará en reunión; 'busque' y 'escap*' (prefijo) quedan como
# candidatos y el backfill los trata como revisión manual.
SEED = [
    {
        'canonico': 'huído',
        'aliases': ['huido', 'hullo', 'huyo', 'huyeron', 'escap*', 'busque'],
        'descripcion': 'Huida / escape de la persona esclavizada (cimarronaje).',
    },
]


def seed(apps, schema_editor):
    ConductaTerm = apps.get_model('dbgestor', 'ConductaTerm')
    for entry in SEED:
        ConductaTerm.objects.update_or_create(
            canonico=entry['canonico'],
            defaults={
                'aliases': entry['aliases'],
                'descripcion': entry['descripcion'],
            },
        )


def unseed(apps, schema_editor):
    ConductaTerm = apps.get_model('dbgestor', 'ConductaTerm')
    for entry in SEED:
        ConductaTerm.objects.filter(canonico=entry['canonico']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('dbgestor', '0019_conductaterm_personaesclavizada_conducta_terms'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
