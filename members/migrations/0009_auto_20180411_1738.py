# -*- coding: utf-8 -*-
# Generated by Django 1.11.12 on 2018-04-11 16:38
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('members', '0008_auto_20180327_2358'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='bartransaction',
            name='member_id',
        ),
        migrations.AddField(
            model_name='creditnote',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='creditnote',
            name='person',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='members.Person'),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='person',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='members.Person'),
        ),
        migrations.AlterField(
            model_name='invoiceitem',
            name='person',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='members.Person'),
        ),
        migrations.AlterField(
            model_name='invoiceitem',
            name='subscription',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='members.Subscription'),
        ),
        migrations.AlterField(
            model_name='payment',
            name='person',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='members.Person'),
        ),
        migrations.AlterField(
            model_name='person',
            name='address',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='members.Address'),
        ),
        migrations.AlterField(
            model_name='person',
            name='auth',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='person', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='person',
            name='linked',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='members.Person'),
        ),
        migrations.AlterField(
            model_name='person',
            name='membership',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='members.Membership'),
        ),
        migrations.AlterField(
            model_name='person',
            name='sub',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='members.Subscription'),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='membership',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='members.Membership'),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='person_member',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='members.Person'),
        ),
        migrations.DeleteModel(
            name='BarTransaction',
        ),
    ]
