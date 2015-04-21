from datetime import datetime
from operator import attrgetter
from django import forms
from django.shortcuts import render, render_to_response
from django.http import HttpRequest, HttpResponseRedirect, HttpResponse
from django.template import RequestContext
from django.views.generic import View, ListView, DetailView, CreateView, UpdateView, TemplateView
from django.views.generic.edit import FormView
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.html import strip_tags
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

#from django.contrib.auth.views import login, logout
#from django.utils.decorators import method_decorator
from braces.views import LoginRequiredMixin

from .models import (Person, Address, Membership, Subscription, InvoiceItem, Invoice, Fees,
                     Payment, ItemType, TextBlock, ExcelBook)
from .forms import (PersonForm, PersonLinkForm, JuniorForm, FilterMemberForm, AddressForm, SubscriptionForm,  XlsInputForm, XlsMoreForm,
                    SelectSheetsForm, InvoiceItemForm, PaymentForm, TextBlockForm, InvoiceSelectForm)
from .excel import *
import ftpService
import xlrd

#class LoginRequiredMixin(object):

#    @method_decorator(login_required)
#    def dispatch(self, *args, **kwargs):
#        return super(LoginRequiredMixin, self).dispatch(*args, **kwargs)

class PersonList(LoginRequiredMixin, ListView):
    model = Person
    template_name = 'members/person_table.html'

    def get_queryset(self):
        qset =  Person.objects.select_related().all()
        return qset

    def get_context_data(self, **kwargs):
        context = super(PersonList, self).get_context_data(**kwargs)
        add_membership_context(context)
        return context

class FilteredPersonList(LoginRequiredMixin, ListView):
    model = Person
    template_name = 'members/person_table.html'

    def get_queryset(self):
        tag_ids = self.kwargs['tags'].split('+')
        tag_list = []
        for id in tag_ids:
            tag_list.append(int(id))
        qset =  Person.objects.filter(
            Q(membership_id__in = tag_list)
        )
        return qset 

    def get_context_data(self, **kwargs):
        context = super(FilteredPersonList, self).get_context_data(**kwargs)
        fields = self.request.path_info.split('/')      
        taglist = fields[2].split('+')
        if len(taglist) > 0:
            context['tags'] = 'Filtered by: '
            for tagid in taglist:
                context['tags'] += Membership.objects.get(pk=tagid).description + ", "
            context['tags'] = context['tags'][:-2]
        else:
            context['tags']=''
        add_membership_context(context)
        return context

class FilterMemberView(LoginRequiredMixin, FormView):
    form_class = FilterMemberForm
    template_name = 'members/filter_member.html'

    def form_valid(self, form):
        tag=''
        for k in form.cleaned_data.keys():
            if form.cleaned_data[k]:
                tag += k + '+'
        return HttpResponseRedirect('/list/' + tag[:-1])

class PersonActionMixin(object):
    """
    Overrides form_valid to display a message
    """
    @property
    def success_msg(self):
        return NotImpemented

    def form_valid(self, form):
        messages.info(self.request, self.success_msg)
        return super(PersonActionMixin, self).form_valid(form)

class PersonCreateView(LoginRequiredMixin, PersonActionMixin, CreateView):
    model = Person
    template_name = 'members/generic_crispy_form.html'
    success_msg = "Person created"
    form_class = PersonForm

    #def get_context_data(self, **kwargs):
    #    context = super(PersonCreateView, self).get_context_data(**kwargs)
    #    context['action'] = reverse('person-create')
    #    return context

    def get_success_url(self):
        return reverse('person-list')

class PersonUpdateView(LoginRequiredMixin, PersonActionMixin, UpdateView):
    model = Person
    template_name = 'members/generic_crispy_form.html'
    success_msg = "Person updated"
    form_class = PersonForm

    def get_success_url(self):
        return reverse('person-list')
    
    #def get_context_data(self, **kwargs):

    #    context = super(PersonUpdateView, self).get_context_data(**kwargs)
    #    context['action'] = reverse('person-edit',
    #                                kwargs={'pk': self.get_object().id})
    #    return context


class PersonLinkView(LoginRequiredMixin, FormView):
    form_class = PersonLinkForm
    template_name = 'members/generic_crispy_form.html'

    def get_context_data(self, **kwargs):
        context = super(PersonLinkView, self).get_context_data(**kwargs)
        context['title'] = 'Link ' + Person.objects.get(pk = self.kwargs['pk']).fullname()
        return context

    def form_valid(self, form):
        child = Person.objects.get(pk = self.kwargs['pk'])
        if 'link' in form.data:
            child.link(form.person)          
            return redirect(form.person)
        else:
            return redirect(child)
            
class PersonUnlinkView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        person = Person.objects.get(pk = self.kwargs['pk'])
        person.link(None)
        return redirect(person)

class JuniorCreateView(LoginRequiredMixin, PersonActionMixin, CreateView):
    model = Person
    template_name = 'members/junior_form.html'
    success_msg = "Junior created"
    form_class = JuniorForm
    form = JuniorForm()

    def get_context_data(self, **kwargs):
        context = super(JuniorCreateView, self).get_context_data(**kwargs)
        context['action'] = reverse('junior-create')
        return context
    
    def get_success_url(self):
        return reverse('person-list')

class PersonDetailView(LoginRequiredMixin, DetailView):
    model = Person
    template_name = 'members/person_detail.html'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(PersonDetailView, self).get_context_data(**kwargs)
        add_membership_context(context)
        return set_person_context(context, self.get_object())

def add_membership_context(context):
    ''' Add membership dictionary to context '''
    mem_dict = {}
    for mem in Membership.objects.all():
        mem_dict[mem.id] = mem.description 
    context['mem_dict'] = mem_dict

def set_person_context(context, pers):
    entries = []
    invoices = pers.invoice_set.all()
    for i in invoices:
        entries.append(i)
    cnotes = pers.creditnote_set.all()
    for c in cnotes:
        entries.append(c)
    payments = pers.payment_set.all()
    for p in payments:
        entries.append(p)
    entries = sorted(entries, key=attrgetter('creation_date'))
    statement= []
    balance = 0
    for entry in entries:
        classname = entry.__class__.__name__
        if classname == "Invoice":
            balance += entry.total          
        elif classname == "Payment":
            balance -= entry.amount
        elif classname == "CreditNote":
            balance -= entry.amount
        statement.append((entry, balance))

    context['person'] = pers
    context['address'] = pers.address
    context['subs'] = pers.subscription_set.all().order_by('sub_year')
    context['statement'] = statement
    context['invoices'] = pers.invoice_set.all().order_by('update_date')
    own_items = pers.invoiceitem_set.filter(invoice=None).order_by('update_date')
    family_items = InvoiceItem.objects.filter(
        invoice=None,
        person__linked=pers).order_by('update_date')
    context['items'] = own_items | family_items
    context['children'] = pers.person_set.all()
    context['state_list'] = Invoice.STATES
    context['types'] = Payment.TYPES
    context['payment_states'] = Payment.TYPES
    context['payments'] = pers.payment_set.all().order_by('update_date')
    return context


class PersonExportView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        return export_members()

# ============== Address

class AddressUpdateView(LoginRequiredMixin, UpdateView):
    model = Address
    form_class = AddressForm
    template_name = 'members/address_form.html'

    def get_object(self):
        self.person = Person.objects.get(pk=self.kwargs['person_id'])
        return self.person.address

    def get_context_data(self, **kwargs):
        context = super(AddressUpdateView, self).get_context_data(**kwargs)
        parent = self.person
        if self.person.linked:
            parent = self.person.linked
        context['person'] = parent
        context['children'] = parent.person_set.all()
        return context

    def get_success_url(self):
        return reverse('person-detail', kwargs={'pk':self.kwargs['person_id']})

# ============== Subscriptions

class SubCreateView(LoginRequiredMixin, CreateView):
    model = Subscription
    form_class = SubscriptionForm
    form = SubscriptionForm()
    template_name = 'members/subscription_form.html'

    def get_success_url(self):
        sub = self.object
        sub.activate()
        sub.generate_invoice_items(month=5)
        return reverse('person-detail', kwargs={'pk':self.kwargs['person_id']})
    
    def get_context_data(self, **kwargs):
        context = super(SubCreateView, self).get_context_data(**kwargs)
        context['person'] = Person.objects.get(pk = self.kwargs['person_id'])
        return context

    def form_valid(self, form):
        form.instance.person_member = Person.objects.get(pk = self.kwargs['person_id'])
        form.instance.invoiced_month = 0
        result = super(SubCreateView, self).form_valid(form)
        return result

class SubUpdateView(LoginRequiredMixin, UpdateView):
    model = Subscription
    form_class = SubscriptionForm
    template_name = 'members/subscription_form.html'

    def get_success_url(self):
        sub = self.get_object()
        sub.activate()
        sub.generate_invoice_items(month=5)
        return reverse('person-detail', kwargs={'pk':sub.person_member_id})                    
    
    def get_context_data(self, **kwargs):
        context = super(SubUpdateView, self).get_context_data(**kwargs)
        sub = self.get_object()
        context['person'] = sub.person_member
        context['items'] = sub.invoiceitem_set.all().order_by('item_type')
        return context

    def form_valid(self, form):
        if 'submit' in form.data:
            return super(SubUpdateView, self).form_valid(form)
        if 'delete_items' in form.data:
            sub = self.get_object()
            sub.delete_invoice_items()
            return redirect(sub)

class SubDetailView(LoginRequiredMixin, DetailView):
    model = Subscription
    template_name = 'members/subscription_detail.html'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(SubDetailView, self).get_context_data(**kwargs)
        sub = self.get_object()
        context['items'] = sub.invoiceitem_set.all().order_by('item_type')
        for item in context['items']:
            if item.invoice and item.invoice.state == Invoice.UNPAID:
                context['cancel_invoice'] = True
                break
        return context

class SubRenewView(LoginRequiredMixin, View):
    
    def get(self, request, *args, **kwargs):
        sub = Subscription.objects.get(pk = self.kwargs['pk'])
        sub.renew(sub.sub_year+1, Subscription.START_MONTH)
        return redirect(sub.person_member)

class SubInvoiceCancel(LoginRequiredMixin, View):
    ''' Deletes unpaid items and invoices associated with a sub '''
    
    def get(self, request, *args, **kwargs):
        sub = get_object_or_404(Subscription, pk = self.kwargs['pk'])
        for item in sub.invoiceitem_set.all():
            if item.invoice and item.invoice.state == Invoice.UNPAID:
                item.invoice.cancel()
            item.delete()
        return redirect(sub)
    
# ================ Invoice items

class InvoiceItemListView(LoginRequiredMixin, ListView):
    model = InvoiceItem
    template_name = 'members/invoiceitem_list.html'

    def get_queryset(self):
        return InvoiceItem.objects.filter(invoice_record_id = self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        context = super(InvoiceItemListView, self).get_context_data(**kwargs)
        context['state_list'] = Invoice.STATES
        return context

class InvoiceItemCreateView(LoginRequiredMixin, CreateView):
    model = InvoiceItem
    form_class = InvoiceItemForm
    form = InvoiceItemForm()
    template_name = 'members/invoiceitem_form.html'

    def get_success_url(self):
        return reverse('person-detail',
                       kwargs={'pk':self.kwargs['person_id']})

    def get_context_data(self, **kwargs):
        context = super(InvoiceItemCreateView, self).get_context_data(**kwargs)
        context['person'] = Person.objects.get(pk = self.kwargs['person_id'])
        return context

    def form_valid(self, form):
        form.instance.person = Person.objects.get(pk = self.kwargs['person_id'])
        return super(InvoiceItemCreateView, self).form_valid(form)

class InvoiceItemUpdateView(LoginRequiredMixin, UpdateView):
    model = InvoiceItem
    form_class = InvoiceItemForm
    template_name = 'members/invoiceitem_form.html'

    def get_success_url(self):
        item = self.get_object()
        return reverse('person-detail', kwargs={'pk':item.person.id})

    def get_context_data(self, **kwargs):
        context = super(InvoiceItemUpdateView, self).get_context_data(**kwargs)
        item = self.get_object()
        context['person'] = item.person
        return context

    def form_valid(self, form):
        if 'submit' in form.data:
            return super(InvoiceItemUpdateView, self).form_valid(form)
        if 'delete' in form.data:
            item = self.get_object()
            person_id = item.person.id
            item.delete()
            return HttpResponseRedirect(reverse('person-detail', kwargs={'pk':person_id}))

class InvoiceItemDetailView(LoginRequiredMixin, DetailView):
    model = InvoiceItem
    template_name = 'members/invoiceitem_detail.html'

# ================= INVOICES

class InvoiceCancelView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        invoice = Invoice.objects.get(pk = self.kwargs['pk'])
        invoice.cancel()
        return redirect(invoice.person)

class InvoiceDeleteView(LoginRequiredMixin, View):
    
    def get(self, request, *args, **kwargs):
        invoice= Invoice.objects.get(pk = self.kwargs['pk'])
        invoice.cancel()
        invoice.delete()
        return redirect(invoice.person)

class InvoiceListView(LoginRequiredMixin, ListView):
    model = Invoice
    paginate_by = 15
    template_name = 'members/invoice_list.html'
    context_object_name = 'invoices'

    def get_context_data(self, **kwargs):
        context = super(InvoiceListView, self).get_context_data(**kwargs)
        context['state_list'] = Invoice.STATES
        dict = self.queryset.aggregate(Sum('total'))
        context['count'] = self.queryset.count()
        context['total'] = dict['total__sum']
        context['option']= self.kwargs['option']
        return context

    def get_queryset(self):
        option = self.kwargs['option']
        if option == 'Paid':
            self.queryset = Invoice.objects.filter(state=Invoice.PAID_IN_FULL)
        elif option == 'Unpaid':
            self.queryset = Invoice.objects.filter(state=Invoice.UNPAID) 
        elif option == 'Cancelled':
            self.queryset = Invoice.objects.filter(state=Invoice.CANCELLED)   
        else:
            self.queryset =  Invoice.objects.all()
        return self.queryset

class InvoiceDetailView(LoginRequiredMixin, DetailView):
    model = Invoice
    template_name = 'members/invoice_detail.html'

    def get_context_data(self, **kwargs):
        context = super(InvoiceDetailView, self).get_context_data(**kwargs)
        inv = self.get_object()
        context['person'] = inv.person
        context['items'] = inv.invoiceitem_set.all().order_by('creation_date')
        context['state_list'] = Invoice.STATES
        context['types'] = Payment.TYPES
        context['payment_states'] = Payment.STATES
        context['full_payment_button'] = inv.state == Invoice.UNPAID
        context['can_delete'] = inv.email_count == 0 and inv.postal_count == 0 and inv.state == Invoice.UNPAID
        c_note = None
        if inv.creditnote_set.count() > 0:
            c_note = inv.creditnote_set.all()[0]
        context['credit_note'] = c_note
        return context

class InvoiceGenerateView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        person = Person.objects.get(pk = self.kwargs['pk'])
        invoice = person.generate_invoice()
        if invoice:
            # calls get_absolute_url to display the invoice
            return redirect(invoice)
        else:
            return redirect(person)
        return

class InvoiceMailView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        invoice= Invoice.objects.get(pk = self.kwargs['pk'])
        option = self.kwargs['option']
        result = do_mail(invoice, option)
        if option == 'view':
            return result
        return redirect(invoice)

class InvoiceMailBatchView(LoginRequiredMixin, View):
    ''' Send email for all invoices that are unpaid and have not been emailed '''

    def get(self, request, *args, **kwargs):
        invs = Invoice.objects.filter(state=Invoice.UNPAID, email_count=0)
        option = 'send'
        count = 0
        for inv in invs:
            count += do_mail(inv, option)
        return HttpResponse("sent {} mails for {} invoices".format(count, invs.count()))

def do_mail(invoice, option):
        count = 0
        family = invoice.person.person_set.all()
        context={
            'invoice': invoice,
            'person': invoice.person,
            'address': invoice.person.address,
            'reference': str(invoice.person.id) + '/' + str(invoice.id),
            'items': invoice.invoiceitem_set.all().order_by('item_type'),
            'text_intro': TextBlock.objects.filter(name='invoice_intro')[0].text,
            'text_notes': TextBlock.objects.filter(name='invoice_notes')[0].text,
            'text_closing': TextBlock.objects.filter(name='invoice_closing')[0].text,
            }
        addressee = invoice.person.first_name + ' ' + invoice.person.last_name
        if invoice.person.first_name == 'Unknown':
            addressee = 'Parent or guardian of '
            for person in family:
                addressee += person.first_name +' ' + person.last_name + ', '
            addressee = addressee[:-2]
            context['unknown'] = "Please supply your details!"  
        context['addressee'] = addressee
        if family.count() > 0:
            context['junior_notes'] = TextBlock.objects.filter(name='junior_notes')[0].text
            context['family'] = family
        subject = "Coombe Wood LTC account"
        if option == 'view':
            return render_to_response("members/invoice_email.html", context)
        
        html_body = render_to_string("members/invoice_email.html", context)
        target = invoice.person.email if option == 'send' else "is@ktconsultants.co.uk"
        if target <> '':
            text_plain = strip_tags(html_body)
            msg = EmailMultiAlternatives(subject=subject,
                                            from_email="subs@coombewoodltc.co.uk",
                                            to=[target],
                                            body=text_plain)
            msg.attach_alternative(html_body, "text/html")
            msg.send()
            if option == 'send':
                invoice.email_count += 1
                count += 1
            invoice.save()
        return count

class InvoiceSelectView(LoginRequiredMixin, FormView):
    form_class = InvoiceSelectForm
    template_name = 'members/invoice_select.html'

    def form_valid(self, form):
        choice = int(form.cleaned_data['choice'])
        ref = form.cleaned_data['ref']
        if choice == 1:
            return HttpResponseRedirect(reverse('invoice-detail', kwargs={'pk':ref}))
        else:
            return HttpResponseRedirect(reverse('person-detail', kwargs={'pk':ref}))

# ================== PAYMENTS

class PaymentCreateView(LoginRequiredMixin, CreateView):
    model = Payment
    form_class = PaymentForm
    form = PaymentForm()
    template_name = 'members/payment_form.html'

    def get_success_url(self):

        return reverse('invoice-detail',
                       kwargs={'pk':self.kwargs['invoice_id']})

    def get_context_data(self, **kwargs):
        context = super(PaymentCreateView, self).get_context_data(**kwargs)
        inv = Invoice.objects.get(pk = self.kwargs['invoice_id'])
        context['invoice'] = inv
        context['person'] = inv.person
        context['items'] = inv.invoiceitem_set.all().order_by('creation_date')
        context['state_list'] = Invoice.STATES
        context['types'] = Payment.TYPES
        context['payment_states'] = Payment.STATES
        return context

    def form_valid(self, form):
        inv = Invoice.objects.get(pk = self.kwargs['invoice_id'])
        form.instance.person = inv.person
        # save new object before handling many to many relationship
        payment = form.save()
        payment.pay_invoice_full(inv)
        return super(PaymentCreateView, self).form_valid(form)

class PaymentDetailView(LoginRequiredMixin, DetailView):
    model = Payment
    template_name = 'members/payment_detail.html'

    def get_context_data(self, **kwargs):
        context = super(PaymentDetailView, self).get_context_data(**kwargs)
        context['payment_types'] = Payment.TYPES
        context['payment_states'] = Payment.STATES
        return context


class TextBlockCreateView(LoginRequiredMixin, CreateView):
    model = TextBlock
    form_class = TextBlockForm
    template_name = 'members/textblock_form.html'
    template_object_name = 'textblock'

    def get_success_url(self):
        return reverse('text-list')
 
class TextBlockUpdateView(LoginRequiredMixin, UpdateView):
    model = TextBlock
    form_class = TextBlockForm
    template_name = 'members/textblock_form.html'

    def get_success_url(self):
        return reverse('text-list') 
    
class TextBlockListView(LoginRequiredMixin, ListView):
    model = TextBlock               
    template_name = 'members/textblock_list.html'


class ImportExcelMore(LoginRequiredMixin, FormView):
    form_class = XlsMoreForm
    template_name = 'members/import_more.html'

    def get_context_data(self, **kwargs):
        context = super(ImportExcelMore, self).get_context_data(**kwargs)
        context['title'] = 'Import Members'
        context['pass'] = self.kwargs['pass']
        context['start'] = self.kwargs['start']
        context['size'] = self.kwargs['size']
        return context
 
    def form_valid(self,form):
        pass_no = int(self.kwargs['pass'])
        my_book = ExcelBook.objects.all()[0]
        start = int(self.kwargs['start'])
        size = int(self.kwargs['size'])   
        if pass_no == 1:
            ''' Pass 1
                Create the members '''
    
            with open_excel_workbook(my_book.file) as book:
                next = import_members_1(book, start, size)
                if next < 0:
                    return HttpResponse('Pass 1 Import error')
                elif next == 0:
                    return HttpResponseRedirect(reverse('import_more',
                                                    args=[2, 0, size]))
                else:
                    return HttpResponseRedirect(reverse('import_more',
                                                    args=[1, next, size]))
        elif pass_no == 2:
            with open_excel_workbook(my_book.file) as book:
                count = import_members_2(book)
                return HttpResponseRedirect(reverse('import_more',
                                args=[3, count, size]))
        
        elif pass_no == 3:
            with open_excel_workbook(my_book.file) as book:
                result = import_members_3(book, size)
                count = result[0]
                if result[1]:
                    context = {'title': 'Import result'}
                    context['message'] = '{} items were imported'.format(result[0])
                    context['errors'] = result[1]
                    return render(self.request, 'members/generic_result.html', context)
                if count == 0:
                    return HttpResponseRedirect(reverse('person-list'))
                else:                                        
                    return HttpResponseRedirect(reverse('import_more',
                                                        args=[3, count, size]))

class ImportExcelView(LoginRequiredMixin, FormView):
    ''' Capture the excel name and batch size '''
    form_class = XlsInputForm
    template_name = 'members/import_excel.html'

    def form_valid(self,form):
        input_excel = form.cleaned_data['input_excel']
        sheet_type = int(form.cleaned_data['sheet_type'])
        batch_size = int(form.cleaned_data['batch_size'])
        
        # When we save the new one, any old file will be overwritten
        newbook = ExcelBook(file = input_excel)
        newbook.save()        
        
        if sheet_type == XlsInputForm.MEMBERS:
            # delete all Excelbooks in the data base
            Person.objects.all().delete()
            Address.objects.all().delete()
            return HttpResponseRedirect(reverse('import_more',
                                                args=[1, 1, batch_size]))
        elif sheet_type == XlsInputForm.BASE:
            Fees.objects.all().delete()
            ItemType.objects.all().delete()
            Membership.objects.all().delete()
            my_book = ExcelBook.objects.all()[0]
            with open_excel_workbook(my_book.file) as book:
                import_base_tables(book)
            return HttpResponseRedirect(reverse('import'))
        
        elif sheet_type == XlsInputForm.BACKUP:
            my_book = ExcelBook.objects.all()[0]
            with open_excel_workbook(my_book.file) as book:
                import_all(book)
            return HttpResponseRedirect(reverse('import'))                                
        else:
            return HttpResponseRedirect(reverse('select-sheets'))

class SelectSheets(LoginRequiredMixin, FormView):
    ''' Select itemtype sheets to import ''' 
    form_class = SelectSheetsForm
    template_name = 'members/generic_crispy_form.html'
    
    def get_context_data(self, **kwargs):
        context = super(SelectSheets, self).get_context_data(**kwargs)
        context['title'] = 'Import invoice items'
        context['message'] = 'Select sheets to import'
        return context 
     
    def form_valid(self,form):
        my_book = ExcelBook.objects.all()[0]
        with open_excel_workbook(my_book.file) as book:
            total = 0
            sheet_count = 0
            context = {'title': 'Import result'}
            for k in form.cleaned_data.keys():
                if form.cleaned_data[k]:
                    sheet = book.sheet_by_name(k)
                    sheet_count += 1
                    result = import_items(sheet)
                    total = total + result[0]
                    if result[1]:
                        result[1].append('Sheet ' + k)
                        context['errors'] = result[1]
                        break          
            context['message'] = '{} items were imported from {} sheets'.format(total, sheet_count)
            return render(self.request, 'members/generic_result.html', context)
                       
class SubRenewBatch(LoginRequiredMixin, FormView):
    form_class = XlsMoreForm
    template_name = 'members/import_more.html'

    def get_context_data(self, **kwargs):
        context = super(SubRenewBatch, self).get_context_data(**kwargs)
        context['title'] = 'Generate subs'
        context['remaining'] = Subscription.renew_batch(2015, 5, 0)
        return context

    def form_valid(self,form):
        remaining = Subscription.renew_batch(2015, 5, 100)
        return HttpResponseRedirect(reverse('sub-renew-batch'))

class InvoiceBatchView(LoginRequiredMixin, FormView):
    form_class = XlsMoreForm
    template_name = 'members/import_more.html'

    def get_context_data(self, **kwargs):
        context = super(InvoiceBatchView, self).get_context_data(**kwargs)
        context['title'] = 'Generate invoices'
        context['remaining'] = InvoiceItem.invoice_batch(size=0)
        return context

    def form_valid(self,form):
        remaining = InvoiceItem.invoice_batch(size=100)
        return HttpResponseRedirect(reverse('invoice-batch'))

def export(request):
    return export_all()

def import_backup(request):
    return import_all()

def testinv(request):
    p=Person.generate_invoices(100)
    return HttpResponse("{0} Subs created".format(count))

def test(request):
    from .mail import test_mail_template
    from django.http import HttpResponse
    test_mail_template()
    return HttpResponse("Test mail sent")

def bar(request):
    """
    Downloads the transaction file generated by the bar system
    """
    result = ftpService.ftpGet()
    return render(
        request,
        'members/contact.html',
        context_instance = RequestContext(request,
        {
            'title':'Contact',
            'message':result,
            'year':datetime.now().year,
        })
     )        
              
def home(request):
    """Renders the home page."""
    assert isinstance(request, HttpRequest)
    db_name = settings.DATABASES['default']['NAME']
    return render(
        request,
        'members/index.html',
        context_instance = RequestContext(request,
        {
            'title':'Home Page',
            'year':datetime.now().year,
            'db_name':db_name,
        })
    )

def contact(request):
    """Renders the contact page."""
    assert isinstance(request, HttpRequest)
    return render(
        request,
        'members/contact.html',
        context_instance = RequestContext(request,
        {
            'title':'Contact',
            'message':'Your contact page.',
            'year':datetime.now().year,
        })
    )

def about(request):
    """Renders the about page."""
    assert isinstance(request, HttpRequest)
    return render(
        request,
        'members/about.html',
        context_instance = RequestContext(request,
        {
            'title':'About',
            'message':'Your application description page.',
            'year':datetime.now().year,
        })
    )

def fixup(request):

        cursor = connection.cursor()
        cursor.execute("SELECT setval('members_person_id_seq', (SELECT MAX(id) FROM members_person)+1)")
        cursor.execute("SELECT setval('members_fees_id_seq', (SELECT MAX(id) FROM members_fees)+1)")
        cursor.execute("SELECT setval('members_membership_id_seq', (SELECT MAX(id) FROM members_membership)+1)")

