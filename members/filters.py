from datetime import *
from .models import Person
import django_filters
from django.forms.widgets import *

class PersonFilter(django_filters.FilterSet):
    class Meta:
        model = Person
        fields = {'first_name': ['icontains',]
                  } 
    first_name = django_filters.CharFilter(lookup_expr='istartswith')
    last_name = django_filters.CharFilter(lookup_expr='istartswith')
    dob1 = django_filters.DateFilter(name='dob',
                                     label='Born after',
                                     lookup_expr='gt')
    dob2 = django_filters.DateFilter(name='dob',
                                     label='Born before',
                                     lookup_expr='lt')