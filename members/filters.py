from datetime import *
from .models import Person, Membership, Settings
import django_filters
from django.forms.widgets import *

def year_choices():
    choices = []
    year = Settings.current().membership_year
    for y in range(year, year-5, -1):
        choices.append([y, str(y)])
    return choices

def members_queryset(juniors):
    if juniors:
        return Membership.objects.filter(is_adult=False)      
    else:
        return Membership.objects.all()

class PersonFilter(django_filters.FilterSet):

    class Meta:
        model = Person
        fields = {'first_name': ['istartswith',],
                  'last_name' : ['istartswith'],
                  } 
  
    first_name = django_filters.CharFilter(lookup_expr='istartswith')
    last_name = django_filters.CharFilter(lookup_expr='istartswith')
    dob1 = django_filters.DateFilter(name='dob',
                                     label='Born after',
                                     lookup_expr='gt')
    dob2 = django_filters.DateFilter(name='dob',
                                     label='Born before',
                                     lookup_expr='lt')
    paid = django_filters.BooleanFilter(name='sub__paid',
                                        label = 'Paid',
                                        lookup_expr='exact'
                                        )
    year = django_filters.ChoiceFilter(name='sub__sub_year',
                                       label='Year',
                                       empty_label=None,
                                       choices=year_choices()
                                      )
    membership = django_filters.ModelChoiceFilter(queryset=Membership.objects.all(),
                                                  required=None,
                                                  label="Membership",
                                                  to_field_name="description",
                                                  empty_label="No filter"
                                                 )

    adult = django_filters.BooleanFilter(name='sub__membership__is_adult',
                                         label='Adult',
                                        )
    playing = django_filters.BooleanFilter(name='sub__membership__is_playing',
                                           label='Playing',
                                          )
    state = django_filters.ChoiceFilter(choices=Person.STATES,
                                        empty_label=None)
    
class JuniorFilter(django_filters.FilterSet):

    class Meta:
        model = Person
        fields = {'first_name': ['istartswith',],
                  'last_name' : ['istartswith'],
                  } 
  
    first_name = django_filters.CharFilter(lookup_expr='istartswith')
    last_name = django_filters.CharFilter(lookup_expr='istartswith')
    dob1 = django_filters.DateFilter(name='dob',
                                     label='Born after',
                                     lookup_expr='gt')
    dob2 = django_filters.DateFilter(name='dob',
                                     label='Born before',
                                     lookup_expr='lt')
    paid = django_filters.BooleanFilter(name='sub__paid',
                                        label = 'Paid',
                                        lookup_expr='exact'
                                        )
    membership = django_filters.ModelChoiceFilter(queryset=Membership.objects.filter(is_adult=False) ,
                                                  required=None,
                                                  label="Membership",
                                                  to_field_name="description",
                                                  empty_label="No filter"
                                                 )
