# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2017-11-25 20:23
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0003_auto_20171125_1951'),
    ]

    operations = [
        migrations.AlterField(
            model_name='person',
            name='pin',
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
    ]