import datetime
from datetime import date
from django.db import models
from django import forms

from django.http import Http404, HttpResponse
from django.utils.dateformat import DateFormat
from django.utils.formats import date_format


from wagtail.core.models import Page
from wagtail.core.fields import RichTextField
from wagtail.admin.edit_handlers import FieldPanel


from wagtail.core.models import Page
from wagtail.core.fields import RichTextField, StreamField
from wagtail.core import blocks
from wagtail.images.blocks import ImageChooserBlock
from wagtail.images.edit_handlers import ImageChooserPanel
from wagtail.embeds.blocks import EmbedBlock
from wagtail.admin.edit_handlers import FieldPanel, FieldRowPanel, MultiFieldPanel, \
    InlinePanel, PageChooserPanel, StreamFieldPanel
from wagtail.snippets.models import register_snippet
from wagtail.contrib.routable_page.models import RoutablePageMixin, route


from modelcluster.fields import ParentalKey, ParentalManyToManyField
from modelcluster.contrib.taggit import ClusterTaggableManager

from taggit.models import TaggedItemBase, Tag as TaggitTag


class HomePage(Page):
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('body', classname="full"),
    ]

class NewsPage(Page):
    description = models.CharField(max_length=255, blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('description', classname="full")
    ]

    def get_items(self):
        return NewsItem.objects.descendant_of(self).live()

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context['top_pages'] = self.get_items().order_by('-date')[:3]
        context['other_pages'] = self.get_items().order_by('-date')[3:8]
        #context['other_pages'] = self.get_items().order_by('-date')[8:]
        return context

    subpage_types= ['NewsItem']


class NewsItem(Page):

    IMAGE_POSITIONS = (
        (0, "Top, before tite"),
        (1, "Top, after title"),
        (2, 'Left'),
        (3, 'Right'),
    )

    summary = models.CharField(max_length=1000, blank=True)
    body = RichTextField(blank=False)
    post_date = models.DateTimeField(verbose_name="Post date", default=datetime.datetime.today)
    date = models.DateField("Post date")
    image = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )
    image_position=models.SmallIntegerField(choices=IMAGE_POSITIONS, default=0)


    # categories = ParentalManyToManyField('blog.BlogCategory', blank=True)
    # tags = ClusterTaggableManager(through='blog.BlogPageTag', blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('date'),
        FieldPanel('body', classname="full"),
        ImageChooserPanel('image'),
        FieldPanel('image_position'),
        # FieldPanel('categories', widget=forms.CheckboxSelectMultiple),
        # FieldPanel('tags'),
    ]

    # settings_panels = Page.settings_panels + [
    #     FieldPanel('post_date'),
    # ]

    @property
    def news_page(self):
        return self.get_parent().specific

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context['news_page'] = self.news_page
        context['item'] = self
        return context