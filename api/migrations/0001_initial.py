# Generated by Django 2.2.15 on 2020-08-26 22:28

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Wallet',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('address', models.UUIDField(default=uuid.uuid4, editable=False)),
                ('alias', models.CharField(max_length=50)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('transaction_type', models.CharField(choices=[('sent_external', 'sent_external'), ('sent_internal', 'sent_internal'), ('received_external', 'received_external'), ('received_external', 'received_external'), ('platform_profit', 'platform_profit')], max_length=20)),
                ('to_address', models.CharField(blank=True, max_length=36)),
                ('from_address', models.CharField(blank=True, max_length=36)),
                ('amount', models.DecimalField(decimal_places=8, max_digits=16)),
                ('details', models.CharField(max_length=250)),
                ('created_at', models.DateTimeField(auto_now=True)),
                ('wallet', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.Wallet')),
            ],
        ),
        migrations.AddConstraint(
            model_name='wallet',
            constraint=models.UniqueConstraint(fields=('address',), name='unique_address'),
        ),
    ]
