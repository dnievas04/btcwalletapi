# Generated by Django 2.2.15 on 2020-08-30 18:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0014_auto_20200830_1759'),
    ]

    operations = [
        migrations.AlterField(
            model_name='wallet',
            name='alias',
            field=models.CharField(blank=True, max_length=50),
        ),
    ]
