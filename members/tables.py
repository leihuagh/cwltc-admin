import django_tables2 as tables
from django_tables2.utils import A
from django.conf import settings
from members.models import Person, Subscription

class PersonTable(tables.Table):
    
    class Meta:
        model = Person
        fields = ('first_name', 'last_name', 'email', 'sub.membership.description')
        attrs = {'class': 'table table-condensed'} 

    edit = tables.LinkColumn('person-detail', text='Edit', args=[A('pk')], orderable=False)
    selection = tables.CheckBoxColumn(accessor='pk',
                                      attrs={ "th__input": {"onclick": "toggle(this)"},
                                              "td__input": {"onclick": "countChecked()",
                                                            "class": "rowcheckbox"}
                                            },
                                      orderable=False)

class SubsTable(tables.Table):
    
    class Meta:
        model = Subscription
        fields = ('person_member.first_name', 'person_member.last_name', 'person_member.email',
                  'membership.description',  'person_member.dob', 'paid')
        attrs = {'class': 'table table-condensed'} 

    edit = tables.LinkColumn('person-detail', text='Edit', args=[A('person_member.id')], orderable=False)
    #dob = tables.columns.DateColumn(settings.DATE_FORMAT, accessor='person_member.dob')
    selection = tables.CheckBoxColumn(accessor='person_member.id',
                                      attrs={ "th__input": {"onclick": "toggle(this)"},
                                              "td__input": {"onclick": "countChecked()",
                                                            "class": "rowcheckbox"}
                                            },
                                      orderable=False)
