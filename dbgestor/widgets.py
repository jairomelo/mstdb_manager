from dal import autocomplete

class PersonaEsclavizadaAutocomplete(autocomplete.Select2Multiple):
    def __init__(self, *args, **kwargs):
        super().__init__(url='persona-esclavizada-autocomplete', *args, **kwargs)

class PersonaNoEsclavizadaAutocomplete(autocomplete.Select2Multiple):
    def __init__(self, *args, **kwargs):
        super().__init__(url='persona-no-esclavizada-autocomplete', *args, **kwargs)
        
class LugarEventoAutocomplete(autocomplete.Select2):
    def __init__(self, *args, **kwargs):
        super().__init__(url='lugar-evento-autocomplete', *args, **kwargs)

class DocumentoAutocomplete(autocomplete.Select2):
    def __init__(self, *args, **kwargs):
        super().__init__(url='documento-autocomplete', *args, **kwargs)
        
class ArchivoAutocomplete(autocomplete.Select2):
    def __init__(self, *args, **kwargs):
        super().__init__(url='archivo-autocomplete', *args, **kwargs)
        
class CalidadesAutocomplete(autocomplete.Select2):
    def __init__(self, *args, **kwargs):
        super().__init__(url='calidades-autocomplete', *args, **kwargs)