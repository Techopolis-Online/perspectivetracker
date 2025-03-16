from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary using a key."""
    if not dictionary:
        return None
    return dictionary.get(key)

@register.filter
def split(value, delimiter):
    """Split a string by a delimiter and return a list."""
    if not value:
        return []
    return value.split(delimiter) 