# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2017-10-15 11:50
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0040_auto_20171015_1250'),
        ('cardless', '0003_auto_20171014_0827'),
    ]

    operations = [
        migrations.CreateModel(
            name='Payment_Event',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_id', models.CharField(max_length=50)),
                ('description', models.CharField(max_length=30)),
                ('person', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='members.Person')),
            ],
        ),
        migrations.AddField(
            model_name='mandate',
            name='active',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='mandate',
            name='event_id',
            field=models.CharField(default='', max_length=50),
            preserve_default=False,
        ),
    ]