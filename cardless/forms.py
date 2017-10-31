from django.forms import Form, FileField, IntegerField
from django.forms.widgets import NumberInput
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit


class UploadCSVForm(Form):
    upload_file = FileField(required=True, label="Select the file")

class ProcessPaymentsForm(Form):
    days = IntegerField(required=True, label="Number of days")

    def __init__(self, *args, **kwargs):
        super(ProcessPaymentsForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-2'
        self.helper.add_input(Submit('process', 'Process payments', css_class='btn-primary'))