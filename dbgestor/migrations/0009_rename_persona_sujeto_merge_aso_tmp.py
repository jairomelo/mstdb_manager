import django.db.models.deletion
from django.db import migrations, models


def migrate_aso_to_tmp(apps, schema_editor):
    PersonaRelaciones = apps.get_model('dbgestor', 'PersonaRelaciones')
    PersonaRelaciones.objects.filter(naturaleza_relacion='aso').update(naturaleza_relacion='tmp')


class Migration(migrations.Migration):

    dependencies = [
        ('dbgestor', '0008_alter_historicallugar_tipo_alter_lugar_tipo'),
    ]

    operations = [
        # Task 1: Rename persona_sujeto → persona_fuente
        migrations.RenameField(
            model_name='personarelaciones',
            old_name='persona_sujeto',
            new_name='persona_fuente',
        ),
        migrations.RenameField(
            model_name='historicalpersonarelaciones',
            old_name='persona_sujeto',
            new_name='persona_fuente',
        ),
        # Update related_name on the live model FK
        migrations.AlterField(
            model_name='personarelaciones',
            name='persona_fuente',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='relaciones_como_fuente',
                to='dbgestor.persona',
            ),
        ),
        # Task 2: Remove 'aso' from naturaleza_relacion choices
        migrations.AlterField(
            model_name='personarelaciones',
            name='naturaleza_relacion',
            field=models.CharField(
                choices=[('fam', 'Familiar'), ('tmp', 'Temporal'), ('sub', 'Subordinación')],
                max_length=50,
            ),
        ),
        migrations.AlterField(
            model_name='historicalpersonarelaciones',
            name='naturaleza_relacion',
            field=models.CharField(
                choices=[('fam', 'Familiar'), ('tmp', 'Temporal'), ('sub', 'Subordinación')],
                max_length=50,
            ),
        ),
        # Data migration: convert remaining 'aso' records to 'tmp'
        migrations.RunPython(migrate_aso_to_tmp, reverse_code=migrations.RunPython.noop),
    ]
