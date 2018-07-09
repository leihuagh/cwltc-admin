# Generated by Django 2.0.6 on 2018-07-08 13:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0011_auto_20180623_0806'),
    ]

    operations = [
        migrations.CreateModel(
            name='VisitorFees',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('year', models.SmallIntegerField()),
                ('adult_fee', models.DecimalField(decimal_places=2, max_digits=5)),
                ('junior_fee', models.DecimalField(decimal_places=2, max_digits=5)),
            ],
        ),
    ]