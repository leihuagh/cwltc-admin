# Generated by Django 2.0.7 on 2018-08-08 15:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0016_auto_20180808_1645'),
    ]

    operations = [
        migrations.RenameField(
            model_name='event',
            old_name='strap_line',
            new_name='slogan',
        ),
        migrations.AlterField(
            model_name='event',
            name='active',
            field=models.BooleanField(default=False),
        ),
    ]