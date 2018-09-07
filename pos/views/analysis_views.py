import logging
from django.views.generic import DetailView, CreateView, UpdateView, TemplateView, View
from django.urls import reverse, reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django_tables2 import SingleTableView
from django.db.models import Sum
from django.http import HttpResponseRedirect
from braces.views import GroupRequiredMixin
from pos.tables import *
from pos.forms import ItemForm, LayoutForm, ColourForm, AppForm
from pos.filters import LineItemFilter
from pos.views.ipad_views import build_pos_array
from pos.services import dump_layout_to_excel

stdlogger = logging.getLogger(__name__)

class AdminView(LoginRequiredMixin, GroupRequiredMixin, TemplateView):
    template_name = 'pos/admin.html'
    group_required = 'Pos'

    def post(self, request, *args, **kwargs):
        if 'attended_on' in request.POST:
            request.session['attended_allowed'] = True
        elif 'attended_off' in request.POST:
            request.session['attended_allowed'] = False
        elif 'start' in request.POST:
            return redirect('pos_set_terminal')
        elif 'clear' in request.POST:
            PosPing.objects.all().delete()
        return redirect('pos_admin')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pings'] = PosPing.objects.all()
        return context


class TransactionListView(LoginRequiredMixin, SingleTableView):
    """List transactions with filtering"""
    model = Transaction
    table_class = TransactionTable
    template_name = 'pos/transactions.html'
    table_pagination = {'per_page': 10}
    main_menu = False
    cash = False
    comp = False
    filter = ''
    person_id = None

    def get(self, request, *args, **kwargs):
        request.session['pos'] =  request.GET.get('pos', None)
        return super().get(request, *args, **kwargs)

    def get_table_data(self):
        self.person_id = self.kwargs.get('person_id', None)
        if self.person_id:
            self.qs = Transaction.objects.filter(person_id=self.person_id, billed=False)
        elif self.cash:
            self.qs = Transaction.objects.filter(cash=True, billed=False)
        elif self.comp:
            self.qs = Transaction.objects.filter(complimentary=True, billed=False)
        else:
            self.qs = Transaction.objects.filter(billed=False)
        self.filter = self.request.GET.get('filter', 'all')
        if self.filter =='bar':
            self.qs = self.qs.filter(item_type_id=ItemType.BAR)
        elif self.filter == 'teas':
            self.qs = self.qs.filter(item_type_id=ItemType.TEAS)
        return self.qs.order_by('-creation_date').select_related('person').select_related('item_type')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['main_menu'] = self.main_menu
        context['sum'] = self.qs.aggregate(sum=Sum('total'))['sum']
        context['heading'] = 'POS Transactions'
        context['bar'] = self.filter == 'bar'
        context['teas'] = self.filter == 'teas'
        context['all'] = self.filter == 'all'
        if self.request.session.get('pos', None):
            if self.person_id == -1:
                context['exit_url'] = reverse('pos_new_start_person', kwargs={'person_id': self.person_id})
            else:
                context['exit_url'] = reverse('pos_new_start')
        elif self.main_menu:
            context['exit_url'] = reverse('home')
        else:
            #todo remove this when old pos is obsolete
            context['exit_url'] = reverse('pos_menu')
        person_id = self.kwargs.get('self.person_id', None)
        if person_id:
            context['person'] = Person.objects.get(pk=person_id)
        self.request.session['last_path'] = self.request.path + '?' + self.request.GET.urlencode()
        return context

    def post(self, request, **kwargs):
        if 'option' in request.POST:
            return HttpResponseRedirect(request.path + f"?filter={request.POST['option']}")
        return HttpResponseRedirect(request.path)


class PaymentListView(TransactionListView):
    """
    This is used to show the payments for a single user as it reflects what will be billed
    whereas the TransactionListView  (which it inherits) shows the transaction total
    """
    model = PosPayment
    table_class = PosPaymentTable
    template_name = 'pos/transactions.html'


    def get_table_data(self):
        person_id = self.kwargs.get('person_id', None)
        if person_id:
            self.qs = PosPayment.objects.filter(person_id=person_id, transaction__billed=False)
        else:
            self.qs = PosPayment.objects.all()
        self.filter = self.request.GET.get('filter', 'all')
        if self.filter =='bar':
            self.qs = self.qs.filter(transaction__item_type_id=ItemType.BAR)
        elif self.filter == 'teas':
            self.qs = self.qs.filter(transaction__item_type_id=ItemType.TEAS)
        return self.qs.select_related('transaction').select_related('person', 'transaction__item_type').order_by('-transaction.creation_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['heading'] = 'POS Account'
        return context


class LineItemListView(LoginRequiredMixin, SingleTableView):
    """
    If trans_id kwarg passed show items for that transaction
    else show all items
    """
    model = LineItem
    table_class = LineItemTable
    template_name = 'pos/lineitems.html'
    filter_class = LineItemFilter
    table_pagination = {'per_page': 10}

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


class TransactionDetailView(LoginRequiredMixin, DetailView):
    """ Transaction details """
    model = Transaction
    template_name = 'pos/transaction_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        trans = self.get_object()
        context['items'] = trans.lineitem_set.all().order_by('id')
        if len(trans.pospayment_set.all()) > 1:
            context['payments'] = trans.pospayment_set.all()
        id = self.request.session.get('person_id', None)
        if id:
            person = Person.objects.get(pk=self.request.session['person_id'])
            context['admin'] = person.auth.is_staff or person.auth.groups.filter(name='Pos').exists()
        else:
            context['admin'] = (self.request.user.is_staff or
                                'Pos' in self.request.user.groups.values_list("name", flat=True))
        return context

    def post(self, request, **kwargs):
        """ post is always a deletion """
        self.get_object().delete()
        path = self.request.session.get('last_path', None)
        if path:
            return redirect(path)
        return redirect('pos_admin')


class ItemListView(LoginRequiredMixin, GroupRequiredMixin, SingleTableView):
    """ POS items List """
    model = Item
    table_class = ItemTable
    template_name = 'pos/item_list.html'
    table_pagination = {'per_page': 100}
    group_required = 'Pos'

    def get_table_data(self):
        return Item.objects.filter().order_by('item_type', 'button_text')

    def post(self, request):
        if 'new' in request.POST:
            return redirect('pos_item_create')
        if 'admin' in request.POST:
            return redirect('pos_admin')
        return redirect('pos_item_list')


class ItemUpdateView(LoginRequiredMixin, GroupRequiredMixin, UpdateView):
    """ Edit POS items"""
    model = Item
    form_class = ItemForm
    success_url = reverse_lazy('pos_item_list')
    group_required = 'Pos'

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


class ItemCreateView(LoginRequiredMixin, GroupRequiredMixin, CreateView):
    """ Create POS items"""
    model = Item
    form_class = ItemForm
    success_url = reverse_lazy('pos_item_list')
    group_required = 'Pos'

    def post(self, request, *args, **kwargs):
        if 'cancel' in request.POST:
            return redirect(self.success_url)
        return super(ItemCreateView, self).post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ItemCreateView, self).get_context_data()
        context['title'] = 'Create new POS item'
        return context


class PriceListView(LoginRequiredMixin, GroupRequiredMixin, View):
    group_required = 'Pos'

    def get(self, request, *args, **kwargs):
        # TODO Don't fix PK in PriceListView
       # layout = Layout.objects.filter(item_type_id=ItemType.BAR)[0]
        layout = Layout.objects.get(pk=3)
        return dump_layout_to_excel(layout)


class LayoutListView(LoginRequiredMixin, GroupRequiredMixin, SingleTableView):
    """ Summary of available POS layouts """
    model = Layout
    table_class = LayoutTable
    template_name = 'pos/layout_list.html'
    group_required = 'Pos'

    def post(self, request):
        if 'new' in request.POST:
            return redirect('pos_layout_create')
        if 'admin' in request.POST:
            return redirect('pos_admin')
        return redirect('pos_layout_list')


class LayoutCreateView(LoginRequiredMixin, GroupRequiredMixin, CreateView):
    """
    Create new POS layout then redirect to edit it
    """
    model = Layout
    form_class = LayoutForm
    success_url = reverse_lazy('pos_layout_list')
    group_required = 'Pos'
    template_name = 'pos/layout_new.html'

    def post(self, request, *args, **kwargs):
        if 'cancel' in request.POST:
            return redirect(self.success_url)
        return super(LayoutCreateView, self).post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(LayoutCreateView, self).get_context_data()
        context['title'] = 'Create new POS Layout'
        return context

    def form_valid(self, form):
        new_layout = form.save()
        return redirect('pos_layout_update', pk=new_layout.id)


class LayoutRenameView(LoginRequiredMixin, GroupRequiredMixin, UpdateView):
    """
    Rename layout, title and item type
    """
    model = Layout
    form_class = LayoutForm
    success_url = reverse_lazy('pos_layout_list')
    group_required = 'Pos'
    template_name = 'pos/layout_new.html'

    def post(self, request, *args, **kwargs):
        if 'cancel' in request.POST:
            return redirect(self.success_url)
        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['title'] = 'Rename POS Layout'
        return context


class LayoutUpdateView(LoginRequiredMixin, GroupRequiredMixin, UpdateView):
    """ Edit a POS layout """
    model = Layout
    form_class = LayoutForm
    template_name = 'pos/layout_form.html'
    group_required = 'Pos'

    def get_context_data(self, **kwargs):
        context = super(LayoutUpdateView, self).get_context_data(**kwargs)
        layout = self.get_object()
        context['rows'], context['items'] = build_pos_array(layout)
        context['layout'] = layout
        return context

    def post(self, request, *args, **kwargs):
        layout = self.get_object()
        if 'cancel' in request.POST:
            return redirect('pos_layout_list')
        if 'delete' in request.POST:
            layout.delete()
            return redirect('pos_layout_list')
        elif request.POST['save_as']:
            file_name = request.POST['filename']
            if file_name:
                new_layout = Layout.objects.create(name=file_name)
                layout = new_layout
        # save or save as or price_list
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
        if 'price_list' in request.POST:
            return dump_layout_to_excel(layout)
        return redirect('pos_layout_list')


class ColourCreateView(LoginRequiredMixin, GroupRequiredMixin, CreateView):
    """ Create new POS layout """
    model = Colour
    form_class = ColourForm
    success_url = reverse_lazy('pos_colour_list')
    template_name = 'pos/colour_form.html'
    group_required = 'Pos'

    def post(self, request, *args, **kwargs):
        if 'cancel' in request.POST:
            return redirect(self.success_url)
        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['title'] = 'Create new colour scheme'
        return context


class ColourUpdateView(LoginRequiredMixin, GroupRequiredMixin, UpdateView):
    model = Colour
    form_class = ColourForm
    template_name = 'pos/colour_form.html'
    success_url = reverse_lazy('pos_colour_list')
    group_required = 'Pos'

    def post(self, request, *args, **kwargs):
        colour = self.get_object()
        if 'cancel' in request.POST:
            return redirect('pos_colour_list')
        if 'delete' in request.POST:
            colour.delete()
            return redirect('pos_colour_list')
        return super().post(request, *args, **kwargs)


class ColourListView(LoginRequiredMixin, GroupRequiredMixin, SingleTableView):
    model = Colour
    table_class = ColourTable
    template_name = 'pos/colour_list.html'
    group_required = 'Pos'

    def post(self, request):
        if 'new' in request.POST:
            return redirect('pos_colour_create')
        if 'admin' in request.POST:
            return redirect('pos_admin')
        return redirect('pos_colour_list')


class AppCreateView(LoginRequiredMixin, GroupRequiredMixin, CreateView):
    """
    Create new POS application
    """
    model = PosApp
    form_class = AppForm
    success_url = reverse_lazy('pos_app_list')
    group_required = 'Pos'
    template_name = 'pos/crispy_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['title'] = 'Create new POS application'
        return context

    def post(self, request, *args, **kwargs):
        if 'cancel' in request.POST:
            return redirect(self.success_url)
        return super().post(request, *args, **kwargs)


class AppUpdateView(LoginRequiredMixin, GroupRequiredMixin, UpdateView):
    """
    Update a POS application
    """
    model = PosApp
    form_class = AppForm
    success_url = reverse_lazy('pos_app_list')
    group_required = 'Pos'
    template_name = 'pos/crispy_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['title'] = 'Edit POS application'
        return context

    def post(self, request, *args, **kwargs):
        if 'cancel' in request.POST:
            return redirect(self.success_url)
        return super().post(request, *args, **kwargs)


class AppListView(LoginRequiredMixin, GroupRequiredMixin, SingleTableView):
    """
    List all POS applications
    """
    model = PosApp
    table_class = PosAppTable
    success_url = reverse_lazy('pos_app_list')
    group_required = 'Pos'
    template_name = 'pos/app_list.html'

    def post(self, request, *args, **kwargs):
        if 'cancel' in request.POST:
            return redirect(self.success_url)
        return super().post(request, *args, **kwargs)