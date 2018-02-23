import logging
from django.shortcuts import redirect
from django.core.signing import Signer
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth.models import User
from django.views.generic.edit import FormView, UpdateView
from mysite.common import Button
from members.models import Person
from public.forms import RegisterForm, RegisterTokenForm, ConsentForm

logger = logging.getLogger(__name__)

class RegisterView(FormView):
    """
    Capture details of an existing member so they
    can register for the system
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
            signer = Signer()
            token = signer.sign(person.id)
            return redirect(self.kwargs['next'], token=token)

        messages.error(self.request, 'Sorry, only adult members can register on the site')
        return redirect(self.get_success_url())

    def get_success_url(self, **kwargs):
        return reverse('public-home')


class RegisterTokenView(FormView):
    """
    Register a member identified in a token
    Creates a link from Person to User in auth system
    POS overrides this view
    """
    template_name = 'public/crispy_card.html'
    form_class = RegisterTokenForm

    def get_initial(self):
        return {'username': self.get_person().email}

    def get_person(self):
        signer = Signer()
        person_id = signer.unsign(self.kwargs['token'])
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
            return redirect(self.get_success_url())
        else:
            # invalid token cannot occur when using POS
            # so we can safely redirect to public home
            messages.error('Invalid token')
            return redirect('public-home')


    def get_success_url(self, **kwargs):
        return reverse('club_home')


class ConsentView(UpdateView):
    """ Update consent flags in the Person record """
    model = Person
    template_name = 'public/consent_form.html'
    form_class = ConsentForm

    def get_object(self, queryset=None):
        signer = Signer()
        person_id = signer.unsign(self.kwargs['token'])
        try:
            return Person.objects.get(pk=person_id)
        except Person.DoesNotExist:
            return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['name'] = self.object.fullname
        return context

    def form_valid(self, form):
        signer = Signer()
        person_id = signer.unsign(self.kwargs['token'])
        try:
            person = Person.objects.get(pk=person_id)
            person.create_user(username=form.cleaned_data['username'],
                               password=form.cleaned_data['password'],
                               pin=form.cleaned_data['pin'])
            return redirect(self.get_success_url())
        except Person.DoesNotExist:
            # invalid token cannot occur when using POS
            # so we can safely redirect to public home
            messages.error('Invalid token')
            return redirect('public-home')

    def get_success_url(self, **kwargs):
        return reverse('club_home')