
Installation the DRAW Client
=====================================

   


This document describes the steps to install the DRAW client on the local computer using Docker.


Prerequisites
-------------

You need to have a Docker desktop installed on your computer. 
To install Docker desktop, please refer to the `Docker Desktop <https://www.docker.com/products/docker-desktop/>`_ website.

Please review the official documentation for Docker Desktop installation here: https://docs.docker.com/desktop/install/windows-install/

.. note::
   You should choose the version of the windows which matches your CPU architecture. For example if you have a Intel or AMD CPU, you need to install the x86_64 version. If you have a M1 or M2 CPU, you need to install the arm64 version.


The following the minimum system requirements for Docker Desktop:

#. A 64 bit processor with Second Level Address Translation (SLAT)
#. 4GB of RAM
#. Enable Hardware virtualization in the BIOS

It is important to follow the instructions for Docker Desktop installation if you are not uising the computer as an administrator in Windows. Specially you need to ensure that the user that is you should be added to the docker-users group. 

After installation, you need to restart your computer. Additionally do no forget to share the directory where the application will be installed and the datastore folder within Docker Desktop. 
To do so please open the Docker Desktop application and click on the gear icon in the top right corner of the application. On the left side menu you will see a section called Resources. Click on it to open the submenu item called File sharing. There please ensure that the directory where the application will be installed and the datastore folder are shared. 

.. image:: images/docker_desktop_resource_sharing.png
   :alt: Docker Desktop File Sharing
   :width: 500
   :align: center



Installation
------------

The latest instructions for installation of the DRAW client can be found in the `DRAW Client GitHub repository <https://github.com/CHAVI-India/draw-client-pipeline>`_.
While the repository hosts the complete source code, for the docker based installation you should pay attention to the section called Installation using the Recommended Way in the `README.md <https://github.com/CHAVI-India/draw-client-pipeline/blob/main/README.md#recommended-way>`_ file.

Please refer to the instructions the page for the latest instructions (in the even there is a conflict with the instructions here and the README file the instructions in the README file will prevail).

Briefly the steps are:  

#. Create a new directory for the project in a folder of your choice. In a windows machine we recommend that you use the D: for the same.   
#. Create three files inside the directory:    

   #. docker-compose.yml    
   #. .env    
   #. nginx.conf  

Please play close attention to the name of the file called .env.docker. The dot in the beginning of the file name is important. It may be hidden in the file explorer.


.. note::
    The Datastore folder path is a key element that needs to be understood properly. For Radiotherapy autosegmentation, we have designed the system to automatically download DICOM files from a chose directory (either local or remote) and then process the files. For most centers this will be shared network drive where the DICOM files are send after the images are acquired before they are imported into the Treatment Planning System (TPS). However in some situations, this folder may be on the local machines, and the user may be sending the images to the local machine, after the scan is acquired. In such cases, we need to configure a system that will allow the local machine to act as a DICOM server able to accept DICOM files for the DRAW client to process. 



This folder path needs to be configured properly in the docker-compose.yml file. (please see the commented lines under the volumes section of the service called 'django-web'). If it is a remote folder it is important that this folder is shared as a network drive to the local machine. 

Additionaly, we recommend that you choose a strong password for the postgres database.

For reference here are the text for the three files

The docker-compose.yml file
---------------------------

Copy the file called example_docker-compose.yml from the docker_example_files folder in the repository and paste its contents into the docker-compose.yml file that you created in step 2.

.. literalinclude:: ../../docker_install_files/example_docker-compose.yml
  :language: yaml


.. note::
   There are 3 places in the docker-compose.yml file where the datastore path needs to be configured. Please make sure that you update all of them.

Please note the following configuration items:

#. If you are using a local folder as a datastore then the path should be provided in the section dicomdata at the bottom. However most commonly this folder will be a network shared folder. In that case we need the IP address, username, password and domain to log into the folder. Hence a cifs storage configuration is provided as an example.
#. The folder paths starting with a ./ indicate that the folder will be created at same folder where the docker-compose.yml file is located.
#. If you are using a proxy to get to internet then you need to provide the proxy settings in the .env file

.. note::
   We will inform you which is the correct version of the image to be used. Please make sure that you use the correct version of the image.

The .env file
---------------------

Copy the file called .env.docker.example from the docker_example_files folder in the repository and paste its contents into the .env file that you created in step 2.

Please note that the following environment variables are sensitive: 

#. SECRET_KEY - This is the secret key for the django application. You can generate a new secret key for the django application using the following website: https://djecrety.ir/
#. NETWORK_USER - This is the username for the network shared folder.
#. NETWORK_PASSWORD - This is the password for the network shared folder.
#. NETWORK_DOMAIN - This is the domain for the network shared folder.
#. POSTGRES_PASSWORD - This is the password for the postgres database.
#. DJANGO_SUPERUSER_PASSWORD - This is the password for the django superuser.
#. DJANGO_DB_PASSWORD - This is the password for the django database. This should be the same as the POSTGRES_PASSWORD.

You can generate a new secret key for the django application using the following website: https://djecrety.ir/



.. literalinclude:: ../../docker_install_files/.env.docker.example
  :language: bash

There are two sections which have been commmented out as they may not be required  for all cases:
The first is the proxy configuration which is used to access the internet from the container. The second is the section for the celery worker which is used to run the celery worker in the container.
The second is the CIFS storage configuration which is used to access the network shared folder from the container.


The nginx.conf file
---------------------

.. literalinclude:: ../../docker_install_files/example_nginx.conf
  :language: bash

We recommend that you copy paste the text first in the files instead of typing them. 


Running the DRAW Client
------------------------

You will need to open a terminal. The terminal is a special application that allows you to give commands to the computer in text. In Windows you can open the terminal by pressing the Windows key + R, then typing cmd and pressing Enter. You will need to navigate to the directory where you created the three files. Alternatively you can right click on the file explorer and click on 'Open in terminal'.

First ensure that Docker Desktop is running. Once you are in the directory where you created the three files, you can run the following command to start the DRAW Client:

.. code-block:: bash

  docker-compose up -d



This will start the DRAW Client and the other services that are required to run the DRAW Client. You can check the status of the services by running the following command:

.. code-block:: bash

  docker-compose ps


Docker Desktop Interface
------------------------

Alternatively in the Docker Desktop application you can see a new container name after the folder name running in the main page. 

.. image:: images/docker_desktop_container_activity.png
   :alt: Docker Desktop Container Showing Activity Indicator
   :width: 500
   :align: center

Clicking the name of the container will open a new tab in the Docker Desktop application showing the logs of the container as well as the status of each of the running containers.

.. image:: images/docker_desktop_detail_interface.png
   :alt: Docker Desktop Container Showing Detail Interface
   :width: 500
   :align: center



Accessing the DRAW Client
-------------------------

You can access the DRAW Client by opening a web browser and navigating to the following URL: http://localhost:8001

If you are accessing this for the first time, please click on the login link at the top right corner of the page. You will need to login as a superuser. 

The username and password are specified in the .env.docker file. You can use those credentials to login.

You should change the password after logging in. 







