# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2017-09-17 17:53
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0038_auto_20170729_1714'),
    ]

    operations = [
        migrations.AlterField(
            model_name='adultapplication',
            name='ability',
            field=models.SmallIntegerField(choices=[(0, 'Beginner'), (1, 'Improver'), (2, 'Rusty - Returning to tennis'), (3, 'Intermediate - average club player'), (4, 'Advanced  - club team player')], default=0, verbose_name='Judge your tennnis ability'),
        ),
        migrations.AlterField(
            model_name='adultapplication',
            name='club',
            field=models.CharField(blank=True, max_length=80, verbose_name='Name of previous tennis club (if any)'),
        ),
        migrations.AlterField(
            model_name='adultapplication',
            name='coaching1',
            field=models.BooleanField(default=False, verbose_name='Individual coaching'),
        ),
        migrations.AlterField(
            model_name='adultapplication',
            name='coaching2',
            field=models.BooleanField(default=False, verbose_name='Group coaching'),
        ),
        migrations.AlterField(
            model_name='adultapplication',
            name='competitions',
            field=models.BooleanField(default=False, verbose_name='Club competitions'),
        ),
        migrations.AlterField(
            model_name='adultapplication',
            name='daytime',
            field=models.BooleanField(default=False, verbose_name='Daytime tennis'),
        ),
        migrations.AlterField(
            model_name='adultapplication',
            name='doubles',
            field=models.BooleanField(default=False, verbose_name='Doubles'),
        ),
        migrations.AlterField(
            model_name='adultapplication',
            name='family',
            field=models.BooleanField(default=False, verbose_name='Family tennis'),
        ),
        migrations.AlterField(
            model_name='adultapplication',
            name='membership_id',
            field=models.SmallIntegerField(choices=[(1, 'Full'), (15, 'Off peak'), (14, 'Parent'), (6, 'Country'), (5, 'Bridge'), (11, 'Non playing'), (7, 'Coach'), (4, 'Under 26'), (8, 'Honorary life'), (7, 'Coach')], default=1, verbose_name='Membership type'),
        ),
        migrations.AlterField(
            model_name='adultapplication',
            name='singles',
            field=models.BooleanField(default=False, verbose_name='Singles'),
        ),
        migrations.AlterField(
            model_name='adultapplication',
            name='social',
            field=models.BooleanField(default=False, verbose_name='Social tennis'),
        ),
        migrations.AlterField(
            model_name='adultapplication',
            name='source',
            field=models.SmallIntegerField(choices=[(0, 'Friend, relative or member'), (1, 'School'), (2, 'Web search'), (3, 'LTA search or promotion'), (4, 'Leaflet'), (5, 'Advertisement'), (6, 'Other')], default=2, verbose_name='How did you hear about us?'),
        ),
        migrations.AlterField(
            model_name='adultapplication',
            name='teams',
            field=models.BooleanField(default=False, verbose_name='Team tennis'),
        ),
        migrations.AlterField(
            model_name='excelbook',
            name='file',
            field=models.FileField(upload_to='excel'),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='state',
            field=models.SmallIntegerField(choices=[(0, 'Unpaid'), (1, 'Part paid'), (2, 'Paid'), (3, 'Cancelled'), (4, 'Part paid & credit note'), (5, 'Error - overpaid'), (6, 'Pending GoCardless')], default=0),
        ),
        migrations.AlterField(
            model_name='membership',
            name='description',
            field=models.CharField(max_length=20, verbose_name='Membership'),
        ),
        migrations.AlterField(
            model_name='membership',
            name='long_description',
            field=models.CharField(blank=True, max_length=300, verbose_name='Description'),
        ),
        migrations.AlterField(
            model_name='payment',
            name='state',
            field=models.SmallIntegerField(choices=[(0, 'Not matched'), (1, 'Partly matched'), (2, 'Fully matched'), (3, 'Error - overpaid')], default=0),
        ),
        migrations.AlterField(
            model_name='payment',
            name='type',
            field=models.SmallIntegerField(choices=[(0, 'Cheque'), (1, 'Cash'), (2, 'BACS'), (3, 'Direct debit'), (4, 'Paypal'), (5, 'Other')], default=2),
        ),
        migrations.AlterField(
            model_name='person',
            name='dob',
            field=models.DateField(blank=True, null=True, verbose_name='Date of birth'),
        ),
        migrations.AlterField(
            model_name='person',
            name='gender',
            field=models.CharField(choices=[('M', 'Male'), ('F', 'Female'), ('U', 'Unknown')], default='M', max_length=1),
        ),
        migrations.AlterField(
            model_name='person',
            name='state',
            field=models.SmallIntegerField(choices=[(0, 'Active'), (1, 'Applied'), (2, 'Rejected'), (3, 'Resigned')], default=0),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='period',
            field=models.SmallIntegerField(choices=[(0, 'Annual'), (1, 'Quarterly'), (2, 'Monthly'), (3, 'Non recurring')], default=0),
        ),
        migrations.AlterField(
            model_name='textblock',
            name='type',
            field=models.SmallIntegerField(choices=[(0, 'Text block'), (1, 'HTML document'), (2, 'Bee editor template')], default=0),
        ),
    ]
