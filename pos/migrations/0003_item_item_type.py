# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2017-11-12 19:09
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0002_itemtype_pos'),
        ('pos', '0002_remove_layout_invoice_itemtype'),
    ]

    operations = [
        migrations.AddField(
            model_name='item',
            name='item_type',
            field=models.ForeignKey(default=4, on_delete=django.db.models.deletion.CASCADE, to='members.ItemType'),
        ),
    ]
