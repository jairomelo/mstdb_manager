from django.db import migrations


def publish_existing_lecciones(apps, schema_editor):
    Leccion = apps.get_model('dbgestor', 'Leccion')
    Leccion.objects.update(is_published=True)


class Migration(migrations.Migration):

    dependencies = [
        ('dbgestor', '0015_leccion_created_by_leccion_is_published_and_more'),
    ]

    operations = [
        migrations.RunPython(publish_existing_lecciones, migrations.RunPython.noop),
    ]
