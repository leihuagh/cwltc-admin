# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2017-01-21 16:06
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0023_membership_cutoff_age'),
    ]

    operations = [
        migrations.AlterField(
            model_name='subscription',
            name='membership',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='members.Membership'),
        ),
    ]
