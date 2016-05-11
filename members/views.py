from datetime import *
from operator import attrgetter
from django import forms
from django.shortcuts import render, render_to_response
from django.http import HttpRequest, HttpResponseRedirect, HttpResponse, JsonResponse
from django.template import RequestContext
from django.views.generic import View, ListView, DetailView, CreateView, UpdateView, TemplateView
from django.views.generic.edit import FormView, FormMixin
from django.core import serializers
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, QuerySet
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.template.loader import render_to_string
from django.conf import settings
from django.core.mail import send_mail
from braces.views import LoginRequiredMixin
from gc_app.views import gc_create_bill_url
from .models import (Person, Address, Membership, Subscription, InvoiceItem, Invoice, Fees,
                     Payment, CreditNote, ItemType, TextBlock, ExcelBook, Group)
from .services import *
from .forms import *
from .mail import *
from .excel import *
import ftpService
import xlrd
from report_builder.models import Report


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
        if self.kwargs['tags'] == 'families':
            people = Person.objects.filter(linked__isnull = True)
            qset=[]
            for p in people:
                if p.person_set.count()>0:
                    qset.append(p)
        else:
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
        tags = self.kwargs['tags']
             
        taglist = fields[2].split('+')
        if len(taglist) > 0:
            context['tags'] = 'Filtered by: '
            for tagid in taglist:
                if tagid == 'families':
                    context['tags'] += 'Families, '
                else:
                    context['tags'] += Membership.objects.get(pk=tagid).description + ', '
            context['tags'] = context['tags'][:-2]
        else:
            context['tags']=''
        add_membership_context(context)
        return context


class FilteredPersonListAjax(LoginRequiredMixin, FormMixin, ListView):
    model = Person
    form_class = FilterMemberAjaxForm
    template_name = 'members/person_table_ajax.html'

    def get(self, request, *args, **kwargs):
        if kwargs:
            self.form = FilterMemberAjaxForm(initial = {'categories': kwargs['tags']})
        else:
            self.form = FilterMemberAjaxForm()
        #self.form = self.get_form(self.form_class)
        self.object_list = []
        context = self.get_context_data()
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        ''' POST handles submit and ajax request '''
        self.form = self.get_form(self.form_class)
        if self.form.is_valid():
            cat = int(self.form.cleaned_data['categories'])
            if cat == 0:
                qset = Person.objects.select_related().all()
            elif cat < 100:
                qset = Person.objects.select_related().filter(membership_id=cat)
            elif cat == Membership.FAMILIES:
                non_kids = Person.objects.select_related().filter(linked__isnull = True)
                plist= []
                for p in non_kids:
                    if p.person_set.count() > 0:
                        cat = p.membership.description if p.membership else ""
                           
                        qlist =[p.first_name, p.last_name, cat, p.email, p.id]
                        plist.append(qlist)
                dict = {"data": plist}
                return JsonResponse(dict)
            
            else:
                taglist = []    
                if cat == Membership.PLAYING:
                    taglist = Membership.PLAYING_LIST
                elif cat == Membership.JUNIORS:
                    taglist = Membership.JUNIORS_LIST
                elif cat == Membership.ALL_NONPLAYING:
                    taglist = Membership.ALL_NONPLAYING_LIST
                qset =  Person.objects.filter(
                    Q(membership_id__in = taglist)
                    )
        else:
            qset = Person.objects.select_related().all()

        plist = list(qset.values_list(
                'first_name',
                'last_name',
                'membership__description',
                'email',
                'id'
                ))
        dict = {"data": plist}
        return JsonResponse(dict)

    #def get_queryset(self):
    #    if self.kwargs:
    #        if self.kwargs['tags'] == 'families':
    #            people = Person.objects.select_related().filter(linked__isnull = True)
    #            qset=[]
    #            for p in people:
    #                if p.person_set.count()>0:
    #                    qset.append(p)
    #        else:
    #            tag_ids = self.kwargs['tags'].split('+')
    #            tag_list = []
    #            for id in tag_ids:
    #                tag_list.append(int(id))
    #            qset =  Person.objects.select_related().filter(
    #                Q(membership_id__in = tag_list)
    #            )
    #    else:
    #        qset =  Person.objects.select_related().all()
    #    return qset 

    def get_context_data(self, **kwargs):
        context = super(FilteredPersonListAjax, self).get_context_data(**kwargs)
        fields = self.request.path_info.split('/') 
        context['tags']=''
        #if self.kwargs:            
        #    taglist = fields[2].split('+')
        #    if len(taglist) > 0:
        #        context['tags'] = 'Filtered by: '
        #        for tagid in taglist:
        #            if tagid == 'families':
        #                context['tags'] += 'Families, '
        #            else:
        #                context['tags'] += Membership.objects.get(pk=tagid).description + ', '
        #        context['tags'] = context['tags'][:-2]
               
        add_membership_context(context)
        context['form'] = self.form
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
    
    #def form_valid(self, form):
    #    tag=''
    #    for k in form.cleaned_data['categories']:
    #        key = int(k)
    #        taglist = []
    #        if key >= 100:
    #            if key == Membership.PLAYING:
    #                taglist = Membership.PLAYING_LIST
    #            elif key == Membership.JUNIORS:
    #                taglist = Membership.JUNIORS_LIST
    #            elif key == Membership.FAMILIES:
    #                taglist = ['families']
    #            for t in taglist:
    #                tag += str(t) + '+'
    #        else:
    #            tag += k + '+'
    #    return HttpResponseRedirect('/list/' + tag[:-1])

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

    def get_form_kwargs(self):
        kwargs = super(PersonCreateView,self).get_form_kwargs()
        kwargs.update({'link': self.kwargs['link']})
        return kwargs

    def form_invalid(self, form):
        if 'cancel' in form.data:
            return(redirect('home'))
        return super(PersonCreateView, self).form_invalid(form)

    def form_valid(self, form): 
        if 'cancel' in form.data:
            return(redirect('home'))
        self.form = form
        return super(PersonCreateView, self).form_valid(form)
            
    def get_success_url(self):
        if 'submit_sub' in self.form.data:
            return reverse('sub-create', kwargs={'person_id': self.form.person.id})
        return reverse('person-detail', kwargs={'pk': self.form.person.id})  

class PersonUpdateView(LoginRequiredMixin, PersonActionMixin, UpdateView):
    model = Person
    template_name = 'members/generic_crispy_form.html'
    success_msg = "Person updated"
    form_class = PersonForm

    def get_success_url(self):
        return reverse('person-detail', kwargs={'pk':self.kwargs['pk']})
    

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
            person_link_to_parent(child, form.person)          
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
    success_msg = "Junior and parent created"
    form_class = JuniorForm

    def form_invalid(self, form):
        if 'cancel' in form.data:
            return HttpResponseRedirect(reverse('home'))
        return super(JuniorCreateView, self).form_invalid(form)

    def form_valid(self, form):
        self.form = form
        if 'cancel' in form.data:
            return HttpResponseRedirect(reverse('home'))   
        return super(JuniorCreateView, self).form_valid(form) 
            
    def get_success_url(self):
        return reverse('sub-create', kwargs={'person_id': self.form.junior.id}) 

class PersonDetailView(LoginRequiredMixin, DetailView):
    model = Person
    template_name = 'members/person_detail.html'

    def get_context_data(self, **kwargs):
        context = super(PersonDetailView, self).get_context_data(**kwargs)
        add_membership_context(context)
        return set_person_context(context, self.get_object())

    def post(self, request, *args, **kwargs):
        person = self.get_object()
        name = person.fullname()
        if 'delete' in request.POST:
            message = person_delete(person)
            if message == "":
                messages.success(self.request,"{0} deleted".format(name))
                return redirect(reverse('person-list'))
            messages.error(self.request,"{0} not deleted because {1}".format(name, message))
            return redirect(reverse('person-detail', kwargs={'pk':person.id}))
        elif 'remove' in request.POST:
            slug=request.POST['remove']
            group = Group.objects.filter(slug=slug)[0]
            person.groups.remove(group)
            return redirect(reverse('person-detail', kwargs={'pk':person.id}))

def add_membership_context(context):
    ''' Add membership dictionary to context '''
    mem_dict = {}
    for mem in Membership.objects.all():
        mem_dict[mem.id] = mem.description 
    context['mem_dict'] = mem_dict

def set_person_context(context, pers):
    year = Settings.current().membership_year
    entries = person_get_book_entries(pers, year)
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
    context['sub'] = pers.active_sub()
    context['statement'] = statement
    context['invoices'] = pers.invoice_set.all().order_by('update_date')
    own_items = pers.invoiceitem_set.filter(invoice=None).order_by('update_date')
    family_items = InvoiceItem.objects.filter(
        invoice=None,
        person__linked=pers).order_by('update_date')
    context['items'] = own_items | family_items
    parent = None
    if pers.linked:
        parent = pers.linked
    else:
        if pers.person_set.count() > 0:
            parent = pers
    if parent:
        context['parent'] = parent   
        context['children'] = parent.person_set.all()
    context['state_list'] = Invoice.STATES
    context['types'] = Payment.TYPES
    context['payment_states'] = Payment.TYPES
    context['payments'] = pers.payment_set.all().order_by('update_date')
    return context


class PersonExportView(LoginRequiredMixin, View):

    def get(self, request, option = "all"):
        return export_members(option)

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

    def form_invalid(self, form):
        if 'cancel' in form.data:
            return redirect(self.get_success_url())
        return super(AddressUpdateView, self).form_invalid(form)

    def form_valid(self, form):
        if 'cancel' in form.data:
            return redirect(self.get_success_url())
        address = form.save()
        self.person.address = address
        self.person.save()
        return super(AddressUpdateView, self).form_valid(form)
   
    def get_success_url(self):
        return reverse('person-detail', kwargs={'pk':self.kwargs['person_id']})

# ============== Groups

class GroupCreateView(LoginRequiredMixin, CreateView):
    model = Group
    form_class = GroupForm
    template_name = 'members/generic_crispy_form.html'

    def get_success_url(self):
        messages.success(self.request, 'Group {} created'.format(form.cleaned_data['description']))
        return reverse('home')

class GroupListView(LoginRequiredMixin, ListView):
    ''' List all groups'''
    model = Group
    template_name = 'members/group_list.html'
    context_object_name = 'groups'

class GroupDetailView(LoginRequiredMixin, DetailView):
    model = Group
    template_name = 'members/group_detail.html'

 
    def get_context_data(self, **kwargs):
        context = super(GroupDetailView, self).get_context_data(**kwargs)
        context['group'] = self.get_object()
        context['object_list'] = context['group'].person_set.order_by('last_name')
        add_membership_context(context)
        return context
    
    def post(self, request, *args, **kwargs):
        group = self.get_object()
        if 'delete' in request.POST:
            group.delete()
        elif 'clear' in request.POST:
            group.person_set.clear()
        return redirect(reverse('group-list'))

class GroupAddPersonView(LoginRequiredMixin, FormView):
    form_class = GroupAddPersonForm
    template_name = 'members/generic_crispy_form.html'
    
    #def __init__(self, *args, **kwargs):
    #    self.person = Person.objects.get(pk = self.kwargs['person_id']).fullname()
    #    return super(GroupDetailView, self).__init__(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(GroupAddPersonView, self).get_context_data(**kwargs)
        #context['groups'] = Group.objects.all()
        self.person = Person.objects.get(pk = self.kwargs['person_id'])
        context['message'] = self.person.fullname()
        return super(GroupAddPersonView, self).get_context_data(**kwargs)

    def form_valid(self, form):
        return super(GroupAddPersonView, self).form_valid(form)

    def get_success_url(self):
        return reverse('group-list')

# ============== Subscriptions

class SubCreateView(LoginRequiredMixin, CreateView):
    model = Subscription
    form_class = SubscriptionForm
    template_name = 'members/subscription_form.html'

    def get_form_kwargs(self):
        ''' pass the person_id to the form '''
        kwargs = super(SubCreateView,self).get_form_kwargs()
        kwargs.update({'person_id': self.kwargs['person_id']})
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super(SubCreateView, self).get_context_data(**kwargs)
        context['person'] = Person.objects.get(pk = self.kwargs['person_id'])
        return context

    def form_valid(self, form):
        form.instance.person_member = Person.objects.get(pk = self.kwargs['person_id'])
        form.instance.invoiced_month = 0
        form.instance.membership = Membership.objects.get(pk = form.cleaned_data['membership_id'])
        return super(SubCreateView, self).form_valid(form)

    def get_success_url(self):
        sub = self.object
        subscription_activate(sub)
        subscription_create_invoiceitems(sub, sub.start_date.month)
        return reverse('person-detail', kwargs={'pk':self.kwargs['person_id']})

class SubUpdateView(LoginRequiredMixin, UpdateView):
    model = Subscription
    form_class = SubscriptionForm
    template_name = 'members/subscription_form.html'                 
    
    def get_form_kwargs(self):
        ''' pass the person_id to the form '''
        sub = self.get_object()
        kwargs = super(SubUpdateView,self).get_form_kwargs()
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
        return super(SubUpdateView, self).form_invalid(form)
    
    def form_valid(self, form):
        sub = self.get_object() 
        if 'cancel' in form.data:
            return redirect(sub.person_member)

        if 'submit' in form.data:
            form.instance.membership = Membership.objects.get(pk = form.cleaned_data['membership_id'])
            return super(SubUpdateView, self).form_valid(form)

        if 'delete' in form.data:  
            sub = self.get_object()  
            subscription_delete_invoiceitems(sub)
            return redirect(sub)

    def get_success_url(self):
        sub = self.get_object()
        subscription_activate(sub)
        subscription_create_invoiceitems(sub, sub.start_date.month)
        return reverse('person-detail', kwargs={'pk':sub.person_member_id}) 

class SubCorrectView(LoginRequiredMixin, UpdateView):
    ''' standard model view that skips validation '''
    model = Subscription
    form_class = SubCorrectForm

    def get_success_url(self):
        subscription_activate(self.get_object())
        return reverse('person-detail', kwargs={'pk':sub.person_member_id}) 

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

class SubListView(LoginRequiredMixin, ListView):
    ''' Subs history for 1 person '''
    model = Subscription
    template_name = 'members/subscription_list.html'
    context_object_name = 'subs'

    def get_queryset(self):
        self.person = get_object_or_404(Person, pk = self.kwargs['person_id'])
        return Subscription.objects.filter(person_member=self.person).order_by('start_date')

    def get_context_data(self, **kwargs):
        context = super(SubListView, self).get_context_data(**kwargs)
        context['person'] = self.person
        return context
       
class SubRenewView(LoginRequiredMixin, FormView):
     
    def get(self, request, *args, **kwargs):    
        sub.renew(sub.sub_year+1, Subscription.START_MONTH)
        return redirect(sub.person_member)

class SubRenewAllView(LoginRequiredMixin, FormView):
    form_class = SubRenewForm
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
            messages.success(self.request,'Subscriptions for {} generated'.format(year))
        return redirect(reverse('home'))
        
    def get_success_url(self):
        return reverse('home')

class SubRenewBatch(LoginRequiredMixin, FormView):
    form_class = XlsMoreForm
    template_name = 'members/import_more.html'

    def get_context_data(self, **kwargs):
        context = super(SubRenewBatch, self).get_context_data(**kwargs)
        context['title'] = 'Generate subs'
        context['remaining'] = subscription_renew_batch(2015, 5, 0)
        return context

    def form_valid(self,form):
        remaining = subscription_renew_batch(2015, 5, 100)
        return HttpResponseRedirect(reverse('sub-renew-batch'))

# ============ Year end

class YearEndView(LoginRequiredMixin, FormView):
    ''' Manage setting '''
    form_class = SettingsForm
    template_name = 'members/generic_crispy_form.html'

    def get_context_data(self, **kwargs):
        context = super(YearEndView, self).get_context_data(**kwargs)
        context['title'] = 'Settings'
        return context

    def get_initial(self):
        initial = super(YearEndView, self).get_initial()
        qset = Settings.objects.all()
        if qset:
            year = qset[0].membership_year
        else:
            year = 2015
        initial['membership_year'] = year
        return initial
   
    def form_valid(self, form):
        year = form.cleaned_data['membership_year']
        if 'cancel' in form.data:
            return redirect('home')

        elif 'submit' in form.data:
            qset = Settings.objects.all()
            if qset:
                record = qset[0]
            else:
                record = Settings()
            record.membership_year = year
            record.save()
            return redirect('home')

        elif 'consolidate' in form.data:
            counts  = consolidate(year)
            message = '{} people processed, {} unpaid  and {} credit notes carried forward'.format(
                counts[0], counts[1], counts[2])
            messages.success(self.request, message)
            return redirect('year-end')

        elif 'renew' in form.data:
            count = subscription_renew_batch(year, Subscription.START_MONTH)
            message = '{} subscriptions generated'.format(count)
            messages.success(self.request, message)
            return redirect('year-end')

        elif 'invoices' in form.data:
            counts = invoice_create_batch(exclude_slug='2015UnpaidImvoices')
            message = '{} invoices created from {} people'.format(counts[1], counts[0])
            messages.success(self.request, message)
            return redirect('year-end')     
        
        elif 'mail' in form.data:
            group = group_get_or_create('2015UnpaidInvoices')
            invs = self.get_unpaid_invoices()
            count = 0
            for inv in invs:
                if not group.person_set.filter(id=inv.person.id).exists():
                    count += 1
                    do_mail(self.request, inv, option='send')
            message = "Sent {} mails for {} invoices".format(count, invs.count())
            messages.success(self.request, message)
            return redirect('year-end')

        elif 'count' in form.data:
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

        return redirect('year-end')

    def get_unpaid_invoices(self):
        year = Settings.current().membership_year
        invs = Invoice.objects.filter(
            state=Invoice.UNPAID, membership_year=year, gocardless_bill_id ='', total__gt = 0)
        return invs

class SubInvoiceCancel(LoginRequiredMixin, View):
    ''' Deletes unpaid items and invoices associated with a sub '''
    
    def get(self, request, *args, **kwargs):
        sub = get_object_or_404(Subscription, pk = self.kwargs['pk'])
        for item in sub.invoiceitem_set.all():
            if item.invoice and item.invoice.state == Invoice.UNPAID:
                invoice_cancel(item.invoice)
            item.delete()
        return redirect(sub)

# ============ Fees

class FeesCreateView(LoginRequiredMixin, CreateView):
    model = Fees
    form_class = FeesForm
    template_name = 'members/fees_form.html'

    def get_success_url(self):
        return reverse('fees-list')   
   
class FeesUpdateView(LoginRequiredMixin, UpdateView):
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

class FeesListView(LoginRequiredMixin, ListView):
    model = Fees
    template_name = 'members/fees_list.html'

    def get_queryset(self):
        self.year = int(self.kwargs.get('year', 0))
        self.latest_year = Fees.objects.all().order_by('-sub_year')[0].sub_year
        if self.year == 0:
            self.year = self.latest_year       
        return Fees.objects.filter(sub_year=self.year).order_by('membership')

    def get_context_data(self, **kwargs):
        context = super(FeesListView, self).get_context_data(**kwargs)
        context['year'] = self.year
        context['latest'] = (self.latest_year == self.year)
        context['forward'] = self.year + 1
        context['back'] = self.year - 1
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
            messages.success(self.request,"Records for {} created".format(year + 1))
            return redirect('fees-list', year + 1)
        elif 'delete' in request.POST:
            for fee in Fees.objects.filter(sub_year=year):
                fee.delete()
            messages.success(self.request,"All records for {} deleted".format(year))
            return redirect('fees-list', year - 1)

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

class InvoiceListView(LoginRequiredMixin, FormMixin, ListView):
    form_class = InvoiceFilterForm
    model = Invoice
    template_name = 'members/invoice_list.html'
    
    def get(self, request, *args, **kwargs):
        ''' GET return HTML '''
        # From ProcessFormMixin
        self.form = self.get_form(self.form_class)
        # From BaseListView
        self.object_list = self.get_queryset()
        context = self.get_context_data()
        return self.render_to_response(context)
      
    def post(self, request, *args, **kwargs):
        ''' POST handles submit and ajax request '''
        self.form = self.get_form(self.form_class)
        if self.form.is_valid():
            self.object_list = self.get_queryset()
            
            if request.is_ajax():
                context = self.get_context_data()
                context['checkboxes'] = False
                html = render_to_string(self.template_name, context)
                dict = {"data": html, "search": request.POST['search']}
                return JsonResponse(dict, safe=False)

            if 'view' in self.form.data:
                for inv in self.object_list:
                    if inv.state == Invoice.UNPAID:
                        return(request, do_mail(inv, 'view'))
                return HttpResponse('No unpaid mails to view')

            if 'mail' in self.form.data:
                count = 0
                for inv in self.object_list:
                    if inv.state == Invoice.UNPAID and inv.total > 0:
                        count += do_mail(request, inv, 'send')
                return HttpResponse("Sent {} mails for {} invoices".format(count, self.object_list.count()))

            if 'export' in self.form.data:
                return export_invoices(self.object_list)
                  
        context = self.get_context_data()
        return self.render_to_response(context)
 
       

    def get_queryset(self):
        form = self.form
        start_date = date(2016,4,1)
        end_date = date.today()
        q_paid = Invoice.PAID_IN_FULL
        q_unpaid = Invoice.UNPAID
        q_cancelled = -1
        if getattr(form, 'cleaned_data', None):
            q_paid = -1
            q_unpaid = -1
            q_cancelled = -1
            if form.cleaned_data['paid']:
                q_paid = Invoice.PAID_IN_FULL
            if form.cleaned_data['unpaid']:
                q_unpaid = Invoice.UNPAID
            if form.cleaned_data['cancelled']:
                q_cancelled = Invoice.CANCELLED
        queryset = Invoice.objects.filter(
            Q(state=q_paid) |
            Q(state=q_unpaid) |
            Q(state=q_cancelled)
            ).select_related(
                'person'
            ).order_by(
                'person__last_name'
            ) 
        if getattr(form, 'cleaned_data', None):
            mem_year = Settings.current().membership_year
            if form.cleaned_data['membership_year']:
                mem_year = form.cleaned_data['membership_year']          
            if form.cleaned_data['start_date']:
                start_date = form.cleaned_data['start_date'] 
            if form.cleaned_data['end_date']:
                end_date = form.cleaned_data['end_date'] + timedelta(days=1)
            queryset = queryset.filter(membership_year=mem_year,
                                       creation_date__gte=start_date,
                                       creation_date__lte=end_date)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super(InvoiceListView, self).get_context_data(**kwargs)
        context['state_list'] = Invoice.STATES
        context['invoices'] = self.object_list
        context['form'] = self.form
        dict = self.object_list.aggregate(Sum('total'))
        context['count'] = self.object_list.count()
        context['total'] = dict['total__sum']
        return context

class InvoiceDetailView(LoginRequiredMixin, DetailView):
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
            return redirect(invoice)

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

    def get_context_data(self, **kwargs):
        context = super(InvoiceDetailView, self).get_context_data(**kwargs)
        user = self.request.user
        context['superuser'] = self.request.user.get_username() == "ian"
        invoice = self.get_object()
        invoice.add_context(context)
        TextBlock.add_email_context(context)

        context['show_buttons'] = True
        return context

class InvoiceGenerateView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        person = Person.objects.get(pk = self.kwargs['pk'])
        invoice = invoice_create_from_items(person)
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
        result = do_mail(request, invoice, option)
        if option == 'view':
            return result
        return redirect(invoice)

class InvoiceMailConfigView(LoginRequiredMixin, FormView):
    form_class = EmailTextForm
    template_name = 'members/generic_crispy_form.html'

    def form_valid(self, form):     
        intro = form.cleaned_data['intro']
        if intro == "":
            intro = "invoice_intro"
        notes = form.cleaned_data['notes']
        if notes == "":
            notes = "invoice_notes"
        closing = form.cleaned_data['closing']
        if closing == "":
            closing = "invoice_closing"
        blocks = TextBlock.objects.filter(name='_email_params')
        if len(blocks) == 0:
            block = TextBlock(name='_email_params')
        else:
            block = blocks[0]
        block.text = intro + "|" + notes + "|" + closing
        block.save()
        return super(InvoiceMailConfigView, self).form_valid(form)

    def get_success_url(self):
        return reverse('invoice-detail', kwargs={'pk':self.kwargs['pk']})

class InvoiceMailBatchView(LoginRequiredMixin, View):
    ''' Send email for all invoices that are unpaid and have not been emailed
        get asks for confirmation
        put sends the mail '''

    def get(self, request, *args, **kwargs):
        count = self.get_list().count
        context = RequestContext(request)
        context['message'] = "This will send {} emails. Continue?".format(count)
        context['action_link'] = reverse('invoice-mail-batch')
        context['cancel_link'] = reverse('home')
        return render_to_response('members/confirm.html', context)

    def post(self, request, *args, **kwargs):
        invs = self.get_list()
        count = 0
        for inv in invs:
            count += do_mail(request, inv, option)
        return HttpResponse("Sent {} mails for {} invoices".format(count, invs.count()))

    def get_list(self):
        year = Settings.current().membership_year
        return Invoice.objects.filter(state=Invoice.UNPAID, membership_year=year)

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

# ================= Public Views

class ResignedView(TemplateView):
    template_name = 'members/resigned.html'

class InvoicePublicView(DetailView):
    model = Invoice
    template_name = 'members/invoice_public.html'

    def get_object(self, querset=None):
        signer = Signer()
        try:
            invoice_id = signer.unsign(self.kwargs['token'])
            self.invoice = Invoice.objects.get(pk = invoice_id)          
        except:
            self.invoice = None
        return self.invoice

    def get_context_data(self, **kwargs):
       
        context = super(InvoicePublicView, self).get_context_data(**kwargs) 
        if self.invoice:  
            self.invoice.add_context(context)
            context['token'] = self.kwargs['token']
        return context

    def post(self, request, *args, **kwargs):
        invoice = self.get_object()
        if 'pay' in request.POST:
            return redirect(gc_create_bill_url(invoice))
        if 'query' in request.POST:
            group = group_get_or_create("2016Query")
            invoice.person.groups.add(group)
            return redirect(reverse('contact-person', kwargs={'person_id': invoice.person.id}))
        elif 'resign' in request.POST:
            group = group_get_or_create("2016Resign")
            invoice.person.groups.add(group)
            return redirect(reverse('contact-resigned', kwargs={'person_id': invoice.person.id}))

class ContactView(FormView):
    form_class = ContactForm
    template_name = 'members/contact.html'
    resigned = False

    #def get_form(self, form_class):
    #    id = ''
    #    if len(self.kwargs) == 1:
    #        id = self.kwargs['person_id']
    #    return form_class(
    #        resigned=self.resigned,
    #        id=id
    #        )

    def get_context_data(self, **kwargs):
        context = super(ContactView, self).get_context_data(**kwargs)
        if self.resigned:
            context['message'] = "Please tell us briefly why you have resigned"
        else:
            context['message'] = "Please enter your query"
        return context

    def form_valid(self, form):
        if self.kwargs['person_id']:
            person = Person.objects.get(pk = self.kwargs['person_id'])
            message = "From {} id {} >".format(person.email, person.id)
        else:
            message = ""
        message += form.cleaned_data['email']
        message += '  '
        if self.resigned:
            message += 'Resignation:  '
        else:
            message += 'Query:  '
        message += form.cleaned_data['message']
        send_mail(subject='CWLTC contact',
                  from_email = 'contact@coombewoodltc.co.uk',
                  message = message,
                  recipient_list = ["subs.cwltc@gmail.com","is@ktconsultants.co.uk"]
                  )
        if self.resigned:
            return HttpResponseRedirect(reverse('resigned'))
        else:
            return HttpResponseRedirect(reverse('thankyou'))
        
    
    def form_invalid(self, form):
        return super(ContactView, self).form_invalid(form)
    
class ThankyouView(TemplateView):
    template_name = 'members/thankyou.html'

# ================== PAYMENTS

class PaymentCreateView(LoginRequiredMixin, CreateView):
    model = Payment
    form_class = PaymentForm
    template_name = 'members/payment_form.html'

    def get_form_kwargs(self):
        ''' if view passed an invoice pass the total to the form '''
        kwargs = super(PaymentCreateView,self).get_form_kwargs()
        self.inv = Invoice.objects.get(pk = self.kwargs['invoice_id'])
        if self.inv:
            kwargs.update({'amount': self.inv.total})
        return kwargs

    def get_context_data(self, **kwargs):
        context = super(PaymentCreateView, self).get_context_data(**kwargs)
        self.inv.add_context(context)
        return context

    def form_valid(self, form):
        invoice = Invoice.objects.get(pk = self.kwargs['invoice_id'])
        form.instance.person = invoice.person
        # save new object before handling many to many relationship
        payment = form.save()
        invoice_pay(invoice, payment)
        return super(PaymentCreateView, self).form_valid(form)

    def get_success_url(self):
        return reverse('invoice-detail',
                       kwargs={'pk':self.kwargs['invoice_id']})

class PaymentDetailView(LoginRequiredMixin, DetailView):
    model = Payment
    template_name = 'members/payment_detail.html'

    def get_context_data(self, **kwargs):
        context = super(PaymentDetailView, self).get_context_data(**kwargs)
        context['payment_types'] = Payment.TYPES
        context['payment_states'] = Payment.STATES
        return context

class PaymentListView(LoginRequiredMixin, FormMixin, TemplateView):
    form_class = PaymentFilterForm
    model = Payment
    template_name = 'members/payment_list.html'

    def get(self, request, *args, **kwargs):
        ''' GET returns HTML '''
        self.form = self.get_form(self.form_class)
        self.object_list = self.get_queryset()
        context = self.get_context_data()
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        ''' POST handles submit and ajax request '''
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
        #self.object_list = self.get_queryset()
        context = super(PaymentListView, self).get_context_data(**kwargs)
        context['form'] = self.get_form(self.form_class)
        context['payments'] = self.object_list
        context['payment_types'] = Payment.TYPES
        context['payment_states'] = Payment.STATES
        dict = self.queryset.aggregate(Sum('amount'),Sum('fee'))
        context['count'] = self.queryset.count()
        context['total'] = dict['amount__sum']
        context['fees'] = dict['fee__sum']
        return context

    def get_queryset(self):
        form = self.form
        year = Settings.current().membership_year    
        start_date = date(year,4,1)
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
        #if getattr(form, 'cleaned_data', None):
        #    mem_year = Settings.current().membership_year
        #    if form.cleaned_data['membership_year']:
        #        mem_year = form.cleaned_data['membership_year']          
        #    if form.cleaned_data['start_date']:
        #        start_date = form.cleaned_data['start_date'] 
        #    if form.cleaned_data['end_date']:
        #        end_date = form.cleaned_data['end_date'] + timedelta(days=1)
        #    self.queryset = self.queryset.filter(     
        


# ================== CREDIT NOTES

class CreditNoteCreateView(LoginRequiredMixin, CreateView):
    model = CreditNote
    form_class = CreditNoteForm
    template_name = 'members/generic_crispy_form.html'
    success_msg = "Credit note added"

    def get_context_data(self, **kwargs):
        person = Person.objects.get(pk=self.kwargs['person_id'])
        context = super(CreditNoteCreateView, self).get_context_data(**kwargs)
        context['title'] = 'Create credit note'
        context['message'] = person.fullname()
        return context

    def form_valid(self, form):
        form.instance.person = Person.objects.get(pk=self.kwargs['person_id'])
        form.instance.detail = "Manually created"
        return super(CreditNoteCreateView, self).form_valid(form)

    def get_success_url(self):
        return reverse('person-detail',
                       kwargs={'pk':self.kwargs['person_id']})

class CreditNoteDetailView(LoginRequiredMixin, DetailView):
    model = Payment
    template_name = 'members/creditnote_detail.html'

    def get_context_data(self, **kwargs):
        context = super(CreditNoteDetailView, self).get_context_data(**kwargs)
        context['payment_types'] = Payment.TYPES
        context['payment_states'] = Payment.STATES
        return context

# ================== TEXT BLOCKS

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

    def get_form_kwargs(self):
        kwargs = super(TextBlockUpdateView, self).get_form_kwargs()
        kwargs.update({'option':self.kwargs['option']})
        return kwargs

    def get_context_data(self, **kwargs):
        context = super(TextBlockUpdateView, self).get_context_data(**kwargs)
        context['option'] = self.kwargs['option']
        return context

    def form_valid(self, form):
        form.save()
        if 'save' in form.data:
            return redirect(reverse('text-list') )
        elif 'html' in form.data:
            return redirect(
                reverse('text-update', kwargs={'pk':self.kwargs['pk'],
                                               'option':'html'}
                        )
                )  
        elif 'editor' in form.data:
            return redirect(
                reverse('text-update', kwargs={'pk':self.kwargs['pk']})
                )

        return super(TextBlockUpdateView, self).form_valid(form)
       
    
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
        try:
            input_excel = form.cleaned_data['input_excel']
            #sheet_type = int(form.cleaned_data['sheet_type'])
            #batch_size = int(form.cleaned_data['batch_size'])
        
            # When we save the new one, any old file will be overwritten
            newbook = ExcelBook(file = input_excel)
            newbook.save() 
        except Exception, e:       
            messages.error(self.request,"Error reading Excel file \n" + repr(e))
            return redirect(reverse('import'))

        
        #if sheet_type == XlsInputForm.MEMBERS:
        #    # delete all Excelbooks in the data base
        #    Person.objects.all().delete()
        #    Address.objects.all().delete()
        #    return HttpResponseRedirect(reverse('import_more',
        #                                        args=[1, 1, batch_size]))
        #elif sheet_type == XlsInputForm.BASE:
        #    Fees.objects.all().delete()
        #    ItemType.objects.all().delete()
        #    Membership.objects.all().delete()
        #    my_book = ExcelBook.objects.all()[0]
        #    with open_excel_workbook(my_book.file) as book:
        #        import_base_tables(book)
        #    return HttpResponseRedirect(reverse('import'))
        
        #elif sheet_type == XlsInputForm.BACKUP:
        #    my_book = ExcelBook.objects.all()[0]
        #    with open_excel_workbook(my_book.file) as book:
        #        import_all(book)
        #    return HttpResponseRedirect(reverse('import'))                                
        #else:
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
            context['errors']=[]
            for k in form.cleaned_data.keys():
                if form.cleaned_data[k]:
                    do_import = 'import' in form.data
                    sheet = book.sheet_by_name(k)
                    sheet_count += 1
                    result = import_items(sheet, do_import)
                    total = total + result[0]
                    if result[1]:
                        context['errors'].append('Sheet {0} contains errors'.format(k))
                        context['errors'].extend(result[1])
                        if do_import:
                            result[1].append('Import aborted')
                            break
                    else:
                        context['errors'].append('Sheet {0} checked OK'.format(k))             
            context['message'] = '{} items were {} from {} sheets'.format(total, 'imported' if do_import else 'checked', sheet_count)
            return render(self.request, 'members/generic_result.html', context)
                       

class InvoiceBatchView(LoginRequiredMixin, FormView):
    form_class = XlsMoreForm
    template_name = 'members/import_more.html'

    def get_context_data(self, **kwargs):
        context = super(InvoiceBatchView, self).get_context_data(**kwargs)
        context['title'] = 'Generate invoices'
        result = invoice_create_batch(size=0)
        context['remaining'] = result[0] - result[1]
        return context

    def form_valid(self,form):
        remaining = invoice_create_batch(size=100)
        return HttpResponseRedirect(reverse('invoice-batch'))

def export(request):
    return export_all()

def import_backup(request):
    return import_all()

def fix_fees(request):
    payments = Payment.objects.filter(type=Payment.DIRECT_DEBIT)
    for p in payments:
        fee = p.amount / 100
        if fee > 2:
            fee = 2
        p.fee = fee
        p.membership_year = 2016
        p.save()
    cnote=CreditNote.objects.filter(pk=336)
    cnote.amount = 307.20
    cnote.save()
    return HttpResponse("Payments & credit note fixed")

def reports(request):
    report=Report.objects.all()[0]
    qset = report.get_query()
    list = report.report_to_list(queryset=qset)
    fields = report.displayfield_set.all()
    html = ""
    for f in fields:
        html += "<br \>" + f.name
    return HttpResponse(html)

#def bar(request):
#    """
#    Downloads the transaction file generated by the bar system
#    """
#    result = ftpService.ftpGet()
#    return render(
#        request,
#        'members/contact.html',
#        context_instance = RequestContext(request,
#        {
#            'title':'Contact',
#            'message':result,
#            'year':datetime.now().year,
#        })
#     )   

class HomeView(TemplateView):
    template_name = 'members/index.html'
    
    def get_context_data(self, **kwargs):
        context = super(HomeView, self).get_context_data(**kwargs)
        context['title'] = 'Home Page'
        context['membership_year'] = Settings.current().membership_year
        context['db_name'] = settings.DATABASES['default']['NAME']
        return context
     
              

def fixup_postgresql(request):

        cursor = connection.cursor()
        cursor.execute("SELECT setval('members_person_id_seq', (SELECT MAX(id) FROM members_person)+1)")
        cursor.execute("SELECT setval('members_fees_id_seq', (SELECT MAX(id) FROM members_fees)+1)")
        cursor.execute("SELECT setval('members_membership_id_seq', (SELECT MAX(id) FROM members_membership)+1)")

def testmailgun(request):
    #send_simple_message()
    mailgun_send()
    return HttpResponse("sent")
