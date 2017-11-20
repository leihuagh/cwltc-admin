from django.contrib.auth import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML
from members.views import SubmitButton


class CrispyAuthenticationForm(forms.AuthenticationForm):
    helper = FormHelper()
    helper.form_tag = False


class CrispyPasswordChangeForm(forms.PasswordChangeForm):
    helper = FormHelper()
    helper.form_tag = False


class CrispyPasswordResetForm(forms.PasswordResetForm):
    helper = FormHelper()
    helper.form_tag = False


class CrispySetPasswordForm(forms.SetPasswordForm):
    helper = FormHelper()
    helper.form_tag = False

