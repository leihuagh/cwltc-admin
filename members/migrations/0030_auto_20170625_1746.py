# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-06-25 16:46
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0029_auto_20170529_1729'),
    ]

    operations = [
        migrations.AlterField(
            model_name='editor',
            name='text',
            field=models.CharField(max_length=1024),
        ),
    ]