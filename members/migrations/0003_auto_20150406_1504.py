# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0002_auto_20150405_1601'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='date',
            field=models.DateField(default=datetime.datetime(2015, 4, 6, 14, 4, 36, 103000, tzinfo=utc)),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='person',
            name='date_joined',
            field=models.DateField(null=True, blank=True),
            preserve_default=True,
        ),
    ]
