# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-04-11 07:17
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0007_payment_fee'),
    ]

    operations = [
        migrations.CreateModel(
            name='Settings',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('membership_year', models.SmallIntegerField(default=0)),
            ],
        ),
        migrations.AddField(
            model_name='creditnote',
            name='membership_year',
            field=models.SmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='invoice',
            name='membership_year',
            field=models.SmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='payment',
            name='membership_year',
            field=models.SmallIntegerField(default=0),
        ),
    ]
