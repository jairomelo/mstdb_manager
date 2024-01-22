from django.contrib import admin

# Register your models here.
from .models import Lugar, HistoricalName
from .models import Archivo, Documento
from .models import Calidades, HistorialActividadesPersona, LugaresPersona, Hispanizaciones, Etonimos
from .models import PersonaEsclavizadaExp, PersonaInvolucradaExp
from .models import Persona, PersonaRelaciones
from .models import Evento


admin.site.register(Archivo)
admin.site.register(Persona)
admin.site.register(Calidades)
admin.site.register(Documento)
admin.site.register(HistorialActividadesPersona)
admin.site.register(LugaresPersona)
admin.site.register(Etonimos)
admin.site.register(Evento)
admin.site.register(Hispanizaciones)
admin.site.register(HistoricalName)
admin.site.register(Lugar)
admin.site.register(PersonaEsclavizadaExp)
admin.site.register(PersonaInvolucradaExp)
admin.site.register(PersonaRelaciones)

