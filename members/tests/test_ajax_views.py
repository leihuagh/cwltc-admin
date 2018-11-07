import datetime
from django.urls import reverse
from django.test import RequestFactory
from mixer.backend.django import mixer
from members.views.ajax_views import *
import pytest


@pytest.fixture
def user_request(db):
    user = mixer.blend(User)
    request = RequestFactory().get('', {}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    request.user = user
    return request


@pytest.fixture
def search_request(db, request):
    mixer.blend(Settings, membership_year=2018)
    user = mixer.blend(User)
    path = reverse('ajax-people')
    request = RequestFactory().get(path, {'term': request.param}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    request.user = user
    return request


@pytest.fixture
def adults_with_sub(db):
    for i in range(2):
        mixer.blend(Person, first_name='Adult', membership__is_adult=True,
                    membership__description='Full', state=Person.ACTIVE, sub__paid=True)
    return


@pytest.fixture
def junior_with_sub(db):
    person = mixer.blend(Person, first_name='Junior', membership__is_adult=False, state=Person.ACTIVE, sub__paid=True)
    return person


@pytest.mark.parametrize('search_request', ['i s', 'ian', 'ste', 'ist'], indirect=True)
def test_ajax_people_finds_person(search_request, db):
    mixer.blend(Person, first_name='Ian', last_name='Stewart')
    request = search_request
    response = ajax_people(request)
    assert response.status_code == 200
    assert b'Ian Stewart' in response.content


@pytest.mark.parametrize('search_request', ['aaa', 'iii'], indirect=True)
def test_ajax_people_bad_names(search_request, db):
    mixer.blend(Person, first_name='Ian', last_name='Stewart')
    request = search_request
    response = ajax_people(request)
    assert response.status_code == 200
    assert b'Ian Stewart' not in response.content


def test_ajax_paid_adults_returns_adults(user_request, adults_with_sub, junior_with_sub):
    request = user_request
    request.path = reverse('ajax-adults')
    response = ajax_adults(request)
    assert response.status_code == 200
    result = json.loads(response.content)
    assert len(result) == 2
    assert 'Adult' in result[0]['value']
    assert 'Adult' in result[1]['value']


def test_ajax_person_returns_details(db):
    person = mixer.blend(Person, first_name='Ian', last_name='Stewart', allow_phone=True, allow_email=False,
                         address__home_phone='1234', membership__description='Full')
    request = RequestFactory().get(reverse('ajax-person'),
                                   {'id': person.id}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    request.user = mixer.blend(User)
    response = ajax_person(request)
    assert response.status_code == 200
    result = json.loads(response.content)
    assert len(result) == 5
    assert result['name'] == 'Ian Stewart'
    assert result['phone'] == '1234'
    assert result['membership'] == 'Full'
    assert 'not shared' in result['email']


def test_ajax_password_pin_correct(db):
    person = mixer.blend(Person)
    person.set_pin(1234)
    request = RequestFactory().post(reverse('ajax-password'),
                                   {'person_id': person.id, 'pin': 1234},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    request.user = mixer.blend(User)
    request.session = {}
    response = ajax_password(request)
    assert response.status_code == 200
    result = json.loads(response.content)
    assert result['authenticated'] == True


def test_ajax_password_pin_wrong(db):
    person = mixer.blend(Person)
    person.set_pin(4567)
    request = RequestFactory().post(reverse('ajax-password'),
                                   {'person_id': person.id, 'pin': 1234},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    request.user = mixer.blend(User)
    request.session = {}
    response = ajax_password(request)
    assert response.status_code == 200
    result = json.loads(response.content)
    assert result['authenticated'] == False


def test_ajax_password_password_correct(db):
    user = mixer.blend(User)
    user.set_password('abc123')
    user.save()
    person = mixer.blend(Person, auth_id=user.id)
    request = RequestFactory().post(reverse('ajax-password'),
                                   {'person_id': person.id, 'password': 'abc123'},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    request.user = mixer.blend(User)
    request.session = {}
    response = ajax_password(request)
    assert response.status_code == 200
    result = json.loads(response.content)
    assert result['authenticated'] == True

def test_ajax_password_password_wrong(db):
    user = mixer.blend(User)
    user.set_password('abc123')
    user.save()
    person = mixer.blend(Person, auth_id=user.id)
    request = RequestFactory().post(reverse('ajax-password'),
                                   {'person_id': person.id, 'password': 'abc'},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    request.user = mixer.blend(User)
    request.session = {}
    response = ajax_password(request)
    assert response.status_code == 200
    result = json.loads(response.content)
    assert result['authenticated'] == False


def test_ajax_dob_returns_dob(db, junior_with_sub):
    person = junior_with_sub
    person.dob = datetime.date(2010, 12, 25)
    person.save()
    request = RequestFactory().post(reverse('ajax-dob'),
                                   {'person_id': person.id, 'dob': '25/12/10'},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    request.user = mixer.blend(User)
    response = ajax_dob(request)
    assert response.status_code == 200
    assert response.content == b'OK'


def test_ajax_postcode_correct(db):
    person = mixer.blend(Person, mobile_phone='1234', address__home_phone='5678', address__post_code='KT8 2LA')
    request = RequestFactory().post(reverse('ajax-postcode'),
                                   {'person_id': person.id,
                                    'postcode': 'kt82la',
                                    'phone': 1234},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    request.user = mixer.blend(User)
    response = ajax_postcode(request)
    assert response.status_code == 200
    assert response.content == b'OK'


def test_ajax_postcode_wrongphone(db):
    person = mixer.blend(Person, mobile_phone='1234', address__home_phone='5678', address__post_code='KT8 2LA')
    request = RequestFactory().post(reverse('ajax-postcode'),
                                   {'person_id': person.id,
                                    'postcode': 'kt82la',
                                    'phone': 9999},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    request.user = mixer.blend(User)
    response = ajax_postcode(request)
    assert response.status_code == 200
    assert response.content != b'OK'


def test_ajax_set_pin_passes(db):
    person = mixer.blend(Person, mobile_phone='1234', address__home_phone='5678', address__post_code='KT8 2LA')
    request = RequestFactory().post(reverse('ajax-set-pin'),
                                   {'person_id': person.id},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    request.user = mixer.blend(User)
    response = ajax_set_pin(request)
    assert response.status_code == 200
    assert response.content == b'Pin set'


def test_ajax_set_pin_fails_bad_person(db):
    request = RequestFactory().post(reverse('ajax-set-pin'),
                                   {'person_id': 9999},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    request.user = mixer.blend(User)
    response = ajax_set_pin(request)
    assert response.status_code == 404


