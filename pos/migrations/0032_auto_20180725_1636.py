# Generated by Django 2.0.6 on 2018-07-25 15:36

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0031_posapp_attended'),
    ]

    operations = [
        migrations.RenameField(
            model_name='pospayment',
            old_name='amount',
            new_name='total',
        ),
    ]
