# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-04-02 12:33
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0008_auto_20180327_2358'),
        ('pos', '0013_auto_20180402_1159'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='transaction',
            name='layout',
        ),
        migrations.AddField(
            model_name='transaction',
            name='item_type',
            field=models.ForeignKey(default=4, on_delete=django.db.models.deletion.CASCADE, to='members.ItemType'),
        ),
    ]