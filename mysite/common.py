from django.utils.text import slugify

class Button(object):
    name = ''
    value = ''
    no_validate = False
    css_class = 'btn'

    def __init__(self, value="submit", name="", css_class='btn-primary', no_validate=False):
        self.value = value
        self.name = slugify(value) if name == "" else name
        self.css_class = 'btn '+ css_class
        self.no_validate = no_validate