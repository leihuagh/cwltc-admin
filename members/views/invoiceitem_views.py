import logging
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.forms import ModelForm
from django.db.models import Sum
from django.shortcuts import redirect, reverse
from braces.views import StaffuserRequiredMixin
from members.views.views import PagedFilteredTableView
from members.models import Person, InvoiceItem, Invoice
from members.forms import InvoiceItemForm
from members.filters import InvoiceItemFilter
from members.tables import InvoiceItemTable

stdlogger = logging.getLogger(__name__)


class InvoiceItemListView(StaffuserRequiredMixin, ListView):
    model = InvoiceItem
    template_name = 'members/invoiceitem_list.html'
    title = 'Invoice items'

    def get_queryset(self):
        return InvoiceItem.objects.filter(invoice_record_id=self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        context = super(InvoiceItemListView, self).get_context_data(**kwargs)
        context['state_list'] = Invoice.STATES
        return context


class InvoiceItemCreateView(StaffuserRequiredMixin, CreateView):
    model = InvoiceItem
    form_class = InvoiceItemForm
    template_name = 'members/crispy_tile.html'
    title = 'Create invoice item'

    def get_success_url(self):
        return reverse('person-detail',
                       kwargs={'pk': self.kwargs['person_id']})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['person'] = Person.objects.get(pk=self.kwargs['person_id'])
        return context

    def form_valid(self, form):
        form.instance.person = Person.objects.get(pk=self.kwargs['person_id'])
        return super(InvoiceItemCreateView, self).form_valid(form)


class InvoiceItemUpdateView(StaffuserRequiredMixin, UpdateView):
    model = InvoiceItem
    form_class = InvoiceItemForm
    template_name = 'members/crispy_tile.html'
    title = 'Update invoice item'

    def post(self, request, *args, **kwargs):
        if 'delete' in request.POST:
            item = self.get_object()
            person_id = item.person.id
            item.delete()
            return redirect('person-detail', pk=person_id)
        return super().post(request, *args, **kwargs)

    def get_success_url(self):
        item = self.get_object()
        return reverse('person-detail', kwargs={'pk': item.person.id})

    def get_context_data(self, **kwargs):
        context = super(InvoiceItemUpdateView, self).get_context_data(**kwargs)
        item = self.get_object()
        context['person'] = item.person
        context['delete'] = True
        return context


class InvoiceItemDetailView(StaffuserRequiredMixin, DetailView):
    model = InvoiceItem
    template_name = 'members/generic_detail.html'
    title = 'Invoice item'

    class Form(ModelForm):
        class Meta:
            model = InvoiceItem
            exclude = ['person', 'invoice', 'payment', 'subscription']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        item = self.object
        context.update(
            {'width': '25rem',
             'sub_title': ('person-detail', item.person_id, item.person.fullname),
             'form': InvoiceItemDetailView.Form(instance=item),
             'edit': ('item-update', item.id)
             })
        if item.invoice:
            context['links'] = [('Invoice', 'invoice-detail', item.invoice.id)]
        return context


class InvoiceItemTableView(StaffuserRequiredMixin, PagedFilteredTableView):
    model = InvoiceItem
    table_class = InvoiceItemTable
    filter_class = InvoiceItemFilter
    template_name = 'members/invoiceitem_table.html'
    table_pagination = {"per_page": 10}
    filter = None
    total = None

    def get_queryset(self, **kwargs):
        qs = InvoiceItem.objects.all().select_related('person')

        # set defaults for first time
        data = self.request.GET.copy()
        self.filter = self.filter_class(data, qs, request=self.request)
        self.total = self.filter.qs.aggregate(total=Sum('amount'))['total']
        self.table_pagination['per_page'] = 10000
        return self.filter.qs

    def get_context_data(self, **kwargs):
        context = super(InvoiceItemTableView, self).get_context_data(**kwargs)
        context['table_title'] = "Invoice items"
        context['total'] = self.total if self.total else 0
        return context
