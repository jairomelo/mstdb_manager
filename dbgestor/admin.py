from django.contrib import admin

# Register your models here.
from .models import Lugar, PlaceHistorical
from .models import Archivo, Documento
from .models import Calidades, Actividades, Hispanizaciones, Etonimos
from .models import PersonaEsclavizada, PersonaInvolucrada
from .models import Persona, PersonaRelaciones
from .models import Evento


admin.site.register(Archivo)
admin.site.register(Persona)
admin.site.register(Calidades)
admin.site.register(Documento)
admin.site.register(Actividades)
admin.site.register(Etonimos)
admin.site.register(Evento)
admin.site.register(Hispanizaciones)
admin.site.register(PlaceHistorical)
admin.site.register(Lugar)
admin.site.register(PersonaEsclavizada)
admin.site.register(PersonaInvolucrada)
admin.site.register(PersonaRelaciones)

