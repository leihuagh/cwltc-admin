from django import forms
from django.forms import Form

class UploadCSVForm(Form):
    upload_file = forms.FileField(required=True, label="Select the file")