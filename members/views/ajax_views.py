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


def ajax_person(request):
    """ Used for member details lookup """
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
    dict['email'] = 'Email not shared'
    dict['membership'] = person.membership.description
    return JsonResponse(dict)


def ajax_password(request):
    id = request.POST.get('person_id', None)
    pin = request.POST.get('pin', None)
    password = request.POST.get('password', None)
    dict = {'authenticated': False,
            'supervisor': False}
    if not id:
        raise Http404
    request.session['person_id'] = id
    try:
        person = Person.objects.get(pk=id)
    except Person.DoesNotExist:
        raise Http404
    try:
        user = User.objects.get(pk=person.auth_id)
    except User.DoesNotExist:
        user = None
    if pin and check_password(pin, person.pin) or password and user.check_password(password):
        dict['authenticated'] = True
        dict['supervisor'] = True if (user and user.groups.filter(name='Pos').exists()) or user.is_staff else False
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
    id = request.POST.get('person_id', '')
    person = Person.objects.get(pk=id)
    pin = request.POST.get('pin', '')
    person.set_pin(pin)
    return HttpResponse('Pin set')


def ajax_chart_members(request):
    year = Settings.current_year()
    set1, labels = create_dataset(year - 2, 'red')
    set2, _ = create_dataset(year - 1, 'green')
    set3, _ = create_dataset(year, 'blue')
    data = {
        'type': 'bar',
        'title': 'Membership by category',
        'labels': labels,
        'datasets': [set1, set2, set3],
    }
    return JsonResponse(data)


# def ajax_chart_members3(request):
#     year = Settings.current_year()
#     counts1 = Subscription.counts.filter(sub_year=year, active=True, resigned=False, paid=True).order_by(
#         'membership__is_adult', '-membership__is_tennis', '-membership__is_playing')
#     labels = [c['membership__description'] for c in counts]
#     values = [c['count'] for c in counts]
#     data = {
#         'type': 'bar',
#         'name': 'Membership numbers',
#         'labels': labels,
#         'values': values,
#     }
#     return JsonResponse(data)

def create_dataset(year, color):
    counts = Subscription.counts.filter(sub_year=year, active=True, resigned=False, paid=True).order_by(
        'membership__is_adult', '-membership__is_tennis', '-membership__is_playing', 'membership_id')
    dataset =  {
        'label': str(year),
        'backgroundColor': color,
        'data': [c['count'] for c in counts],
    }
    labels = [c['membership__description'] for c in counts]
    return dataset, labels