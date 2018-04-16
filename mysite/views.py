from django.shortcuts import redirect, render_to_response
from django.template import RequestContext
from .tasks import addxy

def index_view(request):
    if request.user.is_authenticated():
        return redirect('public-home')
    return redirect('http://www.coombewoodltc.co.uk/')


def test_celery_view(request):
    addxy.delay(10, 20)
    return redirect('home')