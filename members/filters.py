from datetime import *
from django.db.models import Q
from .models import Person, Membership, Settings, Subscription, Invoice, InvoiceItem, Payment
import django_filters

def year_choices(withNone = False):
    choices = []
    if withNone:
        choices.append([0, "Not invoiced"])
    year = Settings.current_year()
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


class InvoiceFilter(django_filters.FilterSet):
    class Meta:
        model = Invoice
        fields = ['membership_year','state']

    STATE_CHOICES = Invoice.STATE.choices()

    membership_year = django_filters.ChoiceFilter(name='membership_year',
                                                  label='Year',
                                                  empty_label=None,
                                                  choices=year_choices(withNone=True))
                                   
    state = django_filters.ChoiceFilter(name='state',
                                        label='State',
                                        choices=STATE_CHOICES,
                                        method ='state_filter',
                                        empty_label=None)

    def state_filter(self, queryset, name, value):
        # if value == str(Invoice.STATE.NOT_CANCELLED):
        #     return queryset.filter(~Q(state=Invoice.STATE.CANCELLED.value))
        # elif value == str(Invoice.PENDING_GC):
        #     return queryset.filter(Q(state=Invoice.STATE.UNPAID.value) & ~Q(gocardless_bill_id=""))
        # elif value == str(Invoice.UNPAID):
        #     return queryset.filter(Q(state=Invoice.STATE.UNPAID.value) & Q(gocardless_bill_id=""))
        # else:
        #     return queryset.filter(state=value)
        return queryset.filter(state=value)

class InvoiceItemFilter(django_filters.FilterSet):
    class Meta:
        model = InvoiceItem
        fields = ['item_type', 'paid']

    invoiced = django_filters.ChoiceFilter(name='invoice',
                                            label='Invoice year',
                                            empty_label=None,
                                            method='has_invoice',
                                            choices=year_choices(withNone=True))
   
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
                                    