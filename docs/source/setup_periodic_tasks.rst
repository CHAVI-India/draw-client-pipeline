Setup Periodic Tasks
=====================

The periodic tasks are used to schedule the tasks to be executed at specified intervals. The periodic tasks are defined in the DRAW client admin interface.

The following periodic tasks need to be setup:

.. list-table:: Periodic Tasks
   :widths: 10 60 20 10
   :header-rows: 1

   * - Task Name
     - Description
     - Task ID
     - Recommended Interval

   * - Copy DICOM
     - This task copies the DICOM files from the datastore to the DRAW server after proper processing, attaching the autosegmentation template, deidentifying the Data and finally sending the DICOM files to the DRAW server for autosegmentation.
     - dicom_handler.tasks.copy_dicom
     - 10 minutes

   * - Poll Server
     - This task polls the DRAW server to check if there are any pending transfers. If there are, it will copy the DICOM RTSTRUCT files from the DRAW server to the datastore.
     - api_client.tasks.poll_pending_transfes_task
     - 15 minutes

   * - Notify Server
     - Notify the DRAW server that the RTSTRUCT files have been received successfully. This allows the DRAW server to delete the files in the server.
     - api_client.tasks.notify_completed_transfers_task
     - 1 hour

   * - Reidentify DICOM
     - Reidentify the DICOM RTSTRUCT files after they have been autosegmented. After that it will move the DICOM RTSTRUCT files to the datastore to the folder where the patient data is stored.
     - api_client.tasks.reidentify_rtstruct
     - 10 minutes

Note that these recommended intervals are based on the case load at Tata Medical Center. If you are using the DRAW client at a different institution, you may need to adjust the intervals based on the case load at your institution. As a general rule of thumb, these intervals are ok if you have 20 - 25 patients undergoing CT scans per day. If you have a lower case load, then you can increase the intervals for the Notify Server and Poll Server tasks.

How to setup the periodic tasks
--------------------------------

Go to the DRAW client admin interface and click on the menu item called Scheduled Tasks under the Task Scheduling Section. You can see all the scheduled tasks that are currently configured. Clicking on the circular button with the plus sign will allow you to add a new task.

.. image:: images/scheduled_tasks.png
   :alt: Scheduled Tasks
   :width: 100%

Enter the name of the new task (we suggest giving an informative name) and select the task to be registered from the dropdown menu (see the table above for the task IDs).

.. image:: images/scheduled_tasks_add1.png
   :alt: Add Scheduled Task
   :width: 100%

Scrolling down further will allow you to configure the schedule. We recommend that you select the Interval Schedule option. If you are doing this for the first time, the dropdown will be empty as no schedules are defined. Click on the + button to add a new schedule. Remember to 

.. image:: images/scheduled_tasks_add2.png
   :alt: Add Schedule
   :width: 100%

Enter the interval number and select minute, second etc as the time unit and click on the Save button to add a new interval schedule.

.. image:: images/scheduled_tasks_add3.png
   :alt: Add Schedule
   :width: 100%

Leave the rest of the fields as is and click on the Save button to add the new task.