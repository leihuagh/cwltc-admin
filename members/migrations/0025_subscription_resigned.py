# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2017-01-21 16:12
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0024_auto_20170121_1606'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscription',
            name='resigned',
            field=models.BooleanField(default=False),
        ),
    ]