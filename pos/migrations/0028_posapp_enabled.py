# Generated by Django 2.0.6 on 2018-07-18 18:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0027_posapp'),
    ]

    operations = [
        migrations.AddField(
            model_name='posapp',
            name='enabled',
            field=models.BooleanField(default=True),
        ),
    ]