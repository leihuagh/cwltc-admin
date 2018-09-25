from django.shortcuts import reverse, redirect, render
from django.views.generic import DetailView, TemplateView, UpdateView, FormView
from django.core.signing import Signer
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.db.models import Sum
from braces.views import LoginRequiredMixin
from mysite.common import Button
from members.models import Person, Address, Settings, Invoice, Payment, ItemType
from pos.models import PosPayment, Transaction, VisitorBook
from .tables import PosPaymentsTable, VisitorBookTable
from members.views import set_person_context, add_membership_context, SingleTableView
from members.services import person_statement
from public.forms import NameForm, AddressForm, ConsentForm
from public.views import InvoicePublicView
from .models import Document
from .forms import DocumentForm

# Club Members views


class ClubHomeView(LoginRequiredMixin, TemplateView):
    template_name = 'club/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['bg_class'] = 'bg-white'
        return context


class PersonView(LoginRequiredMixin, DetailView):
    """
    Display personal data for the logged in user
    """
    model = Person
    template_name = 'club/person_detail.html'
    person = None

    def get_object(self, queryset=None):
        if 'pk' in self.kwargs:
            obj = Person.objects.get(pk=self.kwargs['pk'])
        else:
            try:
                obj = Person.objects.get(auth_id=self.request.user.id)
            except ObjectDoesNotExist:
                raise PermissionDenied
        self.person = obj
        return obj

    def get_context_data(self, **kwargs):
        self.get_object()
        context = super().get_context_data()
        set_person_context(context, self.person)
        add_membership_context(context)
        return context

    def post(self, request, *args, **kwargs):
        self.get_object()
        if 'change_phone' in request.POST:
            self.person.allow_phone = not self.person.allow_phone
        elif 'change_email' in request.POST:
            self.person.allow_email = not self.person.allow_email
        elif 'marketing' in request.POST:
            self.person.allow_marketing = not self.person.allow_marketing
        elif 'mail_subscribe' in request.POST:
            return redirect('mailtype-subscribe', person=self.person.pk)
        self.person.save()
        return redirect('club_person_pk', pk=self.person.pk)


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
    person = None

    def get_object(self, queryset=None):
        self.person = Person.objects.get(pk=self.kwargs['pk'])
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
    """ Search in member's database """
    template_name = 'club/search.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['person'] = person_from_user(self.request)
        context['search_url'] = reverse('ajax-person')
        return context


class ClubMagazineView(LoginRequiredMixin, TemplateView):
    template_name = 'club/magazine.html'

    def get_context_data(self, **kwargs):
        super().get_context_data(**kwargs)


class PoliciesView(LoginRequiredMixin, TemplateView):
    template_name = 'club/policies.html'


class StatementView(LoginRequiredMixin, TemplateView):
    """ List all invoices, payments and POS totals associated with the user """
    template_name = 'club/account_overview.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        person = person_from_user(self.request)
        year = Settings.current_year()
        pos_qs = PosPayment.objects.filter(person=person, transaction__billed=False)
        context['person'] = person
        context['year'] = year
        context['statement'] = person_statement(person, year)
        context['invoice_states'] = Invoice.STATES
        context['payment_types'] = Payment.TYPES
        context['payment_states'] = Payment.STATES
        context['bar_bill'] = pos_qs.filter(transaction__item_type_id=ItemType.BAR).aggregate(sum=Sum('total'))['sum']
        context['teas_bill'] = pos_qs.filter(transaction__item_type_id=ItemType.TEAS).aggregate(sum=Sum('total'))['sum']
        context['visitors_bill'] = VisitorBook.objects.filter(member=person,
                                                              billed=False).aggregate(sum=Sum('fee'))['sum']
        return context

    def post(self, request):
        for key in request.POST:
            if key[:4] == 'inv-':
                token = Signer().sign(key[4:])
                return redirect('club_invoice', token=token)
        return redirect('club_invoice_list')


class InvoiceView(LoginRequiredMixin, InvoicePublicView):
    """ Show detail of 1 invoice """
    template_name = 'club/invoice_club.html'


class PosListView(LoginRequiredMixin, SingleTableView):
    """
    Un-billed Teas or Bar transactions
    """
    model = PosPayment
    table_class = PosPaymentsTable
    template_name = 'club/transactions_table.html'
    table_pagination = {"per_page": 10}
    bar = False
    qs = None

    def get_table_data(self):
        self.person_id = self.kwargs.get('pk', None)
        if self.person_id:
            self.qs = PosPayment.objects.filter(person_id=self.person_id, transaction__billed=False)
        else:
            self.qs = PosPayment.objects.all()
        if self.bar:
            self.qs = self.qs.filter(transaction__item_type_id=ItemType.BAR)
        else:
            self.qs = self.qs.filter(transaction__item_type_id=ItemType.TEAS)
        return self.qs.select_related('transaction').select_related('person', 'transaction__item_type').order_by(
            '-transaction.creation_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sum'] = self.qs.aggregate(sum=Sum('total'))['sum']
        context['title'] = ('Bar' if self.bar else 'Teas') + ' Transactions'
        context['sub_title'] = f'Total: £ {self.qs.aggregate(sum=Sum("total"))["sum"]}'
        context['footnote'] = 'Attended transactions were charged to your account by bar staff'
        context['person_id'] = self.person_id
        return context


class PosDetailView(LoginRequiredMixin, DetailView):
    """ Detail of a Pos transaction"""

    model = Transaction
    template_name = 'club/pos_transaction_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        trans = self.get_object()
        context['items'] = trans.lineitem_set.all().order_by('id')
        if len(trans.pospayment_set.all()) > 1:
            context['payments'] = trans.pospayment_set.all()
        return context


class VisitorsListView(LoginRequiredMixin, SingleTableView):
    """
    List visitors book
    This can be for all entries or for a specific person (not necessary the one logged in)
    """
    model = VisitorBook
    table_class = VisitorBookTable
    template_name = 'club/transactions_table.html'
    table_pagination = {'per_page': 10}
    id = None
    all_entries = False

    def get_table_data(self):
        self.id = self.kwargs.get('person_id', None)
        if self.id:
            self.qs = VisitorBook.objects.filter(member_id=self.id)
        else:
            self.qs = VisitorBook.objects.all()
        return list(self.qs.order_by('-date', '-id').select_related('visitor').select_related('member__membership'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['all_entries'] = self.all_entries
        if self.id:
            person = Person.objects.get(pk=self.id)
            context['person'] = person
        context['title'] = 'Visitors Book Entries'
        context['sub_title'] = f'Total: £ {self.qs.aggregate(sum=Sum("fee"))["sum"]}'
        return context


class HistoryView(LoginRequiredMixin, TemplateView):
    template_name = 'club/history.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['bg_class'] = 'bg-white'
        return context


def person_from_user(request, raiseException=True):
    """
    Return a person object for the logged in user
    Should be called by views that inherit LoginRequiredMixin but if
    for any reason the user is not logged in return PermissionDenied
    """
    if request.user.is_authenticated:
        try:
            return Person.objects.get(auth_id=request.user.id)
        except ObjectDoesNotExist:
            pass
    if raiseException:
        raise PermissionDenied
    return None

def model_form_upload(request):
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('home')
    else:
        form = DocumentForm()
    return render(request, 'club/model_form_upload.html', {
        'form': form
    })