from enum import Enum
from django.shortcuts import redirect
from members.models import Membership

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


def update_data(index, request, cleaned_data):
    """
    Save cleaned data in session at index
    """
    posts = request.session['posts']
    cleaned_data['path'] = request.path
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
    delete the next 1 or 2 records ( contact(adults) and profile) too
    """
    posts = request.session['posts']
    if index < len(posts):
        posts[index]['deleted'] = True
        index += 1
        if index < len(posts):
            if posts[index]['form_type'] == 'Contact':
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


def last_fullname(index, request):
    """ Return the full name of the last applicant """
    while True:
        index -= 1
        data = get_data(index, request)
        if data:
            if data['form_type'] == 'Name':
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
        if not (posts[i].get('deleted', False) or posts[i].get('invalid', False)):
            break
    if i < len(posts) - 1:
        if posts[i]['form_type'] == 'Name':
            return redirect('public-apply-add', index=i)
    return redirect('public-apply-next')


def first_child_profile(index, request):
    """ Return data for the first child profile in the session """
    posts = request.session['posts']
    i = 1
    while i < index:
        if not (posts[i].get('deleted', False) or posts[i].get('invalid', False)):
            if posts[i]['form_type'] == 'Child':
                return posts[i]
        i += 1
    return None


def get_family(request):
    """
    Return a list of name and membership for each family member
    """
    posts = request.session['posts']
    i = 0
    family = []
    while i < len(posts) - 1:
        if not posts[i].get('deleted', False):
            form_type = posts[i]['form_type']
            if form_type == "Name":
                name = posts[i]['first_name'] + " " + posts[i]['last_name']
                i += 1
                form_type = posts[i]['form_type']
            if form_type == 'Contact':
                i += 1
                form_type = posts[i]['form_type']
            if form_type in ['Adult', 'Child']:
                membership_id = posts[i]['membership_id']
                membership = Membership.objects.get(pk=membership_id).description
                family.append([name, membership])
                i += 1
            else:
                family.append([name, "Parent or guardian"])
        else:
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
        if posts[i]['form_type'] == "Name":
            name = posts[i]['first_name'] + " " + posts[i]['last_name']
            i += 1
            if posts[i]['form_type'] == "Child":
                if children != "":
                    children += ", "
                children += name
            i += 1
        else:
            i += 1
    return children
