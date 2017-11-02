# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2017-11-02 20:49
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import markdownx.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Address',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('address1', models.CharField(max_length=50)),
                ('address2', models.CharField(blank=True, max_length=50)),
                ('town', models.CharField(max_length=30)),
                ('post_code', models.CharField(max_length=15)),
                ('home_phone', models.CharField(blank=True, max_length=20)),
            ],
        ),
        migrations.CreateModel(
            name='AdultApplication',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('membership_id', models.SmallIntegerField(choices=[(1, 'Full'), (15, 'Off peak'), (14, 'Parent'), (6, 'Country'), (5, 'Bridge'), (11, 'Non playing'), (7, 'Coach'), (4, 'Under 26'), (8, 'Honorary life'), (7, 'Coach')], default=1, verbose_name='Membership type')),
                ('ability', models.SmallIntegerField(choices=[(0, 'Beginner'), (1, 'Improver'), (2, 'Rusty - Returning to tennis'), (3, 'Intermediate - average club player'), (4, 'Advanced  - club team player')], default=0, verbose_name='Judge your tennnis ability')),
                ('singles', models.BooleanField(default=False, verbose_name='Singles')),
                ('doubles', models.BooleanField(default=False, verbose_name='Doubles')),
                ('coaching1', models.BooleanField(default=False, verbose_name='Individual coaching')),
                ('coaching2', models.BooleanField(default=False, verbose_name='Group coaching')),
                ('daytime', models.BooleanField(default=False, verbose_name='Daytime tennis')),
                ('family', models.BooleanField(default=False, verbose_name='Family tennis')),
                ('social', models.BooleanField(default=False, verbose_name='Social tennis')),
                ('competitions', models.BooleanField(default=False, verbose_name='Club competitions')),
                ('teams', models.BooleanField(default=False, verbose_name='Team tennis')),
                ('club', models.CharField(blank=True, max_length=80, verbose_name='Name of previous tennis club (if any)')),
                ('source', models.SmallIntegerField(choices=[(0, 'Friend, relative or member'), (1, 'School'), (2, 'Web search'), (3, 'LTA search or promotion'), (4, 'Leaflet'), (5, 'Advertisement'), (6, 'Other')], default=2, verbose_name='How did you hear about us?')),
            ],
        ),
        migrations.CreateModel(
            name='BarTransaction',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False)),
                ('date', models.DateField()),
                ('time', models.TimeField()),
                ('member_split', models.IntegerField()),
                ('product', models.CharField(max_length=20)),
                ('description', models.CharField(max_length=20)),
                ('price', models.DecimalField(decimal_places=2, max_digits=7)),
                ('total', models.DecimalField(decimal_places=2, max_digits=7)),
            ],
        ),
        migrations.CreateModel(
            name='CreditNote',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('creation_date', models.DateTimeField(auto_now_add=True)),
                ('update_date', models.DateTimeField(auto_now=True)),
                ('membership_year', models.SmallIntegerField(default=0)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=7)),
                ('reference', models.CharField(blank=True, max_length=80, null=True)),
                ('detail', models.CharField(blank=True, max_length=1000, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Editor',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', markdownx.models.MarkdownxField()),
            ],
        ),
        migrations.CreateModel(
            name='ExcelBook',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='excel')),
            ],
        ),
        migrations.CreateModel(
            name='Fees',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sub_year', models.SmallIntegerField()),
                ('annual_sub', models.DecimalField(decimal_places=2, default=0, max_digits=7)),
                ('monthly_sub', models.DecimalField(decimal_places=2, default=0, max_digits=7)),
                ('joining_fee', models.DecimalField(decimal_places=2, max_digits=7, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Group',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', models.SlugField(max_length=20)),
                ('description', models.CharField(max_length=80)),
            ],
        ),
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('creation_date', models.DateTimeField(auto_now_add=True)),
                ('update_date', models.DateTimeField(auto_now=True)),
                ('date', models.DateField()),
                ('membership_year', models.SmallIntegerField(default=0)),
                ('reference', models.CharField(max_length=80)),
                ('state', models.SmallIntegerField(choices=[(0, 'Unpaid'), (1, 'Part paid'), (2, 'Paid'), (3, 'Cancelled'), (4, 'Overpaid')], default=0)),
                ('pending', models.BooleanField(default=False)),
                ('email_count', models.SmallIntegerField(default=0)),
                ('total', models.DecimalField(decimal_places=2, default=0, max_digits=7)),
                ('payments_expected', models.SmallIntegerField(default=1)),
                ('gocardless_action', models.CharField(blank=True, max_length=10)),
                ('gocardless_bill_id', models.CharField(blank=True, max_length=255)),
                ('postal_count', models.SmallIntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='InvoiceItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('creation_date', models.DateTimeField(auto_now_add=True)),
                ('update_date', models.DateTimeField(auto_now=True)),
                ('item_date', models.DateField(blank=True, null=True)),
                ('description', models.CharField(blank=True, max_length=100, null=True)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=7)),
                ('paid', models.BooleanField(default=False)),
                ('invoice', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='invoice_items', to='members.Invoice')),
            ],
        ),
        migrations.CreateModel(
            name='ItemType',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False)),
                ('description', models.CharField(max_length=30)),
                ('credit', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='MailCampaign',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('creation_date', models.DateTimeField(auto_now_add=True)),
                ('update_date', models.DateTimeField(auto_now=True)),
                ('sent_date', models.DateTimeField(null=True)),
                ('name', models.CharField(max_length=50)),
                ('text', models.TextField(null=True)),
                ('json', models.TextField(blank=True, null=True)),
            ],
            options={
                'ordering': ['-update_date'],
            },
        ),
        migrations.CreateModel(
            name='MailTemplate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('json', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='MailType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=30)),
                ('description', models.CharField(max_length=300)),
                ('can_unsubscribe', models.BooleanField(default=True)),
                ('sequence', models.IntegerField(default=0)),
                ('mail_campaign', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='members.MailCampaign')),
            ],
        ),
        migrations.CreateModel(
            name='Membership',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.CharField(max_length=20, verbose_name='Membership')),
                ('long_description', models.CharField(blank=True, max_length=300, verbose_name='Description')),
                ('is_adult', models.BooleanField(default=True)),
                ('is_playing', models.BooleanField(default=True)),
                ('apply_online', models.BooleanField(default=True)),
                ('cutoff_age', models.IntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('creation_date', models.DateTimeField(auto_now_add=True)),
                ('update_date', models.DateTimeField(auto_now=True)),
                ('membership_year', models.SmallIntegerField(default=0)),
                ('type', models.SmallIntegerField(choices=[(0, 'Cheque'), (1, 'Cash'), (2, 'BACS'), (3, 'Direct debit'), (4, 'Paypal'), (5, 'Other')], default=2)),
                ('reference', models.CharField(blank=True, max_length=80, null=True)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=7)),
                ('credited', models.DecimalField(decimal_places=2, default=0, max_digits=7)),
                ('match_state', models.SmallIntegerField(choices=[(0, 'Not matched'), (1, 'Partly matched'), (2, 'Fully matched'), (3, 'Error - overpaid')], default=0)),
                ('fee', models.DecimalField(decimal_places=2, default=0, max_digits=7)),
                ('payment_number', models.SmallIntegerField(default=1)),
                ('state', models.SmallIntegerField(choices=[(0, 'Pending'), (1, 'Confirmed'), (2, 'Failed'), (3, 'Cancelled')], default=0)),
                ('cardless_id', models.CharField(blank=True, max_length=50, null=True)),
                ('banked', models.BooleanField(default=False)),
                ('banked_date', models.DateField(null=True)),
                ('invoice', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='members.Invoice')),
            ],
        ),
        migrations.CreateModel(
            name='Person',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('gender', models.CharField(choices=[('M', 'Male'), ('F', 'Female'), ('U', 'Unknown')], default='M', max_length=1)),
                ('first_name', models.CharField(max_length=30)),
                ('last_name', models.CharField(max_length=30)),
                ('mobile_phone', models.CharField(blank=True, max_length=20)),
                ('email', models.EmailField(max_length=75)),
                ('dob', models.DateField(blank=True, null=True, verbose_name='Date of birth')),
                ('british_tennis', models.IntegerField(blank=True, null=True)),
                ('notes', models.TextField(blank=True)),
                ('pays_own_bill', models.BooleanField(default=False)),
                ('state', models.SmallIntegerField(choices=[(0, 'Active'), (1, 'Applied'), (2, 'Rejected'), (3, 'Resigned')], default=0)),
                ('date_joined', models.DateField(blank=True, null=True)),
                ('hex_key', models.CharField(blank=True, max_length=50, null=True)),
                ('allow_phone', models.BooleanField(default=True)),
                ('allow_email', models.BooleanField(default=True)),
                ('address', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='members.Address')),
                ('auth', models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='person', to=settings.AUTH_USER_MODEL)),
                ('groups', models.ManyToManyField(to='members.Group')),
                ('linked', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='members.Person')),
                ('membership', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='members.Membership')),
            ],
        ),
        migrations.CreateModel(
            name='Settings',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('membership_year', models.SmallIntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='Subscription',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sub_year', models.SmallIntegerField()),
                ('start_date', models.DateField(blank=True, null=True)),
                ('end_date', models.DateField(blank=True, null=True)),
                ('period', models.SmallIntegerField(choices=[(0, 'Annual'), (1, 'Quarterly'), (2, 'Monthly'), (3, 'Non recurring')], default=0)),
                ('new_member', models.BooleanField(default=False)),
                ('paid', models.BooleanField(default=False)),
                ('active', models.BooleanField(default=False)),
                ('resigned', models.BooleanField(default=False)),
                ('invoiced_month', models.SmallIntegerField()),
                ('no_renewal', models.BooleanField(default=False)),
                ('membership', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='members.Membership')),
                ('person_member', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='members.Person')),
            ],
        ),
        migrations.CreateModel(
            name='TextBlock',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=30)),
                ('type', models.SmallIntegerField(choices=[(0, 'Text block'), (1, 'HTML document'), (2, 'Bee editor template')], default=0)),
                ('text', models.TextField()),
            ],
        ),
        migrations.AddField(
            model_name='person',
            name='sub',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='members.Subscription'),
        ),
        migrations.AddField(
            model_name='person',
            name='unsubscribed',
            field=models.ManyToManyField(to='members.MailType'),
        ),
        migrations.AddField(
            model_name='payment',
            name='person',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='members.Person'),
        ),
        migrations.AddField(
            model_name='mailcampaign',
            name='mail_template',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='members.MailTemplate'),
        ),
        migrations.AddField(
            model_name='invoiceitem',
            name='item_type',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='members.ItemType'),
        ),
        migrations.AddField(
            model_name='invoiceitem',
            name='payment',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='members.Payment'),
        ),
        migrations.AddField(
            model_name='invoiceitem',
            name='person',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='members.Person'),
        ),
        migrations.AddField(
            model_name='invoiceitem',
            name='subscription',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='members.Subscription'),
        ),
        migrations.AddField(
            model_name='invoice',
            name='person',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='members.Person'),
        ),
        migrations.AddField(
            model_name='fees',
            name='membership',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='members.Membership'),
        ),
        migrations.AddField(
            model_name='creditnote',
            name='invoice',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='members.Invoice'),
        ),
        migrations.AddField(
            model_name='creditnote',
            name='person',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='members.Person'),
        ),
        migrations.AddField(
            model_name='bartransaction',
            name='member_id',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='members.Person'),
        ),
        migrations.AddField(
            model_name='adultapplication',
            name='person',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='members.Person'),
        ),
    ]
