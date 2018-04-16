from django.views.generic import DetailView, CreateView, UpdateView, ListView, TemplateView, View
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django_tables2 import SingleTableView
from events.models import *
from events.forms import *

EventsList(ListView)
    model=