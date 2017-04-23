# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2017-04-23 11:57
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gc_app', '0002_auto_20160410_1203'),
    ]

    operations = [
        migrations.CreateModel(
            name='Document',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.CharField(blank=True, max_length=255)),
                ('document', models.FileField(upload_to=b'documents/')),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
