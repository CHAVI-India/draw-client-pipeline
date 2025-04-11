Interface Guidance
====================

The administrative interface which is accessible using the Admin Dashboard link is organized into the following sections:

Client Configuration
----------------------
This section provides the interface to configure the DRAW client on your local machines. Details are provided in the configuration section (See the page :doc:`configuration`)


DICOM Processing 
-----------------
This section gives you an overview of the DICOM data being processed and includes:

Dicom Data copied from Datastore
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
View and manage DICOM data folders that have been copied from the datastore. This copy will be done using the automatically configured task schedule created by you when you configured the client. Note that this will show you the paths where the DICOM data will be copied from as well as the folder where they have been copied too. As you will note that all folders are organized inside a subfolder called folders for easier access. 

Dicom Series for Processing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
After the DICOM data has been copied it is separated into series. Additionally the system attempts to match autosegmentation templates to the series based on the Rulesets you have created during client configuration. If this is successful then the series will be de-identified. This table also shows all the series where the template matching failed and are unprocessed. In this section you can also choose to send a DICOM series for segmentation after manual section of an autosegmentation template.

Processing Logs
~~~~~~~~~~~~~~~~~
Access detailed logs of DICOM processing activities with timestamp and any error messages for troubleshooting

Upload DICOM Zip Files
~~~~~~~~~~~~~~~~~~~~~~~~~~
Upload DICOM data in compressed format for processing. One or multiple patients can be uploaded using this method. 

Deidentification Overview
--------------------------
This section provides access to deidentified DICOM data and includes:

Patient
~~~~~~~~~~
View the deidentified patient information. Note that the API client will have access to deidentified data and therefore any troubleshooting purposes, you may need to see the deidentified patient data.

Dicom Study
~~~~~~~~~~~~~~~
View deidentified study-level DICOM data.

Dicom Series
~~~~~~~~~~~~~~~
View deidentified series-level DICOM information.

Dicom Instance
~~~~~~~~~~~~~~~~~~
View individual deidentified DICOM instances. Each instance is the file in the DICOM dataset.

RT Structure File
~~~~~~~~~~~~~~~~~~
Manage deidentified RT structure files.

Remote Transfers
-----------------
This section manages data transfers and includes:

API Data Processing Status
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Monitor the status of data transfers to and from the API. This table will automatically update the data from the server at regular intervals. After the RTStruct has been segmented and retrieved it will update the status also. 

Autosegmentation Templates
---------------------------
This section allows you to view autosegmentation templates in the system. 

View Autosegmentation Templates
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Access and manage existing autosegmentation templates. You can delete the autosegmentation templates from here.

Task Status
------------
This section provides information about tasks being executed by the system.

View Task Status
~~~~~~~~~~~~~~~~~~
Monitor the status and results of scheduled tasks.