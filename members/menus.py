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

Menu.add_item('side', MenuItem('Dashboard', reverse('home'), icon='fas fa-tachometer-alt'))

Menu.add_item('side', MenuItem("People", None, icon='fas fa-user', children=[
    MenuItem('Members', reverse('members-list'), icon='fas fa-user-check'),
    MenuItem('Juniors', reverse('juniors-list'), icon='fas fa-child'),
    MenuItem('Parents', reverse('parents-list'), icon='fas fa-female'),
    MenuItem('Applications', reverse('applied-list'), icon='fas fa-user-plus'),
    MenuItem('All people', reverse('all-people-list'), icon='fas fa-users'),
    MenuItem('Create adult', reverse('person-create'), icon='fas fa-user'),
    MenuItem('Create junior', reverse('person-junior-create'), icon='fas fa-child'),
]   ))

Menu.add_item("side", MenuItem("Groups", None, icon='fas fa-users', children=[
    MenuItem('List groups', reverse('group-list'), icon='fas fa-list-ul'),
    MenuItem('New group', reverse('group-create'), icon='fas fa-plus'),
    ]))

Menu.add_item("side", MenuItem("Finance", None, icon='fas fa-pound-sign', children=[
    MenuItem('Invoices', reverse('invoice-list'), icon='fas fa-list-ul'),
    MenuItem('Payments', reverse('payment-list'), icon='fas fa-list-ul'),
    ]))

Menu.add_item("side", MenuItem("POS admin", reverse('pos_admin'), icon='fas fa-shopping-cart'))


