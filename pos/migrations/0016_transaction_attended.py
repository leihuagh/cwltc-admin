# -*- coding: utf-8 -*-
# Generated by Django 1.11.12 on 2018-04-04 14:46
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0015_auto_20180403_1212'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='attended',
            field=models.BooleanField(default=False),
        ),
    ]
