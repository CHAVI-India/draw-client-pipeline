DICOM Process Interface Guidance
===================================

The following sections are available in the DICOM Process section:

Dicom Data copied from Datastore
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
View and manage DICOM data folders that have been copied from the datastore. This copy will be done using the automatically configured task schedule created by you when you configured the client. Note that this will show you the paths where the DICOM data will be copied from as well as the folder where they have been copied too. As you will note that all folders are organized inside a subfolder called folders for easier access. 

.. image:: images/dicom_data_copied.png
   :alt: Dicom Data Copied
   :width: 800
   :align: center


Dicom Series for Processing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
After the DICOM data has been copied it is separated into series. Additionally the system attempts to match autosegmentation templates to the series based on the Rulesets you have created during client configuration. If this is successful then the series will be de-identified. This table also shows all the series where the template matching failed and are unprocessed. In this section you can also choose to send a DICOM series for segmentation after manual section of an autosegmentation template.

.. image:: images/dicom_series_for_processing.png
   :alt: Dicom Series for Processing
   :width: 800
   :align: center

You can filter the list displayed by clicking on the dropdown menu in the top left corner and selecting the processing status of the series.

.. image:: images/dicom_series_for_processing_filter.png
   :alt: Dicom Series for Processing Filter
   :width: 800
   :align: center

You can also search for a specific series by clicking on the search bar and entering the patient ID, name etc.

.. image:: images/dicom_series_for_processing_search.png
   :alt: Dicom Series for Processing Search
   :width: 800
   :align: center

Please refer to the document called :doc:`processsing_status_choices` for more details on the processing status choices.   

Additionally, you can also send series for manual processing from this page. To do this we need to ensure that an automatic segmentation template is associated with the series. Please review the image below:

#. First we need to click the dropdown menu under the column called Template File to select the desired autosegmentation template. If you wish to create the template you can click on the button with a + sign to create a new template. Note that the buttons beside the dropdown menu may not be visible for all user roles. 

.. image:: images/dicom_series_for_processing_template_selection.png
   :alt: Selecting template for manual processing
   :width: 800
   :align: center

#. Once you have selected the template, click on the save button on the bottom right corner of the page. This will save the data for the series. 


.. image:: images/dicom_series_for_processing_save.png
   :alt: Saving template for manual processing
   :width: 800
   :align: center

#. After that click the checkbox beside the series that you wish to send for manual processing. Remember to select this carefully otherwise you may send the wrong series for manual processing.

.. image:: images/dicom_series_for_processing_checkbox.png
   :alt: Selecting series for manual processing
   :width: 800
   :align: center

#. Once you have selected the series, you will see a bar appear at the bottom of the page with a dropdown menu. There select the option "Send Dicom for processing action" to send the series for manual processing. You will see a message at the top once the series has started processing. After successful processing that status will also be changed. 

.. image:: images/dicom_series_for_processing_send.png
   :alt: Sending series for manual processing
   :width: 800
   :align: center

Processing Logs
~~~~~~~~~~~~~~~~~
In this page you can view the logs of the processing activities for the series. This allows you get a birds eye view of the processing activities for the series. The search bar allows you to search for a specific series by patient ID, name etc. 

.. image:: images/dicom_series_for_processing_logs.png
   :alt: Processing Logs
   :width: 800
   :align: center

You can also filter the logs by the processing status by clicking on the dropdown menu in the top left corner and selecting the processing status.

.. image:: images/dicom_series_for_processing_logs_filter.png
   :alt: Processing Logs Filter
   :width: 800
   :align: center

Upload DICOM Zip Files
~~~~~~~~~~~~~~~~~~~~~~~~~~
Upload DICOM data in compressed format for processing. One or multiple patients can be uploaded using this method. Please note that after you have uploaded the zip file, you will need to process it also. 

.. image:: images/dicom_upload_zip.png
   :alt: Upload DICOM Zip
   :width: 800
   :align: center


Note that the zip file will be unzipped after you select the action called Extract selected DICOM zip files to subfolders in the datastore.

.. image:: images/dicom_upload_zip_extract.png
   :alt: Extract DICOM Zip
   :width: 800
   :align: center
..

Please note that the files will be processed after they have been unzipped to the datastore folder by the task schedule created by you when you configured the client. Hence you may need to wait for the task schedule to run before you can process the files. By default the task schedule will ensure that a new folder is processed at least 10 minutes after it was last modified. As the folder newly created will be modified at the time of the unzipping process, the files will not be processed 10 minutes after the unzipping process or when the task schedule next runs which ever is later. 

.. image:: images/dicom_upload_zip_extract_task_schedule.png
   :alt: Extract DICOM Zip Task Schedule
   :width: 800
   :align: center
..

