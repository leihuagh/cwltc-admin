import django_tables2 as tables
from django_tables2.utils import A
from django.conf import settings
from members.models import Person

class PersonTable(tables.Table):
    
    class Meta:
        model = Person
        fields = ('first_name', 'last_name', 'sub.membership.description', 'dob', 'sub.paid', )
        attrs = {'class': 'table table-condensed'} 

    edit = tables.LinkColumn('person-detail', text='Edit', args=[A('pk')], orderable=False)
    dob = tables.columns.DateColumn(settings.DATE_FORMAT)
    selection = tables.CheckBoxColumn(accessor='pk',
                                      attrs={ "th__input": {"onclick": "toggle(this)"},
                                              "td__input": {"onclick": "countChecked()",
                                                            "class": "rowcheckbox"}
                                            },
                                      orderable=False)