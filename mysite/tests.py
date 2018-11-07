from django.urls import reverse, resolve
from django.contrib.auth.models import User, AnonymousUser
from django.test import RequestFactory, TestCase
from mixer.backend.django import mixer
from members.models import Settings
from mysite.views import index_view
import pytest

# @pytest.mark.django_db
# class TestHomePage(TestCase):
#
#     @classmethod
#     def setUpClass(cls):
#         super(TestHomePage, cls).setUpClass()
#         mixer.blend(Settings, membership_year=2018)
#         cls.factory = RequestFactory()
#
#     def test_anonymous_user_redirects_to_public_view(self):
#         path = reverse('index')
#         request = self.factory.get(path)
#         request.user = AnonymousUser()
#         response = index_view(request)
#         assert response.status_code == 302
#         assert 'public' in response.url
#
#     def test_user_redirects_to_club_view(self):
#         path = reverse('index')
#         request = self.factory.get(path)
#         request.user = mixer.blend(User)
#         response = index_view(request)
#         assert response.status_code == 302
#         assert 'club' in response.url

@pytest.mark.django_db
def test_anonymous_user_redirects_to_public_view():
    mixer.blend(Settings, membership_year=2018)
    path = reverse('index')
    request = RequestFactory().get(path)
    request.user = AnonymousUser()
    response = index_view(request)
    assert response.status_code == 302
    assert 'public' in response.url

@pytest.mark.django_db
def test_user_redirects_to_club_view():
    mixer.blend(Settings, membership_year=2018)
    path = reverse('index')
    request = RequestFactory().get(path)
    request.user = mixer.blend(User)
    response = index_view(request)
    assert response.status_code == 302
    assert 'club' in response.url