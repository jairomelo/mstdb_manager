from import_export import resources
from import_export.fields import Field
from import_export.widgets import ForeignKeyWidget

from .models import (SituacionLugar, TiposInstitucion)

class SituacionLugarResource(resources.ModelResource):
    situacion_id = Field(attribute='situacion_id', column_name='situacion_id', saves_null_values=False)
    situacion = Field(attribute='situacion', column_name='situacion')
    descripcion = Field(attribute='descripcion', column_name='descripcion')

    class Meta:
        model = SituacionLugar
        import_id_fields = ['situacion_id'] 
        fields = ('situacion_id', 'situacion', 'descripcion') 
        skip_unchanged = True
        report_skipped = False
        
class TipoInstitucionResource(resources.ModelResource):
    tipo_id = Field(attribute='tipo_id', column_name='tipo_id', saves_null_values=False)
    tipo = Field(attribute='tipo', column_name='tipo')
    descripcion = Field(attribute='descripcion', column_name='descripcion')
    
    class Meta:
        model = TiposInstitucion
        import_id_fields = ['tipo_id']
        fields = ('tipo_id', 'tipo', 'descripcion')
        skip_unchanged = True
        report_skipped = False