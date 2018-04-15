from django.shortcuts import reverse, redirect
from django.views.generic import DetailView, TemplateView, UpdateView
from django.core.signing import Signer
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from braces.views import LoginRequiredMixin
from mysite.common import Button
from members.models import Person, Address, Settings, Invoice, Payment
from members.views import set_person_context, add_membership_context
from members.services import person_statement
from public.forms import NameForm, AddressForm
from public.views import InvoicePublicView

# Club Members views


class ClubHomeView(LoginRequiredMixin, TemplateView):
    template_name = 'club/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['bg_class']='bg-white'
        return context


class PersonView(LoginRequiredMixin, DetailView):
    '''
    Display personal data for the logged in user
    '''
    model = Person
    form_class = NameForm
    template_name = 'club/person_detail.html'

    def get_object(self, queryset = None):
        if 'pk' in self.kwargs:
            obj = Person.objects.get(pk=self.kwargs['pk'])
        else:
            try:
                obj = Person.objects.get(auth_id=self.request.user.id)
            except ObjectDoesNotExist:
                raise PermissionDenied
        return obj

    def get_context_data(self, **kwargs):
        person = self.get_object()
        context = super().get_context_data()
        set_person_context(context, person)
        add_membership_context(context)
        return context


class PersonUpdateView(LoginRequiredMixin, UpdateView):
    """
    Update name and address
    """
    model = Person
    form_class = NameForm
    template_name = 'club/crispy_card.html'

    def get_context_data(self, **kwargs):
        kwargs['form_title'] = 'Edit personal details'
        kwargs['buttons'] = (Button('Save', css_class='btn-success'),
                             Button('Cancel', css_class='btn-outline-success'))
        return super().get_context_data(**kwargs)

    def post(self, request, *args, **kwargs):
        if 'cancel' in request.POST:
            return redirect('club_person')
        return super().post(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('club_person')


class AddressUpdateView(LoginRequiredMixin, UpdateView):
    """
    Update address
    """
    model = Address
    form_class = AddressForm
    template_name = 'club/crispy_card.html'

    def get_object(self, queryset=None):
        self.person = Person.objects.get(pk=self.kwargs['person_id'])
        return Address.objects.get(pk=self.person.address_id)


    def get_context_data(self, **kwargs):
        kwargs['form_title'] = 'Edit address details'
        kwargs['buttons'] = (Button('Save', css_class='btn-success'),
                             Button('Cancel', css_class='btn-outline-success'))
        return super().get_context_data(**kwargs)

    def post(self, request, *args, **kwargs):
        if 'cancel' in request.POST:
            self.get_object()
            return redirect('club_person_pk', pk=self.person.id)
        return super().post(request, *args, **kwargs)


    def get_success_url(self):
        return reverse('club_person')


class ClubSearchView(LoginRequiredMixin, TemplateView):
    template_name = 'club/search.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['person'] = person_from_user(self.request)
        return context


class ClubMagazineView(LoginRequiredMixin, TemplateView):
    template_name = 'club/magazine.html'

    def get_context_data(self, **kwargs):
        super().get_context_data(**kwargs)


class PoliciesView(LoginRequiredMixin, TemplateView):
    template_name = 'club/policies.html'


class InvoiceListView(LoginRequiredMixin, TemplateView):
    """ List all invoices associated with the user"""
    template_name = 'club/account_overview.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        person = person_from_user(self.request)
        year = Settings.current_year()
        context['person'] = person
        context['year'] = year
        context['statement'] = person_statement(person, year)
        context['invoice_states'] = Invoice.STATES
        context['payment_types'] = Payment.TYPES
        context['payment_states'] = Payment.STATES
        return context

    def post(self, request):
        for key in request.POST:
            if key[:4] == 'inv-':
                token = Signer().sign(key[4:])
                return redirect('club_invoice', token=token)
        return redirect('club_invoice_list')


class ClubInvoiceView(LoginRequiredMixin, InvoicePublicView):
    """ Show detail of 1 invoice """
    template_name = 'club/invoice_club.html'


class HistoryView(LoginRequiredMixin, TemplateView):
    template_name = 'club/history.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['bg_class']='bg-white'
        return context


def person_from_user(request):
    try:
        return Person.objects.get(auth_id=request.user.id)
    except ObjectDoesNotExist:
        raise PermissionDenied