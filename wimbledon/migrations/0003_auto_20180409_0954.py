# -*- coding: utf-8 -*-
# Generated by Django 1.11.12 on 2018-04-09 08:54
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('wimbledon', '0002_optout_all_days'),
    ]

    operations = [
        migrations.AlterField(
            model_name='optout',
            name='ticket',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='wimbledon.Tickets'),
        ),
    ]
