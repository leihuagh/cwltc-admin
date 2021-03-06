# Generated by Django 2.0.4 on 2018-05-10 19:36

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0010_auto_20180424_1452'),
        ('diary', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='player_1',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='player_1', to='members.Person'),
        ),
        migrations.AddField(
            model_name='booking',
            name='player_2',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='player_2', to='members.Person'),
        ),
        migrations.AddField(
            model_name='booking',
            name='player_3',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='player_3', to='members.Person'),
        ),
    ]
