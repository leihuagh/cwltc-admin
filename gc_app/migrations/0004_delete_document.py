# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2017-04-23 18:25
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gc_app', '0003_document'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Document',
        ),
    ]