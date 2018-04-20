# -*- coding: utf-8 -*-
# Generated by Django 1.11.12 on 2018-04-17 16:01
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0009_auto_20180411_1738'),
        ('events', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='event',
            name='url_name',
        ),
        migrations.RemoveField(
            model_name='participant',
            name='person_2',
        ),
        migrations.AddField(
            model_name='event',
            name='event_type',
            field=models.SmallIntegerField(choices=[(0, 'Mens singles'), (1, 'Ladies singles'), (2, 'Mens doubles'), (3, 'Ladies doubles'), (4, 'Mixed doubles'), (5, 'Open singles'), (6, 'Open doubles')], default=0),
        ),
        migrations.AddField(
            model_name='participant',
            name='partner',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='partner', to='members.Person'),
        ),
    ]
