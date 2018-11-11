from django.urls import path
from public.views import AdultProfileView, JuniorProfileView
from members.views.ajax_views import ajax_people, ajax_person, ajax_adults, ajax_password, ajax_postcode, \
    ajax_dob, ajax_chart, ajax_set_pin
from members.views.person_views import PersonDetailView, PersonCreateView, PersonUpdateView, PersonMergeView, \
    PersonLinkView, JuniorCreateView, AddressUpdateView
from members.views.people_views import MembersTableView, JuniorsTableView, ParentsTableView, AllPeopleTableView, \
    GroupPeopleTableView, AppliedTableView, ResignView
from members.views.group_views import GroupAddPersonView, GroupCreateView, GroupTableView

ajax_patterns = [
    path('people/', ajax_people, name='ajax-people'),
    path('person/', ajax_person, name='ajax-person'),
    path('adults/', ajax_adults, name='ajax-adults'),
    path('password/', ajax_password, name='ajax-password'),
    path('postcode/', ajax_postcode, name='ajax-postcode'),
    path('dob/', ajax_dob, name='ajax-dob'),
    path('set_pin/', ajax_set_pin, name='ajax-set-pin'),
    path('chart/', ajax_chart, name='ajax-chart-members', ),
]
person_patterns = [
    path('create/', PersonCreateView.as_view(), name='person-create'),
    path('junior/create/', JuniorCreateView.as_view(), name='person-junior-create'),
    path('create/<int:link>/', PersonCreateView.as_view(), name='person-create-link'),
    path('update/<int:pk>/', PersonUpdateView.as_view(), name='person-update'),
    path('detail/<int:pk>/', PersonDetailView.as_view(), name='person-detail'),
    path('merge/<int:pk>/', PersonMergeView.as_view(), name='person-merge'),
    path('link/<int:pk>/', PersonLinkView.as_view(), name='person-link'),
    path('address/<int:person_id>', AddressUpdateView.as_view(), name='person-address'),

    path('profile/<int:pk>/', AdultProfileView.as_view(edit=False), name='person-profile'),
    path('profile/edit/<int:pk>/', AdultProfileView.as_view(edit=True), name='person-profile-edit'),
    path('junior/profile/<int:pk>/', JuniorProfileView.as_view(edit=False), name='junior-profile'),
    path('junior/profile/edit/<int:pk>/', JuniorProfileView.as_view(edit=True), name='junior-profile-edit'),
]
people_patterns = [
    path('members/', MembersTableView.as_view(), name='members-list'),
    path('juniors/', JuniorsTableView.as_view(), name='juniors-list'),
    path('parents/', ParentsTableView.as_view(), name='parents-list'),
    path('all/', AllPeopleTableView.as_view(), name='all-people-list'),
    path('applied/', AppliedTableView.as_view(), name='applied-list'),
    path('resigned/', ResignView.as_view(), name='people-resign'),
]
group_patterns = [
    path('create/', GroupCreateView.as_view(), name='group-create'),
    path('detail/<int:pk>/', GroupPeopleTableView.as_view(), name='group-detail'),
    path('list/', GroupTableView.as_view(), name='group-list'),
    path('add/person/<int:person_id>/', GroupAddPersonView.as_view(), name='group-add-person'),
]
