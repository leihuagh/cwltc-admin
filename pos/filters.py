from .models import Transaction, Layout
import django_filters

def trans_type_choices():
    choices = []
    layouts = Layout.objects.all()
    for layout in layouts:
        choices.append([layout.invoice_itemtype.id, layout.invoice_itemtype.description])
    return choices

class TransactionFilter(django_filters.FilterSet):
    class Meta:
        model = Transaction
        fields = {'layout__invoice_itemtype_id'}
    
    trans_type = django_filters.ChoiceFilter(name='layout__invoice_itemtype_id',
                                             label='Transaction type',
                                             choices=trans_type_choices(),
                                             empty_label="All"
                                             )
