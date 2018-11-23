from datetime import datetime
import logging

from braces.views import StaffuserRequiredMixin
from django.contrib import messages
from django.db.models import Sum
from django.shortcuts import redirect
from django.views.generic.edit import FormView
from members.forms import PeriodForm, SettingsForm
from members.models import Settings, ItemType, Invoice, Fees, InvoiceItem, Subscription
from pos.models import PosPayment, VisitorBook


stdlogger = logging.getLogger(__name__)


class YearEndView(StaffuserRequiredMixin, FormView):
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


class BillingView(StaffuserRequiredMixin, FormView):
    """
    Year end requires that the year has been changed and the fees set
    """
    template_name = 'members/year_end.html'
    form_class = PeriodForm
    year = 0
    title = 'Period end'


    # def get(self, request, *args, **kwargs):
    #     self.year = Settings.current_year()
    #     if datetime.now().year != self.year:
    #         messages.warning(request, f'Please change the membership year before running year end')
    #         return redirect('yearend-year')
    #     if not Fees.objects.filter(sub_year=self.year).exists():
    #         messages.warning(request, f'Please set fees for {self.year} before running year end')
    #         return redirect('fees-list')
    #     return super().get(request, *args, **kwargs)

    def get_initial(self):
        self.year = Settings.current_year()
        self.from_date = datetime(self.year, Subscription.START_MONTH, 1).date()
        self.to_date = datetime.now().date()
        self.minimum_amount = 0
        self.invoice_date = datetime.now().date()
        initial = {'from_date': self.from_date,
                   'to_date': self.to_date,
                   'minimum_amount': self.minimum_amount,
                   'invoice_date': self.invoice_date
                   }
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['year'] = self.year
        bar = PosPayment.billing.unbilled_total(item_type_id=ItemType.BAR,
                                                from_date=self.from_date,
                                                to_date=self.to_date)
        teas = PosPayment.billing.unbilled_total(item_type_id=ItemType.TEAS,
                                                 from_date=self.from_date,
                                                 to_date=self.to_date)
        visitors = VisitorBook.billing.unbilled_total(from_date=self.from_date,
                                                      to_date=self.to_date)
        pos_total = bar + teas + visitors
        context['pos_bar'] = bar
        context['pos_teas'] = teas
        context['pos_visitors'] = visitors
        context['pos_total'] = pos_total
        qs = InvoiceItem.objects.filter(invoice=None).values(
            'item_type_id', 'item_type__description').annotate(
            total=Sum('amount'))
        query = '?invoiced=0&item_type='
        context['items'] = [[record['item_type__description'], record['total'], query+str(record['item_type_id'])]
                            for record in qs]
        context['item_total'] = sum([record['total'] for record in qs])
        # context['buttons'] = [
        #     Button('Cancel', css_class='btn-default'),
        #     Button('Renew subs', name='renew', css_class='btn-danger'),
        #     Button('Create invoices', name='invoices', css_class='btn-danger'),
        #     Button('Count mail invoices', name='count', css_class='btn-primary'),
        #     Button('Mail invoices', name='mail', css_class='btn-danger')
        # ]
        return context

    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        if form.is_valid():
            self.year = Settings.current_year()
            self.from_date = form.cleaned_data['from_date']
            self.to_date = form.cleaned_data['to_date']
        else:
            return redirect('billing-period')

        if 'filter' in request.POST:
            return self.render_to_response(self.get_context_data(form=form))

        pos_type = None
        if 'bar' in request.POST:
            pos_type = 'bar'
            count, value = PosPayment.billing.process(item_type_id=ItemType.BAR,
                                               from_date=self.from_date,
                                               to_date=self.to_date)


        elif 'teas' in request.POST:
            pos_type = 'teas'
            count, value = PosPayment.billing.process(item_type_id=ItemType.TEAS,
                                               from_date=self.from_date,
                                               to_date=self.to_date)

        elif 'visitors' in request.POST:
            pos_type = 'visitors'
            count, value = VisitorBook.billing.process(from_date=self.from_date,
                                                to_date=self.to_date)

        elif 'all' in request.POST:
            pos_type = 'bar, teas and vistors'
            count, value = PosPayment.billing.process(from_date=self.from_date,
                                               to_date=self.to_date)
            count2, value2 = VisitorBook.billing.process(from_date=self.from_date,
                                                 to_date=self.to_date)
            count += count2
            value += value2

        if pos_type:
            message = f'{count} invoice item records with value {value} generated from {pos_type} records'
            messages.success(self.request, message)
            return self.render_to_response(self.get_context_data(form=form))


        # elif 'consolidate' in request.POST:
        #     counts = consolidate(year)
        #     message = '{} people processed, {} unpaid  and {} credit notes carried forward'.format(
        #         counts[0], counts[1], counts[2])
        #     messages.success(self.request, message)
        #     return redirect('year-end')

        # elif 'renew' in request.POST:
        #
        #     #count = subscription_renew_batch(year, Subscription.START_MONTH)
        #     message = '{} subscriptions generated'.format(count)
        #     messages.success(self.request, message)
        #     return redirect('billing')
        #




        # elif 'invoices' in request.POST:
        #     counts = invoice_create_batch(exclude_name='2015UnpaidInvoices')
        #     people = "person" if counts[0] == 1 else "people"
        #     message = '{} invoices created from {} {}'.format(counts[1], counts[0], people)
        #     messages.success(self.request, message)
        #     return redirect('billing')
        #
        # elif 'count' in request.POST:
        #     inv_group = group_get_or_create('invoiceTest')
        #     inv_group.person_set.clear()
        #     invs = self.get_unpaid_invoices()
        #     group = group_get_or_create('2015UnpaidInvoices')
        #     count = 0
        #     for inv in invs:
        #         if not group.person_set.filter(id=inv.person.id).exists():
        #             count += 1
        #             inv.person.groups.add(inv_group)
        #     message = "Will send {} mails for {} invoices".format(count, invs.count())
        #     messages.success(self.request, message)
        #
        # elif 'mail' in request.POST:
        #     group = group_get_or_create(f'{year}_UnpaidInvoices')
        #     invs = self.get_unpaid_invoices()
        #     count = 0
        #     for inv in invs:
        #         if not group.person_set.filter(id=inv.person.id).exists():
        #             count += 1
        #             do_mail(self.request, inv, option='send')
        #     message = "Sent {} mails for {} invoices".format(count, invs.count())
        #     messages.success(self.request, message)
        #     return redirect('billing')

        return redirect('billing')

