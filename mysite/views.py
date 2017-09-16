from django.shortcuts import redirect

def index_view(request):
    if request.user.is_authenticated():
        return redirect('public-home')
    return redirect('http://www.coombewoodltc.co.uk/')



