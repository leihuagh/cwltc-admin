import datetime
import re
from django.utils.formats import get_format, datetime_safe
from django.forms.widgets import Widget, Select, SelectDateWidget
from django.utils.dates import MONTHS
from django.utils.safestring import mark_safe
from django.conf import settings

__all__ = ('MonthYearWidget',)

#RE_DATE = re.compile(r'(\d{4})-(\d\d?)-(\d\d?)$')
RE_DATE = re.compile(r'(\d\d?)/(\d\d?)/(\d{4})$')

# class MonthYearWidget(Widget):
#     """
#     A Widget that splits date input into two <select> boxes for month and year,
#     with 'day' defaulting to the first of the month.
#
#     Based on SelectDateWidget, in
#
#     django/trunk/django/forms/extras/widgets.py
#     https://djangosnippets.org/snippets/1688/
#
#     Note date format must be d/m/yyyy
#
#     """
#     none_value = (0, '---')
#     month_field = '%s_month'
#     year_field = '%s_year'
#
#     def __init__(self, attrs=None, years=None, required=True):
#         # years is an optional list/tuple of years to use in the "year" select box.
#         self.attrs = attrs or {}
#         self.required = required
#         if years:
#             self.years = years
#         else:
#             this_year = datetime.date.today().year
#             self.years = range(this_year, this_year+10)
#
#     def render(self, name, value, attrs=None):
#         try:
#             year_val, month_val = value.year, value.month
#         except AttributeError:
#             year_val = month_val = None
#             if isinstance(value, basestring):
#                 match = RE_DATE.match(value)
#                 if match:
#                     day_val, month_val, year_val = [int(v) for v in match.groups()]
#
#         output = []
#
#         if 'id' in self.attrs:
#             id_ = self.attrs['id']
#         else:
#             id_ = 'id_%s' % name
#
#         month_choices = MONTHS.items()
#         #if not (self.required and month_val):
#         #    month_choices.append(self.none_value)
#         month_choices.sort()
#         local_attrs = self.build_attrs(id=self.month_field % id_)
#         s = Select(choices=month_choices)
#         select_html = s.render(self.month_field % name, month_val, local_attrs)
#         output.append(select_html)
#
#         year_choices = [(i, i) for i in self.years]
#         #if not (self.required and year_val):
#         #    year_choices.insert(0, self.none_value)
#         local_attrs['id'] = self.year_field % id_
#         s = Select(choices=year_choices)
#         select_html = s.render(self.year_field % name, year_val, local_attrs)
#         output.append(select_html)
#
#         return mark_safe(u'\n'.join(output))
#
#     def id_for_label(self, id_):
#         return '%s_month' % id_
#     id_for_label = classmethod(id_for_label)
#
#     def value_from_datadict(self, data, files, name):
#         y = data.get(self.year_field % name)
#         m = data.get(self.month_field % name)
#         if y == m == "0":
#             return None
#         if y and m:
#             temp =  datetime.date(int(y), int(m), 1).strftime(
#                 settings.DATE_INPUT_FORMATS[0]
#                 )
#             return temp
#         return data.get(name, None)


class MySelectDate(SelectDateWidget):

    def get_context(self, name, value, attrs):
        context = super(SelectDateWidget, self).get_context(name, value, attrs)
        date_context = {}
        year_choices = [(i, i) for i in self.years]
        if self.is_required is False:
            year_choices.insert(0, self.year_none_value)
        year_attrs = context['widget']['attrs'].copy()
        year_name = self.year_field % name
        year_attrs['id'] = 'id_%s' % year_name
        date_context['year'] = self.select_widget(attrs, choices=year_choices).get_context(
            name=year_name,
            value=context['widget']['value']['year'],
            attrs=year_attrs,
        )
        month_choices = list(self.months.items())
        if self.is_required is False:
            month_choices.insert(0, self.month_none_value)
        month_attrs = context['widget']['attrs'].copy()
        month_name = self.month_field % name
        month_attrs['id'] = 'id_%s' % month_name
        date_context['month'] = self.select_widget(attrs, choices=month_choices).get_context(
            name=month_name,
            value=context['widget']['value']['month'],
            attrs=month_attrs,
        )
        subwidgets = []
        # for field in self._parse_date_fmt():
        subwidgets.append(date_context['month']['widget'])
        subwidgets.append(date_context['year']['widget'])
        context['widget']['subwidgets'] = subwidgets
        return context

    def value_from_datadict(self, data, files, name):
        y = data.get(self.year_field % name)
        m = data.get(self.month_field % name)
        if y == m == "0":
            return None
        if y and m:
            if settings.USE_L10N:
                input_format = get_format('DATE_INPUT_FORMATS')[0]
                try:
                    date_value = datetime.date(int(y), int(m), 1)
                except ValueError:
                    return '%s-%s' % (y, m)
                else:
                    date_value = datetime_safe.new_date(date_value)
                    return date_value.strftime(input_format)
            else:
                return datetime.date(int(y), int(m), 1)
        return data.get(name)