from django.urls import path
from .views import *

app_name = 'diary'
urlpatterns = [
    path('', WeekNowView.as_view(), name='week_now'),
    path('week/<date>/', WeekView.as_view(), name='week'),
    path('create/<date>/<time>/<int:court>/', BookingCreateView.as_view(), name='create'),
    path('update/<int:pk>/', BookingUpdateView.as_view(), name='update'),
    path('list/', BookingListView.as_view(), name='list'),
]