# Generated by Django 5.1.4 on 2025-02-10 09:41

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dicom_handler', '0007_alter_uploaddicom_options_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='uploaddicom',
            options={'verbose_name': 'Upload Images', 'verbose_name_plural': 'Upload Images'},
        ),
    ]
