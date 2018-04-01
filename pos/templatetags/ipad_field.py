from django import template
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

register = template.Library()

@register.inclusion_tag('pos/ipad_field.html')
def ipad_field(field):
    return {'field': field}