# Generated by Django 2.2.15 on 2020-08-30 17:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0013_auto_20200830_1740'),
    ]

    operations = [
        migrations.AlterField(
            model_name='wallet',
            name='alias',
            field=models.CharField(max_length=50),
        ),
    ]
