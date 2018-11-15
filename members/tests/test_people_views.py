from django.urls import reverse
from mixer.backend.django import mixer
from members.models import Person, Settings, Subscription
import pytest

@pytest.fixture()
def settings(db):
    mixer.blend(Settings, membership_year=2018)

@pytest.fixture
def members(db):
    # 10 adult members
    for i in range(10):
        mixer.blend(Subscription, active=True, sub_year=2018, paid=True,
                    membership__description='Full', person_member__first_name='Adult-member')
    # 5 juniors with 5 parents
    for i in range(5):
        mixer.blend(Subscription, active=True, sub_year=2018, paid=True,
                    membership__description='Junior', membership__is_adult=False,
                    person_member__first_name='Junior-member',
                    person_member__linked__first_name='Parent')
    # 1 adult applicant with 1 linked junior
    mixer.blend(Person, state=Person.APPLIED, first_name='Applied-1',
                linked__state=Person.APPLIED, linked__first_name='Applied-2')


def test_members_list_view(settings, admin_client, members):
    response = admin_client.get(reverse('members-list'))
    assert response.status_code == 200
    assert b'of 15 rows' in response.content
    assert b'Adult-member' in response.content


def test_juniors_list_view(settings, admin_client, members):
    response = admin_client.get(reverse('juniors-list'))
    assert response.status_code == 200
    assert b'of 5 rows' in response.content
    assert b'Junior-member' in response.content


def test_parents_list_view(settings, admin_client, members):
    response = admin_client.get(reverse('parents-list'))
    assert response.status_code == 200
    assert b'of 5 rows' in response.content
    assert b'Parent' in response.content


def test_applied_list_view(settings, admin_client, members):
    response = admin_client.get(reverse('applied-list'))
    assert response.status_code == 200
    assert b'Applied-1' in response.content
    assert b'Applied-2' in response.content


def test_all_people_list_view(settings, admin_client, members):
    response = admin_client.get(reverse('all-people-list'))
    assert response.status_code == 200
    assert b'of 22 rows' in response.content

