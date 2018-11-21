from decimal import Decimal
import logging
from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext
from django.views.generic import View, DetailView, TemplateView
from django.views.generic.edit import FormView
from django.contrib import messages
from django.db.models import Sum
from django.shortcuts import render_to_response, reverse, redirect, get_object_or_404
from django.core.signing import Signer
from braces.views import StaffuserRequiredMixin
from cardless.services import invoice_payments_list, detokenise
from members.views.views import PagedFilteredTableView
from members.models import Invoice, Payment, TextBlock, Settings, Subscription
from members.services import invoice_cancel, invoices_create_from_list, invoice_update_state, invoice_create_batch, \
    group_get_or_create
from members.forms import YearConfirmForm, EmailTextForm, InvoiceSelectForm, XlsMoreForm
from members.mail import do_mail
from members.excel import export_invoices
from members.filters import InvoiceFilter
from members.tables import InvoiceTable

stdlogger = logging.getLogger(__name__)


class InvoiceTableView(StaffuserRequiredMixin, PagedFilteredTableView):
    model = Invoice
    table_class = InvoiceTable
    filter_class = InvoiceFilter
    template_name = 'members/invoice_table.html'
    title = ''

    def get_queryset(self, **kwargs):
        qs = Invoice.objects.all().prefetch_related('payment_set').select_related('person').select_related(
            'person__membership')

        # set defaults for first time
        data = self.request.GET.copy()
        data['membership_year'] = data.get('membership_year', Settings.current_year())
        data['state'] = data.get('state', Invoice.STATE.UNPAID.value)
        data['older'] = data.get('older', 10)
        data['younger'] = data.get('younger', 365)
        data['lines'] = data.get('lines', 100000)

        self.table_pagination['per_page'] = data['lines']
        self.filter = self.filter_class(data, qs, request=self.request)
        self.total = self.filter.qs.aggregate(total=Sum('total'))['total']
        # return list so can sort by a property
        return list(self.filter.qs)

    def get_context_data(self, **kwargs):
        context = super(InvoiceTableView, self).get_context_data(**kwargs)
        context['table_title'] = 'Invoices'
        context['total'] = self.total if self.total else 0
        context['lines'] = self.table_pagination['per_page']
        context['actions'] = (('none', 'No action'),
                              ('export', 'Export'),
                              ('mail', 'Mail'),
                              ('group', 'Add to group'),
                              ('resign', 'Resign'),
                              )
        return context

    def post(self, request):
        """
        POST builds a list of selected people ids in a session variable
        and calls the action routine
        """
        request.session['source_path'] = request.META['HTTP_REFERER']

        action = request.POST['action']
        if action == 'none':
            return redirect(request.session['source_path'])

        selected_invoices = Invoice.objects.filter(pk__in=request.POST.getlist('selection'))

        if action == 'export':
            return export_invoices(selected_invoices)

        # remaining actions work with people list
        # Note values_list does not return a list
        request.session['selected_people_ids'] = list(selected_invoices.values_list('person_id', flat=True))

        if action == 'mail':
            return redirect('email-selection')

        if action == 'group':
            return redirect('group-add-list')

        if action == 'resign':
            return redirect('people-resign')

        return redirect('home')


# todo invoice summary tidy up
class InvoiceSummaryView(TemplateView):
    template_name = 'members/invoice_summary.html'
    title = 'Invoice summary'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = Settings.current_year()
        paid = Invoice.objects.filter(membership_year=year, state=Invoice.STATE.PAID).count()
        paid_total = Invoice.objects.filter(membership_year=year, state=Invoice.STATE.PAID
                                            ).aggregate(total=Sum('total'))
        unpaid = Invoice.objects.filter(membership_year=year, state=Invoice.STATE.UNPAID
                                        ).prefetch_related('payment_set')
        no_payment = 0
        no_payment_total = Decimal(0)
        pending = 0
        pending_total = Decimal(0)
        failed = 0
        failed_total = Decimal(0)
        cancelled = 0
        cancelled_total = Decimal(0)

        for record in unpaid:
            if record.payment_state == -1:
                no_payment += 1
                no_payment_total += record.total
            elif record.payment_state == Payment.STATE.PENDING:
                pending += 1
                pending_total += record.total
            elif record.payment_state == Payment.STATE.FAILED:
                failed += 1
                failed_total += record.total
            elif record.payment_state == Payment.STATE.CANCELLED:
                cancelled += 1
                cancelled_total += record.total
        context['paid'] = paid
        context['paid_total'] = paid_total
        context['no_payment'] = no_payment
        context['no_payment_total'] = no_payment_total
        context['pending'] = pending
        context['pending_total'] = pending_total
        context['failed'] = failed
        context['failed_total'] = failed_total
        context['cancelled'] = cancelled
        context['cancelled_total'] = cancelled_total
        context['count'] = paid + no_payment + pending + failed
        context['total'] = context['paid'] + no_payment_total + pending_total + failed_total
        return context


def add_invoice_summary(context):
    year = Settings.current_year()
    qs = Invoice.objects.filter(membership_year=year, state=Invoice.STATE.PAID)
    paid = qs.count()
    paid_total = qs.aggregate(total=Sum('total'))['total']

    pending_qs = Invoice.objects.filter(membership_year=year, pending=True)
    pending = pending_qs.count()
    pending_total = pending_qs.aggregate(total=Sum('total'))['total']

    unpaid = Invoice.objects.filter(membership_year=year, state=Invoice.STATE.UNPAID
                                    ).prefetch_related('payment_set')
    no_payment = 0
    no_payment_total = Decimal(0)
    failed = 0
    failed_total = Decimal(0)
    cancelled = 0
    cancelled_total = Decimal(0)

    for record in unpaid:
        if record.payment_state == -1:
            no_payment += 1
            no_payment_total += record.total
        elif record.payment_state == Payment.STATE.FAILED:
            failed += 1
            failed_total += record.total
        elif record.payment_state == Payment.STATE.CANCELLED:
            cancelled += 1
            cancelled_total += record.total

    context['paid'] = paid
    context['paid_total'] = paid_total
    context['no_payment'] = no_payment
    context['no_payment_total'] = no_payment_total
    context['pending'] = pending
    context['pending_total'] = pending_total
    context['failed'] = failed
    context['failed_total'] = failed_total
    context['cancelled'] = cancelled
    context['cancelled_total'] = cancelled_total
    context['count'] = paid + no_payment + pending + failed
    context['total'] = paid_total + no_payment_total + pending_total + failed_total
    return context


class InvoiceDetailView(StaffuserRequiredMixin, DetailView):
    model = Invoice
    template_name = 'members/invoice_detail.html'
    title = 'Invoice'

    def post(self, request, *args, **kwargs):
        invoice = self.get_object()
        if 'view' in request.POST:
            return do_mail(request, invoice, 'view')

        elif 'test' in request.POST:
            do_mail(request, invoice, 'test')
            return redirect(invoice)

        elif 'send' in request.POST:
            do_mail(request, invoice, 'send')
            messages.success(self.request, f'Invoice {invoice.id} has been mailed')
            return redirect(invoice.person)

        elif 'pay' in request.POST:
            return redirect(reverse('payment-invoice', kwargs={'invoice_id': invoice.id}))

        elif 'cancel' in request.POST:
            invoice_cancel(invoice, with_credit_note=True)
            return redirect(invoice.person)

        elif 'delete' in request.POST:
            invoice_cancel(invoice, with_credit_note=False)
            return redirect(invoice.person)

        elif 'superdelete' in request.POST:
            invoice_cancel(invoice, with_credit_note=False, superuser=True)
            return redirect(invoice.person)

        elif 'save_note' in request.POST:
            invoice.note = request.POST['note']
            if request.POST.get('special_case', None):
                invoice.special_case = True
            else:
                invoice.special_case = False
            invoice_update_state(invoice)
            return redirect(invoice)

        elif 'delete_note' in request.POST:
            invoice.note = ""
            invoice.special_case = False
            invoice_update_state(invoice)
            return redirect(invoice)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        invoice = self.get_object()
        invoice.add_context(context)
        context['payments'] = invoice_payments_list(invoice)
        TextBlock.add_email_context(context)
        return context


class InvoiceGenerateSelectionView(StaffuserRequiredMixin, FormView):
    """
    Create invoices for a selection of people
    """
    form_class = YearConfirmForm
    template_name = 'members/generic_crispy_form.html'
    title = 'Generate invoices'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        selection = self.request.session['selected_people_ids']
        context['title'] = 'Generate invoices'
        if selection:
            context['message'] = "{} people in the list".format(len(selection))
        return context

    def form_valid(self, form):
        year = form.cleaned_data['sub_year']
        selection = self.request.session['selected_people_ids']
        if 'apply' in self.request.POST and selection:
            count = invoices_create_from_list(selection, year)
            people = "person" if len(selection) == 1 else "people"
            messages.success(self.request, '{} {} processed and {} invoices generated for {}'.format(
                len(selection),
                people,
                count,
                year))
        self.request.session['selected_people_ids'] = []
        return redirect((self.request.session['source_path']))

    def get_success_url(self):
        return reverse('home')


class InvoiceMailView(StaffuserRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        invoice = Invoice.objects.get(pk=self.kwargs['pk'])
        option = self.kwargs['option']
        result = do_mail(request, invoice, option)
        if option == 'view':
            return result
        return redirect(invoice)


class InvoiceMailConfigView(StaffuserRequiredMixin, FormView):
    form_class = EmailTextForm
    template_name = 'members/generic_crispy_form.html'
    title = 'Invoice mail configuration'

    def get_initial(self):
        initial = super(InvoiceMailConfigView, self).get_initial()
        ids = TextBlock.email_params()
        if ids:
            initial['intro'] = ids[0]
            initial['notes'] = ids[1]
            initial['closing'] = ids[2]
        return initial

    def form_valid(self, form):
        intro = form.cleaned_data['intro']
        notes = form.cleaned_data['notes']
        closing = form.cleaned_data['closing']
        blocks = TextBlock.objects.filter(name='_invoice_mail')
        if len(blocks) == 0:
            block = TextBlock(name='_invoice_mail')
        else:
            block = blocks[0]
        block.text = intro + "|" + notes + "|" + closing
        block.save()
        return super(InvoiceMailConfigView, self).form_valid(form)

    def get_success_url(self):
        return reverse('invoice-detail', kwargs={'pk': self.kwargs['pk']})


class InvoiceMailBatchView(StaffuserRequiredMixin, View):
    """ Send email for all invoices that are unpaid and have not been emailed
        get asks for confirmation
        put sends the mail """

    def get(self, request, *args, **kwargs):
        count = self.get_list().count
        context = RequestContext(request)
        context['message'] = "This will send {} emails. Continue?".format(count)
        context['action_link'] = reverse('invoice-mail-batch')
        context['cancel_link'] = reverse('home')
        return render_to_response('members/confirm.html', context)

    def post(self, request, *args, **kwargs):
        invoices = self.get_list()
        count = 0
        for inv in invoices:
            count += do_mail(request, inv, option=None)
        return HttpResponse("Sent {} mails for {} invoices".format(count, len(invoices)))

    def get_list(self):
        year = Settings.current_year()
        return Invoice.objects.filter(state=Invoice.STATE.UNPAID.value, membership_year=year)


class InvoiceSelectView(StaffuserRequiredMixin, FormView):
    form_class = InvoiceSelectForm
    template_name = 'members/invoice_select.html'
    title = 'Invoice selection'

    def form_valid(self, form):
        choice = int(form.cleaned_data['choice'])
        ref = form.cleaned_data['ref']
        if choice == 1:
            return HttpResponseRedirect(reverse('invoice-detail', kwargs={'pk': ref}))
        else:
            return HttpResponseRedirect(reverse('person-detail', kwargs={'pk': ref}))


class InvoiceDeleteView(StaffuserRequiredMixin, View):
    """ Deletes unpaid items and invoices associated with a sub """

    def get(self, request, *args, **kwargs):
        sub = get_object_or_404(Subscription, pk=self.kwargs['pk'])
        for item in sub.invoiceitem_set.all():
            if item.invoice and item.invoice.state == Invoice.STATE.UNPAID.value:
                invoice_cancel(item.invoice)
            item.delete()
        return redirect(sub)


class InvoiceBatchView(StaffuserRequiredMixin, FormView):
    form_class = XlsMoreForm
    template_name = 'members/import_more.html'

    def get_context_data(self, **kwargs):
        context = super(InvoiceBatchView, self).get_context_data(**kwargs)
        context['title'] = 'Generate invoices'
        result = invoice_create_batch(size=0)
        context['remaining'] = result[0] - result[1]
        return context

    def form_valid(self, form):
        invoice_create_batch(size=100)
        return HttpResponseRedirect(reverse('invoice-batch'))


class InvoicePublicView(DetailView):
    """ Public view, accessed by a token"""
    model = Invoice
    template_name = 'public/invoice_public.html'
    invoice = None

    def get_object(self, queryset=None):
        self.invoice = detokenise(self.kwargs['token'], Invoice)
        return self.invoice

    def get_context_data(self, **kwargs):
        context = super(InvoicePublicView, self).get_context_data(**kwargs)
        if self.invoice:
            self.invoice.add_context(context)
            context['token'] = self.kwargs['token']
            context['cancelled'] = self.invoice.state == Invoice.STATE.CANCELLED.value
            context['payments_pending'] = invoice_payments_list(self.invoice, pending=True)
            context['payments_paid'] = invoice_payments_list(self.invoice, paid=True)
        return context

    def post(self, request, *args, **kwargs):
        year = Settings.current_year()
        invoice = self.get_object()
        person_token = Signer().sign(invoice.person.id)
        if 'pay' in request.POST:
            return redirect('cardless_payment_create', kwargs['token'])
        if 'query' in request.POST:
            group = group_get_or_create(f'{year}_subs_query')
            invoice.person.groups.add(group)
            return redirect('public-contact-token', token=person_token)
        elif 'resign' in request.POST:
            group = group_get_or_create(f'{year}_resignation')
            invoice.person.groups.add(group)
            return redirect('public-resign-token', token=person_token)
