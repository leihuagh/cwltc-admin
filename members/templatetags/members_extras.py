from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    '''
    get value from dictionary
    usage {{ mydict|get_item:item.NAME }}
    '''
    return dictionary.get(key)

@register.filter
def get_option(options, key):
    '''
    Gets a value from a list of options
    usage: {{options|get_option:key }}
    '''
    if key <= len(options) - 1:
        return options[key][1]
    else:
        return "{} is out of range".format(key)

@register.filter
def classname(obj):
    '''
    Returns the classname of an object
    '''
    classname = obj.__class__.__name__
    return classname