from django.urls import reverse

from menu import Menu, MenuItem

def profile_title(request):
    """
    Return a personalized title for our profile menu item
    """
    # we don't need to check if the user is authenticated because our menu
    # item will have a check that does that for us
    name = request.user.get_full_name() or request.user

    return "%s's Profile" % name

Menu.add_item('main', MenuItem('Dashboard', reverse('home')))

Menu.add_item("main", MenuItem("People", None, children=[
    MenuItem('Members', reverse('members-list')),
    MenuItem('Juniors', reverse('juniors-list')),
    MenuItem('Parents', reverse('parents-list')),
    MenuItem('Applications', reverse('applied-list')),
    MenuItem('All people', reverse('all-people-list')),
]   ))

Menu.add_item("main", MenuItem("Groups", None, children=[
    MenuItem('List groups', reverse('group-list')),
    MenuItem('New group', reverse('group-create')),
    ]))


