from enum import Enum
from django.shortcuts import redirect
from members.models import Membership
from .forms import *

# During the application process we store data posted from each of the forms
# in session variables

class ApplicationType(Enum):
    ADULT_MEMBER = 1
    CHILD_MEMBER = 2
    NON_MEMBER = 3


def clear(request):
    """ Clear session variables """
    request.session['person'] = None
    request.session['address'] = None
    request.session['family'] = []
    request.session['posts'] = []
    request.session['app_type'] = None


def start_adult_application(request):
    clear(request)
    request.session['app_type'] = ApplicationType.ADULT_MEMBER


def start_child_application(request):
    clear(request)
    request.session['app_type'] = ApplicationType.CHILD_MEMBER


def start_non_member_application(request):
    clear(request)
    request.session['app_type'] = ApplicationType.NON_MEMBER


def exists(request):
    return request.session.get('app_type', None) is not None


def is_adult_application(request):
    return _test_application(request, ApplicationType.ADULT_MEMBER)


def is_child_application(request):
    return _test_application(request,ApplicationType.CHILD_MEMBER)


def is_non_member_application(request):
    return _test_application(request,ApplicationType.NON_MEMBER)


def _test_application(request, app_type):
    try:
        return request.session['app_type'] == app_type
    except KeyError:
        return False


def add_to_context(context, request):
    """
    Add session variables to context
    """
    context['person'] = request.session['person']
    context['address'] = request.session['address']
    return context


def update_data(index, request, form, form2=None):
    """
    Save cleaned data in session at index
    """
    posts = request.session['posts']
    if form2:
        cleaned_data = {**form.cleaned_data, **form2.cleaned_data}
    else:
        cleaned_data = form.cleaned_data
    cleaned_data['path'] = request.path
    cleaned_data['form_class'] = form.__class__.__name__
    if index >= len(posts):
        posts.append(cleaned_data)
    else:
        posts[index] = cleaned_data
    request.session['posts'] = posts


def get_data(index, request):
    """
    Return cleaned_data for index else None
    """
    posts = request.session.get('posts', None)
    if posts:
        if index >= 0 and index < len(posts):
            if not (posts[index].get('invalid', False) or posts[index].get('deleted', False)):
                return posts[index]
    return None


def delete_data(index, request):
    """
    Delete post data for index
    If it is not the last one in the list,
    delete the next 1 record (junior profile) or 2 records ( contact/membership(adults) and adult profile) too
    """
    posts = request.session['posts']
    if index < len(posts):
        posts[index]['deleted'] = True
        index += 1
        if index < len(posts):
            if is_membership_form(posts[index]):
                posts[index]['deleted'] = True
                index += 1
            if index < len(posts):
                posts[index]['deleted'] = True
        request.session.modified = True


def invalidate_data(index, request):
    """
    Invalidate post data for index
    Used when child profile is changed to adult profile or vice versa
    """
    posts = request.session['posts']
    if index < len(posts):
        posts[index]['invalid'] = True
        if is_membership_form(posts[index]):
            index += 1
            if index < len(posts):
                posts[index]['invalid'] = True
        request.session.modified = True

def last_index(request):
    """
    return the next free index
    """
    return len(request.session['posts']) - 1


def next_index(index, request):
    """
    Return next index, skipping deleted records
    """
    posts = request.session['posts']
    i = index
    while i + 1 < len(posts):
        i += 1
        if not posts[i].get('deleted', False):
            return i
    return len(posts)


def back(index, request):
    """
    Return previous path, skipping deleted records
    """
    posts = request.session['posts']
    while index > 0:
        index -= 1
        if not posts[index].get('deleted', False):
            return posts[index]['path']
    return posts[0]['path']


def is_name_form(data):
    return data['form_class'] in [NameForm.__name__, FamilyMemberForm.__name__]


def is_membership_form(data):
    return data['form_class'] in [AdultMembershipForm.__name__, AdultContactForm.__name__]


def is_profile_form(data):
    return data['form_class'] in [AdultProfileForm.__name__, JuniorProfileForm.__name__]


def is_adult_profile(data):
    return data['form_class'] == AdultProfileForm.__name__


def is_junior_profile(data):
    return data['form_class'] == JuniorProfileForm.__name__


def is_valid(data):
    return None if not data else not (data.get('deleted', False) or data.get('invalid', False))


def last_fullname(index, request):
    """ Return the full name of the last applicant """
    while True:
        index -= 1
        data = get_data(index, request)
        if is_valid(data):
            if is_name_form(data):
                return data['first_name'] + " " + data['last_name']
        if index <= 0:
            return 'Name error'


def update_kwargs(view, kwargs):
    """
    Update the forms kwargs with stored POST data if it exists
    """
    data = post_data(view)
    if data:
        kwargs.update({'data': data})
    return kwargs


def post_data(view):
    """ Return POST data if it exists for a view"""
    if view.request.method == 'GET':
        return get_data(view.index, view.request)
    return None


def redirect_next(index, request):
    """ Redirect to form if data exists else to next action form """
    posts = request.session['posts']
    i = index
    while i < len(posts) - 1:
        i += 1
        if is_valid(posts[i]):
            break
    if i < len(posts) - 1:
        if is_name_form(posts[i]):
            return redirect('public-apply-add', index=i)
    return redirect('public-apply-next')


def first_child_profile(index, request):
    """ Return data for the first child profile in the session """
    posts = request.session['posts']
    i = 1
    while i < index:
        if is_valid(posts[i]):
            if posts[i]['form_class'] == JuniorProfileForm.__name__:
                return posts[i]
        i += 1
    return None


def get_family(request):
    """
    Return a list of name and membership for each family member
    """
    family = []
    if exists(request):
        posts = request.session['posts']
        i = 1
        # first entries can be adult + membership + profile OR parent + child
        name = posts[0]['first_name'] + " " + posts[0]['last_name']
        if is_membership_form(posts[1]):
            membership = Membership.objects.get(pk=posts[1]['membership_id']).description
            i = 3
        else:
            membership = 'Parent or guardian'
            i = 2
        family.append([name, membership])
        while i < len(posts):
            if is_valid(posts[i]):
                if is_name_form(posts[i]):
                    name = posts[i]['first_name'] + " " + posts[i]['last_name']
                elif is_membership_form(posts[i]) or is_junior_profile(posts[i]):
                    membership = Membership.objects.get(pk=posts[i]['membership_id']).description
                    family.append([name, membership])
            i += 1
    return family


def get_children(request):
    """
    Return a string of comma separated child names (if any)
    """
    posts = request.session['posts']
    i = 1
    children = ""
    while i < len(posts) - 1:
        if is_valid(posts[i]):
            if is_name_form(posts[i]):
                name = posts[i]['first_name'] + " " + posts[i]['last_name']
                i += 1
                if is_junior_profile(posts[i]):
                    if children != "":
                        children += ", "
                    children += name
        i += 1
    return children
