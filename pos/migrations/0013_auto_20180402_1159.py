# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-04-02 10:59
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0012_transaction_terminal'),
    ]

    operations = [
        migrations.RenameField(
            model_name='transaction',
            old_name='complementary',
            new_name='complimentary',
        ),
    ]