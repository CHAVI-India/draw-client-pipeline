Processing Status Choices
=========================

Processing Status
--------------------

The following are the processing status choices that are available in the DRAW Client.

#. SERIES_SEPARATED: The series has been separated into individual studies.
#. TEMPLATE_NOT_MATCHED: The series does not match any of the autosegmentation templates.
#. MULTIPLE_TEMPLATES_MATCHED: The series matches multiple autosegmentation templates.
#. MULTIPLE_TEMPLATES_FOUND: The series matches multiple autosegmentation templates.
#. NO_TEMPLATE_FOUND: The series does not match any of the autosegmentation templates.
#. READY_FOR_DEIDENTIFICATION: The series is ready for deidentification.
#. DEIDENTIFIED: The series has been deidentified.
#. DEIDENTIFICATION_FAILED: The series deidentification failed.
#. RTSTRUCT_EXPORT_FAILED: The RTStruct export failed.
#. RTSTRUCT_EXPORTED: The RTStruct has been exported.
#. ERROR: An error occurred during the processing of the series.

Series State Choices
---------------------

The following are the series state choices that are available in the DRAW Client.

#. PROCESSING: The series is being processed.
#. UNPROCESSED: The series has not been processed as the autosegmentation templates are not matched.
#. COMPLETE: The series has been processed completely.
#. FAILED: The series processing failed. Please see the Series Processing Logs for more details.


