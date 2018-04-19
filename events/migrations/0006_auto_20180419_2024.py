# -*- coding: utf-8 -*-
# Generated by Django 1.11.12 on 2018-04-19 19:24
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0005_auto_20180418_1813'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='active',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='event',
            name='online_entry',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='tournament',
            name='active',
            field=models.BooleanField(default=True),
        ),
    ]
