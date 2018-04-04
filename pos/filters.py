from members.models import ItemType
from .models import LineItem
import django_filters

def item_type_choices():
    choices = []
    item_types = ItemType.objects.filter(pos=True)
    for it in item_types:
        choices.append([it.id, it.description])
    return choices

class LineItemFilter(django_filters.FilterSet):

    item_type_id = django_filters.ChoiceFilter(name='item__item_type_id',
                                            label='Item type',
                                            choices=item_type_choices(),
                                            empty_label="All"
                                            )
    class Meta:
        model = LineItem
        fields = ['transaction__creation_date']