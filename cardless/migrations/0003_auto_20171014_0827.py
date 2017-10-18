# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2017-10-14 07:27
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0039_auto_20171013_1847'),
        ('cardless', '0002_cardless_person'),
    ]

    operations = [
        migrations.CreateModel(
            name='Mandate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mandate_id', models.CharField(max_length=50)),
                ('customer_id', models.CharField(max_length=50)),
                ('person', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='members.Person')),
            ],
        ),
        migrations.RemoveField(
            model_name='cardless',
            name='person',
        ),
        migrations.DeleteModel(
            name='Cardless',
        ),
    ]