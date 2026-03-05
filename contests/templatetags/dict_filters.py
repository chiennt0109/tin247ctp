from django import template
register = template.Library()

@register.filter
def dict_key(d, key):
    if d is None:
        return {}
    return d.get(key, {})
