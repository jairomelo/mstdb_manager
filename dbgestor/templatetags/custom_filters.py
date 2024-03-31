from django import template
from django.urls import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def map_attribute(value, attribute):
    return [item.get(attribute) if isinstance(item, dict) else getattr(item, attribute, None) for item in value]

@register.filter
def filter_person(places, person_id):
    return {place: details for place, details in places.items() if person_id in details['personas']}

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

