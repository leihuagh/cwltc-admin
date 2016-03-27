# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0002_auto_20150415_0033'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='person',
            name='pays_family_bill',
        ),
    ]
