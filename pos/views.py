from django.shortcuts import render, render_to_response
from django.http import HttpRequest, HttpResponseRedirect, HttpResponse, JsonResponse, Http404
from django.template import RequestContext
from django.views.generic import View, ListView, DetailView, CreateView, UpdateView, TemplateView
from django.views.generic.edit import FormView, FormMixin, ProcessFormView
from django.urls import reverse, reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django_tables2 import SingleTableView
from decimal import *
from .models import *
from .tables import *
from .forms import ItemForm, LayoutForm
from .services import *
from .filters import LineItemFilter


class LoadView(LoginRequiredMixin, TemplateView):
    template_name = 'pos/load.html'

    def get_context_data(self, **kwargs):
        context = super(LoadView, self).get_context_data(**kwargs)
        context['layouts'] = Layout.objects.all()
        return context

    def post(self, request, *args, **kwargs):
        layout = Layout.objects.filter(name=request.POST['layout'])[0]
        request.session['layout_id'] = layout.id
        request.session['attended'] = True
        return HttpResponseRedirect(reverse('pos_start'))


class StartView(LoginRequiredMixin, TemplateView):
    template_name = 'pos/start.html'

    def get_context_data(self, **kwargs):
        context = super(StartView, self).get_context_data(**kwargs)
        context['attended'] = self.request.session['attended']
        return context


class GetUserView(TemplateView):
    template_name = 'pos/get_user.html'

    def post(self, request, *args, **kwargs):
        if request.POST['person_id']:
            request.session['person_id'] = request.POST['person_id']
            person = Person.objects.get(pk=request.POST['person_id'])
            if person.auth_id:
                return redirect('pos_password')
            return redirect('public_register')
        return redirect('home')

    def get_context_data(self, **kwargs):
        context = super(GetUserView, self).get_context_data(**kwargs)
        context['timeout_url'] = reverse('pos_start')
        context['timeout'] = 10000
        return context


class GetPasswordView(TemplateView):
    template_name = 'pos/get_password.html'

    def post(self, request, *args, **kwargs):
        if request.POST['submit']:
            person = Person.objects.get(pk=request.session['person_id'])
            user = User.objects.get(pk=person.auth_id)
            if user.check_password(request.POST['password']):
                return redirect('pos_member_menu')
            else:
                pass
        return redirect('home')

    def get_context_data(self, **kwargs):
        context = super(GetPasswordView, self).get_context_data(**kwargs)
        person = Person.objects.get(pk=self.request.session['person_id'])
        context['full_name'] = person.fullname
        context['timeout_url'] = reverse('pos_start')
        context['timeout'] = 10000
        return context


class MemberMenuView(LoginRequiredMixin, TemplateView):
    template_name = 'pos/member_menu.html'

    def get_context_data(self, **kwargs):
        context = super(MemberMenuView, self).get_context_data(**kwargs)
        context['person']= Person.objects.get(pk=self.request.session['person_id'])
        context['timeout_url'] = reverse('pos_start')
        context['timeout'] = 10000
        return context


class PosView(LoginRequiredMixin, TemplateView):
    template_name = 'pos/pos.html'

    def get_context_data(self, **kwargs):
        context = super(PosView, self).get_context_data(**kwargs)
        layout_id = self.request.session['layout_id']
        layout = Layout.objects.get(pk=layout_id)
        locations = Location.objects.filter(layout_id=layout_id).order_by('row', 'col')
        rows = []
        current_row = 1
        cols = []
        for loc in locations:
            if loc.row == current_row:
                cols.append(loc)
            else:
                rows.append(cols)
                for row in range(current_row, loc.row - 1):
                    rows.append([])
                current_row = loc.row
                cols=[]
                cols.append(loc)
        rows.append(cols)
        context['rows'] = rows
        self.request.session['pos_items'] = []
        context['person']= Person.objects.get(pk=self.request.session['person_id'])
        context['enable_payment'] = False
        context['timeout_url'] = reverse('pos_start')
        context['timeout'] = 10000
        return context

    def post(self, request, *args, **kwargs):

        if request.is_ajax():
            # if request.POST['timeout']:
            #     receipt = []
            #     request.session['pos_items'] = []
            #     response = HttpResponse()
            #     response['X-IC-Redirect'] = reverse('pos_member_menu')
            #     return response

            receipt = request.session['pos_items']
            element_id = request.POST['ic-element-id']
            if element_id[3] == '_':
                key = element_id[0:3]

                if key == 'pay':
                    response = HttpResponse()
                    response['X-IC-Script'] = "$('#id_confirm').text($('#id_total').text());$('#pay_modal').modal('show')"
                    return response

                elif key == 'bak':
                    response = HttpResponse()
                    response['X-IC-Script'] = "$('#pay_modal').modal('hide')"
                    return response

                if key == 'yes':
                    create_transaction_from_receipt(request.user.id,
                                                    request.session['person_id'],
                                                    request.session['layout_id'],
                                                    receipt)

                if key == 'end' or key =='yes':
                    receipt = []
                    request.session['pos_items'] = []
                    response = HttpResponse()
                    response['X-IC-Redirect'] = reverse('pos_user')
                    return response

                elif key == 'can':
                    receipt = []

                elif key == "itm":
                    item_id = int(element_id[4:])
                    item = Item.objects.get(id=item_id)
                    item_dict = item.to_dict()
                    receipt.append(item_dict)

                elif key == 'del':
                    counter = int(element_id[4:])
                    receipt.remove(receipt[counter])

                request.session['pos_items'] = receipt
                tot = 0
                for item_dict in receipt:
                    tot += item_dict['sale_price'] * item_dict['quantity']
                context = {}
                context['receipt'] = receipt
                context['total'] = chr(163) + ' {0:.2f}'.format(Decimal(tot)/100)
                context['request'] = request
                context['enable_payment'] = tot > 0
                return render_to_response("pos/receipt.html", context)

        return HttpResponse("Error - wrong id",content_type='application/xhtml+xml')


class TransactionListView(SingleTableView):
    '''
    List transactions with filtering
    '''
    model = Transaction
    table_class = TransactionTable
    template_name = 'pos/transactions.html'
    table_pagination={'per_page': 10}
    main_menu = False
 
    def get_table_data(self):
        person_id = self.kwargs.get('person_id', None)
        if person_id:
            self.qs = Transaction.objects.filter(person_id=person_id)
        else:
            self.qs = Transaction.objects.all()
        return self.qs

    def get_context_data(self, **kwargs):
        context = super(TransactionListView, self).get_context_data(**kwargs)
        context['main_menu'] = self.main_menu
        context['sum'] = self.qs.aggregate(sum=Sum('total'))['sum']
        person_id = self.kwargs.get('person_id', None)
        if person_id:
            context['person'] = Person.objects.get(pk=person_id)
        return context


class LineItemListView(SingleTableView):
    '''
    If trans_id kwarg passed show items for that transaction
    else show all items
    '''
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
    model = Transaction
    template_name = 'pos/transaction_detail.html'

    def get_context_data(self, **kwargs):
        context = super(TransactionDetailView, self).get_context_data(**kwargs)
        trans = self.get_object()
        context['items'] =trans.lineitem_set.all().order_by('id')
        return context


class ItemListView(LoginRequiredMixin, SingleTableView):
    model = Item
    table_class = ItemTable
    template_name = 'pos/item_list.html'

    def post(self, request):
        if 'new' in request.POST:
            return redirect('pos_item_create')
        return redirect('pos_item_list')


class ItemUpdateView(LoginRequiredMixin, UpdateView):
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
    model = Layout
    table_class = LayoutTable
    template_name = 'pos/layout_list.html'

    def post(self, request):
        if 'new' in request.POST:
            return redirect('pos_layout_create')
        return redirect('pos_layout_list')


class LayoutCreateView(LoginRequiredMixin, CreateView):
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
    model = Layout
    form_class = LayoutForm
    template_name = 'pos/layout_form.html'

    def get_context_data(self, **kwargs):
        context = super(LayoutUpdateView, self).get_context_data(**kwargs)
        layout = self.get_object()
        locations = Location.objects.filter(layout_id=layout.id).order_by('row', 'col')
        items = Item.objects.all().order_by('button_text')
        rows = []
        for r in range(1, Location.ROW_MAX + 1):
            cols = []
            for c in range(1, Location.COL_MAX + 1):
                cols.append([r, c])
            rows.append(cols)
        for loc in locations:
            rows[loc.row - 1][loc.col -1].append(loc.item)
            item = [item for item in items if item.button_text == loc.item.button_text]
            if item:
                item[0].used=True
        context['rows'] = rows
        context['items'] = items
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
                    invoice_itemtype=layout.invoice_itemtype
                )
                layout=new_layout
            else:
                pass
        # save or save as
        Location.objects.filter(layout_id=layout.id).delete()
        for key, value in request.POST.items():
            parts = key.split(":")
            if len(parts) == 3 and value:
                item = Item.objects.get(button_text=value)
                Location.objects.create(layout=layout,
                                        row=int(parts[1]),
                                        col=int(parts[2]),
                                        item=item,
                                        visible=True)

        return redirect('pos_layout_list')
