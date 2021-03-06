# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-03-02 18:10
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0006_auto_20180227_1532'),
    ]

    operations = [
        migrations.AddField(
            model_name='juniorprofile',
            name='contact0',
            field=models.CharField(blank=True, max_length=50, verbose_name='Primary contact'),
        ),
        migrations.AddField(
            model_name='juniorprofile',
            name='phone0',
            field=models.CharField(blank=True, max_length=20, verbose_name='Phone number'),
        ),
        migrations.AlterField(
            model_name='juniorprofile',
            name='has_needs',
            field=models.BooleanField(choices=[(0, 'Zero'), (1, 'One'), (2, 'Two')], verbose_name='Special needs'),
        ),
        migrations.AlterField(
            model_name='juniorprofile',
            name='photo_consent',
            field=models.BooleanField(choices=[(0, 'Zero'), (1, 'One'), (2, 'Two')], default=False),
        ),
    ]
