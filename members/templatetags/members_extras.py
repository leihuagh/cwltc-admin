from django import template
from django.urls import reverse
from os import path
from django.core.signing import Signer

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    get value from dictionary
    usage {{ mydict|get_item:item.NAME }}
    """
    return dictionary.get(key)


@register.filter
def get_option(options, key):
    """
    Gets a value from a list of options
    usage: {{options|get_option:key }}
    """
    if key <= len(options) - 1:
        return options[key][1]
    else:
        return "{} is out of range".format(key)


@register.filter
def index(List, i):
    """
    Gets value form indexed list
    """
    return List[int(i)]


@register.filter
def classname(obj):
    """
    Returns the classname of an object
    """
    classname = obj.__class__.__name__
    return classname


# From http://vanderwijk.info/blog/adding-css-classes-formfields-in-django-templates/#comment-1193609278
@register.filter
def add_attributes(field, css):
    attrs = {}
    definition = css.split(',')
 
    for d in definition:
        if ':' not in d:
            attrs['class'] = d
        else:
            t, v = d.split(':')
            attrs[t] = v
 
    return field.as_widget(attrs=attrs)


@register.filter
def add_class(field, css):
   return field.as_widget(attrs={"class":css})


@register.simple_tag(takes_context=True)
def signed_url(context, url_name, pk):
    """
    Returns an absolute url with signed token
    Usage: {% signed_url url_name pk %}

    """
    request = context['request']
    signer = Signer()
    token = signer.sign(pk)
    resolved_url = reverse(url_name, kwargs={'token': token})
    return request.build_absolute_uri(resolved_url)