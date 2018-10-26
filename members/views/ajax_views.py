import json
from datetime import date
import logging
from django.http import HttpResponse, JsonResponse, Http404
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import User
from django.db.models import Q
from members.models import Person, Subscription, Settings

stdlogger = logging.getLogger(__name__)


def ajax_people(request):
    """
    Returns a list of people for autocomplete search field
    If id field is sent include the id after the name
    if ?members=true only return paid members
    if ?adults=true only return paid adult members
    """
    if request.is_ajax():
        results = []
        q = request.GET.get('term', '')
        keys = q.split(" ", 1)
        if q.lower() == 'comp':
            results.append({'id': -1, 'value': 'Complimentary'})
        else:
            if len(keys) == 1:
                if q.isdigit():
                    people = Person.objects.filter(pk=q)
                else:
                    people = Person.objects.filter(Q(first_name__istartswith=q) |
                                                   Q(last_name__istartswith=q))
                    if len(people) == 0:
                        people = Person.objects.filter(Q(first_name__istartswith=q[0]) &
                                                       Q(last_name__istartswith=q[1:]))
            else:
                people = Person.objects.filter(first_name__istartswith=keys[0],
                                               last_name__istartswith=keys[1]
                                               )
            if request.GET.get('adults', ""):
                people = people.filter(membership__is_adult=True, state=Person.ACTIVE, sub__paid=True)[:9]
            elif request.GET.get('members', ""):
                people = people.filter(state=Person.ACTIVE, sub__paid=True)
            for person in people:
                dict = {
                    'id': person.id,
                    'value': person.fullname,
                    'age': person.age_for_membership(),
                }
                if request.GET.get('id', ''):
                    dict['value'] += ' (id = {})'.format(person.id)
                results.append(dict)
        return JsonResponse(results, safe=False)
    else:
        data = 'error'
        mimetype = 'application/json'
        return HttpResponse(data, mimetype)


def ajax_adults(request):
    """ return json of all paid adults for bloodhound prefetch """
    if request.is_ajax():
        people = list(Person.objects.filter(membership__is_adult=True, state=Person.ACTIVE, sub__paid=True).values(
            'first_name', 'last_name', 'id'))
        result = []
        for person in people:
            dict = {
                'value': person['first_name'] + ' ' + person['last_name'],
                'id': person['id']
            }
            result.append(dict)
        return JsonResponse(result, safe=False)
    return Http404


def ajax_person(request):
    """ Used for member details lookup """
    if request.is_ajax():
        id = request.GET.get('id', '')
        person = Person.objects.get(pk=id)
        dict = {'name': person.fullname}
        if person.allow_phone:
            dict['mobile'] = person.mobile_phone
            dict['phone'] = person.address.home_phone
        else:
            dict['mobile'] = 'Mobile not shared'
            dict['phone'] = 'Phone not shared'
        dict['email'] = person.email if person.allow_email else 'Email not shared'
        dict['membership'] = person.membership.description
        return JsonResponse(dict)
    return Http404


def ajax_password(request):

    dict = {'authenticated': False,
            'supervisor': False}
    if request.is_ajax():
        id = request.POST.get('person_id', None)
        pin = request.POST.get('pin', None)
        password = request.POST.get('password', None)
        request.session['person_id'] = id
        try:
            person = Person.objects.get(pk=id)
        except Person.DoesNotExist:
            return JsonResponse(dict)

        try:
            user = User.objects.get(pk=person.auth_id)
        except User.DoesNotExist:
            user = None

        authenticated = False
        if pin and person.pin:
            authenticated = check_password(pin, person.pin)
        if not authenticated and user and password:
            authenticated = user.check_password(password)
        if authenticated:
            dict['authenticated'] = True
            if user:
                dict['supervisor'] = True if user.groups.filter(name='Pos').exists() or user.is_staff else False
    return JsonResponse(dict)


def ajax_dob(request):
    """ Validate junior by checking the date of birth """
    if request.is_ajax() and request.method == 'POST':
        id = request.POST.get('person_id', None)
        dob = request.POST.get('dob', None)
        parts = dob.split('/')
        try:
            d = int(parts[0])
            m = int(parts[1])
            y = int(parts[2])
        except ValueError:
            return HttpResponse('Invalid date')
        if y < 40:
            y += 2000
        elif y < 1900:
            y += 1900
        dob_date = date(y, m, d)
        person = Person.objects.get(pk=id)
        if person.dob == dob_date:
            return HttpResponse('OK')
    return HttpResponse('Wrong date of birth')


def ajax_postcode(request):
    """ validate post code & phone for POS PIN reset """
    if request.is_ajax():
        id = request.POST.get('person_id', '')
        person = Person.objects.get(pk=id)
        code = request.POST.get('postcode', '').replace(' ', '').lower()
        phone = request.POST.get('phone', '')
        if person.address.post_code.replace(' ', '').lower() == code:
            if phone == person.mobile_phone.replace(' ', '') or phone == person.address.home_phone.replace(' ', ''):
                return HttpResponse('OK')
            else:
                return HttpResponse('Wrong phone or mobile number')
    return HttpResponse('Wrong post code')


def ajax_set_pin(request):
    """ Set pin from POS """
    if request.is_ajax():
        id = request.POST.get('person_id', '')
        if id:
            person = Person.objects.get(pk=id)
            pin = request.POST.get('pin', '')
            person.set_pin(pin)
            return HttpResponse('Pin set')
    return Http404


def ajax_chart(request):
    error = 'bad request'
    if request.is_ajax():
        year = Settings.current_year()
        chart = request.GET.get('chart', '')
        filter = request.GET.get('filter', '')
        data = {}

        if chart == 'membership':
            set, labels = create_membership_dataset(year, filter, 'green')
            data = {
                'type': 'bar',
                'title': 'Membership by category',
                'labels': labels,
                'datasets': [set],
            }

        elif chart == 'trend':
            set1, labels = create_membership_dataset(year - 2, filter, 'red')
            set2, _ = create_membership_dataset(year - 1, filter, 'blue')
            set3, _ = create_membership_dataset(year, filter, 'green')
            data = {
                'type': 'bar',
                'title': 'Membership by category',
                'labels': labels,
                'datasets': [set1, set2, set3],
            }

        elif chart == 'ages':
            buckets_male, buckets_female, min, max = get_age_buckets()
            data = {
                'type': 'bar',
                'title': 'Juniors age distribution',
                'labels': [i for i in range(min, max)],
                'datasets': [{'data': [buckets_male[i] for i in range(min, max)],
                              'backgroundColor': 'Green',
                              'label': 'Boys'},
                             {'data': [buckets_female[i] for i in range(min, max)],
                              'backgroundColor': '#009688',
                              'label': ' Girls'},
                             ],
                'options': {
                    'scales': {
                        'xAxes': [{'stacked': True}],
                        'yAxes': [{'stacked': True}]
                    }
                }
            }

        if data:
            return JsonResponse(data)
        error = 'Chart type unknown'
    response = JsonResponse({"error": error})
    response.status_code = 404
    return response


def create_membership_dataset(year, filter, color):
    """" Create dataset from a count of Subscription by membership category"""
    counts = Subscription.counts.filter(sub_year=year, active=True, resigned=False, paid=True).order_by(
        'membership__is_adult', '-membership__is_tennis', '-membership__is_playing', 'membership_id')
    if filter:
        if 'tennis' in filter:
            counts = counts.filter(membership__is_tennis=True)
        if 'adults' in filter:
            counts = counts.filter(membership__is_adult=True)
        if 'playing' in filter:
            counts = counts.filter(membership__is_playing=True)
    dataset = {
        'label': str(year),
        'backgroundColor': color,
        'data': [c['count'] for c in counts],
    }
    labels = [c['membership__description'] for c in counts]
    return dataset, labels


def get_age_buckets():
    year = Settings.current_year()
    ids = Subscription.objects.filter(sub_year=year, active=True, resigned=False, paid=True,
                                      membership__is_adult=False).values_list('person_member_id')
    people = Person.objects.filter(id__in=ids)
    buckets_male = [0 for i in range(19)]
    buckets_female = [0 for i in range(19)]
    for p in people:
        if p.gender == 'M':
            buckets_male[p.age(date(year, 5, 1))] += 1
        else:
            buckets_female[p.age(date(year, 5, 1))] += 1
    min = 0
    max = 18
    for i in range(19):
        if buckets_male[i] > 0 or buckets_female[i] > 0:
            if min == 0:
                min = i
            max = i
    return buckets_male, buckets_female, min, max + 1


def lta_figures(year):
    adult_ids = Subscription.objects.filter(sub_year=year, active=True, resigned=False, paid=True,
                                            membership__is_adult=True, membership__is_playing=True
                                            ).values_list('person_member_id')
    adults = Person.objects.filter(id__in=adult_ids)
    adults_male = adults.filter(gender='M').count()
    adults_female = adults.filter(gender='F').count()
    junior_ids = Subscription.objects.filter(sub_year=year, active=True, resigned=False, paid=True,
                                             membership__is_adult=False, membership__is_playing=True
                                            ).values_list('person_member_id')
    mini_date = date(year - 11, 5, 1)
    juniors = Person.objects.filter(id__in=junior_ids)
    minis_male = juniors.filter(gender='M', dob__gt=mini_date).count()
    minis_female = juniors.filter(gender='F', dob__gt=mini_date).count()
    juniors_male = juniors.filter(gender='M', dob__lte=mini_date).count()
    juniors_female = juniors.filter(gender='F', dob__lte=mini_date).count()

    return {'adults_male': adults_male,
            'adults_female': adults_female,
            'adults_total': adults.count(),
            'juniors_male': juniors_male,
            'juniors_female': juniors_female,
            'juniors_total': juniors_male + juniors_female,
            'minis_males': minis_male,
            'minis_females': minis_female,
            'minis_total': minis_male + minis_female,
            }

