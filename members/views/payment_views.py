# Includes Credit notes
import logging
from django.http import HttpResponseRedirect
from django.views.generic import CreateView, DetailView, UpdateView
from django.forms import ModelForm
from django.contrib import messages
from django.db.models import Sum
from django.shortcuts import reverse, redirect
from braces.views import StaffuserRequiredMixin
from cardless.services import get_payment, update_payment
from members.views.views import PagedFilteredTableView
from members.models import Invoice, Payment, CreditNote, Person, Settings
from members.services import invoice_update_state, invoice_pay
from members.forms import PaymentForm, CreditNoteForm
from members.filters import PaymentFilter
from members.tables import PaymentTable

stdlogger = logging.getLogger(__name__)


class PaymentCreateView(StaffuserRequiredMixin, CreateView):
    model = Payment
    form_class = PaymentForm
    template_name = 'members/payment_form.html'

    def get_form_kwargs(self):
        """ if view passed an invoice pass the total to the form """
        kwargs = super(PaymentCreateView, self).get_form_kwargs()
        self.inv = Invoice.objects.get(pk=self.kwargs['invoice_id'])
        if self.inv:
            kwargs.update({'amount': self.inv.total})
        return kwargs

    def get_context_data(self, **kwargs):
        context = super(PaymentCreateView, self).get_context_data(**kwargs)
        self.inv.add_context(context)
        return context

    def form_valid(self, form):
        invoice = Invoice.objects.get(pk=self.kwargs['invoice_id'])
        form.instance.person = invoice.person
        # save new object before handling many to many relationship
        payment = form.save()
        payment.state = Payment.STATE.CONFIRMED
        invoice_pay(invoice, payment)
        return super(PaymentCreateView, self).form_valid(form)

    def get_success_url(self):
        return reverse('invoice-detail',
                       kwargs={'pk': self.kwargs['invoice_id']})


class PaymentUpdateView(StaffuserRequiredMixin, UpdateView):
    """
    Allows payment detail to be updated bu authorised user
    """
    model = Payment
    form_class = PaymentForm
    template_name = 'members/payment_form.html'

    def get_context_data(self, **kwargs):
        context = super(PaymentUpdateView, self).get_context_data(**kwargs)
        self.get_object().invoice.add_context(context)
        return context

    def form_valid(self, form):
        payment = form.save()
        invoice = payment.invoice
        invoice_update_state(invoice)
        return super(PaymentUpdateView, self).form_valid(form)

    def get_success_url(self):
        invoice_id = self.get_object().invoice.id
        return reverse('invoice-detail',
                       kwargs={'pk': invoice_id})


class PaymentDetailViewOld(StaffuserRequiredMixin, DetailView):
    model = Payment
    template_name = 'members/payment_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payment = self.object
        if payment.cardless_id:
            try: #catch case when developing without go cardless
                gc_payment = get_payment(payment.cardless_id)
                context['gc_payment'] = gc_payment
                update_payment(payment, gc_payment)
            except:
                pass
        context['events'] = payment.events.all()
        context['invoice'] = payment.invoice
        context['user'] = self.request.user
        return context

    def post(self, request, **kwargs):
        payment = self.get_object(queryset=None)
        invoice = payment.invoice
        if "delete" in request.POST:
            if invoice:
                invoice_update_state(invoice)
            payment.delete()
        return redirect('invoice-detail', pk=invoice.id)


# todo Finish this view
class PaymentDetailView(StaffuserRequiredMixin, DetailView):
    model = Payment
    template_name = 'members/generic_detail.html'

    class DetailForm(ModelForm):
        class Meta:
            model = Payment
            exclude = ['person', 'invoice']


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        payment = self.object
        if payment.cardless_id:
            try: #catch case when developing without go cardless
                gc_payment = get_payment(payment.cardless_id)
                context['gc_payment'] = gc_payment
                update_payment(payment, gc_payment)
            except:
                pass
        context.update(
            {'width': '25rem',
             'title': 'Payment',
             'sub_title': ('person-detail', payment.person_id, payment.person.fullname),
             'form': PaymentDetailView.DetailForm(instance=payment),
             'fields': [('Number', payment.id)],
             'links': [('Invoice', 'invoice-detail', payment.invoice.id)],
             'edit': ('invoice-detail', payment.invoice.id),
             'delete': True
             })
        return context

    def post(self, request, **kwargs):
        payment = self.get_object(queryset=None)
        invoice = payment.invoice
        if "delete" in request.POST:
            if invoice:
                invoice_update_state(invoice)
            payment.delete()
        return redirect('invoice-detail', pk=invoice.id)


class PaymentListView(StaffuserRequiredMixin, PagedFilteredTableView):
    model = Payment
    table_class = PaymentTable
    filter_class = PaymentFilter
    template_name = 'members/invoice_table.html'

    def get_queryset(self, **kwargs):
        qs = Payment.objects.all().select_related(
            'person').select_related('person__membership').select_related('invoice')
        # set defaults for first time
        data = self.request.GET.copy()
        if len(data) == 0:
            data['membership_year'] = Settings.current_year()
            data['lines'] = 20
        lines = int(data.get('lines', 0))
        if lines > 0:
            self.table_pagination['per_page'] = lines
        self.filter = self.filter_class(data, qs, request=self.request)
        self.total = self.filter.qs.aggregate(total=Sum('amount'))['total']
        return self.filter.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Payments"
        context['total'] = self.total if self.total else 0
        return context


# ================== CREDIT NOTES


class CreditNoteCreateView(StaffuserRequiredMixin, CreateView):
    model = CreditNote
    form_class = CreditNoteForm
    template_name = 'members/generic_crispy_form.html'
    success_msg = "Credit note added"

    def get_context_data(self, **kwargs):
        person = Person.objects.get(pk=self.kwargs['person_id'])
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create credit note'
        context['message'] = person.fullname
        return context

    def form_valid(self, form):
        form.instance.person = Person.objects.get(pk=self.kwargs['person_id'])
        form.instance.detail = "Manually created"
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('person-detail',
                       kwargs={'pk': self.kwargs['person_id']})


class CreditNoteDetailView(StaffuserRequiredMixin, DetailView):
    """ Credit note detail with staff option to delete """
    model = CreditNote
    template_name = 'members/credit_note.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['person'] = Person.objects.get(pk=self.get_object().person_id)
        context['cnote'] = self.get_object()
        return context

    def post(self, request, *args, **kwargs):
        item = self.get_object()
        person_id = item.person.id
        if 'delete' in request.POST:
            item.delete()
            messages.info(request, "Credit note deleted")
        return HttpResponseRedirect(reverse('person-detail', kwargs={'pk': person_id}))

