from django import template

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