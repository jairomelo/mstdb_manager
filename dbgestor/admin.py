from django.contrib import admin

from import_export.admin import ImportExportModelAdmin

# resources

from .resources import SituacionLugarResource, TipoInstitucionResource

# Register your models here.
from .models import Lugar, PersonaRolEvento
from .models import Archivo, Documento
from .models import Calidades, Actividades, Hispanizaciones, Etonimos
from .models import SituacionLugar, TipoDocumental, TipoLugar, TiposInstitucion
from .models import PersonaEsclavizada, PersonaNoEsclavizada, Corporacion
from .models import PersonaRelaciones, PersonaLugarRel, RolEvento, SugerenciaMerge
from .models import Leccion, LeccionImagen, LeccionNivel, LeccionPalabraClave, LeccionAcceso
    

class SituacionLugarAdmin(ImportExportModelAdmin):
    resource_class = SituacionLugarResource
    
class TipoInstitucionAdmin(ImportExportModelAdmin):
    resource_class = TipoInstitucionResource


class LeccionImagenInline(admin.TabularInline):
    model = LeccionImagen
    extra = 0
    readonly_fields = ('created_at',)


class LeccionAccesoInline(admin.TabularInline):
    model = LeccionAcceso
    extra = 0
    readonly_fields = ('created_at',)
    raw_id_fields = ('user',)


class LeccionAdmin(ImportExportModelAdmin):
    inlines = [LeccionImagenInline, LeccionAccesoInline]
    list_display = ('title', 'is_published', 'created_by', 'created_at', 'updated_at')
    list_filter = ('is_published',)
    search_fields = ('title', 'body')
    filter_horizontal = ('levels', 'keywords', 'personas', 'documentos', 'corporaciones')

admin.site.register(Archivo, ImportExportModelAdmin)
admin.site.register(Calidades, ImportExportModelAdmin)
admin.site.register(Documento, ImportExportModelAdmin)
admin.site.register(Actividades, ImportExportModelAdmin)
admin.site.register(Etonimos, ImportExportModelAdmin)
admin.site.register(Hispanizaciones, ImportExportModelAdmin)
admin.site.register(Lugar, ImportExportModelAdmin)
admin.site.register(PersonaEsclavizada, ImportExportModelAdmin)
admin.site.register(PersonaNoEsclavizada, ImportExportModelAdmin)
admin.site.register(PersonaRelaciones, ImportExportModelAdmin)
admin.site.register(PersonaLugarRel, ImportExportModelAdmin)
admin.site.register(SituacionLugar, SituacionLugarAdmin)
admin.site.register(TipoDocumental, ImportExportModelAdmin)
admin.site.register(TipoLugar, ImportExportModelAdmin)
admin.site.register(RolEvento, ImportExportModelAdmin)
admin.site.register(TiposInstitucion, TipoInstitucionAdmin)
admin.site.register(Corporacion, ImportExportModelAdmin)
admin.site.register(PersonaRolEvento, ImportExportModelAdmin)
admin.site.register(SugerenciaMerge)
admin.site.register(Leccion, LeccionAdmin)
admin.site.register(LeccionNivel, ImportExportModelAdmin)
admin.site.register(LeccionPalabraClave, ImportExportModelAdmin)

