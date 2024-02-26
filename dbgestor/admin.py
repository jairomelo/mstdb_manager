from django.contrib import admin

from import_export.admin import ImportExportModelAdmin

# resources

from .resources import SituacionLugarResource

# Register your models here.
from .models import Lugar
from .models import Archivo, Documento
from .models import Calidades, Actividades, Hispanizaciones, Etonimos
from .models import SituacionLugar, TipoDocumental, TipoLugar
from .models import PersonaEsclavizada, PersonaNoEsclavizada
from .models import PersonaRelaciones, PersonaLugarRel, RolEvento
    

class SituacionLugarAdmin(ImportExportModelAdmin):
    resource_class = SituacionLugarResource

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

