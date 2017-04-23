from os import path
from django import forms
from django.forms import Form
from crispy_forms.helper import FormHelper
from members.forms import SubmitButton

class UploadForm(Form):

    upload_file = forms.FileField(required=True, label="Select the file")