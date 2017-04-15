from datetime import *
from django.db.models import Q
from .models import Person, Membership, Settings, Subscription, Invoice, InvoiceItem, Payment
import django_filters

def year_choices():
    choices = []
    year = Settings.current().membership_year
    for y in range(year, year-5, -1):
        choices.append([y, str(y)])
    return choices

class SubsBaseFilter(django_filters.FilterSet):

    class Meta:
        model = Subscription
        fields = {'person_member__email':['icontains']}
                  
    PAID_CHOICES = (
        (False, "Not paid"),
        (True, "Paid")
        )
    

    year = django_filters.ChoiceFilter(name='sub_year',
                                       label='Year',
                                       empty_label=None,
                                       choices=year_choices()
                                      )
    
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
                                     lookup_expr='gt'
                                     )
    dob2 = django_filters.DateFilter(name='person_member__dob',
                                     label='Born before',
                                     lookup_expr='lt'
                                     )
    membership = django_filters.ModelChoiceFilter(queryset=Membership.objects.filter(is_adult=False),
                                                  required=None,
                                                  label="Junior membership",
                                                  to_field_name="description",
                                                  empty_label="Juniors & cadets"
                                                 )


class SubsFilter(SubsBaseFilter):

    adult = django_filters.BooleanFilter(name='membership__is_adult',
                                         label='Adult',
                                        )
    playing = django_filters.BooleanFilter(name='membership__is_playing',
                                           label='Playing',
                                          )
    state = django_filters.ChoiceFilter(name='person_member__state',
                                        label='State',
                                        choices=Person.STATES,
                                        empty_label=None)

def inv_year_choices():
    choices = [[0, 'Not invoiced']]
    year = Settings.current().membership_year
    for y in range(year, year-5, -1):
        choices.append([y, str(y)])
    return choices


class InvoiceFilter(django_filters.FilterSet):
    class Meta:
        model = Invoice
        fields = ['membership_year','state']

    STATE_CHOICES = (
        (Invoice.PAID_AND_UNPAID, 'Paid & unpaid'),
        (Invoice.UNPAID, 'Unpaid'),
        (Invoice.PAID_IN_FULL, 'Paid'),
        (Invoice.CANCELLED, 'Cancelled')
        )

    membership_year = django_filters.ChoiceFilter(name='membership_year',
                                                  label='Year',
                                                  empty_label=None,
                                                  choices=inv_year_choices())
                                   
    state = django_filters.ChoiceFilter(name='state',
                                        label='State',
                                        choices=STATE_CHOICES,
                                        method ='state_filter',
                                        empty_label=None)

    def state_filter(self, queryset, name, value):
        if value == str(Invoice.PAID_AND_UNPAID):
            return queryset.filter(Q(state=Invoice.PAID_IN_FULL) | Q(state=Invoice.UNPAID))        
        else:
            return queryset.filter(state=value)


class InvoiceItemFilter(django_filters.FilterSet):
    class Meta:
        model = InvoiceItem
        fields = ['item_type', 'paid']

    invoiced = django_filters.ChoiceFilter(name='invoice',
                                            label='Invoiced',
                                            empty_label=None,
                                            method='has_invoice',
                                            choices=year_choices())
   
    #membership_year = django_filters.ChoiceFilter(name='invoice__membership_year',
    #                                              label='Year',
    #                                              empty_label=None,
    #                                              choices=SubsBaseFilter.year_choices())

    def has_invoice(self, queryset, name, value):
        if value == '0':
            return queryset.filter(invoice__isnull=True)
        else:
            return queryset.filter(invoice__membership_year=value)
     
            
                                            
class PaymentFilter(django_filters.FilterSet):
    class Meta:
        model = Payment
        fields = ['membership_year', 'type']

    membership_year = django_filters.ChoiceFilter(name='membership_year',
                                                  label='Year',
                                                  empty_label=None,
                                                  choices=year_choices()
                                                  )
    type = django_filters.ChoiceFilter(name='type',
                                       label='Type',
                                       empty_label='All',
                                       choices=Payment.TYPES
                                       )
                                    