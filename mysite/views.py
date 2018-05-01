from django.shortcuts import redirect
from .tasks import addxy


def index_view(request):
    if request.user.is_authenticated:
        return redirect('club_home')
    return redirect('public-home')


def test_celery_view(request):
    addxy.delay(10, 20)
    return redirect('home')
