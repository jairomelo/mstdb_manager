from django.db import migrations, models


class Migration(migrations.Migration):
    """Restore the 'aso' (Asociativa) naturaleza_relacion choice.

    Removed in 0009 (rows were converted aso→tmp). Restored per data-entry
    team feedback; existing 'tmp' rows are NOT auto-reverted — catalogers
    reclassify manually (original aso rows remain auditable via
    HistoricalPersonaRelaciones).
    """

    dependencies = [
        ('dbgestor', '0017_leccionadjunto'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicalpersonarelaciones',
            name='naturaleza_relacion',
            field=models.CharField(
                choices=[('fam', 'Familiar'), ('aso', 'Asociativa'), ('tmp', 'Temporal'), ('sub', 'Subordinación')],
                max_length=50,
            ),
        ),
        migrations.AlterField(
            model_name='personarelaciones',
            name='naturaleza_relacion',
            field=models.CharField(
                choices=[('fam', 'Familiar'), ('aso', 'Asociativa'), ('tmp', 'Temporal'), ('sub', 'Subordinación')],
                max_length=50,
            ),
        ),
    ]
