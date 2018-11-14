import logging
import datetime
from django.conf import settings
from django.db.models import Sum
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, Http404
from django.template import RequestContext
from django.views.generic import View, ListView, CreateView, UpdateView, TemplateView
from django.views.generic.edit import FormView
from django.contrib import messages
from django.shortcuts import render, redirect, reverse, render_to_response
from braces.views import StaffuserRequiredMixin
from django_tables2 import SingleTableView
from mysite.common import Button
from members.services import group_get_or_create, invoice_create_batch
from members.forms import PeriodForm, SettingsForm, MailCampaignForm, XlsInputForm, SelectSheetsForm
from members.mail import do_mail, send_htmlmail
from members.excel import export_members, export_all, import_items, open_excel_workbook
from members.models import Settings, Membership, ItemType, Invoice, Fees, InvoiceItem, MailCampaign, ExcelBook, \
    TextBlock
from pos.models import PosPayment, VisitorBook
# from members.views.invoice_views import add_invoice_summary

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
        qs = super().get_queryset()
        self.filter = self.filter_class(self.request.GET, queryset=qs)
        return self.filter.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
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
        #add_invoice_summary(context)
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


class YearEndView(StaffuserRequiredMixin, FormView):
    """
    Year end requires that the year has been changed and the fees set
    """
    template_name = 'members/year_end.html'
    form_class = PeriodForm
    year = 0
    title = 'Period end'

    def get_initial(self):
        initial = {'start_date': Settings.year_start_date(),
                   'end_date': datetime.datetime.now().date()}
        return initial

    def get(self, request, *args, **kwargs):
        self.year = Settings.current_year()
        if datetime.datetime.now().year != self.year:
            messages.warning(request, f'Please change the membership year before running year end')
            return redirect('yearend-year')
        if not Fees.objects.filter(sub_year=self.year).exists():
            messages.warning(request, f'Please set fees for {self.year} before running year end')
            return redirect('fees-list')
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(YearEndView, self).get_context_data(**kwargs)
        context['year'] = self.year

        context['unbilled_bar'] = PosPayment.billing.unbilled_total(item_type=ItemType.BAR)
        context['unbilled_teas'] = PosPayment.billing.unbilled_total(item_type=ItemType.TEAS)
        context['unbilled_visitors'] = VisitorBook.billing.unbilled_total()
        qs = InvoiceItem.objects.filter(invoice=None
                                        ).values('item_type_id', 'item_type__description'
                                                 ).annotate(total=Sum('amount'))
        items = []
        query = '?invoiced=0&item_type='
        for record in qs:
            items.append([record['item_type__description'], record['total'], query+str(record['item_type_id'])])
        context['items'] = items
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

    def post(self, request, *args, **kwargs):
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
            counts = invoice_create_batch(exclude_name='2015UnpaidInvoices')
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
