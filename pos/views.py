import json
from django.core.serializers import serialize
from django.http import HttpResponse, JsonResponse, Http404
from django.views.generic import DetailView, CreateView, UpdateView, TemplateView, View
from django.urls import reverse, reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.hashers import check_password
from django.shortcuts import redirect
from django_tables2 import SingleTableView
from braces.views import GroupRequiredMixin
from public.views import RegisterView, RegisterTokenView, ConsentTokenView
from mysite.common import Button
from .tables import *
from .forms import ItemForm, LayoutForm
from .services import *
from .filters import LineItemFilter

LONG_TIMEOUT = 120000
SHORT_TIMEOUT = 30000

class AdminView(LoginRequiredMixin, GroupRequiredMixin, TemplateView):
    template_name = 'pos/admin.html'
    group_required = 'pos'

    def get_context_data(self, **kwargs):
        context = super(AdminView, self).get_context_data(**kwargs)
        context['layouts'] = Layout.objects.all()
        context['admin_record'] = PosAdmin.record()
        return context

    def post(self, request, *args, **kwargs):
        record = PosAdmin.record()
        if 'admin_on' in request.POST:
            record.attended_mode = True
            record.save()
        elif 'admin_off' in request.POST:
            record.attended_mode = False
            record.save()
        elif 'default' in request.POST:
            return redirect('pos_start_default')
        elif 'layout' in request.POST:
            layout = Layout.objects.filter(name=request.POST['layout'])[0]
            request.session['layout_id'] = layout.id
            return redirect('pos_start')
        return redirect('pos_admin')

class StartDefaultView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        request.session['layout_id'] = PosAdmin.record().default_layout_id
        return redirect('pos_start')

class StartView(LoginRequiredMixin, TemplateView):
    """ Member login or attended mode selection """
    template_name = 'pos/start.html'

    def get_context_data(self, **kwargs):
        context = super(StartView, self).get_context_data(**kwargs)
        context['attended_mode'] = PosAdmin.record().attended_mode
        self.request.session['person_id'] = None
        return context

    def post(self, request, *args, **kwargs):
        if 'login' in request.POST:
            request.session['attended'] = False
            return redirect('pos_user')
        elif 'attended' in request.POST:
            request.session['attended'] = True
            return redirect('pos_run')
        return redirect('pos_start')
1

class GetUserView(TemplateView):
    """ User identification """
    template_name = 'pos/get_user.html'

    def post(self, request, *args, **kwargs):
        if request.POST['person_id']:
            request.session['person_id'] = request.POST['person_id']
            person = Person.objects.get(pk=request.POST['person_id'])
            if person.auth_id:
                return redirect('pos_password')
            return redirect('pos_register')
        return redirect('pos_start')

    def get_context_data(self, **kwargs):
        context = super(GetUserView, self).get_context_data(**kwargs)
        context['timeout_url'] = reverse('pos_start')
        context['timeout'] = LONG_TIMEOUT
        return context


class GetPasswordView(TemplateView):
    """ User's password or PIN """
    template_name = 'pos/get_password.html'

    def post(self, request, *args, **kwargs):
        if request.POST['submit']:
            person = Person.objects.get(pk=request.session['person_id'])
            if check_password(request.POST['pin'], person.pin):
                return redirect('pos_menu')
            user = User.objects.get(pk=person.auth_id)
            if user.check_password(request.POST['password']):
                return redirect('pos_menu')
        return redirect('pos_start')

    def get_context_data(self, **kwargs):
        context = super(GetPasswordView, self).get_context_data(**kwargs)
        person = Person.objects.get(pk=self.request.session['person_id'])
        context['full_name'] = person.fullname
        context['timeout_url'] = reverse('pos_start')
        context['timeout'] = LONG_TIMEOUT
        return context


class PosRegisterView(RegisterView):
    """ When user is not registered we use the public
    registration form and override some things """
    template_name = 'pos/register.html'

    def get_initial(self):
        initial = super(PosRegisterView, self).get_initial()
        self.person = Person.objects.get(pk=self.request.session['person_id'])
        initial['first_name'] = self.person.first_name
        initial['last_name'] = self.person.last_name
        return initial

    def get_form_kwargs(self):
        """ set form kwargs so the name is hidden """
        kwargs = super().get_form_kwargs()
        kwargs.update({'hide_name': True})
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['person'] = self.person
        context['timeout_url'] = reverse('pos_start')
        context['timeout'] = LONG_TIMEOUT
        context['buttons'] = [Button('Back', 'back', css_class='btn-success btn-lg'),
                             Button('Next', 'register', css_class='btn-success btn-lg')]
        return context

    def post(self, request, *args, **kwargs):
        if 'back' in request.POST:
            return redirect('pos_start')
        return super().post(request, args, kwargs)

    def get_success_url_name(self):
        return 'pos_register_token'

    def get_failure_url_name(self):
        return 'pos_start'


class PosRegisterTokenView(RegisterTokenView):
    template_name = 'pos/register_token.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pos'] = True
        context['timeout_url'] = reverse('pos_start')
        context['timeout'] = LONG_TIMEOUT
        return context

    def get_success_url_name(self, **kwargs):
        return 'pos_consent_token'


class PosConsentView(ConsentTokenView):
    template_name = 'pos/consent.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pos'] = True
        context['timeout_url'] = reverse('pos_start')
        context['timeout'] = LONG_TIMEOUT
        return context

    def get_success_url(self, **kwargs):
        return 'pos-menu'

class MemberMenuView(LoginRequiredMixin, TemplateView):
    """ Menu of options for members """
    template_name = 'pos/menu.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.request.session['people_ids'] = []
        person = Person.objects.get(pk=self.request.session['person_id'])
        context['person'] = person
        context['exit_menu'] = person.auth.is_staff or person.auth.groups.filter(name='pos').exists()
        context['timeout_url'] = reverse('pos_start')
        context['timeout'] = LONG_TIMEOUT
        return context


class PosView(LoginRequiredMixin, TemplateView):
    """ The main POS screen """
    template_name = 'pos/pos.html'

    def get_context_data(self, **kwargs):
        context = super(PosView, self).get_context_data(**kwargs)
        layout_id = self.request.session['layout_id']
        locations = Location.objects.filter(layout_id=layout_id).order_by('row', 'col')
        context['rows'] = pos_layout_context(layout_id, locations)
        context['timeout_url'] = reverse('pos_start')
        context['items_url'] = reverse('pos_ajax_items')
        context['post_url'] = reverse('pos_run')
        context['exit_url'] = reverse('pos_start' if self.request.session['attended'] else 'pos_menu')
        if self.request.session['attended']:
            context['is_attended'] = 'true'
        else:
            context['is_attended'] = 'false'
            person = Person.objects.get(pk=self.request.session['person_id'])
            context['person'] = person
        context['timeout_url'] = reverse('pos_start')
        context['timeout'] = LONG_TIMEOUT
        return context

    def post(self, request, *args, **kwargs):
        """ Write transaction to database"""

        if request.is_ajax():
            receipt = json.loads(request.body)
            pay_record = receipt.pop()
            create_transaction_from_receipt(request.user.id,
                                            request.session['layout_id'],
                                            receipt,
                                            pay_record['total'],
                                            pay_record['people'],
                                            )
            return HttpResponse(reverse('pos_start'))
        # should not get here - all posts are ajax
        return redirect('pos_start')


def ajax_items_view(request):
    """ responds to ajax request for item list"""
    data = serialize('json', Item.objects.all())
    return JsonResponse(data, safe=False)


class TransactionListView(SingleTableView):
    """List transactions with filtering"""
    model = Transaction
    table_class = TransactionTable
    template_name = 'pos/transactions.html'
    table_pagination = {'per_page': 10}
    main_menu = False
 
    def get_table_data(self):
        person_id = self.kwargs.get('person_id', None)
        if person_id:
            self.qs = Transaction.objects.filter(person_id=person_id).order_by('-creation_date')
        else:
            self.qs = Transaction.objects.all().order_by('-creation_date')
        return self.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['main_menu'] = self.main_menu
        context['sum'] = self.qs.aggregate(sum=Sum('total'))['sum']
        person_id = self.kwargs.get('person_id', None)
        if person_id:
            context['person'] = Person.objects.get(pk=person_id)
        return context


class PaymentListView(SingleTableView):
    """ List payments with filter"""
    model = PosPayment
    table_class = PosPaymentTable
    template_name = 'pos/transactions.html'
    table_pagination = {'per_page': 10}
    main_menu = False

    def get_table_data(self):
        person_id = self.kwargs.get('person_id', None)
        if person_id:
            self.qs = PosPayment.objects.filter(person_id=person_id).select_related('transaction').order_by('-transaction.creation_date')
        else:
            self.qs = PosPayment.objects.all().select_related('transaction').order_by('-transaction.creation_date')
        return self.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['main_menu'] = self.main_menu
        context['sum'] = self.qs.aggregate(sum=Sum('amount'))['sum']
        person_id = self.kwargs.get('person_id', None)
        if person_id:
            context['person'] = Person.objects.get(pk=person_id)
        return context


class LineItemListView(SingleTableView):
    """
    If trans_id kwarg passed show items for that transaction
    else show all items
    """
    model = LineItem
    table_class = LineItemTable
    template_name = 'pos/lineitems.html'
    filter_class = LineItemFilter

    def get_table_data(self):
        trans_id = self.kwargs.get('trans_id', None)
        if trans_id:
            qs = LineItem.objects.filter(transaction_id=trans_id).select_related('transaction')
        else:
            qs = LineItem.objects.all().select_related('transaction')
        self.filter = self.filter_class(self.request.GET, qs)
        self.qs = self.filter.qs
        return self.qs
    
    def get_context_data(self, **kwargs):
        context = super(LineItemListView, self).get_context_data(**kwargs)
        trans_id = self.kwargs.get('trans_id', None)
        if trans_id:
            transaction = Transaction.objects.get(pk=trans_id)
            context['transaction'] = transaction
        else:
            context['transaction'] = None
        context['filter'] = self.filter
        return context


class TransactionDetailView(DetailView):
    """ Transaction details """
    model = Transaction
    template_name = 'pos/transaction_detail.html'

    def get_context_data(self, **kwargs):
        context = super(TransactionDetailView, self).get_context_data(**kwargs)
        trans = self.get_object()
        context['items'] = trans.lineitem_set.all().order_by('id')
        if len(trans.pospayment_set.all()) > 1:
            context['payments'] = trans.pospayment_set.all()
        return context


class ItemListView(LoginRequiredMixin, SingleTableView):
    """ POS items List """
    model = Item
    table_class = ItemTable
    template_name = 'pos/item_list.html'

    def post(self, request):
        if 'new' in request.POST:
            return redirect('pos_item_create')
        return redirect('pos_item_list')


class ItemUpdateView(LoginRequiredMixin, UpdateView):
    """ Edit POS items"""
    model = Item
    form_class = ItemForm
    success_url = reverse_lazy('pos_item_list')

    def get_form_kwargs(self):
        kwargs = super(ItemUpdateView, self).get_form_kwargs()
        kwargs['delete'] = True
        return kwargs

    def post(self, request, *args, **kwargs):
        if 'cancel' in request.POST:
            return redirect(self.success_url)
        elif 'delete' in request.POST:
            item = self.get_object()
            item.delete()
            return redirect(self.success_url)
        return super(ItemUpdateView, self).post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ItemUpdateView, self).get_context_data()
        context['title'] = 'Edit POS item'
        return context


class ItemCreateView(LoginRequiredMixin, CreateView):
    """ Create POS items"""
    model = Item
    form_class = ItemForm
    success_url = reverse_lazy('pos_item_list')

    def post(self, request, *args, **kwargs):
        if 'cancel' in request.POST:
            return redirect(self.success_url)
        return super(ItemCreateView, self).post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ItemCreateView, self).get_context_data()
        context['title'] = 'Create new POS item'
        return context
    

class LayoutListView(LoginRequiredMixin, SingleTableView):
    """ Summary of available POS layouts """
    model = Layout
    table_class = LayoutTable
    template_name = 'pos/layout_list.html'

    def get_queryset(self, **kwargs):
        qs = super().get_queryset()
        default_id = ""
        default_layout = PosAdmin.record().default_layout
        if default_layout:
            default_id=default_layout.id
        for item in qs:
            item.is_default = default_id == item.id
        return qs

    def post(self, request):
        if 'new' in request.POST:
            return redirect('pos_layout_create')
        if 'admin' in request.POST:
            return redirect('pos_admin')
        admin = PosAdmin.record()
        for key in request.POST:
            if key.isnumeric():
                admin.default_layout_id = key
                admin.save()
                break
        return redirect('pos_layout_list')


class LayoutCreateView(LoginRequiredMixin, CreateView):
    """ Create new POS layout """
    model = Layout
    form_class = LayoutForm
    success_url = reverse_lazy('pos_layout_list')

    def post(self, request, *args, **kwargs):
        if 'cancel' in request.POST:
            return redirect(self.success_url)
        return super(LayoutCreateView, self).post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(LayoutCreateView, self).get_context_data()
        context['title'] = 'Create new POS Layout'
        return context


class LayoutUpdateView(LoginRequiredMixin, UpdateView):
    """ Edit a POS layout """
    model = Layout
    form_class = LayoutForm
    template_name = 'pos/layout_form.html'

    def get_context_data(self, **kwargs):
        context = super(LayoutUpdateView, self).get_context_data(**kwargs)
        layout = self.get_object()
        locations = Location.objects.filter(layout_id=layout.id).order_by('row', 'col')
        items = Item.objects.all().order_by('button_text')
        context['rows'], context['items'] = pos_layout_context(layout.id, locations, items)
        return context

    def post(self, request, *args, **kwargs):
        layout = self.get_object()
        if 'cancel' in request.POST:
            return redirect('pos_layout_list')
        if 'delete' in request.POST:
            layout.delete()
            return redirect('pos_layout_list')
        elif request.POST['save_as']:
            file_name=request.POST['filename']
            if file_name:
                new_layout = Layout.objects.create(
                    name=file_name,
                    #invoice_itemtype=layout.invoice_itemtype
                )
                layout=new_layout
            else:
                pass
        # save or save as
        Location.objects.filter(layout_id=layout.id).delete()
        for key, value in request.POST.items():
            parts = key.split(":")
            if len(parts) == 3 and value:
                if int(parts[2]) == 0:
                    description = value
                    item = None
                else:
                    item = Item.objects.get(button_text=value)
                    description = ""
                Location.objects.create(layout=layout,
                                        row=int(parts[1]),
                                        col=int(parts[2]),
                                        item=item,
                                        description=description,
                                        visible=True)

        return redirect('pos_layout_list')


def pos_layout_context(layout_id, locations, items=None):
    rows = []
    for r in range(1, Location.ROW_MAX + 1):
        cols = []
        for c in range(0, Location.COL_MAX + 1):
            cols.append([r, c])
        rows.append(cols)
    for loc in locations:
        if loc.col == 0:
            rows[loc.row - 1][loc.col].append(loc.description)
        else:
            rows[loc.row - 1][loc.col].append(loc.item)
            if items:
                item = [item for item in items if item.button_text == loc.item.button_text]
                if item:
                    item[0].used = True
    if items:
        return rows, items
    return rows

