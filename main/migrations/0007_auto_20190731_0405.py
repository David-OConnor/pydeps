# Generated by Django 2.2.3 on 2019-07-31 04:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("main", "0006_auto_20190731_0401")]

    operations = [
        migrations.AlterField(
            model_name="dependency",
            name="requires_dist",
            field=models.CharField(blank=True, max_length=500, null=True),
        )
    ]
