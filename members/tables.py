import django_tables2 as tables
from django_tables2.utils import A
from django.conf import settings
from members.models import Person

class PersonTable(tables.Table):
    
    class Meta:
        model = Person
        fields = ('first_name', 'last_name', 'sub.membership.description', 'dob', 'sub.paid', )
        attrs = {'class': 'table table-condensed'} 

    edit = tables.LinkColumn('person-detail', text='Edit', args=[A('pk')])
    dob = tables.columns.DateColumn(settings.DATE_FORMAT)
