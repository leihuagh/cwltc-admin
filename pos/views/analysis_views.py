from django.views.generic import DetailView, CreateView, UpdateView, TemplateView, View
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django_tables2 import SingleTableView
from django.db.models import Sum
from braces.views import GroupRequiredMixin
from pos.tables import *
from pos.forms import ItemForm, LayoutForm, ColourForm
from pos.filters import LineItemFilter
from pos.views.ipad_views import build_pos_array
from pos.services import dump_items_to_excel, dump_layout_to_excel

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
        elif 'default' in request.POST:
            return redirect('pos_start_default')
        elif 'layout' in request.POST:
            layout = Layout.objects.filter(name=request.POST['layout'])[0]
            request.session['layout_id'] = layout.id
            return redirect('pos_start')
        return redirect('pos_admin')

class TransactionListView(SingleTableView):
    """List transactions with filtering"""
    model = Transaction
    table_class = TransactionTable
    template_name = 'pos/transactions.html'
    table_pagination = {'per_page': 10}
    main_menu = False
    cash = False
    comp = False

    def get_table_data(self):
        person_id = self.kwargs.get('person_id', None)
        if person_id:
            self.qs = Transaction.objects.filter(person_id=person_id, billed=False).order_by('-creation_date')
        elif self.cash:
            self.qs = Transaction.objects.filter(cash=True, billed=False).order_by('-creation_date')
        elif self.comp:
            self.qs = Transaction.objects.filter(complimentary=True, billed=False).order_by('-creation_date')
        else:
            self.qs = Transaction.objects.filter(billed=False).order_by('-creation_date')
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
            self.qs = PosPayment.objects.filter(person_id=person_id).select_related('transaction').order_by(
                '-transaction.creation_date')
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