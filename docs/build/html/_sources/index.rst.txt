.. Deep learning based Radiotherapy Autosegmentation Workflow (DRAW) - Client Documentation documentation master file, created by
   sphinx-quickstart on Sat Mar 29 22:42:05 2025.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Deep learning based Radiotherapy Autosegmentation Workflow (DRAW) - Client Documentation
======================================================================================================

Welcome to the Deep learning based Radiotherapy Autosegmentation Workflow (DRAW) - Client Documentation. In this documentation, you will find information on how to use the DRAW client to interact with the DRAW server. 

The DRAW client is a Django based application that runs on a computer and allows the user to send DICOM images to the DRAW server for autosegmentation. After the autosegmentation is completed, the DRAW client retrives the RTStructureSet files from the DRAW server and saves them to the correct path. 

The DRAW client performs the following major tasks:

#. It allows the user to configure a directory / folder from which the client will take DICOM data for autosegmentation.
#. It allows the user to create autosegmentation templates. These templates are created using the data provided from the DRAW server and allow users to quickly modify / adapt the templates to new or updated models. 
#. It allows the user to configure rulesets that determine which autosegmentation template to use for a given DICOM data.
#. It allows the user to schedule periodic autosegmentation tasks to run at specified intervals.
#. Before sending the DICOM data to the DRAW server it ensures that the DICOM data is properly deidentifies and associates the autosegmentation templates (selected based on the ruleset or manually) with the DICOM data.
#. It retrives the RTStructureSet files from the DRAW server and saves them to the correct path after the reidentification is completed. 
#. Finally it allows the users to view the File operations performed by the client. 


.. toctree::
   :maxdepth: 2
   :caption: Contents:
   
   installation
   configuration
   datastore_configuration
   get_api_tokens
   creating_autosegmentation_templates
   configure_rules
   setup_periodic_tasks
   how_to_manual_segmentation
   interface_guide
   processsing_status_choices

