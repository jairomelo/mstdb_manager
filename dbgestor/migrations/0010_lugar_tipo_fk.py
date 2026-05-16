import django.db.models.deletion
from django.db import migrations, models

# The 15 place type codes that seed TipoLugar
PLACE_TYPE_CODES = [
    'ciudad', 'pueblo', 'estado', 'gobernacion', 'pais', 'provincia',
    'villa', 'real', 'parroquia', 'fuerte', 'puerto', 'isla',
    'region', 'diocesis', 'hacienda',
]


def seed_tipolugar(apps, schema_editor):
    TipoLugar = apps.get_model('dbgestor', 'TipoLugar')
    for code in PLACE_TYPE_CODES:
        TipoLugar.objects.get_or_create(tipo_lugar=code)


def populate_tipo_fk(apps, schema_editor):
    Lugar = apps.get_model('dbgestor', 'Lugar')
    TipoLugar = apps.get_model('dbgestor', 'TipoLugar')
    tipo_map = {t.tipo_lugar: t.pk for t in TipoLugar.objects.all()}
    for lugar in Lugar.objects.exclude(tipo='').exclude(tipo__isnull=True):
        pk = tipo_map.get(lugar.tipo)
        if pk:
            lugar.tipo_fk_id = pk
            lugar.save(update_fields=['tipo_fk_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('dbgestor', '0009_rename_persona_sujeto_merge_aso_tmp'),
    ]

    operations = [
        # 1. Seed TipoLugar lookup table with the 15 place type codes
        migrations.RunPython(seed_tipolugar, reverse_code=migrations.RunPython.noop),

        # 2. Add new FK column (nullable) alongside the old CharField
        migrations.AddField(
            model_name='lugar',
            name='tipo_fk',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='lugares',
                to='dbgestor.tipolugar',
            ),
        ),
        # Historical model: simple_history FK fields use DO_NOTHING + no constraint
        migrations.AddField(
            model_name='historicallugar',
            name='tipo_fk',
            field=models.ForeignKey(
                blank=True, db_constraint=False, null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name='+',
                to='dbgestor.tipolugar',
            ),
        ),

        # 3. Populate the FK for live Lugar records
        migrations.RunPython(populate_tipo_fk, reverse_code=migrations.RunPython.noop),

        # 4. Drop old CharField
        migrations.RemoveField(model_name='lugar', name='tipo'),
        migrations.RemoveField(model_name='historicallugar', name='tipo'),

        # 5. Rename tipo_fk → tipo
        migrations.RenameField(model_name='lugar', old_name='tipo_fk', new_name='tipo'),
        migrations.RenameField(model_name='historicallugar', old_name='tipo_fk', new_name='tipo'),
    ]
