import json
import logging
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, Http404
from django.template import RequestContext
from django.views.generic import View, ListView, DetailView, CreateView, UpdateView, TemplateView
from django.views.generic.edit import FormView, FormMixin
from django.contrib import messages
from django.db.models import Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.shortcuts import render_to_response, reverse
from django.forms import ModelForm
from django.contrib.auth.hashers import check_password
from django.urls.base import reverse_lazy
from django.utils.dateparse import parse_date
from django.core.serializers import serialize
from braces.views import StaffuserRequiredMixin

from django_tables2 import SingleTableView
from mysite.common import Button
from public.forms import NameForm, AddressForm
from members.models import (Person, Address, Membership, Subscription, InvoiceItem, Invoice, Fees,
                     Payment, CreditNote, ItemType, TextBlock, ExcelBook, Group, MailCampaign)
from cardless.services import invoice_payments_list, get_payment, update_payment
from members.services import *
from members.forms import *
from members.mail import do_mail, send_multiple_mails, send_template_mail, send_htmlmail
from members.excel import export_members,export_invoices,export_payments, export_all, export_people, import_items
from members.filters import JuniorFilter, SubsFilter, InvoiceFilter, InvoiceItemFilter, PaymentFilter
from members.tables import InvoiceTable, InvoiceItemTable, PaymentTable, ApplicantTable, MembershipTable
from pos.models import PosPayment, VisitorBook

stdlogger = logging.getLogger(__name__)


def permission_denied(view, request):
    """
    Redirect to login with error message when user has not got staff permission
    """
    messages.error(request, "You are logged in as {} but don't have permission to access {}.\
    Would you like to login as a different user?".format(request.user, request.path))
    return redirect('login')


class PagedFilteredTableView(SingleTableView):
    """
    Generic view for django tables 2 with filter
    http://www.craigderington.me/django-generic-listview-with-django-filters-and-django-tables2/
    """
    filter_class = None
    formhelper_class = None
    context_filter_name = 'filter'
    table_pagination = {"per_page": 100000}

    def get_queryset(self, **kwargs):
        qs = super(PagedFilteredTableView, self).get_queryset()
        self.filter = self.filter_class(self.request.GET, queryset=qs)
        return self.filter.qs

    def get_context_data(self, **kwargs):
        context = super(PagedFilteredTableView, self).get_context_data()
        context['lines'] = self.table_pagination['per_page']
        context[self.context_filter_name] = self.filter
        return context


class HomeView(StaffuserRequiredMixin, TemplateView):
    template_name = 'members/index.html'

    def get_context_data(self, **kwargs):
        context = super(HomeView, self).get_context_data(**kwargs)
        context['title'] = 'Home Page'
        context['membership_year'] = Settings.current_year()
        context['db_name'] = settings.DATABASES['default']['NAME']
        add_invoice_summary(context)
        return context


def add_membership_context(context):
    """ Add membership dictionary to context """
    mem_dict = {}
    for mem in Membership.objects.all():
        mem_dict[mem.id] = mem.description
    context['mem_dict'] = mem_dict


def search_person(request):
    """
    Redirect to a person detail page
    In response to a search on the navbar
    """
    id = request.GET.get('nav_person_id', '')
    if id:
        return redirect(reverse('person-detail', kwargs={'pk': id}))
    return Http404


class PersonExportView(StaffuserRequiredMixin, View):

    def get(self, request, option="all"):
        return export_members(option)

# ============== Subscriptions


class SubCreateView(StaffuserRequiredMixin, CreateView):
    model = Subscription
    form_class = SubscriptionForm
    template_name = 'members/subscription_form.html'

    def get_form_kwargs(self):
        """ pass the person_id to the form """
        kwargs = super().get_form_kwargs()
        kwargs.update({'person_id': self.kwargs['person_id']})
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['person'] = Person.objects.get(pk=self.kwargs['person_id'])
        return context

    def form_valid(self, form):
        # if 'cancel' in form.data:
        #     return redirect(reverse('person-detail', kwargs={'pk': self.kwargs['person_id']}))

        form.instance.person_member = Person.objects.get(pk=self.kwargs['person_id'])
        # ensure a previously inactive or resigned person is now active
        form.instance.person_member.state = Person.ACTIVE
        form.instance.person_member.save()
        parent = form.instance.person_member.linked
        if parent:
            if parent.state == Person.APPLIED and parent.adultapplication_set.count == 0:
                parent.state == Person.ACTIVE
                parent.save()

        form.instance.invoiced_month = 0
        form.instance.membership = Membership.objects.get(pk=form.cleaned_data['membership_id'])

        sub = form.save()
        subscription_activate(sub)
        subscription_create_invoiceitems(sub, sub.start_date.month)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('person-detail', kwargs={'pk': self.kwargs['person_id']})


class SubUpdateView(StaffuserRequiredMixin, UpdateView):
    model = Subscription
    form_class = SubscriptionForm
    template_name = 'members/subscription_form.html'

    def get_form_kwargs(self):
        """ pass the person_id to the form """
        sub = self.get_object()
        kwargs = super().get_form_kwargs()
        kwargs.update({'person_id': sub.person_member_id})
        return kwargs

    def get_context_data(self, **kwargs):
        context = super(SubUpdateView, self).get_context_data(**kwargs)
        sub = self.get_object()
        context['sub'] = sub
        context['person'] = sub.person_member
        context['items'] = sub.invoiceitem_set.all().order_by('item_type')
        return context

    def form_invalid(self, form):
        sub = self.get_object()
        if 'cancel' in form.data:
            return redirect(sub.person_member)
        return super().form_invalid(form)

    def form_valid(self, form):
        sub = self.get_object()
        if 'cancel' in form.data:
            return redirect(sub.person_member)

        if 'submit' in form.data:
            form.instance.membership = Membership.objects.get(pk=form.cleaned_data['membership_id'])
            return super(SubUpdateView, self).form_valid(form)

        if 'delete' in form.data:
            sub = self.get_object()
            subscription_delete_invoiceitems(sub)
            person = sub.person_member
            subscription_delete(sub)
            return redirect(person)

        if 'resign' in form.data:
            person_resign(form.instance.person_member)
            return redirect(reverse('person-detail', kwargs={'pk': sub.person_member_id}))

    def get_success_url(self):
        sub = self.get_object()
        subscription_activate(sub)
        subscription_create_invoiceitems(sub, sub.start_date.month)
        return reverse('person-detail', kwargs={'pk': sub.person_member_id})


class SubCorrectView(StaffuserRequiredMixin, UpdateView):
    """ standard model view that skips validation """
    model = Subscription
    form_class = SubCorrectForm

    def get_success_url(self):
        sub = self.get_object()
        subscription_activate(sub)
        return reverse('person-detail', kwargs={'pk': sub.person_member_id})


class SubDetailView(StaffuserRequiredMixin, DetailView):
    model = Subscription
    template_name = 'members/generic_detail.html'

    class Form(ModelForm):
        class Meta:
            model = Subscription
            exclude = ['person_member', 'membership']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        sub = self.object
        context.update(
            {'width': '25rem',
             'title': 'Subscription',
             'sub_title': ('person-detail', sub.person_member.id, sub.person_member.fullname),
             'form': SubDetailView.Form(instance=sub),
             })
        items = sub.invoiceitem_set.all()
        if items:
            context['links'] = [('Invoice item', 'item-detail', items[0].id)]
        return context


class SubHistoryView(StaffuserRequiredMixin, ListView):
    """ Subs history for 1 person """
    model = Subscription
    template_name = 'members/subscription_history.html'
    context_object_name = 'subs'

    def get_queryset(self):
        self.person = get_object_or_404(Person, pk=self.kwargs['person_id'])
        return Subscription.objects.filter(person_member=self.person).order_by('-start_date', 'active')

    def get_context_data(self, **kwargs):
        context = super(SubHistoryView, self).get_context_data(**kwargs)
        context['person'] = self.person
        return context


class SubRenewAllView(StaffuserRequiredMixin, FormView):
    form_class = YearConfirmForm
    template_name = 'members/generic_crispy_form.html'

    def get_context_data(self, **kwargs):
        context = super(SubRenewAllView, self).get_context_data(**kwargs)
        self.subs = Subscription.objects.filter(active=True, no_renewal=False)
        context['title'] = 'Renew subscriptions'
        context['message'] = '{} subscriptions to renew'.format(self.subs.count())
        return context

    def form_valid(self, form):
        year = form.cleaned_data['sub_year']
        if 'renew' in self.request.POST:
            subscription_renew_batch(year, 5)
            messages.success(self.request, 'Subscriptions for {} generated'.format(year))
        return redirect(reverse('home'))

    def get_success_url(self):
        return reverse('home')


class SubRenewSelectionView(StaffuserRequiredMixin, FormView):
    """
    Renew a selected list of subscriptions
    If the list contains only one person, redirect to the person
    else redirect to the source path 
    """
    form_class = YearConfirmForm
    template_name = 'members/generic_crispy_form.html'

    def get_context_data(self, **kwargs):
        context = super(SubRenewSelectionView, self).get_context_data(**kwargs)
        selection = self.request.session['selected_people_ids']
        subtext = "subscription"
        if len(selection) > 1:
            subtext += "s"
        context['title'] = "Renew " + subtext
        if selection:
            context['message'] = '{} {} to renew'.format(len(selection), subtext)
        return context

    def form_valid(self, form):
        sub_year = form.cleaned_data['sub_year']
        selection = self.request.session['selected_people_ids']
        if 'apply' in self.request.POST and selection:
            if len(selection) == 1:
                person = Person.objects.get(pk=self.request.session['selected_people_ids'][0])
                subscription_renew(person.sub, sub_year, Subscription.START_MONTH, generate_item=True)
                self.request.session['selected_people_ids'] = []
                return redirect(person)
            else:
                count = subscription_renew_list(sub_year, Subscription.START_MONTH, selection)
                people = "person" if len(selection) == 1 else "people"
                messages.success(self.request, '{} {} processed and {} subscriptions for {} generated'.format(
                    len(selection),
                    people,
                    count,
                    sub_year))
        self.request.session['selected_people_ids'] = []
        return redirect(self.request.session['source_path'])

    def get_success_url(self):
        return reverse('home')


# ============ Year end

class ChangeYearView(StaffuserRequiredMixin, FormView):
    """
    Change membership year in Setting File
    """
    form_class = SettingsForm
    template_name = 'members/generic_crispy_form.html'

    def get_initial(self):
        initial = super().get_initial()
        initial['membership_year'] = Settings.current_year()
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Change membership year'
        return context

    def form_valid(self, form):
        if 'submit' in form.data:
            qset = Settings.objects.all()
            if qset:
                record = qset[0]
            else:
                record = Settings()
            record.membership_year = form.cleaned_data['membership_year']
            record.save()
        return redirect('home')


class YearEndView(StaffuserRequiredMixin, TemplateView):
    """
    Year end requires that the year has been changed and the fees set
    """
    template_name = 'members/year_end.html'
    year = 0

    def get(self, request, *args, **kwargs):
        self.year = Settings.current_year()
        if datetime.now().year != self.year:
            messages.warning(request, f'Please change the membership year before running year end')
            return redirect('yearend-year')
        if not Fees.objects.filter(sub_year=self.year).exists():
            messages.warning(request, f'Please set fees for {self.year} before running year end')
            return redirect('fees-list')
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(YearEndView, self).get_context_data(**kwargs)
        context['year'] = self.year
        context['buttons'] = [
            Button('Cancel', css_class='btn-default'),
            Button('Renew subs', name='renew', css_class='btn-danger'),
            Button('Create bar invoice items', name='bar', css_class='btn-danger'),
            Button('Create teas invoice items', name='teas', css_class='btn-danger'),
            Button('Create visitors invoice items', name='visitors', css_class='btn-danger'),
            Button('Create invoices', name='invoices', css_class='btn-danger'),
            Button('Count mail invoices', name='count', css_class='btn-primary'),
            Button('Mail invoices', name='mail', css_class='btn-danger')
        ]
        return context

    def post(self, request):
        year = Settings.current_year()
        if 'cancel' in request.POST:
            return redirect('home')

        # elif 'consolidate' in request.POST:
        #     counts = consolidate(year)
        #     message = '{} people processed, {} unpaid  and {} credit notes carried forward'.format(
        #         counts[0], counts[1], counts[2])
        #     messages.success(self.request, message)
        #     return redirect('year-end')

        # todo fix year end billing
        # elif 'renew' in request.POST:
        #
        #     #count = subscription_renew_batch(year, Subscription.START_MONTH)
        #     message = '{} subscriptions generated'.format(count)
        #     messages.success(self.request, message)
        #     return redirect('yearend')
        #
        # elif 'bar' in request.POST:
        #     count1, count2 = create_invoiceitems_from_payments(item_type_id=ItemType.BAR)
        #     message = f'{count1} POS records processed and {count2} invoice item records generated'
        #     messages.success(self.request, message)
        #     return redirect('yearend')
        #
        # elif 'teas' in request.POST:
        #     count1, count2 = create_invoiceitems_from_payments(item_type_id=ItemType.TEAS)
        #     message = f'{count1} POS records processed and {count2} invoice item records generated'
        #     messages.success(self.request, message)
        #     return redirect('yearend')
        #
        # elif 'visitors' in request.POST:
        #     count1, count2 = create_invoiceitems_from_payments(item_type_id=ItemType.VISITORS)
        #     message = f'{count1} POS records processed and {count2} invoice item records generated'
        #     messages.success(self.request, message)
        #     return redirect('yearend')

        elif 'invoices' in request.POST:
            counts = invoice_create_batch(exclude_slug='2015UnpaidInvoices')
            people = "person" if counts[0] == 1 else "people"
            message = '{} invoices created from {} {}'.format(counts[1], counts[0], people)
            messages.success(self.request, message)
            return redirect('yearend')

        elif 'count' in request.POST:
            inv_group = group_get_or_create('invoiceTest')
            inv_group.person_set.clear()
            invs = self.get_unpaid_invoices()
            group = group_get_or_create('2015UnpaidInvoices')
            count = 0
            for inv in invs:
                if not group.person_set.filter(id=inv.person.id).exists():
                    count += 1
                    inv.person.groups.add(inv_group)
            message = "Will send {} mails for {} invoices".format(count, invs.count())
            messages.success(self.request, message)

        elif 'mail' in request.POST:
            group = group_get_or_create(f'{year}_UnpaidInvoices')
            invs = self.get_unpaid_invoices()
            count = 0
            for inv in invs:
                if not group.person_set.filter(id=inv.person.id).exists():
                    count += 1
                    do_mail(self.request, inv, option='send')
            message = "Sent {} mails for {} invoices".format(count, invs.count())
            messages.success(self.request, message)
            return redirect('yearend')

        return redirect('yearend')

    def get_unpaid_invoices(self):
        year = Settings.current_year()
        invs = Invoice.objects.filter(
            state=Invoice.STATE.UNPAID.value, membership_year=year, gocardless_bill_id='', total__gt=0)
        return invs


class SubInvoiceCancel(StaffuserRequiredMixin, View):
    """ Deletes unpaid items and invoices associated with a sub """

    def get(self, request, *args, **kwargs):
        sub = get_object_or_404(Subscription, pk=self.kwargs['pk'])
        for item in sub.invoiceitem_set.all():
            if item.invoice and item.invoice.state == Invoice.STATE.UNPAID.value:
                invoice_cancel(item.invoice)
            item.delete()
        return redirect(sub)


# ============ Fees


class FeesCreateView(StaffuserRequiredMixin, CreateView):
    model = Fees
    form_class = FeesForm
    template_name = 'members/generic_crispy_form.html'

    def get_success_url(self):
        return reverse('fees-list')


class FeesUpdateView(StaffuserRequiredMixin, UpdateView):
    model = Fees
    form_class = FeesForm
    template_name = 'members/generic_crispy_form.html'

    def get_context_data(self, **kwargs):
        context = super(FeesUpdateView, self).get_context_data(**kwargs)
        context['title'] = 'Fees for {}'.format(self.get_object().sub_year)
        return context

    def form_invalid(self, form):
        if 'cancel' in form.data:
            return redirect('fees-list', year=self.get_object().sub_year)
        return super(FeesUpdateView, self).form_invalid(form)

    def form_valid(self, form):
        if 'cancel' in form.data:
            return redirect('fees-list', year=self.get_object().sub_year)

        if 'submit' in form.data:
            return super(FeesUpdateView, self).form_valid(form)

    def get_success_url(self):
        return reverse('fees-list',
                       kwargs={'year': self.get_object().sub_year}
                       )


class FeesListView(StaffuserRequiredMixin, ListView):
    model = Fees
    template_name = 'members/fees_list.html'

    def get_queryset(self):
        self.year = int(self.kwargs.get('year', 0))
        self.latest_year = Fees.objects.all().order_by('-sub_year')[0].sub_year
        if self.year == 0:
            self.year = self.latest_year
        return Fees.objects.filter(sub_year=self.year).order_by('membership')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['year'] = self.year
        context['latest'] = (self.latest_year == self.year)
        context['forward'] = self.year + 1
        context['back'] = self.year - 1
        if not VisitorFees.objects.filter(year=self.year).exists():
            messages.warning(self.request, f'Warning: No visitors fees exist for {self.year}')
        return context

    def post(self, request, *args, **kwargs):
        year = int(request.POST['year'])
        if 'back' in request.POST:
            return redirect('fees-list', year - 1)
        elif 'forward' in request.POST:
            return redirect('fees-list', year + 1)
        elif 'copy' in request.POST:
            for cat in Membership.objects.all():
                fee = Fees.objects.filter(sub_year=year, membership_id=cat.id)[0]
                if not fee:
                    fee = Fees(annual_sub=0, monthly_sub=0, joining_fee=0, Membership_id=cat.id)
                fee.sub_year = year + 1
                fee.id = None
                fee.save()
            messages.success(self.request, "Records for {} created".format(year + 1))
            return redirect('fees-list', year + 1)
        elif 'delete' in request.POST:
            for fee in Fees.objects.filter(sub_year=year):
                fee.delete()
            messages.success(self.request, "All records for {} deleted".format(year))
            return redirect('fees-list', year - 1)


class VisitorFeesUpdateView(StaffuserRequiredMixin, UpdateView):
    model = VisitorFees
    form_class = VisitorFeesForm
    template_name = 'members/generic_crispy_form_well.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Visitor fees'
        context['buttons'] = [
            Button('Save', name='save', css_class='btn-default'),
            Button('Delete', name='delete', css_class='btn-danger'), ]
        return context

    def get_success_url(self):
        return reverse('visitor-fees-list')

    def post(self, request, *args, **kwargs):
        if 'delete' in request.POST:
            self.get_object().delete()
            return redirect(self.get_success_url())
        return super().post(request, *args, **kwargs)


class VisitorFeesListView(StaffuserRequiredMixin, SingleTableView):
    model = VisitorFees
    template_name = 'members/visitors_fees_list.html'

    def get_queryset(self):
        return VisitorFees.objects.all().order_by('-year')

    def post(self, request, *args, **kwargs):
        if 'create' in request.POST:
            records = self.get_queryset()
            if records:
                record = records[0]
                VisitorFees.objects.create(year=record.year + 1,
                                           adult_fee=record.adult_fee,
                                           junior_fee=record.junior_fee)
            else:
                VisitorFees.objects.create(year=2017, adult_fee=6, junior_fee=3)
        return redirect('visitor-fees-list')


# ================ Membership categories


class MembershipTableView(StaffuserRequiredMixin, SingleTableView):
    model = Membership
    table_class = MembershipTable
    template_name = 'members/generic_table.html'
    table_pagination = {"per_page": 10000}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Membership categories'
        return context


class MembershipCreateView(StaffuserRequiredMixin, CreateView):
    model = Membership
    template_name = 'members/generic_crispy_form_well.html'
    form_class = MembershipForm
    success_url = reverse_lazy('categories-list')


class MembershipUpdateView(StaffuserRequiredMixin, UpdateView):
    model = Membership
    template_name = 'members/generic_crispy_form.html'
    form_class = MembershipForm
    success_url = reverse_lazy('categories-list')

# ================ Invoice items


class InvoiceItemListView(StaffuserRequiredMixin, ListView):
    model = InvoiceItem
    template_name = 'members/invoiceitem_list.html'

    def get_queryset(self):
        return InvoiceItem.objects.filter(invoice_record_id=self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        context = super(InvoiceItemListView, self).get_context_data(**kwargs)
        context['state_list'] = Invoice.STATES
        return context


class InvoiceItemCreateViewOld(StaffuserRequiredMixin, CreateView):
    model = InvoiceItem
    form_class = InvoiceItemForm
    form = InvoiceItemForm()
    template_name = 'members/invoiceitem_form.html'

    def get_success_url(self):
        return reverse('person-detail',
                       kwargs={'pk': self.kwargs['person_id']})

    def get_context_data(self, **kwargs):
        context = super(InvoiceItemCreateView, self).get_context_data(**kwargs)
        context['person'] = Person.objects.get(pk=self.kwargs['person_id'])
        return context

    def form_valid(self, form):
        form.instance.person = Person.objects.get(pk=self.kwargs['person_id'])
        return super(InvoiceItemCreateView, self).form_valid(form)


class InvoiceItemCreateView(StaffuserRequiredMixin, CreateView):
    model = InvoiceItem
    form_class = InvoiceItemForm
    template_name = 'members/crispy_tile.html'

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


class InvoiceItemDetailViewOld(StaffuserRequiredMixin, DetailView):
    model = InvoiceItem
    template_name = 'members/invoiceitem_detail.html'


class InvoiceItemDetailView(StaffuserRequiredMixin, DetailView):
    model = InvoiceItem
    template_name = 'members/generic_detail.html'

    class Form(ModelForm):
        class Meta:
            model = InvoiceItem
            exclude = ['person', 'invoice', 'payment', 'subscription']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        item = self.object
        context.update(
            {'width': '25rem',
             'title': 'Invoice Item',
             'sub_title': ('person-detail', item.person_id, item.person.fullname),
             'form': InvoiceItemDetailView.Form(instance=item),
             'links': [('Invoice', 'invoice-detail', item.invoice.id)],
             'edit': ('item-update', item.id)
             })
        return context


class InvoiceItemTableView(StaffuserRequiredMixin, PagedFilteredTableView):
    model = InvoiceItem
    table_class = InvoiceItemTable
    filter_class = InvoiceItemFilter
    template_name = 'members/invoiceitem_table.html'
    table_pagination = {"per_page": 10}

    def get_queryset(self, **kwargs):
        qs = InvoiceItem.objects.all().select_related('person')

        # set defaults for first time
        data = self.request.GET.copy()
        self.filter = self.filter_class(data, qs, request=self.request)
        self.total = self.filter.qs.aggregate(total=Sum('amount'))['total']
        return self.filter.qs

    def get_context_data(self, **kwargs):
        context = super(InvoiceItemTableView, self).get_context_data(**kwargs)
        context['title'] = "Invoice items"
        context['total'] = self.total if self.total else 0
        return context


# ================= INVOICES


class InvoiceTableView(StaffuserRequiredMixin, PagedFilteredTableView):
    model = Invoice
    table_class = InvoiceTable
    filter_class = InvoiceFilter
    template_name = 'members/invoice_table.html'

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
        context['title'] = "Invoices"
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

        selected_invoices = Invoice.objects.filter(
            pk__in=request.POST.getlist('selection')
        )

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


class InvoiceSummaryView(TemplateView):
    template_name = 'members/invoice_summary.html'

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


# class InvoiceListViewx(StaffuserRequiredMixin, FormMixin, ListView):
#     form_class = InvoiceFilterForm
#     model = Invoice
#     template_name = 'members/invoice_list.html'
#
#     def get(self, request, *args, **kwargs):
#         """ GET return HTML """
#         # From ProcessFormMixin
#         self.form = self.get_form(self.form_class)
#         # From BaseListView
#         self.object_list = self.get_queryset()
#         context = self.get_context_data()
#         return self.render_to_response(context)
#
#     def post(self, request, *args, **kwargs):
#         """ POST handles submit and ajax request """
#         self.form = self.get_form(self.form_class)
#         if self.form.is_valid():
#             self.object_list = self.get_queryset()
#
#             if request.is_ajax():
#                 context = self.get_context_data()
#                 context['checkboxes'] = False
#                 html = render_to_string('members/_invoice_list.html', context)
#                 dict = {"data": html}
#                 return JsonResponse(dict, safe=False)
#
#             if 'view' in self.form.data:
#                 """ show the rendered mail fro the first unpaid invoice """
#                 for inv in self.object_list:
#                     if inv.state == Invoice.UNPAID and (
#                             inv.gocardless_bill_id == "") and (
#                             inv.total > 0):
#                         return do_mail(request, inv, 'view')
#                 return HttpResponse('No unpaid mails to view')
#
#             if 'mail' in self.form.data:
#                 count = 0
#                 for inv in self.object_list:
#                     if inv.state == Invoice.UNPAID and (
#                             inv.gocardless_bill_id == "") and (
#                             inv.total > 0):
#                         count += do_mail(request, inv, 'send')
#                 return HttpResponse("Sent {} mails for {} invoices".format(
#                     count, self.object_list.count()))
#
#             if 'export' in self.form.data:
#                 return export_invoices(self.object_list)
#
#         context = self.get_context_data()
#         return self.render_to_response(context)
# 
#     def get_queryset(self):
#         form = self.form
#         # default settings for initial get which does not use the form
#         year = Settings.current_year()
#         start_datetime = datetime(year, Subscription.START_MONTH-1,1)
#         end_datetime = datetime.combine(date.today(), time(23, 59, 59))
#         q_paid = Invoice.PAID_IN_FULL
#         q_unpaid = Invoice.UNPAID
#         q_cancelled = -1
#         if getattr(form, 'cleaned_data', None):
#             q_paid = -1
#             q_unpaid = -1
#             q_cancelled = -1
#             if form.cleaned_data['membership_year']:
#                 year = form.cleaned_data['membership_year']
#             if form.cleaned_data['start_datetime']:
#                 start_datetime = form.cleaned_data['start_datetime']
#             if form.cleaned_data['end_datetime']:
#                 end_datetime = form.cleaned_data['end_datetime']
#             if form.cleaned_data['membership_year']:
#                 year = form.cleaned_data['membership_year']
#             if form.cleaned_data['paid']:
#                 q_paid = Invoice.PAID_IN_FULL
#             if form.cleaned_data['unpaid']:
#                 q_unpaid = Invoice.UNPAID
#             if form.cleaned_data['cancelled']:
#                 q_cancelled = Invoice.CANCELLED
#         queryset = Invoice.objects.filter(
#             membership_year=year,
#             creation_date__gte=start_datetime,
#             creation_date__lte=end_datetime).filter(
#                 Q(state=q_paid) |
#                 Q(state=q_unpaid) |
#                 Q(state=q_cancelled)
#             ).select_related(
#                 'person'
#             ).order_by(
#                 'person__last_name'
#             )
#         return queryset
# 
#     def get_context_data(self, **kwargs):
#         context = super(InvoiceListViewx, self).get_context_data(**kwargs)
#         context['state_list'] = Invoice.STATES
#         context['invoices'] = self.object_list
#         context['form'] = self.form
#         context['count'] = self.object_list.count()
#         context['total'] = self.object_list.aggregate(Sum('total'))['total__sum']
#         context['pending'] = self.object_list.filter(
#             state=Invoice.UNPAID).exclude(
#                 gocardless_bill_id="").aggregate(
#                     Sum('total')
#                     )['total__sum']
#         return context


class InvoiceDetailView(StaffuserRequiredMixin, DetailView):
    model = Invoice
    template_name = 'members/invoice_detail.html'

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
        context = super(InvoiceDetailView, self).get_context_data(**kwargs)
        invoice = self.get_object()
        invoice.add_context(context)
        context['payments'] = invoice_payments_list(invoice)
        TextBlock.add_email_context(context)
        context['show_buttons'] = True
        return context


class InvoiceGenerateSelectionView(StaffuserRequiredMixin, FormView):
    """
    Create invoices for a selection of people
    """
    form_class = YearConfirmForm
    template_name = 'members/generic_crispy_form.html'

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

    def form_valid(self, form):
        choice = int(form.cleaned_data['choice'])
        ref = form.cleaned_data['ref']
        if choice == 1:
            return HttpResponseRedirect(reverse('invoice-detail', kwargs={'pk': ref}))
        else:
            return HttpResponseRedirect(reverse('person-detail', kwargs={'pk': ref}))


# ================ MailType Views


class MailTypeCreateView(StaffuserRequiredMixin, CreateView):
    model = MailType
    form_class = MailTypeForm
    template_name = 'members/generic_crispy_form.html'

    def get_success_url(self):
        return reverse('mailtype-list')


class MailTypeUpdateView(StaffuserRequiredMixin, UpdateView):
    model = MailType
    form_class = MailTypeForm
    template_name = 'members/generic_crispy_form.html'

    def get_form_kwargs(self):
        kwargs = super(MailTypeUpdateView, self).get_form_kwargs()
        kwargs['with_delete'] = True
        return kwargs

    def get_context_data(self, **kwargs):
        context = super(MailTypeUpdateView, self).get_context_data(**kwargs)
        context['title'] = 'Edit message type'
        return context

    def form_invalid(self, form):
        if 'cancel' in form.data:
            return HttpResponseRedirect(self.get_success_url())
        return super(MailTypeUpdateView, self).form_invalid(form)

    def form_valid(self, form):
        if 'cancel' in form.data:
            return HttpResponseRedirect(self.get_success_url())
        if 'submit' in form.data:
            return super(MailTypeUpdateView, self).form_valid(form)
        if 'delete' in form.data:
            self.get_object().delete()
            return super(MailTypeUpdateView, self).form_valid(form)

    def get_success_url(self):
        return reverse('mailtype-list')


class MailTypeListView(StaffuserRequiredMixin, ListView):
    """ List all mail type """
    model = MailType
    template_name = 'members/mailtype_list.html'
    context_object_name = 'mailtypes'
    ordering = 'sequence'


class MailTypeDetailView(StaffuserRequiredMixin, DetailView):
    model = MailType
    template_name = 'members/mailtype_detail.html'

    def get_context_data(self, **kwargs):
        context = super(MailTypeDetailView, self).get_context_data(**kwargs)
        mailtype = self.get_object()
        context['people'] = mailtype.person_set.all()
        context['mailtype'] = mailtype
        return context


# ================== PAYMENTS

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
        context = super(PaymentDetailView, self).get_context_data(**kwargs)
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
        context = super(PaymentListView, self).get_context_data(**kwargs)
        context['title'] = "Payments"
        context['total'] = self.total if self.total else 0
        return context


class PaymentListViewX(StaffuserRequiredMixin, FormMixin, TemplateView):
    form_class = PaymentFilterForm
    model = Payment
    template_name = 'members/payment_list.html'

    def get(self, request, *args, **kwargs):
        """ GET returns HTML """
        self.form = self.get_form(self.form_class)
        self.object_list = self.get_queryset()
        context = self.get_context_data()
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        """ POST handles submit and ajax request """
        self.form = self.get_form(self.form_class)
        if self.form.is_valid():
            self.object_list = self.get_queryset()

            if request.is_ajax():
                context = self.get_context_data()
                html = render_to_string("members/_payment_list.html", context)
                dict = {"data": html}
                return JsonResponse(dict, safe=False)

            if 'export' in self.form.data:
                return export_payments(self.object_list)

        context = self.get_context_data()
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super(PaymentListViewX, self).get_context_data(**kwargs)
        context['form'] = self.get_form(self.form_class)
        context['payments'] = self.object_list
        context['payment_types'] = Payment.TYPES
        context['payment_states'] = Payment.STATE.choices
        dict = self.queryset.aggregate(Sum('amount'), Sum('fee'))
        context['count'] = self.queryset.count()
        context['total'] = dict['amount__sum']
        context['fees'] = dict['fee__sum']
        return context

    def get_queryset(self):
        form = self.form
        year = Settings.current_year()
        start_date = date(year, 4, 1)
        end_date = date.today()
        q_direct_debit = Payment.DIRECT_DEBIT
        q_bacs = Payment.BACS
        q_cheque = Payment.CHEQUE
        q_other = Payment.OTHER
        q_cash = Payment.CASH
        if getattr(form, 'cleaned_data', None):
            if form.cleaned_data['membership_year']:
                year = form.cleaned_data['membership_year']
            if form.cleaned_data['start_date']:
                start_date = form.cleaned_data['start_date']
            if form.cleaned_data['end_date']:
                end_date = form.cleaned_data['end_date'] + timedelta(days=1)
            q_direct_debit = -1
            q_bacs = -1
            q_cheque = -1
            q_other = -1
            q_cash = -1
            if form.cleaned_data['direct_debit']:
                q_direct_debit = Payment.DIRECT_DEBIT
            if form.cleaned_data['bacs']:
                q_bacs = Payment.BACS
            if form.cleaned_data['cheque']:
                q_cheque = Payment.CHEQUE
            if form.cleaned_data['other']:
                q_other = Payment.OTHER
            if form.cleaned_data['cash']:
                q_cash = Payment.CASH
        self.queryset = Payment.objects.filter(
            membership_year=year,
            creation_date__gte=start_date,
            creation_date__lte=end_date).filter(
            Q(type=q_direct_debit) |
            Q(type=q_bacs) |
            Q(type=q_cheque) |
            Q(type=q_cash) |
            Q(type=q_other)
        ).select_related(
            'person'
        ).order_by(
            'person__last_name'
        )
        return self.queryset


# ================== CREDIT NOTES


class CreditNoteCreateView(StaffuserRequiredMixin, CreateView):
    model = CreditNote
    form_class = CreditNoteForm
    template_name = 'members/generic_crispy_form.html'
    success_msg = "Credit note added"

    def get_context_data(self, **kwargs):
        person = Person.objects.get(pk=self.kwargs['person_id'])
        context = super(CreditNoteCreateView, self).get_context_data(**kwargs)
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
        context = super(CreditNoteDetailView, self).get_context_data(**kwargs)

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


# ================ MailCampaign Views


class MailCampaignCreateView(StaffuserRequiredMixin, CreateView):
    model = MailCampaign
    form_class = MailCampaignForm
    template_name = 'members/generic_crispy_form.html'

    def form_invalid(self, form):
        if 'cancel' in form.data:
            return HttpResponseRedirect(reverse('home'))
        return super(MailCampaignCreateView, self).form_invalid(form)

    def form_valid(self, form):
        if 'cancel' in form.data:
            return HttpResponseRedirect(reverse('home'))

        # Copy template json to campaign
        mail_template = form.cleaned_data['mail_template']
        form.instance.json = mail_template.json
        return super(MailCampaignCreateView, self).form_valid(form)

    def get_success_url(self):
        return reverse('mail-campaign-bee', kwargs={'pk': self.object.id})


class MailCampaignUpdateView(StaffuserRequiredMixin, UpdateView):
    model = MailCampaign
    form_class = MailCampaignForm
    template_name = 'members/generic_crispy_form.html'

    def get_form_kwargs(self):
        kwargs = super(MailCampaignUpdateView, self).get_form_kwargs()
        kwargs['with_delete'] = True
        return kwargs

    def get_context_data(self, **kwargs):
        context = super(MailCampaignUpdateView, self).get_context_data(**kwargs)
        context['title'] = 'Edit campaign'
        return context

    def form_invalid(self, form):
        if 'cancel' in form.data:
            return HttpResponseRedirect(self.get_success_url())
        return super(MailCampaignUpdateView, self).form_invalid(form)

    def form_valid(self, form):
        if 'next' in form.data:
            mail_template = form.cleaned_data['mail_template']
            form.instance.json = mail_template.json
            return super(MailCampaignUpdateView, self).form_valid(form)

        if 'delete' in form.data:
            self.get_object().delete()
            return super(MailCampaignUpdateView, self).form_valid(form)
        return Http404

    def get_success_url(self):
        return reverse('mail-campaign-bee', kwargs={'pk': self.object.id})


class MailCampaignListView(StaffuserRequiredMixin, ListView):
    """ List all mail type """
    model = MailCampaign
    template_name = 'members/mail_campaign_list.html'
    context_object_name = 'mail_campaigns'


class MailCampaignBeeView(StaffuserRequiredMixin, TemplateView):
    """
    Edit campaign using bee editor
    """
    template_name = 'members/bee.html'

    def get(self, request, *args, **kwargs):
        """ Bee editor is asking for json template """
        if request.is_ajax():
            campaign = MailCampaign.objects.get(pk=request.GET['campaign_id'])
            return JsonResponse(campaign.json, safe=False)
        else:
            return super(MailCampaignBeeView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        action = request.POST['action']
        html = request.POST['html']
        if action == 'save':
            """ Save pressed in BEE editor so update the campaign """
            campaign = MailCampaign.objects.get(pk=request.POST['campaignId'])
            campaign.text = html
            campaign.json = request.POST['template']
            campaign.save()
            return redirect(reverse('mail-campaign-list'))

        elif action == "send":
            """ send a test mail """
            from_email = getattr(settings, "INFO_EMAIL", "is@ktconsultants.co.uk")
            to_email = getattr(settings, "TEST_EMAIL", "is@ktconsultants.co.uk")
            send_htmlmail(from_email=from_email, to=to_email, subject="Test", html_body=html)
            return JsonResponse({'status': 'ok'})

    def get_context_data(self, **kwargs):
        context = super(MailCampaignBeeView, self).get_context_data(**kwargs)
        context['campaign_id'] = self.kwargs.get('pk', None)
        return context


# ================== TEXT BLOCKS


class TextBlockCreateView(StaffuserRequiredMixin, CreateView):
    model = TextBlock
    form_class = TextBlockForm
    template_name = 'members/textblock_form.html'

    def get_context_data(self, **kwargs):
        context = super(TextBlockCreateView, self).get_context_data(**kwargs)
        context['title'] = 'Create text block'
        return context

    def get_form_kwargs(self):
        kwargs = super(TextBlockCreateView, self).get_form_kwargs()
        kwargs.update({'no_delete': True})
        return kwargs

    def form_invalid(self, form):
        if 'cancel' in form.data:
            return redirect('text-list')
        return super(TextBlockCreateView, self).form_invalid(form)

    def form_valid(self, form):
        if 'cancel' in form.data:
            return redirect('text-list')
        return super(TextBlockCreateView, self).form_valid(form)

    def get_success_url(self):
        return reverse('text-list')


class TextBlockUpdateView(StaffuserRequiredMixin, UpdateView):
    model = TextBlock
    form_class = TextBlockForm
    template_name = 'members/textblock_form.html'

    def get_context_data(self, **kwargs):
        context = super(TextBlockUpdateView, self).get_context_data(**kwargs)
        context['title'] = 'Update text block'
        return context

    def form_valid(self, form):

        if 'save' in form.data:
            form.save()
        if 'delete' in form.data:
            block = self.get_object()
            block.delete()
        return redirect(reverse('text-list'))

    def form_invalid(self, form):
        if 'delete' in form.data:
            block = self.get_object()
            block.delete()
            return redirect(reverse('text-list'))
        return super(TextBlockUpdateView, self).form_invalid(form)


class TextBlockListView(StaffuserRequiredMixin, ListView):
    model = TextBlock
    template_name = 'members/textblock_list.html'


class EmailView(StaffuserRequiredMixin, FormView):
    form_class = EmailForm
    template_name = 'members/email.html'
    selection = False

    def get_context_data(self, **kwargs):
        context = super(EmailView, self).get_context_data(**kwargs)
        target = 'Send email'
        context['title'] = target
        blocks = TextBlock.objects.all()
        try:
            value_list = []
            for block in blocks:
                dict_entry = {"text": "'" + block.name + "'", "value": "'" + str(block.id) + "'"}
                json_entry = json.dumps(dict_entry).replace('"', '')
                value_list.append(json_entry)
            context['blocks'] = value_list
        except:
            pass
        return context

    def get_form_kwargs(self):
        person_id = self.kwargs.get('person', '')
        self.to = ''
        self.person = None
        if person_id:
            self.person = Person.objects.get(pk=person_id)
            self.to = self.person.email
        self.group = self.kwargs.get('group', '-1')
        self.campaign_id = self.kwargs.get('campaign', 0)
        kwargs = super(EmailView, self).get_form_kwargs()
        kwargs.update({'to': self.to,
                       'group': self.group,
                       'selection': self.selection})

        return kwargs

    def get_initial(self):
        """
        This is called by get_context_data
        """
        initial = super(EmailView, self).get_initial()
        person_id = self.kwargs.get('person', '')
        if person_id:
            self.person = Person.objects.get(pk=person_id)
            self.to = self.person.email
            initial['to'] = self.to
        initial['group'] = self.kwargs.get('group', '-1')
        initial['from_email'] = getattr(settings, 'SUBS_EMAIL')
        initial['subject'] = "Coombe Wood LTC membership"
        initial['selected'] = self.selection
        initial['text'] = """Dear {{first_name}}"""
        campaign_id = self.kwargs.get('campaign', 0)
        if campaign_id:
            campaign = MailCampaign.objects.get(pk=campaign_id)
            initial['text'] = campaign.text
        return initial

    def get(self, request, *args, **kwargs):
        if request.is_ajax():
            try:
                blockId = int(request.GET['blockId'])
                block = TextBlock.objects.get(pk=blockId)
                dict = {}
                dict['text'] = block.text
                return JsonResponse(dict)
            except:
                return JsonResponse({'error': 'Bad AJAX request'})
        else:
            return super(EmailView, self).get(request, *args, **kwargs)

    def form_invalid(self, form):
        return super(EmailView, self).form_invalid(form)

    def form_valid(self, form):
        from_email = form.cleaned_data['from_email']
        to = form.cleaned_data['to']
        group_id = form.cleaned_data['group']
        selection = form.cleaned_data['selected']
        text = form.cleaned_data['text']
        subject = form.cleaned_data['subject']
        mail_type_list = []
        for mail_type in form.cleaned_data['mailtype']:
            mail_type_list.append(mail_type.id)
        mail_types = MailType.objects.filter(id__in=mail_type_list)

        if self.person:
            result = send_template_mail(request=self.request,
                                        person=self.person,
                                        text=text,
                                        from_email=from_email,
                                        subject=subject,
                                        mail_types=mail_types)
            if result == 'sent':
                messages.success(self.request, "Mail sent")
            else:
                messages.error(self.request, f'Mail not sent - {result}')
            return redirect('person-detail', pk=self.person.id)

        elif group_id != '':
            group = Group.objects.get(pk=group_id)
            result = send_multiple_mails(self.request, group.person_set.all(),
                                         text, from_email, None, None, subject, mail_types)
            messages.info(self.request, result)
            return redirect('group-detail', pk=group_id)

        elif selection:
            id_list = self.request.session['selected_people_ids']
            result = send_multiple_mails(self.request, Person.objects.filter(pk__in=id_list),
                                         text, from_email, None, None, subject, mail_types)
            self.request.session['selected_people_ids'] = []
            messages.info(self.request, result)
            return redirect(self.request.session['source_path'])

        else:
            return redirect('home')



class ImportExcelView(StaffuserRequiredMixin, FormView):
    """ Capture the excel name and batch size """
    form_class = XlsInputForm
    template_name = 'members/generic_crispy_form.html'

    def get_context_data(self, **kwargs):
        context = super(ImportExcelView, self).get_context_data(**kwargs)
        context['title'] = "Import from Excel"
        return context

    def form_valid(self, form):
        try:
            input_excel = form.cleaned_data['input_excel']

            # When we save the new one, any old file will be overwritten
            newbook = ExcelBook(file=input_excel)
            newbook.save()
        except Exception:
            messages.error(self.request, "Error reading Excel file \n")
            return redirect(reverse('import'))

        return HttpResponseRedirect(reverse('select-sheets'))


class SelectSheets(StaffuserRequiredMixin, FormView):
    """ Select itemtype sheets to import """
    form_class = SelectSheetsForm
    template_name = 'members/generic_crispy_form.html'

    def get_context_data(self, **kwargs):
        context = super(SelectSheets, self).get_context_data(**kwargs)
        context['title'] = 'Import invoice items'
        context['message'] = 'Select sheets to import'
        return context

    def form_valid(self, form):
        my_book = ExcelBook.objects.all()[0]
        with open_excel_workbook(my_book.file) as book:
            total = 0
            sheet_count = 0
            context = {'title': 'Import result'}
            error_list = []
            do_import = False
            for k in form.cleaned_data.keys():
                if form.cleaned_data[k]:
                    do_import = 'import' in form.data
                    sheet = book.sheet_by_name(k)
                    sheet_count += 1
                    result = import_items(sheet, do_import)
                    total = total + result[0]
                    if result[1]:
                        error_list.append('Sheet {0} contains errors'.format(k))
                        error_list.extend(result[1])
                        if do_import:
                            result[1].append('Import aborted')
                            break
                    else:
                        error_list.append('Sheet {0} checked OK'.format(k))
            context['errors'] = error_list
            context['message'] = '{} items were {} from {} sheets'.format(total, 'imported' if do_import else 'checked',
                                                                          sheet_count)
            return render(self.request, 'members/generic_result.html', context)


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


def export(request):
    return export_all()


# def reports(request):
#     report=Report.objects.all()[0]
#     qset = report.get_query()
#     list = report.report_to_list(queryset=qset)
#     fields = report.displayfield_set.all()
#     html = ""
#     for f in fields:
#         html += "<br \>" + f.name
#     return HttpResponse(html)


def bee_test(request):
    if request.is_ajax():
        if request.method == 'GET':
            template = request.GET['template']
            block = TextBlock.objects.get(type=TextBlock.BEE_TEMPLATE,
                                          name=template)
            # dict={'template': block.text}
            return JsonResponse(block.text, safe=False)
        else:
            html = request.POST['html']
            template = request.POST['template']
            name = "bee_test"
            blocks = TextBlock.objects.filter(type=TextBlock.BEE_TEMPLATE,
                                              name=name)
            if len(blocks) == 0:
                block = TextBlock(name=name,
                                  type=TextBlock.BEE_TEMPLATE,
                                  text=template)
                block.save()
            elif len(blocks) == 1:
                block = blocks[0]
                block.text = template
                block.save()
            else:
                return HttpResponse("Error in template name")
            return HttpResponse("")
    else:
        return render_to_response('members/bee.html', RequestContext(request))
