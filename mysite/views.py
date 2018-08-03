import sys
from django.shortcuts import redirect
from django.template import loader
from django.http.response import HttpResponseServerError
from .tasks import addxy


def index_view(request):
    if request.user.is_authenticated:
        return redirect('club_home')
    return redirect('public-home')


def test_celery_view(request):
    addxy.delay(10, 20)
    return redirect('home')


def custom_500(request):
    t = loader.get_template('500.html')
    typ, value, tb = sys.exc_info()
    path = tb.tb_frame.f_locals['request'].path
    if '/pos/' in path:
        request.session['message'] = "Terminal was restarted because an error occurred."
        return redirect('pos_start')
    context = {}
    return HttpResponseServerError(t.render(context))
