# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-04-03 11:26
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0005_auto_20160313_0945'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='banked_date',
            field=models.DateField(null=True),
        ),
    ]
