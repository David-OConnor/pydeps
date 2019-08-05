# Generated by Django 2.2.3 on 2019-07-31 03:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("main", "0004_auto_20190722_1831")]

    operations = [
        migrations.AddField(
            model_name="dependency",
            name="file_url",
            field=models.CharField(default="", max_length=500),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="dependency",
            name="filename",
            field=models.CharField(default="", max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="dependency",
            name="hash",
            field=models.CharField(default="", max_length=300),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="dependency",
            name="version_reqs",
            field=models.CharField(default="", max_length=300),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="dependency",
            name="version",
            field=models.CharField(max_length=100),
        ),
    ]