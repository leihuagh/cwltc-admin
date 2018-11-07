import logging
from django.http import HttpResponseRedirect, Http404
from django.views.generic import View, DetailView, CreateView, UpdateView, TemplateView
from django.contrib import messages
from django.db.models import Sum
from django.shortcuts import redirect, reverse
from braces.views import StaffuserRequiredMixin

from django_tables2 import SingleTableView

from members.models import Person, Address, Group, Settings, Membership, Invoice, Payment, InvoiceItem, ItemType
from members.forms import PersonForm, PersonNameForm, JuniorForm, PersonLinkForm
from members.services import person_can_delete, person_delete, person_link, person_merge, person_resign, \
    invoice_create_from_items, person_statement
from members.tables import ApplicantTable
from public.forms import AddressForm
from pos.models import PosPayment, VisitorBook
from members.excel import export_members

stdlogger = logging.getLogger(__name__)


class AppliedTableView(StaffuserRequiredMixin, SingleTableView):
    """
    List of people who have applied to join
    """
    template_name = 'members/generic_table.html'
    table_pagination = {"per_page": 10000}
    table_class = ApplicantTable

    def get_queryset(self):
        return Person.objects.filter(state=Person.APPLIED).order_by('last_name')

    def get_context_data(self, **kwargs):
        context = super(AppliedTableView, self).get_context_data(**kwargs)
        context['title'] = 'Applicants'
        return context


# class PersonActionMixin(object):
#     """
#     Overrides form_valid to display a message
#     """
#
#     @property
#     def success_msg(self):
#         return NotImplemented
#
#     def form_valid(self, form):
#         messages.info(self.request, self.success_msg)
#         return super(PersonActionMixin, self).form_valid(form)
#
#     def get_success_url(self):
#         return reverse('home')


class PersonCreateView(StaffuserRequiredMixin, CreateView):
    """ Create person and address, optional link kwarg is link to parent """
    model = Person
    template_name = 'members/bs4_crispy_form.html'
    success_msg = "Person created"
    form_class = PersonForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        link = self.kwargs.get('link', '')
        if link:
            kwargs.update({'link': link})
        return kwargs

    def form_invalid(self, form):
        if 'cancel' in form.data:
            return redirect('home')
        return super(PersonCreateView, self).form_invalid(form)

    def form_valid(self, form):
        if 'cancel' in form.data:
            return redirect('home')
        self.form = form
        return super(PersonCreateView, self).form_valid(form)

    def get_success_url(self):
        if 'submit_sub' in self.form.data:
            return reverse('sub-create', kwargs={'person_id': self.form.person.id})
        return reverse('person-detail', kwargs={'pk': self.form.person.id})


class PersonUpdateView(StaffuserRequiredMixin, UpdateView):
    model = Person
    template_name = 'members/crispy_tile.html'
    success_msg = 'Person updated'
    form_class = PersonNameForm

    def get_success_url(self):
        return reverse('person-detail', kwargs={'pk': self.kwargs['pk']})


class PersonLinkView(StaffuserRequiredMixin, TemplateView):
    template_name = 'members/person_link_merge.html'

    def get_context_data(self, **kwargs):
        context = super(PersonLinkView, self).get_context_data(**kwargs)
        person = Person.objects.get(pk=self.kwargs['pk'])
        context['title'] = 'Link person'
        context['person'] = person
        context['info'] = "All invoices, payments and credit notes will be transferred to the person you select below."
        context['action1'] = "Link"
        if person.linked:
            context['action2'] = "UnLink"
            context['title'] = 'Link / unlink person'
        return context

    def post(self, request, *args, **kwargs):
        child = Person.objects.get(pk=self.kwargs['pk'])

        if 'action1' in request.POST:
            id = request.POST['person_id']
            if id.isdigit():
                target = Person.objects.get(pk=request.POST['person_id'])
                if target == child:
                    messages.error(request, "Cannot link a person to themself")
                elif target.linked:
                    messages.error(request, "Cannot link to a person that has a parent")
                else:
                    person_link(child, target)
                    messages.success(request, '{} has been linked to {}'.format(child.fullname, target.fullname))
                    return redirect(target)
            else:
                messages.error(request, "No person selected")
                return redirect('person-link', pk=child.id)
        elif 'action2' in request.POST:
            child.linked = None
            child.save()

        return redirect(child)


class PersonMergeView(StaffuserRequiredMixin, TemplateView):
    template_name = 'members/person_link_merge.html'

    def get_context_data(self, **kwargs):
        context = super(PersonMergeView, self).get_context_data(**kwargs)
        context['title'] = 'Merge person with another'
        context['person'] = Person.objects.get(pk=self.kwargs['pk'])
        context['info'] = "All linked records of {} will be transferred to the person you select below.".format(
            context['person'])
        context['action1'] = "Merge"
        return context

    def post(self, request, *args, **kwargs):
        person = Person.objects.get(pk=self.kwargs['pk'])

        if 'action1' in request.POST:
            target = Person.objects.get(pk=request.POST['person_id'])
            person_merge(person, target)
            messages.success(request, '{} has been merged with this record'.format(person.fullname))
            return redirect(target)
        return redirect(person)


class JuniorCreateView(StaffuserRequiredMixin, CreateView):
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


class PersonDetailView(StaffuserRequiredMixin, DetailView):
    model = Person
    template_name = 'members/person_detail.html'

    def get_context_data(self, **kwargs):
        person = self.get_object()
        context = super().get_context_data(**kwargs)
        add_membership_context(context)
        context['pos_bill'] = True
        return set_person_context(context, person)

    def post(self, request, *args, **kwargs):
        person = self.get_object()
        if 'delete' in request.POST:
            errs = person_delete(person)
            if len(errs) == 0:
                messages.success(self.request, "{0} deleted".format(person.fullname))
                return redirect(reverse('home'))
            message = "{0} was not deleted /n"
            err = ""
            for err in errs:
                message += err + '/n'
            messages.error(self.request, err)

        elif 'resign' in request.POST:
            person_resign(person)

        elif 'remove' in request.POST:
            # remove from group
            slug = request.POST['remove']
            group = Group.objects.filter(slug=slug)[0]
            person.groups.remove(group)

        elif 'unlink' in request.POST:
            person.link(None)

        elif 'renew' in request.POST:
            # renew subscription
            self.request.session['selected_people_ids'] = [person.id]
            return redirect(reverse('sub-renew-list'))

        elif 'deregister' in request.POST:
            person.unregister()

        elif 'invoice' in request.POST:
            year = Settings.objects.all()[0].membership_year
            invoice = invoice_create_from_items(person, year)
            if invoice:
                return redirect(invoice)
            else:
                return redirect(person)

        elif 'pos_bill' in request.POST:
            PosPayment.billing.process(person)
            VisitorBook.billing.process(person)
            for fam in person.person_set.all():
                if not fam.pays_own_bill:
                    PosPayment.billing.process(fam)
                    VisitorBook.billing.process(fam)

        return redirect(person)


def add_membership_context(context):
    """ Add membership dictionary to context """
    mem_dict = {}
    for mem in Membership.objects.all():
        mem_dict[mem.id] = mem.description
    context['mem_dict'] = mem_dict


def set_person_context(context, person):
    context['can_delete'] = person_can_delete(person)

    sub_year = Settings.current_year()
    years = []
    statements = []
    for year in range(sub_year, sub_year - 3, -1):
        years.append(year)
        statements.append(person_statement(person, year))
    context['years'] = years
    context['statements'] = statements
    context['person'] = person
    context['state'] = Person.STATES[person.state][1]
    context['address'] = person.address
    context['subs'] = person.subscription_set.all().order_by('sub_year')
    current_sub = person.subscription_set.filter(sub_year=sub_year, active=True)
    membership = 'Non member'
    membership_icon = 'fas fa-user'
    membership_colour = 'info'
    if len(current_sub) == 1:
        sub = current_sub[0]
        context['sub'] = current_sub[0]
        # for widgets
        if sub.resigned:
            membership = 'Resigned'
            membership_colour = 'info'
            membership_icon = 'fas fa-user-alt-slash'
        else:
            membership = sub.membership.description
            membership_colour = 'primary'
            membership_icon = 'fas fa-user-check'
            context['sub_icon'] = 'fas fa-pound-sign'
            context['sub_colour'] = 'primary' if sub.paid else 'danger'
            context['sub_state'] = sub.invoice_payment_state()

    context['membership_colour'] = membership_colour
    context['membership_icon'] = membership_icon
    context['membership'] = membership

    context['invoices'] = person.invoice_set.all().order_by('update_date')
    own_items = person.invoiceitem_set.filter(invoice=None).order_by('update_date')
    family_items = InvoiceItem.objects.filter(
        invoice=None,
        person__linked=person).order_by('update_date')
    context['items'] = own_items | family_items
    context['items_total'] = context['items'].aggregate(Sum('amount'))['amount__sum']

    pos_list = []
    pos_total = 0
    tot = PosPayment.billing.unbilled_total(person, ItemType.BAR)
    if tot:
        pos_list.append([person.fullname, 'Bar', tot])
        pos_total += tot
    tot = PosPayment.billing.unbilled_total(person, ItemType.TEAS)
    if tot:
        pos_list.append([person.fullname, 'Teas', tot])
        pos_total += tot
    tot = VisitorBook.billing.unbilled_total(person)
    if tot:
        pos_list.append([person.fullname, 'Visitors', tot])
        pos_total += tot

    # Totals for POS items
    parent = None
    if person.person_set.count() > 0:
        parent = person
        for fam in person.person_set.all():
            if not fam.pays_own_bill:
                tot = PosPayment.billing.unbilled_total(fam, ItemType.BAR)
                if tot:
                    pos_list.append([fam.fullname, 'Bar', tot])
                    pos_total += tot
                tot = PosPayment.billing.unbilled_total(fam, ItemType.TEAS)
                if tot:
                    pos_list.append([fam.fullname, 'Teas', tot])
                    pos_total += tot
                tot = VisitorBook.billing.unbilled_total(fam)
                if tot:
                    pos_list.append([fam.fullname, 'Visitors', tot])
                    pos_total += tot
    context['pos_list'] = pos_list
    context['pos_total'] = pos_total

    if person.linked:
        parent = person.linked
    if parent:
        context['parent'] = parent
        context['children'] = parent.person_set.all()

    context['invoice_states'] = Invoice.STATES
    context['payment_states'] = Payment.STATES
    context['payment_types'] = Payment.TYPES
    context['payments'] = person.payment_set.all().order_by('update_date')
    return context


def search_person(request):
    """
    Redirect to a person detail page
    In response to a search on the navbar
    """
    id = request.GET.get('nav_person_id', '')
    if id:
        return redirect(reverse('person-detail', kwargs={'pk': id}))
    return Http404


class AddressUpdateView(StaffuserRequiredMixin, UpdateView):
    model = Address
    form_class = AddressForm  # public!
    template_name = 'members/address_form.html'

    def get_object(self, queryset=None):
        self.person = Person.objects.get(pk=self.kwargs['person_id'])
        return self.person.address

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
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
        return reverse('person-detail', kwargs={'pk': self.kwargs['person_id']})