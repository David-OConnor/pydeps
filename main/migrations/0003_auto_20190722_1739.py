# Generated by Django 2.2.3 on 2019-07-22 17:39

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0002_auto_20190722_1316'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='requirement',
            unique_together={('name', 'versions', 'dependency')},
        ),
    ]
