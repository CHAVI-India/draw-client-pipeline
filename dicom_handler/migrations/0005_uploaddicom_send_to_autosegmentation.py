# Generated by Django 5.1.4 on 2025-01-15 07:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dicom_handler', '0004_alter_uploaddicom_dicom_file'),
    ]

    operations = [
        migrations.AddField(
            model_name='uploaddicom',
            name='send_to_autosegmentation',
            field=models.BooleanField(default=False),
        ),
    ]
