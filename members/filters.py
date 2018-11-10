from datetime import datetime, timedelta
from django.db.models import Q
from django.utils import timezone
from .models import Person, Membership, Settings, Subscription, Invoice, InvoiceItem, Payment
import django_filters
from tempus_dominus.widgets import DatePicker


def year_choices(withNone=False):
    choices = []
    if withNone:
        choices.append([0, "Not invoiced"])
    year = Settings.current_year()
    #TODO fix dependcy on settings
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
    

    year = django_filters.ChoiceFilter(field_name='sub_year',
                                       label='Year',
                                       empty_label=None,
                                       choices=year_choices()
                                      )

    paid = django_filters.ChoiceFilter(field_name='paid',
                                       label='Subscription',
                                       choices=PAID_CHOICES,
                                       empty_label='Paid & unpaid'
                                      )

    membership = django_filters.ModelChoiceFilter(queryset=Membership.objects.filter(),
                                                  required=None,
                                                  label="Membership",
                                                  to_field_name="description",
                                                  empty_label="No filter"
                                                 )


class JuniorFilter(SubsBaseFilter):

    dob1 = django_filters.DateFilter(field_name='person_member__dob',
                                     label='Born after',
                                     lookup_expr='gt',
                                     widget=DatePicker(options={'format': 'DD/MM/YYYY'})
                                     )
    dob2 = django_filters.DateFilter(field_name='person_member__dob',
                                     label='Born before',
                                     lookup_expr='lt',
                                     widget=DatePicker(options={'format': 'DD/MM/YYYY'})
                                     )
    membership = django_filters.ModelChoiceFilter(queryset=Membership.objects.filter(is_adult=False),
                                                  required=None,
                                                  label="Membership",
                                                  to_field_name="description",
                                                  empty_label="Juniors & cadets"
                                                 )


class SubsFilter(SubsBaseFilter):

    adult = django_filters.BooleanFilter(field_name='membership__is_adult',
                                         label='Adult',
                                        )
    playing = django_filters.BooleanFilter(field_name='membership__is_playing',
                                           label='Playing',
                                          )
    state = django_filters.ChoiceFilter(field_name='person_member__state',
                                        label='State',
                                        choices=Person.STATES,
                                        empty_label=None)


class InvoiceFilter(django_filters.FilterSet):
    class Meta:
        model = Invoice
        fields = ['membership_year', 'state']


    membership_year = django_filters.ChoiceFilter(field_name='membership_year',
                                                  label='Year',
                                                  empty_label=None,
                                                  choices=year_choices(withNone=False))

    state_choices = [(-1, 'All not cancelled')] + Invoice.STATES
    state = django_filters.ChoiceFilter(field_name='state',
                                        label='State',
                                        choices=state_choices,
                                        method ='state_filter',
                                        empty_label=None)

    pending = django_filters.BooleanFilter(field_name='pending',
                                           label='Pending',
                                           )

    older = django_filters.Filter(field_name='older',
                                  label='Age >=',
                                  method='older_filter')

    younger = django_filters.Filter(field_name='younger',
                                    label='Age <',
                                    method='younger_filter')

    def older_filter(self, queryset, name, value):
        default_timezone = timezone.get_default_timezone()
        before_date = timezone.make_aware(datetime.now() - timedelta(days=int(value)), default_timezone)
        return queryset.filter(creation_date__lte=before_date)

    def younger_filter(self, queryset, name, value):
        default_timezone = timezone.get_default_timezone()
        after_date = timezone.make_aware(datetime.now() - timedelta(days=int(value)), default_timezone)
        return queryset.filter(creation_date__gt=after_date)

    def state_filter(self, queryset, name, value):
        if value == '-1':
            return queryset.filter(~Q(state=Invoice.STATE.CANCELLED.value))
        return queryset.filter(state=value)


class InvoiceItemFilter(django_filters.FilterSet):
    class Meta:
        model = InvoiceItem
        fields = ['item_type', 'paid']

    invoiced = django_filters.ChoiceFilter(field_name='invoice',
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
        fields = ['membership_year', 'type', 'state']

    membership_year = django_filters.ChoiceFilter(field_name='membership_year',
                                                  label='Year',
                                                  empty_label=None,
                                                  choices=year_choices()
                                                  )
    type = django_filters.ChoiceFilter(field_name='type',
                                       label='Type',
                                       empty_label='All',
                                       choices=Payment.TYPES
                                       )
    state = django_filters.ChoiceFilter(field_name='state',
                                       label='State',
                                       empty_label='All',
                                   choices=Payment.STATES
                                       )
