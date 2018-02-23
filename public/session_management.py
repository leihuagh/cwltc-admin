# During the application process we store data posted from each of the forms
# in session variables
from django.shortcuts import redirect
from members.models import Membership


def add_session_context(context, request):
    """
    Add all session variables to context
    """
    context['person'] = request.session['person']
    context['address'] = request.session['address']
    return context


def clear_session(request):
    """
    Clear session variables
    """
    request.session['person'] = None
    request.session['address'] = None
    request.session['family'] = []
    request.session['posts'] = []


def session_update_post(index, request):
    """
    Save request.POST data in session at index
    """
    posts = request.session['posts']
    request.POST._mutable = True
    request.POST['path'] = request.path
    if index >= len(posts):
        posts.append(request.POST)
    else:
        posts[index] = request.POST
    request.session['posts'] = posts


def session_get_post(index, request):
    """
    Return post data for index else None
    """
    posts = request.session.get('posts', None)
    if posts:
        if index >= 0 and index < len(posts):
            if not (posts[index].get('invalid', False) or posts[index].get('deleted', False)):
                return posts[index]
    return None


def session_last_fullname(index, request):
    """ Return the full name of the last applicant """
    while True:
        index -= 1
        data = session_get_post(index, request)
        if data:
            if data['form_type'] == 'Name':
                return data['first_name'] + " " + data['last_name']
        if index <= 0:
            return 'Name error'


def session_delete_post(index, request):
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


def session_invalidate_post(index, request):
    """
    Invalidate post data for index
    Used when child profile is changed to adult profile or vice versa
    """
    posts = request.session['posts']
    if index < len(posts):
        posts[index]['invalid'] = True
        request.session.modified = True


def session_next_index(index, request):
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


def session_back(index, request):
    """
    Return previous path, skipping deleted records
    """
    posts = request.session['posts']
    while index > 0:
        index -= 1
        if not posts[index].get('deleted', False):
            return posts[index]['path']
    return posts[0]['path']


def session_update_kwargs(view, kwargs):
    """
    Update the forms kwargs with stored POST data if it exists
    """
    data = session_post_data(view)
    if data:
        kwargs.update({'data': data})
    return kwargs


def session_last_index(request):
    """
    return the next free index
    """
    return len(request.session['posts']) - 1


def session_post_data(view):
    """ Return POST data if it exists for a view"""
    if view.request.method == 'GET':
        return session_get_post(view.index, view.request)
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
        form_type = posts[i]['form_type']
        if form_type == 'Name':
            return redirect('public-apply-add', index=i)
    return redirect('public-apply-next')


def build_family(request):
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


def build_children(request):
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
