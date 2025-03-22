# Generated by Django 5.1.4 on 2025-03-22 08:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dicom_handler', '0009_alter_modelyamlinfo_yaml_name'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='dicompathconfig',
            options={'verbose_name': 'Dicom Path Configuration'},
        ),
        migrations.RemoveField(
            model_name='dicompathconfig',
            name='deidentificationfolderpath',
        ),
        migrations.RemoveField(
            model_name='dicompathconfig',
            name='dicomimportfolderpath',
        ),
        migrations.RemoveField(
            model_name='dicompathconfig',
            name='dicomnonprocessedfolderpath',
        ),
        migrations.RemoveField(
            model_name='dicompathconfig',
            name='dicomprocessingfolderpath',
        ),
        migrations.RemoveField(
            model_name='dicompathconfig',
            name='finalrtstructfolderpath',
        ),
        migrations.RemoveField(
            model_name='dicompathconfig',
            name='templatefolderpath',
        ),
        migrations.AddField(
            model_name='dicompathconfig',
            name='import_dicom',
            field=models.TextField(help_text='Enter the full path to the import_dicom folder which is the local folder where the DICOM data will be imported.', null=True),
        ),
        migrations.AlterField(
            model_name='dicompathconfig',
            name='datastorepath',
            field=models.TextField(help_text='Enter the full path to the datastore which is the remote folder from the DICOM data will be imported.', null=True),
        ),
    ]
