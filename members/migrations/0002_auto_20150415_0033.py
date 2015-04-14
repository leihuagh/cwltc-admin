# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='banked',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='creditnote',
            name='invoice',
            field=models.ForeignKey(blank=True, to='members.Invoice', null=True),
            preserve_default=True,
        ),
    ]
