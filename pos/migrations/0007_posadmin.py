# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-03-23 15:50
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0006_location_description'),
    ]

    operations = [
        migrations.CreateModel(
            name='PosAdmin',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('attended_mode', models.BooleanField(default=False)),
                ('default_layout', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='pos.Layout')),
            ],
        ),
    ]
