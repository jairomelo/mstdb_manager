from django import template
from django.urls import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.utils.safestring import mark_safe
from dbgestor.models import PersonaLugarRel, Persona

register = template.Library()

@register.filter
def map_attribute(value, attribute):
    return [item.get(attribute) if isinstance(item, dict) else getattr(item, attribute, None) for item in value]

@register.simple_tag
def filter_person_places(places_dict, person_idno, documento_id=None):
    """
    Filter places to show only those associated with the specific person,
    with the correct rel_id for that person.
    """
    filtered_places = {}
    
    for place_name, details in places_dict.items():
        if person_idno in details['personas']:
            # Get the correct rel_id for this specific person-place combination including ordinal
            correct_rel_id = get_rel_id_for_person_place(
                person_idno, 
                details['place_id'], 
                documento_id,
                details.get('ordinal')  # Pass the ordinal from the details
            )
            
            if correct_rel_id:
                filtered_places[place_name] = {
                    'ordinal': details['ordinal'],
                    'place_id': details['place_id'],
                    'rel_id': correct_rel_id
                }
    
    return filtered_places

def get_rel_id_for_person_place(person_idno, place_id, documento_id=None, ordinal=None):
    """
    Helper function to get the correct rel_id for a specific person-place combination
    """
    try:
        # Handle NULL or empty persona_idno values
        if not person_idno:
            return None
            
        persona = Persona.objects.get(persona_idno=person_idno)
        
        # Build the filter with document constraint if available
        filter_kwargs = {
            'personas': persona,
            'lugar_id': place_id
        }
        
        if documento_id:
            filter_kwargs['documento_id'] = documento_id
            
        if ordinal is not None:
            filter_kwargs['ordinal'] = ordinal
        
        rel = PersonaLugarRel.objects.filter(**filter_kwargs).first()
        return rel.persona_x_lugares if rel else None
    except (Persona.DoesNotExist, Persona.MultipleObjectsReturned) as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Persona lookup issue for persona_idno='{person_idno}': {e}")
        return None

@register.filter
def filter_relation(relations, person_id):
    return [relation for relation in relations if person_id in [persona['idno'] for persona in relation['personas']]]

@register.simple_tag
def display_field(obj, field_name, display_name=None):
    """
    Displays the field value with a label if the field is not None/empty.
    
    Args:
    - obj: The Django model instance.
    - field_name: The field name as a string.
    - display_name: Optional human-readable name for the field. If not provided,
      the field_name is used.
    """
    value = getattr(obj, field_name, None)
    if value:
        display_name = display_name or field_name.capitalize()
        return mark_safe(f'<p><strong>{display_name}:</strong> {value}</p>')
    return ""

