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
from public.forms import RegisterForm, RegisterTokenForm, ConsentForm, JuniorProfileForm
from cardless.services import person_from_token
logger = logging.getLogger(__name__)


class PleaseRegisterView(TemplateView):
    """
    External link asking unregistered people to register
    """
    template_name = 'public/please_register.html'

    def post(self, request):
        if 'register' in request.POST:
            return redirect('public-register-invoice-token')
        return redirect('public-consent-invoice-token')


class GoOnlineView(TemplateView):
    """
    User has clicked the link in an invoice
    """
    template_name = 'public/go_online.html'
    person = None

    def dispatch(self, request, *args, **kwargs):
        self.token = kwargs.pop('token')
        self.person = person_from_token(self.token, is_invoice_token=True)
        if self.person.auth:
            kwargs['token'] = self.token
            return ConsentTokenView.as_view(invoice=True)(request, *args, **kwargs)
        else:
            return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['person'] = self.person
        return context

    def post(self, request):
        if 'register' in request.POST:
            return redirect('public-register-invoice-token', token=self.token)
        if 'skip' in request.POST:
            return redirect('public-consent-invoice-token', token=self.token)
        if 'resign' in request.POST:
            self.person.consent_for_marketing(False)
            return redirect('public-resigned')
        if 'resign_marketing' in request.POST:
            self.person.consent_for_marketing(True)
            return redirect('public-resigned')
        if not self.person.auth:
            return redirect('public-register-invoice-token', token=self.token)
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
        context = super().get_context_data(**kwargs)
        context['form_title'] = 'Register for the club website and online services'
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
    if Invoice is True token is an invoice token and afterwards we redirect back to this view
    This view redirects to get each junior profile until all are done
    Then redirects to invoice public.
    """
    template_name = 'public/consent.html'
    form_class = ConsentForm
    invoice = False
    person = None

    def dispatch(self, request, *args, **kwargs):
        self.token = kwargs['token']
        self.person = person_from_token(self.token, is_invoice_token=self.invoice)
        if self.person:
            return super().dispatch(request, *args, **kwargs)
        messages.error(self.request, 'Invalid token')
        return redirect('public-home')

    def get(self, request, *args, **kwargs):
        if self.person.has_consented():
            for person in self.person.person_set.all():
                if person.sub and not person.sub.membership.is_adult and person.juniorprofile_set.count() == 0:
                    return redirect('public-consent-junior-token', person_id=person.id, token=self.token)
            if self.invoice:
                return redirect('public-invoice-token', token=self.token)
        return super().get(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if not self.person.sub:
            kwargs.update({'non_member': True})
        return kwargs

    def get_context_data(self, **kwargs):
        kwargs['person'] = self.person
        if kwargs['person'].sub:
            kwargs['member'] = True
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        self.person.consent_for_marketing(form.cleaned_data['marketing'] == 'yes')
        if self.person.sub:
            self.person.consent_for_database(form.cleaned_data['database'] == 'yes')
        self.person.save()
        messages.success(self.request, 'You have successfully registered.')
        if self.invoice:
            return redirect('public-consent-invoice-token', token=self.token)
        return super().form_valid(form)

    def get_success_url(self):
        if self.person.sub:
            return reverse('login')
        else:
            return reverse('public-home')


class ConsentJuniorTokenView(FormView):
    """
    Capture the junior profile
    The token is an invoice token
    The junior id is passed in the url as person-id
    """
    template_name = 'public/junior_member_profile.html'
    form_class = JuniorProfileForm
    parent = None
    person = None
    token = None

    def dispatch(self, request, *args, **kwargs):
        self.person = Person.objects.get(pk=kwargs['person_id'])
        self.token = kwargs['token']
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        self.initial = super().get_initial()
        parent = self.person.linked
        if parent.mobile_phone:
            phone = parent.mobile_phone
        else:
            phone = parent.address.home_phone
        self.initial.update({'contact0': parent.fullname, 'phone0': parent.mobile_phone})
        return self.initial

    def get_context_data(self, **kwargs):
        kwargs['person'] = self.person
        kwargs['buttons'] = [Button('Next', css_class='btn-success')]
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        profile = form.save(commit=False)
        profile.has_needs = form.cleaned_data['rad_has_needs'] == '2'
        profile.photo_consent = form.cleaned_data['photo'] == 'yes'
        profile.person = self.person
        profile.save()
        return redirect('public-consent-invoice-token', token=self.token)



