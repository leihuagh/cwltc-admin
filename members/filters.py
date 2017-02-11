from datetime import *
from .models import Person, Membership, Settings, Subscription
import django_filters
from django.forms.widgets import *

def year_choices():
    choices = []
    year = Settings.current().membership_year
    for y in range(year+1, year-5, -1):
        choices.append([y, str(y)])
    return choices

PAID_CHOICES = (
    (False, "Not paid"),
    (True, "Paid")
    )

class SubsBaseFilter(django_filters.FilterSet):

    class Meta:
        model = Subscription
        fields = {
                  'person_member__email':['icontains']}
  
    first_name = django_filters.CharFilter(name='person_member__first_name',
                                           lookup_expr='istartswith',
                                           label = 'First name starts'
                                           )
    last_name = django_filters.CharFilter(name='person_member__last_name',
                                          lookup_expr='istartswith',
                                          label='Last name starts'
                                          )

    membership = django_filters.ModelChoiceFilter(queryset=Membership.objects.filter(),
                                                required=None,
                                                label="Membership",
                                                to_field_name="description",
                                                empty_label="No filter"
                                                )
    paid = django_filters.ChoiceFilter(name='paid',
                                       label = 'Subscription',
                                       choices=PAID_CHOICES,
                                       empty_label='Paid & unpaid'
                                       )
                                     
class JuniorFilter(SubsBaseFilter):


    dob1 = django_filters.DateFilter(name='person_member__dob',
                                     label='Born after',
                                     lookup_expr='gt')
    dob2 = django_filters.DateFilter(name='person_member__dob',
                                     label='Born before',
                                     lookup_expr='lt')
    membership = django_filters.ModelChoiceFilter(queryset=Membership.objects.filter(is_adult=False),
                                                  required=None,
                                                  label="Junior membership",
                                                  to_field_name="description",
                                                  empty_label="Juniors & cadets"
                                                 )
class SubsFilter(SubsBaseFilter):

    year = django_filters.ChoiceFilter(name='sub_year',
                                       label='Year',
                                       empty_label=None,
                                       choices=year_choices()
                                    )

    adult = django_filters.BooleanFilter(name='membership__is_adult',
                                         label='Adult',
                                        )
    playing = django_filters.BooleanFilter(name='membership__is_playing',
                                           label='Playing',
                                          )
    state = django_filters.ChoiceFilter(name='person_member__state',
                                        choices=Person.STATES,
                                        empty_label=None)
