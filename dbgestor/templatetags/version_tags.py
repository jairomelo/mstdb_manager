from django import template
from dbgestor.version import VERSION_STRING, VERSION_DATE

register = template.Library()

@register.simple_tag
def get_version():
    """Returns the version string"""
    return VERSION_STRING

@register.simple_tag
def get_version_with_date():
    """Returns the version string with date"""
    return f"V. {VERSION_STRING} [{VERSION_DATE}]" 