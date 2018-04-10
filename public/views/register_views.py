import logging
import datetime
from django.shortcuts import redirect, reverse
from django.core.signing import Signer
from django.contrib import messages
from django.contrib.auth.models import User
from django.views.generic import TemplateView
from django.views.generic.edit import FormView
from django.template.loader import get_template
from mysite.common import Button
from members.models import Person, Invoice
from members.mail import send_template_mail
from public.forms import RegisterForm, RegisterTokenForm, ConsentForm

logger = logging.getLogger(__name__)


class PleaseRegisterView(TemplateView):
    template_name = 'public/please_register.html'

    def post(self, request):
        if 'register' in request.POST:
            return redirect('public-register-invoice-token')
        return redirect('public-consent-invoice-token')


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
    Register a member identified in a person token or invoice token
    Creates a link from Person to User in auth system
    POS overrides this view
    """
    template_name = 'public/crispy_card.html'
    form_class = RegisterTokenForm
    invoice = False

    def get_initial(self):
        person = self.get_person()
        if person:
            return {'username': self.get_person().email}
        return {}

    def get_person(self):
        self.person = None
        if self.invoice:
            invoice_id = Signer().unsign(self.kwargs['token'])
            try:
                person_id= Invoice.objects.get(pk=invoice_id).person_id
            except Invoice.DoesNotExist:
                pass
        else:
            person_id = Signer().unsign(self.kwargs['token'])
        try:
            self.person = Person.objects.get(pk=person_id)
        except Person.DoesNotExist:
            pass
        return self.person

    def get_context_data(self, **kwargs):
        kwargs['person'] = self.get_person()
        kwargs['form_title'] = "Registration for " + self.person.fullname
        kwargs['buttons'] = [Button('Next', css_class='btn-success')]
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        person = self.get_person()
        if person:
            person.create_user(username=form.cleaned_data['username'],
                               password=form.cleaned_data['password1'],
                               pin=form.cleaned_data['pin'])
            template = get_template('public/registration_mail.html')
            send_template_mail(self.request, person, template.template.source, 'membership@coombewoodltc.co.uk',
                               subject='Coombe Wood LTC site registration')
            return redirect(self.get_success_url_name(), token=self.kwargs['token'])
        else:
            # invalid token cannot occur when using POS
            # so we can safely redirect to public home
            messages.error('Invalid token')
            return redirect('public-home')

    def get_success_url_name(self, **kwargs):
        if self.invoice:
            return 'public-consent-invoice-token'
        return 'public-consent-token'


class ConsentTokenView(FormView):
    """
    Update consent flags in the Person record
    if Invoice is True token is an invoice token and afterwards we redirect to show the invoice
    """
    template_name = 'public/consent.html'
    form_class = ConsentForm
    invoice = False

    def get_person(self):
        if self.invoice:
            invoice_id = Signer().unsign(self.kwargs['token'])
            try:
                person_id= Invoice.objects.get(pk=invoice_id).person_id
            except Invoice.DoesNotExist:
                return None
        else:
            person_id = Signer().unsign(self.kwargs['token'])
        try:
            return Person.objects.get(pk=person_id)
        except Person.DoesNotExist:
            return None

    def get_context_data(self, **kwargs):
        kwargs['person'] = self.get_person()
        if kwargs['person'].sub:
            kwargs['member'] = True
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        self.person = self.get_person()
        if self.person:
            self.person.allow_marketing = form.cleaned_data['marketing'] == 'yes'
            if self.person.sub:
                database = form.cleaned_data['database'] == 'yes'
                self.person.allow_email = database
                self.person.allow_phone = database
            self.person.consent_date = datetime.datetime.now()
            self.person.save()
            if self.invoice:
                return redirect('invoice-public', token=self.kwargs['token'])

            messages.success(self.request, 'You have successfully registered.')
            return super().form_valid(form)
        messages.error(self.request, 'Invalid token')
        return redirect('public-home')

    def get_success_url(self):
        if self.person.sub:
            return reverse('login')
        else:
            return reverse('public-home')
