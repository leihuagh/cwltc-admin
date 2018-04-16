from django.shortcuts import redirect, render_to_response
from django.template import RequestContext
from .tasks import addxy

def index_view(request):
    if request.user.is_authenticated():
        return redirect('public-home')
    return redirect('http://www.coombewoodltc.co.uk/')


def handler404(request):
    response = render_to_response('404.html', {},
                                  context_instance=RequestContext(request))
    response.status_code = 404
    return response



def handler500(request):
    response = render_to_response('500.html', {},
                                  context_instance=RequestContext(request))
    response.status_code = 500
    return response


def test_celery_view(request):
    addxy.delay(10, 20)
    return redirect('home')