# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-07-19 07:03
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0033_auto_20170718_0810'),
    ]

    operations = [
        migrations.AlterField(
            model_name='adultapplication',
            name='club',
            field=models.CharField(blank=True, max_length=80, verbose_name=b'Name of previous tennis club (if any)'),
        ),
    ]