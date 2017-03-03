from django.shortcuts import render, render_to_response
from django.http import HttpRequest, HttpResponseRedirect, HttpResponse, JsonResponse, Http404
from django.template import RequestContext
from django.views.generic import View, ListView, DetailView, CreateView, UpdateView, TemplateView
from django.views.generic.edit import FormView, FormMixin, ProcessFormView
from django.core.urlresolvers import reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django_tables2 import SingleTableView
from decimal import *
from .models import *
from .tables import *
from .services import *

class StartView(LoginRequiredMixin, TemplateView):
    template_name = 'pos/start.html'

    def get_context_data(self, **kwargs):
        context = super(StartView, self).get_context_data(**kwargs)
        context['layouts'] = Layout.objects.all()
        return context

class PosView(LoginRequiredMixin, TemplateView):
    template_name = 'pos/pos.html'

    def get_context_data(self, **kwargs):
        context = super(PosView, self).get_context_data(**kwargs)
        layout = Layout.objects.get(pk=kwargs['layout_id'])
        locations = Location.objects.filter(layout_id=kwargs['layout_id']).order_by('row', 'col')
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
        return context

    def post(self, request, *args, **kwargs):
        if request.is_ajax():
            element_id = request.POST['ic-element-id']
            receipt = request.session['pos_items']
            person_id = request.POST['person_id']
            if element_id[3] == '_':
                key = element_id[0:3]
               
                if key == 'can':
                    receipt = []

                elif key == 'pay':
                    create_transaction_from_receipt(request.user.id, person_id=person_id, receipt=receipt)
                    receipt = []
                    request.session['pos_items'] = []
                    return HttpResponse("Paid",content_type='application/xhtml+xml') 
                
                else:
                    item_id = int(element_id[4:])               
                    found = False
                    for item_dict in receipt:
                        if item_dict['id'] == item_id:
                            found = True
                            break
                    if not found:
                        item_dict = {}
                
                if key == "itm":
                    item = Item.objects.get(id=item_id)
                    if item_dict == {}:
                        item_dict = item.to_dict()
                        receipt.append(item_dict)  
                    else:
                        item_dict['quantity'] += 1
                        item_dict['total'] = unichr(163) + " " + str(item.sale_price * item_dict['quantity'])          
                
                elif key == 'del':
                    receipt.remove(item_dict)        
                            
                request.session['pos_items'] = receipt
                tot = 0    
                for item_dict in receipt:
                    tot += item_dict['sale_price'] * item_dict['quantity']
                context ={}
                context['receipt'] = receipt
                context['total'] = unichr(163) + ' {0:.2f}'.format(Decimal(tot)/100)
                context['request'] = request
                return render_to_response("pos/receipt.html", context)

        return HttpResponse("Error - wrong id",content_type='application/xhtml+xml')

    def create_transaction(self, creator_id, person_id, receipt):
        trans = Transaction()
        total = Decimal(0)
        trans.creator_id = creator_id
        trans.person_id = person_id
        trans.save()
        for item_dict in receipt:
            line_item = LineItem()
            line_item.item_id = item_dict['id']
            line_item.sale_price = Decimal(item_dict['sale_price'])/100
            line_item.cost_price = Decimal(item_dict['cost_price'])/100
            line_item.quantity = item_dict['quantity']
            total += line_item.quantity * line_item.sale_price
            line_item.transaction = trans
            line_item.save()
        trans.total = total
        trans.save()

class TransactionListView(SingleTableView):
    model = Transaction
    table_class = TransactionTable
    template_name = 'pos/transactions.html'   

class LineItemListView(SingleTableView):
    model = LineItem
    table_class = LineItemTable
    template_name = 'pos/lineitems.html' 

class GetUserView(TemplateView):
    template_name = 'pos/getuser.html'

    def post(self, request, *args, **kwargs):
        if request.POST['login']:
            request.session['person_id'] = request.POST['person_id']
            return redirect('pos-view', layout_id=2)
        return redirect('home')