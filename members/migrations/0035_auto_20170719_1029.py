# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-07-19 09:29
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0034_auto_20170719_0803'),
    ]

    operations = [
        migrations.RenameField(
            model_name='adultapplication',
            old_name='membership',
            new_name='membership_id',
        ),
    ]