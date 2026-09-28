import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dbgestor', '0018_restore_asociativa_relacion'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConductaTerm',
            fields=[
                ('conducta_term_id', models.AutoField(primary_key=True, serialize=False)),
                ('canonico', models.CharField(max_length=150, unique=True)),
                ('aliases', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=150), default=list, blank=True, help_text='Variantes documentadas (minúsculas). Un * final indica prefijo.', size=None)),
                ('descripcion', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['canonico'],
            },
        ),
        migrations.AddField(
            model_name='personaesclavizada',
            name='conducta_terms',
            field=models.ManyToManyField(blank=True, related_name='personas_esclavizadas', to='dbgestor.conductaterm'),
        ),
    ]
