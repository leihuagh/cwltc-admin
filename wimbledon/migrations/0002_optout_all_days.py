# -*- coding: utf-8 -*-
# Generated by Django 1.11.12 on 2018-04-09 07:59
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wimbledon', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='optout',
            name='all_days',
            field=models.BooleanField(default=False),
        ),
    ]
