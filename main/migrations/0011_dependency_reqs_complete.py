# Generated by Django 2.2.3 on 2019-08-06 14:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0010_auto_20190731_0420'),
    ]

    operations = [
        migrations.AddField(
            model_name='dependency',
            name='reqs_complete',
            field=models.BooleanField(default=False),
        ),
    ]
