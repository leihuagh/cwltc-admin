import logging
from django.views.generic import TemplateView


stdlogger = logging.getLogger(__name__)

class ChartMembers(TemplateView):
    template_name = 'members/charts.html'

