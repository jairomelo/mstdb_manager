# Generated migration for adding PostgreSQL search fields to models

from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dbgestor', '0003_enable_search_extensions'),
    ]

    operations = [
        # Add search_vector field to Lugar
        migrations.AddField(
            model_name='lugar',
            name='search_vector',
            field=SearchVectorField(blank=True, null=True),
        ),
        
        # Add search_vector field to Documento
        migrations.AddField(
            model_name='documento',
            name='search_vector',
            field=SearchVectorField(blank=True, null=True),
        ),
        
        # Add search_vector field to Persona
        migrations.AddField(
            model_name='persona',
            name='search_vector',
            field=SearchVectorField(blank=True, null=True),
        ),
        
        # Add search_vector field to Corporacion
        migrations.AddField(
            model_name='corporacion',
            name='search_vector',
            field=SearchVectorField(blank=True, null=True),
        ),
        
        # Add GIN indexes for Lugar
        migrations.AddIndex(
            model_name='lugar',
            index=GinIndex(fields=['search_vector'], name='dbgestor_lu_search__idx'),
        ),
        migrations.AddIndex(
            model_name='lugar',
            index=GinIndex(fields=['nombre_lugar'], name='dbgestor_lu_nombre__idx', opclasses=['gin_trgm_ops']),
        ),
        
        # Add GIN indexes for Documento
        migrations.AddIndex(
            model_name='documento',
            index=GinIndex(fields=['search_vector'], name='dbgestor_do_search__idx'),
        ),
        migrations.AddIndex(
            model_name='documento',
            index=GinIndex(fields=['titulo'], name='dbgestor_do_titulo__idx', opclasses=['gin_trgm_ops']),
        ),
        migrations.AddIndex(
            model_name='documento',
            index=GinIndex(fields=['descripcion'], name='dbgestor_do_descrip_idx', opclasses=['gin_trgm_ops']),
        ),
        
        # Add GIN indexes for Persona
        migrations.AddIndex(
            model_name='persona',
            index=GinIndex(fields=['search_vector'], name='dbgestor_pe_search__idx'),
        ),
        migrations.AddIndex(
            model_name='persona',
            index=GinIndex(fields=['nombres'], name='dbgestor_pe_nombres__idx', opclasses=['gin_trgm_ops']),
        ),
        migrations.AddIndex(
            model_name='persona',
            index=GinIndex(fields=['apellidos'], name='dbgestor_pe_apellid_idx', opclasses=['gin_trgm_ops']),
        ),
        migrations.AddIndex(
            model_name='persona',
            index=GinIndex(fields=['nombre_normalizado'], name='dbgestor_pe_nombre__idx', opclasses=['gin_trgm_ops']),
        ),
        
        # Add GIN indexes for Corporacion
        migrations.AddIndex(
            model_name='corporacion',
            index=GinIndex(fields=['search_vector'], name='dbgestor_co_search__idx'),
        ),
        migrations.AddIndex(
            model_name='corporacion',
            index=GinIndex(fields=['nombre_institucion'], name='dbgestor_co_nombre__idx', opclasses=['gin_trgm_ops']),
        ),
        migrations.AddIndex(
            model_name='corporacion',
            index=GinIndex(fields=['nombres_alternativos'], name='dbgestor_co_nombres_idx', opclasses=['gin_trgm_ops']),
        ),
    ]
