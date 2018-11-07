from django import template

register = template.Library()

@register.filter
def is_integer(obj):
    return isinstance(obj, int)