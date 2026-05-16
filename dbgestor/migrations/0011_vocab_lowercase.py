from django.db import migrations


def lowercase_vocab(apps, schema_editor):
    """Lowercase all existing Calidades, Hispanizaciones, and Etonimos records.
    Handles potential duplicates caused by case normalization by keeping the
    first (lowest PK) record and skipping any that would create a conflict.
    """
    for model_name, field_name in [
        ('Calidades', 'calidad'),
        ('Hispanizaciones', 'hispanizacion'),
        ('Etonimos', 'etonimo'),
    ]:
        Model = apps.get_model('dbgestor', model_name)
        seen = {}
        for obj in Model.objects.all().order_by('pk'):
            lowered = getattr(obj, field_name).lower()
            if lowered not in seen:
                seen[lowered] = obj.pk
                if getattr(obj, field_name) != lowered:
                    setattr(obj, field_name, lowered)
                    obj.save(update_fields=[field_name])
            else:
                # Duplicate after lowercasing — remove the later record
                obj.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('dbgestor', '0010_lugar_tipo_fk'),
    ]

    operations = [
        migrations.RunPython(lowercase_vocab, reverse_code=migrations.RunPython.noop),
    ]
