# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Address',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('address1', models.CharField(max_length=50)),
                ('address2', models.CharField(max_length=50, blank=True)),
                ('town', models.CharField(max_length=30)),
                ('post_code', models.CharField(max_length=15)),
                ('home_phone', models.CharField(max_length=20, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='BarTransaction',
            fields=[
                ('id', models.IntegerField(serialize=False, primary_key=True)),
                ('date', models.DateField()),
                ('time', models.TimeField()),
                ('member_split', models.IntegerField()),
                ('product', models.CharField(max_length=20)),
                ('description', models.CharField(max_length=20)),
                ('price', models.DecimalField(max_digits=7, decimal_places=2)),
                ('total', models.DecimalField(max_digits=7, decimal_places=2)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CreditNote',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('creation_date', models.DateTimeField(auto_now_add=True)),
                ('update_date', models.DateTimeField(auto_now=True)),
                ('amount', models.DecimalField(max_digits=7, decimal_places=2)),
                ('reference', models.CharField(max_length=80, null=True, blank=True)),
                ('detail', models.CharField(max_length=1000, null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ExcelBook',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('file', models.FileField(upload_to=b'excel')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Fees',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('sub_year', models.SmallIntegerField()),
                ('annual_sub', models.DecimalField(default=0, max_digits=7, decimal_places=2)),
                ('monthly_sub', models.DecimalField(default=0, max_digits=7, decimal_places=2)),
                ('joining_fee', models.DecimalField(null=True, max_digits=7, decimal_places=2)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('creation_date', models.DateTimeField(auto_now_add=True)),
                ('update_date', models.DateTimeField(auto_now=True)),
                ('date', models.DateField()),
                ('reference', models.CharField(max_length=80)),
                ('state', models.SmallIntegerField(default=0, choices=[(0, b'Unpaid'), (1, b'Part paid'), (2, b'Paid in full'), (3, b'Cancelled'), (4, b'Part paid & credit note'), (5, b'Error - overpaid')])),
                ('email_count', models.SmallIntegerField(default=0)),
                ('postal_count', models.SmallIntegerField(default=0)),
                ('total', models.DecimalField(default=0, max_digits=7, decimal_places=2)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='InvoiceItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('creation_date', models.DateTimeField(auto_now_add=True)),
                ('update_date', models.DateTimeField(auto_now=True)),
                ('item_date', models.DateField(null=True, blank=True)),
                ('description', models.CharField(max_length=100, null=True, blank=True)),
                ('amount', models.DecimalField(max_digits=7, decimal_places=2)),
                ('paid', models.BooleanField(default=False)),
                ('invoice', models.ForeignKey(blank=True, to='members.Invoice', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ItemType',
            fields=[
                ('id', models.IntegerField(serialize=False, primary_key=True)),
                ('description', models.CharField(max_length=30)),
                ('credit', models.BooleanField(default=False)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Membership',
            fields=[
                ('id', models.IntegerField(serialize=False, primary_key=True)),
                ('description', models.CharField(max_length=20)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('creation_date', models.DateTimeField(auto_now_add=True)),
                ('update_date', models.DateTimeField(auto_now=True)),
                ('type', models.SmallIntegerField(default=2, choices=[(0, b'Cheque'), (1, b'Cash'), (2, b'BACS transfer'), (3, b'Direct debit'), (4, b'Paypal'), (5, b'Other')])),
                ('reference', models.CharField(max_length=80, null=True, blank=True)),
                ('amount', models.DecimalField(max_digits=7, decimal_places=2)),
                ('credited', models.DecimalField(default=0, max_digits=7, decimal_places=2)),
                ('state', models.SmallIntegerField(default=0, choices=[(0, b'Not matched'), (1, b'Partly matched'), (2, b'Fully matched'), (3, b'Error - overpaid')])),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Person',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('gender', models.CharField(default=b'M', max_length=1, choices=[(b'M', b'Male'), (b'F', b'Female'), (b'U', b'Unknown')])),
                ('first_name', models.CharField(max_length=30)),
                ('last_name', models.CharField(max_length=30)),
                ('mobile_phone', models.CharField(max_length=20, blank=True)),
                ('email', models.EmailField(max_length=75)),
                ('dob', models.DateField(null=True, blank=True)),
                ('british_tennis', models.IntegerField(null=True, blank=True)),
                ('notes', models.TextField(blank=True)),
                ('pays_own_bill', models.BooleanField(default=False)),
                ('pays_family_bill', models.BooleanField(default=False)),
                ('state', models.SmallIntegerField(default=0, choices=[(0, b'Active'), (1, b'Applied'), (2, b'Rejected'), (3, b'Resigned')])),
                ('date_joined', models.DateField(null=True, blank=True)),
                ('address', models.ForeignKey(blank=True, to='members.Address', null=True)),
                ('linked', models.ForeignKey(blank=True, to='members.Person', null=True)),
                ('membership', models.ForeignKey(blank=True, to='members.Membership', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Subscription',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('sub_year', models.SmallIntegerField()),
                ('start_date', models.DateField(null=True, blank=True)),
                ('end_date', models.DateField(null=True, blank=True)),
                ('period', models.SmallIntegerField(default=0, choices=[(0, b'Annual'), (1, b'Quarterly'), (2, b'Monthly'), (3, b'Non recurring')])),
                ('new_member', models.BooleanField(default=False)),
                ('paid', models.BooleanField(default=False)),
                ('active', models.BooleanField(default=False)),
                ('invoiced_month', models.SmallIntegerField()),
                ('no_renewal', models.BooleanField(default=False)),
                ('membership', models.ForeignKey(to='members.Membership')),
                ('person_member', models.ForeignKey(to='members.Person')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TextBlock',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=30)),
                ('text', models.CharField(max_length=8000)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='payment',
            name='person',
            field=models.ForeignKey(to='members.Person'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='invoiceitem',
            name='item_type',
            field=models.ForeignKey(default=1, to='members.ItemType'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='invoiceitem',
            name='payment',
            field=models.ForeignKey(blank=True, to='members.Payment', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='invoiceitem',
            name='person',
            field=models.ForeignKey(blank=True, to='members.Person', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='invoiceitem',
            name='subscription',
            field=models.ForeignKey(blank=True, to='members.Subscription', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='invoice',
            name='person',
            field=models.ForeignKey(to='members.Person'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='fees',
            name='membership',
            field=models.ForeignKey(to='members.Membership'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='creditnote',
            name='invoice',
            field=models.ForeignKey(to='members.Invoice'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='creditnote',
            name='person',
            field=models.ForeignKey(to='members.Person'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='bartransaction',
            name='member_id',
            field=models.ForeignKey(to='members.Person'),
            preserve_default=True,
        ),
    ]
