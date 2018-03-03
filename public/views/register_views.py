import logging
from django.shortcuts import redirect, render_to_response
from django.core.signing import Signer
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth.models import User
from django.views.generic.edit import FormView
from django.views.generic import TemplateView
from mysite.common import Button
from members.models import Person
from public.forms import RegisterForm, RegisterTokenForm

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
        context['buttons'] = [Button('Register', css_class='btn-success')]
        return context

    def form_valid(self, form):
        person = form.cleaned_data['person']
        if person.auth_id:
            user = User.objects.filter(pk=person.auth_id)
            if len(user) == 1:
                messages.error(self.request, 'You are already registered with username {}'.format(user[0].username))
                return redirect('login-token', token=Signer().sign(user[0].username))

        if person.membership and person.membership.is_adult:
            return redirect(self.get_success_url_name(), token=Signer().sign(person.id))

        messages.error(self.request, 'Sorry, only adult members can register on the site')
        return redirect(self.get_failure_url_name())

    def get_success_url_name(self):
        return 'public-register-token'

    def get_failure_url_name(self):
        return 'public-home'


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
                               password=form.cleaned_data['password'],
                               pin=form.cleaned_data['pin'])
            return redirect(self.get_success_url_name(), token=self.kwargs['token'])
        else:
            # invalid token cannot occur when using POS
            # so we can safely redirect to public home
            messages.error('Invalid token')
            return redirect('public-home')

    def get_success_url_name(self, **kwargs):
        return 'public_consent_token'


class ConsentTokenView(TemplateView):
    """ Update consent flags in the Person record """
    template_name = 'public/consent_form.html'
    fields = ('marketing', 'database')

    def set_fields(self, fields):
        self.fields = fields

    def post(self, request, *args, **kwargs):
        person_id = Signer().unsign(self.kwargs['token'])
        errors = False
        try:
            person = Person.objects.get(pk=person_id)
        except Person.DoesNotExist:
            return redirect(self.get_success_url())
        if 'marketing' in self.fields:
            marketing = request.POST.get('marketing', None)
            if marketing:
                person.allow_marketing =  marketing == 'yes'
            else:
                errors = True
        if 'database' in self.fields:
            database = request.POST.get('database', None)
            if database:
                person.allow_email = database == 'yes'
                person.allow_phone = database == 'yes'
            else:
                errors = True
        if 'photo' in self.fields:
            photo = request.POST.get('photo', None)
            if photo:
                person.allow_photo =  photo == 'yes'
            else:
                errors = True
        if not errors:
            person.save()
            return redirect(self.get_success_url_name())
        else:
            return render_to_response(self.template_name, context)

    def get_success_url_name(self, **kwargs):
        return 'public-home'

    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)
    #     context['name'] = self.object.fullname
    #     return context

    def get_success_url(self, **kwargs):
        return reverse('pos_start')
