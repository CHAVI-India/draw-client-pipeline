# Generated by Django 5.1.4 on 2025-01-16 06:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dicom_handler', '0006_alter_uploaddicom_dicom_file'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='uploaddicom',
            options={'verbose_name': 'Upload Images'},
        ),
        migrations.AlterField(
            model_name='uploaddicom',
            name='dicom_file',
            field=models.FileField(upload_to='uploaddicom/'),
        ),
        migrations.AlterModelTable(
            name='uploaddicom',
            table='upload_images',
        ),
    ]
