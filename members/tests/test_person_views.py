from django.urls import reverse
from mixer.backend.django import mixer
from members.models import Person, Settings
import pytest


@pytest.fixture()
def settings(db):
    mixer.blend(Settings, membership_year=2018)


@pytest.mark.parametrize('path', ['person-create', 'person-junior-create'])
def test_person_create_view_status(settings, admin_client, path):
    response = admin_client.get(reverse('path'))
    assert response.status_code == 200


@pytest.mark.parametrize('path', ['person-create', 'person-junior-create'])
def test_person_create_view_redirects_not_staff(settings, client, path):
    response = client.get(reverse('path'))
    assert response.status_code == 302
    assert 'login' in response.url


@pytest.mark.parametrize('path', ['person-update', 'person-detail', 'person-merge', 'person-link'])
def test_person_view_status(settings, admin_client, path):
    person = mixer.blend(Person)
    response = admin_client.get(reverse(path, kwargs={'pk': person.id}))
    assert response.status_code == 200


@pytest.mark.parametrize('path', ['person-update', 'person-detail', 'person-merge', 'person-link'])
def test_person_view_redirects_not_staff(settings, client, path):
    person = mixer.blend(Person)
    response = client.get(reverse(path, kwargs={'pk': person.id}))
    assert response.status_code == 302
    assert 'login' in response.url
