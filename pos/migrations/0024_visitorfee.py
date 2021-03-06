# Generated by Django 2.0.6 on 2018-07-08 12:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0023_auto_20180702_1128'),
    ]

    operations = [
        migrations.CreateModel(
            name='VisitorFee',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('year', models.SmallIntegerField()),
                ('adult_fee', models.DecimalField(decimal_places=2, max_digits=5)),
                ('junior_fee', models.DecimalField(decimal_places=2, max_digits=5)),
            ],
        ),
    ]
