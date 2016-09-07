# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-08-31 09:54
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0011_remove_group_generated'),
    ]

    operations = [
        migrations.CreateModel(
            name='MailType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=30)),
                ('description', models.CharField(max_length=100)),
                ('can_unsubscribe', models.BooleanField(default=True)),
                ('person', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='members.Person')),
            ],
        ),
        migrations.AlterField(
            model_name='invoice',
            name='state',
            field=models.SmallIntegerField(choices=[(0, b'Unpaid'), (1, b'Part paid'), (2, b'Paid'), (3, b'Cancelled'), (4, b'Part paid & credit note'), (5, b'Error - overpaid')], default=0),
        ),
        migrations.AlterField(
            model_name='payment',
            name='type',
            field=models.SmallIntegerField(choices=[(0, b'Cheque'), (1, b'Cash'), (2, b'BACS'), (3, b'Direct debit'), (4, b'Paypal'), (5, b'Other')], default=2),
        ),
    ]