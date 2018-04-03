import logging
from django.shortcuts import redirect
from django.core.signing import Signer
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.models import User
from django.views.generic.edit import FormView
from mysite.common import Button
from members.models import Person
from public.forms import RegisterForm, RegisterTokenForm, ConsentForm

logger = logging.getLogger(__name__)


class RegisterView(FormView):
    """
    Capture details of an existing member so they can register
    if successful pass token to next step
    POS overrides this view
    """
    template_name = 'public/crispy_card.html'
    form_class = RegisterForm

    def get_context_data(self, **kwargs):
        context = super(RegisterView, self).get_context_data(**kwargs)
        context['form_title'] = 'Register for the club website and bar system'
        context['info'] = 'Enter these details to confirm you are a club member:'
        context['buttons'] = [Button('Register', css_class='btn-success')]
        return context

    def form_valid(self, form):
        person = form.cleaned_data['person']
        if person.auth_id:
            user = User.objects.filter(pk=person.auth_id)
            if len(user) == 1:
                messages.error(self.request, f'You are already registered with username: {(user[0].username)}')
                return redirect(self.get_already_registered_url_name(), token=Signer().sign(person.id))

        return redirect(self.get_success_url_name(), token=Signer().sign(person.id))

    def get_success_url_name(self):
        return 'public-register-token'

    def get_already_registered_url_name(self):
        return 'login-token'


class RegisterTokenView(FormView):
    """
    Register a member identified in a token
    Creates a link from Person to User in auth system
    POS overrides this view
    """
    template_name = 'public/crispy_card.html'
    form_class = RegisterTokenForm

    def get_initial(self):
        person = self.get_person()
        if person:
            return {'username': self.get_person().email}
        return {}

    def get_person(self):
        person_id = Signer().unsign(self.kwargs['token'])
        try:
            return Person.objects.get(pk=person_id)
        except Person.DoesNotExist:
            return None

    def get_context_data(self, **kwargs):
        kwargs['person'] = self.get_person()
        kwargs['form_title'] = 'Choose your password'
        kwargs['buttons'] = [Button('Next', css_class='btn-success')]
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        person = self.get_person()
        if person:
            person.create_user(username=form.cleaned_data['username'],
                               password=form.cleaned_data['password1'],
                               pin=form.cleaned_data['pin'])
            return redirect(self.get_success_url_name(), token=self.kwargs['token'])
        else:
            # invalid token cannot occur when using POS
            # so we can safely redirect to public home
            messages.error('Invalid token')
            return redirect('public-home')

    def get_success_url_name(self, **kwargs):
        return 'public-consent-token'


class ConsentTokenView(FormView):
    """
    Update consent flags in the Person record
    """
    template_name = 'public/consent.html'
    form_class = ConsentForm
    success_url = reverse_lazy('public-home')

    def get_person(self):
        person_id = Signer().unsign(self.kwargs['token'])
        try:
            return Person.objects.get(pk=person_id)
        except Person.DoesNotExist:
            return None

    def get_context_data(self, **kwargs):
        kwargs['person'] = self.get_person()
        kwargs['form_title'] = 'Consent'
        kwargs['buttons'] = [Button('Next', css_class='btn-success')]
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        person = self.get_person()
        if person:
            person.allow_marketing = form.cleaned_data['marketing'] == 'yes'
            database = form.cleaned_data['database'] == 'yes'
            person.allow_email = database
            person.allow_phone = database
            messages.success(self.request, 'You have successfully registered')
            return super().form_valid(form)
        messages.error(self.request, 'Invalid token')
        return redirect('public-home')


