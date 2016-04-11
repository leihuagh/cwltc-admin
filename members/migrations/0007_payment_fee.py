# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-04-10 11:03
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0006_payment_banked_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='fee',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=7),
        ),
    ]
