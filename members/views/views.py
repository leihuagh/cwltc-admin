import logging

from braces.views import StaffuserRequiredMixin
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, Http404
from django.shortcuts import render, redirect, reverse, render_to_response
from django.template import RequestContext
from django.views.generic import View, ListView, CreateView, UpdateView, TemplateView
from django.views.generic.edit import FormView
from django_tables2 import SingleTableView

from members.excel import export_members, export_all, import_items, open_excel_workbook
from members.forms import MailCampaignForm, XlsInputForm, SelectSheetsForm
from members.mail import  send_htmlmail
from members.models import Settings, Membership, Invoice, MailCampaign, ExcelBook, TextBlock


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


#
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
