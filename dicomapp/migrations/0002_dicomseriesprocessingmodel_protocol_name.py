# Generated by Django 5.1.7 on 2025-04-09 13:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dicomapp', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='dicomseriesprocessingmodel',
            name='protocol_name',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
