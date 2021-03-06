# Generated by Django 2.2.15 on 2020-08-28 11:34

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0002_auto_20200827_1745'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='operation_type',
            field=models.CharField(choices=[('credit', 'credit'), ('debit', 'debit')], default='credit', max_length=6),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='transaction',
            name='details',
            field=models.CharField(blank=True, max_length=250),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='transaction_type',
            field=models.CharField(blank=True, choices=[('sent_external', 'sent_external'), ('sent_internal', 'sent_internal'), ('received_external', 'received_external'), ('received_external', 'received_external')], max_length=20),
        ),
        migrations.AlterField(
            model_name='wallet',
            name='user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
    ]
