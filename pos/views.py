import json
from django.shortcuts import render_to_response
from django.core.serializers.json import DjangoJSONEncoder
from django.core.serializers import serialize
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse, Http404
from django.views.generic import DetailView, CreateView, UpdateView, TemplateView
from django.urls import reverse, reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.hashers import check_password
from django.shortcuts import redirect
from django_tables2 import SingleTableView
from public.views import RegisterView, RegisterTokenView, ConsentTokenView
from mysite.common import Button
from .tables import *
from .forms import ItemForm, LayoutForm
from .services import *
from .filters import LineItemFilter

LONG_TIMEOUT = 120000
SHORT_TIMEOUT = 30000

class LoadView(LoginRequiredMixin, TemplateView):
    template_name = 'pos/load.html'

    def get_context_data(self, **kwargs):
        context = super(LoadView, self).get_context_data(**kwargs)
        context['layouts'] = Layout.objects.all()
        context['allow_attended'] = True
        return context

    def post(self, request, *args, **kwargs):
        layout = Layout.objects.filter(name=request.POST['layout'])[0]
        request.session['layout_id'] = layout.id
        return redirect('pos_start')


class StartView(LoginRequiredMixin, TemplateView):
    """ Member login or attended mode selection """
    template_name = 'pos/start.html'

    def get_context_data(self, **kwargs):
        context = super(StartView, self).get_context_data(**kwargs)
        context['allow_attended'] = True
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
            if check_password(request.POST['password'], person.pin):
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
            if pay_record['pay_type'] == 'split':
                request.session['people_ids'] = [pay_record['person_id']]
                request.session['receipt'] = receipt
                request.session['total'] = pay_record['total']
                return HttpResponse(reverse('pos_split_summary'))

            elif pay_record['pay_type'] == 'cash':
                create_transaction_from_receipt(request.user.id,
                                                [],
                                                request.session['layout_id'],
                                                receipt,
                                                pay_record['total'],
                                                cash=True)
            else:
                create_transaction_from_receipt(request.user.id,
                                                [pay_record['person_id']],
                                                request.session['layout_id'],
                                                receipt,
                                                pay_record['total']
                                                )
            return HttpResponse(reverse('pos_start'))
        # should not get here - all posts are ajax
        return redirect('pos_start')


class SplitSummaryView(TemplateView):
    """ Summarise current state of a split transaction """
    template_name = 'pos/split_summary.html'

    def post(self, request, *args, **kwargs):
        if 'pay' in request.POST:
            create_transaction_from_receipt(request.user.id,
                                            request.session['people_ids'],
                                            request.session['layout_id'],
                                            request.session['receipt'],
                                            request.session['total']
                                            )
            return redirect('pos_menu')
        if 'add' in request.POST:
            return redirect('pos_split_user')
        return redirect ('pos_run')

    def get_context_data(self, **kwargs):
        context = super(SplitSummaryView, self).get_context_data(**kwargs)
        return make_split_context(self.request, context)


class GetUserSplitView(TemplateView):
    """ Add a user to a split transaction """
    template_name = 'pos/split_user.html'

    def post(self, request, *args, **kwargs):
        if 'back' in request.POST:
            pass
        elif 'person_id' in request.POST:
            people_ids = request.session['people_ids']
            people_ids.append(request.POST['person_id'])
            request.session['people_ids'] = people_ids
        return redirect('pos_split_summary')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return make_split_context(self.request, context)


def make_split_context(request, context):
    """ Common context for split summary and user views"""
    people = []
    for id in request.session['people_ids']:
        people.append(Person.objects.get(pk=id))

    total = request.session['total'] * 100

    first_amount, split_amount = get_split_amounts(total, len(people))

    for i in range(0, len(people)):
        if i == 0:
            people[i].pos_charge = Decimal("{0:.2f}".format(first_amount/100))
        else:
            people[i].pos_charge = Decimal("{0:.2f}".format(split_amount/100))

    context['people'] = people
    context['timeout_url'] = reverse('pos_start')
    context['timeout'] = LONG_TIMEOUT
    return context


def ajax_items_view(request):
    """ responds to ajax request for item list"""
    data = serialize('json', Item.objects.all())
    return JsonResponse(data, safe=False)
    # items = Item.objects.all().values_list('pk', 'description','sale_price')
    # return JsonResponse(json.dumps(list(items), cls=DjangoJSONEncoder), safe=False)


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
        context = super(TransactionListView, self).get_context_data(**kwargs)
        context['main_menu'] = self.main_menu
        context['sum'] = self.qs.aggregate(sum=Sum('total'))['sum']
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

    def post(self, request):
        if 'new' in request.POST:
            return redirect('pos_layout_create')
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
                item = Item.objects.get(button_text=value)
                Location.objects.create(layout=layout,
                                        row=int(parts[1]),
                                        col=int(parts[2]),
                                        item=item,
                                        visible=True)

        return redirect('pos_layout_list')


def pos_layout_context(layout_id, locations, items=None):
    rows = []
    for r in range(1, Location.ROW_MAX + 1):
        cols = []
        for c in range(1, Location.COL_MAX + 1):
            cols.append([r, c])
        rows.append(cols)
    for loc in locations:
        rows[loc.row - 1][loc.col - 1].append(loc.item)
        if items:
            item = [item for item in items if item.button_text == loc.item.button_text]
            if item:
                item[0].used = True
    if items:
        return rows, items
    return rows

