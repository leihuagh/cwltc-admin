# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-04-08 16:30
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='WebHook',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('creation_date', models.DateTimeField(auto_now_add=True)),
                ('resource_type', models.CharField(max_length=30)),
                ('action', models.CharField(max_length=20)),
                ('message', models.CharField(max_length=1000)),
                ('processed', models.BooleanField(default=False)),
                ('error', models.CharField(max_length=80)),
            ],
        ),
    ]