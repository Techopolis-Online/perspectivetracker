from django import template
from django.template.defaultfilters import stringfilter

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

@register.filter
def can_see_internal_comments(user):
    """Check if a user can see internal comments."""
    return user.is_superuser or (hasattr(user, 'role') and user.role and user.role.name == 'admin')

@register.filter
def can_mark_ready_for_testing(user):
    """Check if a user can mark issues as ready for testing."""
    return user.is_superuser or (user.is_authenticated and hasattr(user, 'role') and user.role and user.role.name == 'admin') 