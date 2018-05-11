from django import template
from django.urls import reverse
from os import path
from django.core.signing import Signer

register = template.Library()

@register.filter
def is_integer(obj):
    return isinstance(obj, int)