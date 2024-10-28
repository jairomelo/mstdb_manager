from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry

from .models import (
    Actividades,
    Archivo,
    Calidades,
    Documento,
    EstadoCivil,
    Etonimos,
    Hispanizaciones,
    InstitucionRolEvento,
    Lugar,
    Persona,
    PersonaEsclavizada,
    PersonaLugarRel,
    PersonaNoEsclavizada,
    Corporacion,
    PersonaRelaciones,
    PersonaRolEvento,
    RolEvento,
    SituacionLugar,
    TipoDocumental,
    TipoLugar,
    TiposInstitucion
)


@registry.register_document
class SituacionLugarDocument(Document):
    class Index:
        name = 'situacionlugar'  # Name of the Elasticsearch index

    class Django:
        model = SituacionLugar
        fields = ['situacion']


@registry.register_document
class TipoDocumentalDocument(Document):
    class Index:
        name = 'tipodocumental'

    class Django:
        model = TipoDocumental
        fields = ['tipo_documental', 'descripcion']


@registry.register_document
class RolEventoDocument(Document):
    class Index:
        name = 'rolevento'

    class Django:
        model = RolEvento
        fields = ['rol_evento', 'descripcion']


@registry.register_document
class TipoLugarDocument(Document):
    class Index:
        name = 'tipolugar'

    class Django:
        model = TipoLugar
        fields = ['tipo_lugar', 'descripcion']


@registry.register_document
class LugarDocument(Document):
    lugar_id = fields.IntegerField(attr='lugar_id')
    nombre_lugar = fields.TextField(attr='nombre_lugar')
    otros_nombres = fields.TextField(attr='otros_nombres')
    tipo = fields.TextField(attr='tipo')
    es_parte_de = fields.ObjectField(attr='es_parte_de',
                                     properties={
                                         'lugarpk': fields.IntegerField(attr='lugar_id'),
                                         'nombre_lugar': fields.TextField(attr='nombre_lugar'),
                                         'tipo': fields.TextField(attr='tipo')
                                     })
    
    persona_lugar_rel = fields.IntegerField(multi=True)
    
    def prepare_persona_lugar_rel(self, instance):
        return list(PersonaLugarRel.objects.filter(lugar=instance).values_list('persona_x_lugares', flat=True))

    class Index:
        name = 'lugar'

    class Django:
        model = Lugar


@registry.register_document
class ArchivoDocument(Document):
    archivo_id = fields.IntegerField(attr='archivo_id')
    ubicacion_archivo = fields.ObjectField(attr='ubicacion_archivo',
                                           properties={
                                               'lugarpk': fields.IntegerField(attr='lugar_id'),
                                               'nombre_lugar': fields.TextField(attr='nombre_lugar'),
                                               'tipo': fields.TextField(attr='tipo')
                                           })

    class Index:
        name = 'archivo'

    class Django:
        model = Archivo
        fields = ['nombre', 'nombre_abreviado', 'archivo_idno']


@registry.register_document
class DocumentoDocument(Document):
    documento_id = fields.IntegerField(attr='documento_id')
    archivo = fields.ObjectField(attr='archivo',
                                 properties={
                                     'archivopk': fields.IntegerField(attr='archivo_id'),
                                     'nombre': fields.TextField(attr='nombre'),
                                     'nombre_abreviado': fields.TextField(attr='nombre_abreviado')
                                 })
    tipo_documento = fields.ObjectField(attr='tipo_documento',
                                        properties={
                                            'tipodocumentalpk': fields.IntegerField(attr='id'),
                                            'tipo_documental': fields.TextField(attr='tipo_documental')
                                        })
    lugar_de_produccion = fields.ObjectField(attr='lugar_de_produccion',
                                             properties={
                                                 'lugarpk': fields.IntegerField(attr='lugar_id'),
                                                 'nombre_lugar': fields.TextField(attr='nombre_lugar'),
                                                 'tipo': fields.TextField(attr='tipo')
                                             })

    class Index:
        name = 'documento'

    class Django:
        model = Documento
        fields = ['documento_idno', 'fondo', 'subfondo', 'serie', 'subserie', 'tipo_udc',
                  'unidad_documental_compuesta', 'sigla_documento', 'titulo', 'descripcion',
                  'deteriorado', 'fecha_inicial', 'fecha_inicial_raw', 'fecha_final', 'fecha_final_raw', 'folio_inicial', 'folio_final',
                  'evento_valor_sp', 'evento_forma_de_pago', 'evento_total', 'notas']


@registry.register_document
class CalidadesDocument(Document):
    class Index:
        name = 'calidades'

    class Django:
        model = Calidades
        fields = ['calidad']


@registry.register_document
class ActividadesDocument(Document):
    class Index:
        name = 'actividades'

    class Django:
        model = Actividades
        fields = ['actividad']


@registry.register_document
class HispanizacionesDocument(Document):
    class Index:
        name = 'hispanizaciones'

    class Django:
        model = Hispanizaciones
        fields = ['hispanizacion']


@registry.register_document
class EtonimosDocument(Document):
    class Index:
        name = 'etonimos'

    class Django:
        model = Etonimos
        fields = ['etonimo']


@registry.register_document
class EstadoCivilDocument(Document):
    class Index:
        name = 'estadocivil'

    class Django:
        model = EstadoCivil
        fields = ['estado_civil']


@registry.register_document
class PersonaDocument(Document):
    persona_id = fields.IntegerField(attr='persona_id')
    
    documentos = fields.NestedField(attr='documentos',
                                   properties={
                                       'documentopk': fields.IntegerField(attr='documento_id'),
                                       'titulo': fields.TextField(attr='titulo'),
                                       'documento_idno': fields.TextField(attr='documento_idno')
                                   })
    
    calidades = fields.NestedField(properties={
        'calidad': fields.TextField()
    })
    lugar_nacimiento = fields.ObjectField(attr='lugar_nacimiento',
                                          properties={
                                              'lugarpk': fields.IntegerField(attr='lugar_id'),
                                              'nombre_lugar': fields.TextField(attr='nombre_lugar'),
                                              'tipo': fields.TextField(attr='tipo')
                                          })
    lugar_defuncion = fields.ObjectField(attr='lugar_defuncion',
                                         properties={
                                             'lugarpk': fields.IntegerField(attr='lugar_id'),
                                             'nombre_lugar': fields.TextField(attr='nombre_lugar'),
                                             'tipo': fields.TextField(attr='tipo')
                                         })
    estado_civil = fields.NestedField(properties={
        'estadopk': fields.IntegerField(attr='id'),
        'estado_civil': fields.TextField()
    })
    ocupaciones = fields.NestedField(properties={
        'actividadpk': fields.IntegerField(attr='actividad_id'),
        'actividad': fields.TextField()
    })

    persona_lugar_rel = fields.IntegerField(multi=True)
    
    persona_x_persona_rel = fields.IntegerField(multi=True)

    class Index:
        name = 'persona'

    class Django:
        model = Persona
        fields = ['persona_idno', 'nombres', 'apellidos', 'nombre_normalizado', 'sexo',
                  'fecha_nacimiento', 'fecha_defuncion', 'ocupacion_categoria', 'notas']

    
    def prepare_persona_lugar_rel(self, instance):
        return list(PersonaLugarRel.objects.filter(personas=instance).values_list('persona_x_lugares', flat=True))

    def prepare_persona_x_persona_rel(self, instance):
        return list(PersonaRelaciones.objects.filter(personas=instance).values_list('persona_relacion_id', flat=True))
    

@registry.register_document
class PersonaEsclavizadaDocument(PersonaDocument):
    persona_idno = fields.KeywordField(attr='persona_idno')
    nombre_normalizado = fields.TextField(attr='nombre_normalizado')
    sexo = fields.TextField(attr='sexo')
    edad = fields.IntegerField(attr='edad')
    unidad_temporal_edad = fields.TextField(attr='unidad_temporal_edad')
    altura = fields.TextField(attr='altura')
    cabello = fields.TextField(attr='cabello')
    ojos = fields.TextField(attr='ojos')

    hispanizacion = fields.NestedField(properties={
        'hispanizacionpk': fields.IntegerField(attr='hispanizacion_id'),
        'hispanizacion': fields.TextField()
    })

    etnonimos = fields.NestedField(properties={
        'etnonimopk': fields.IntegerField(attr='etonimo_id'),
        'etnonimo': fields.TextField()
    })

    procedencia = fields.ObjectField(attr='procedencia', properties={
        'procedenciapk': fields.IntegerField(attr='lugar_id'),
        'nombre_lugar': fields.TextField(attr='nombre_lugar'),
        'tipo': fields.TextField(attr='tipo')
    })

    procedencia_adicional = fields.TextField(attr='procedencia_adicional')
    marcas_corporales = fields.TextField(attr='marcas_corporales')
    conducta = fields.TextField(attr='conducta')
    salud = fields.TextField(attr='salud')

    def prepare_sexo(self, instance):
        return instance.get_sexo_display()
    
    class Index:
        name = 'personaesclavizada'

    class Django:
        model = PersonaEsclavizada


@registry.register_document
class PersonaNoEsclavizadaDocument(PersonaDocument):
    class Index:
        name = 'personanoesclavizada'

    class Django:
        model = PersonaNoEsclavizada
        fields = ['entidad_asociada', 'honorifico']


@registry.register_document
class PersonaLugarRelDocument(Document):
    documento = fields.ObjectField(attr='documento',
                                   properties={
                                       'documentopk': fields.IntegerField(attr='documento_id'),
                                       'titulo': fields.TextField(attr='titulo'),
                                       'documento_idno': fields.TextField(attr='documento_idno')
                                   })
    personas = fields.NestedField(properties={
        'personapk': fields.IntegerField(attr='persona_id'),
        'nombre_normalizado': fields.TextField(),
        'persona_idno': fields.TextField()
    })
    lugar = fields.ObjectField(attr='lugar',
                               properties={
                                   'lugarpk': fields.IntegerField(attr='lugar_id'),
                                   'nombre_lugar': fields.TextField(attr='nombre_lugar'),
                                   'tipo': fields.TextField(attr='tipo')
                               })
    situacion_lugar = fields.ObjectField(attr='situacion_lugar',
                                         properties={
                                             'situacionpk': fields.IntegerField(attr='situacion_id'),
                                             'situacion': fields.TextField(attr='situacion')
                                         })

    class Index:
        name = 'personalugarrel'

    class Django:
        model = PersonaLugarRel
        fields = ['ordinal', 'fecha_inicial_lugar',
                  'fecha_final_lugar', 'notas']


@registry.register_document
class PersonaRelacionesDocument(Document):
    documento = fields.ObjectField(attr='documento',
                                   properties={
                                       'documentopk': fields.IntegerField(attr='documento_id'),
                                       'titulo': fields.TextField(attr='titulo'),
                                       'documento_idno': fields.TextField(attr='documento_idno')
                                   })
    personas = fields.NestedField(properties={
        'personapk': fields.IntegerField(attr='persona_id'),
        'nombre_normalizado': fields.TextField(),
        'persona_idno': fields.TextField()
    })

    class Index:
        name = 'personalrelaciones'

    class Django:
        model = PersonaRelaciones
        fields = ['naturaleza_relacion', 'descripcion_relacion', 'fecha_inicial_relacion',
                  'fecha_final_relacion', 'notas']


@registry.register_document
class PersonaRolEventoDocument(Document):
    documento = fields.ObjectField(attr='documento',
                                   properties={
                                       'documentopk': fields.IntegerField(attr='documento_id'),
                                       'titulo': fields.TextField(attr='titulo'),
                                       'documento_idno': fields.TextField(attr='documento_idno')
                                   })
    personas = fields.NestedField(properties={
        'personapk': fields.IntegerField(attr='persona_id'),
        'nombre_normalizado': fields.TextField(),
        'persona_idno': fields.TextField()
    })
    rol_evento = fields.ObjectField(attr='rol_evento',
                                    properties={
                                        'rol_eventopk': fields.IntegerField(attr='id'),
                                        'rol_evento': fields.TextField(attr='rol_evento')
                                    })

    class Index:
        name = 'personalrolevento'

    class Django:
        model = PersonaRolEvento


@registry.register_document
class TiposInstitucionDocument(Document):
    class Index:
        name = 'tiposinstitucion'

    class Django:
        model = TiposInstitucion
        fields = ['tipo']


@registry.register_document
class CorporacionDocument(Document):
    
    corporacion_id = fields.IntegerField(attr='corporacion_id')
    
    documentos = fields.NestedField(attr='documentos',
                                   properties={
                                       'documentopk': fields.IntegerField(attr='documento_id'),
                                       'titulo': fields.TextField(attr='titulo'),
                                       'documento_idno': fields.TextField(attr='documento_idno')
                                   })
    
    tipo_institucion = fields.ObjectField(attr='tipo_institucion',
                                          properties={
                                              'tipopk': fields.IntegerField(attr='tipo_id'),
                                              'tipo': fields.TextField(attr='tipo')
                                          })
    personas_asociadas = fields.NestedField(properties={
        'personapk': fields.IntegerField(attr='persona_id'),
        'nombre_normalizado': fields.TextField(),
        'persona_idno': fields.TextField()
    })

    class Index:
        name = 'corporacion'

    class Django:
        model = Corporacion
        fields = ['corporacion_idno', 'nombre_institucion',
                  'nombres_alternativos', 'notas']


@registry.register_document
class InstitucionRolEventoDocument(Document):
    documento = fields.ObjectField(attr='documento',
                                   properties={
                                       'documentopk': fields.IntegerField(attr='documento_id'),
                                       'titulo': fields.TextField(attr='titulo'),
                                       'documento_idno': fields.TextField(attr='documento_idno')
                                   })
    corporaciones = fields.NestedField(properties={
        'corporacionpk': fields.IntegerField(attr='corporacion_id'),
        'nombre_institucion': fields.TextField(),
        'corporacion_idno': fields.TextField()
    })
    rol_evento = fields.ObjectField(attr='rol_evento',
                                    properties={
                                        'rol_eventopk': fields.IntegerField(attr='id'),
                                        'rol_evento': fields.TextField(attr='rol_evento')
                                    })

    class Index:
        name = 'institucionrolevento'

    class Django:
        model = InstitucionRolEvento
