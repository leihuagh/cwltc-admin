# Generated by Django 2.0.6 on 2018-07-20 16:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0029_posapp_view_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='posapp',
            name='allow_juniors',
            field=models.BooleanField(default=False),
        ),
    ]