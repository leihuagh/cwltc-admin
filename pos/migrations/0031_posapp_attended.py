# Generated by Django 2.0.6 on 2018-07-24 13:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0030_posapp_allow_juniors'),
    ]

    operations = [
        migrations.AddField(
            model_name='posapp',
            name='attended',
            field=models.BooleanField(default=False),
        ),
    ]
