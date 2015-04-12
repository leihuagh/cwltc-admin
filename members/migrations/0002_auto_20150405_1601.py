# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='textblock',
            name='text',
            field=models.CharField(max_length=8000),
            preserve_default=True,
        ),
    ]
