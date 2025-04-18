# Welcome to the DRAW Client Repository

Deep learning for Radiotherapy Autosegmentation Workflow (DRAW) has been developed by Tata Medical Center, Kolkata and Indian Institute of Technology, Kharagpur to provide Radiation Oncologists with a flexible, automated autosegmentation solution. Please visit the website https://draw.chavi.ai for further details on the project. This repository hosts the code for the client software.

# DRAW Architecture

DRAW uses a client-server architecture to enable parallel autosegmentation across multiple geographically and temporally distributed centers. A central server is hosted at https://draw.chavi.ai. The client software is installed in the local machines and communicates securly with the central server. 

# DRAW Client
The present repository hosts the code for the DRAW client. The DRAW client performs several tasks:


1. It fetches DICOM data from a pre-defined datastorage location (located on the network or on the local machine) at configurable intervals.  
2. It processes the DICOM data to ensure that only specific types of DICOM images are processed.  
3. It checks the DICOM metadata and matches the autosegmentation template to be used for the autosegmentation process.   
4. It de-identifies the DICOM data and uploads it to the server for autosegmentation. 
5. It periodically polls the server to determine the status of the segmentation. When segmentation is completed, it will retrieve the segmented RTStruct object from the server.
6. Post retrieval it re-identifies the DICOM data and moves it to the datastorage location such that it can be imported into the planning system. 

Additionally it allows users to create autosegmentation templates by selecting the DRAW models avaialble on the server. After the template is created it allows the users to create rules to match the DICOM metadata to the autosegmentation template.

Finally it provides an UI to the user so that entire process is observable.

# Installation

## Recommended way

We recommend using docker to install and use the DRAW client. The docker based installation is easier and works across system architectures. Please follow the following steps.

### Docker Installation

#### Windows
1. Download Docker Desktop from [Docker's website](https://www.docker.com/products/docker-desktop/)
2. Run the installer and follow the on-screen instructions
3. Start Docker Desktop after installation

#### macOS
1. Download Docker Desktop from [Docker's website](https://www.docker.com/products/docker-desktop/)
2. Drag Docker to your Applications folder
3. Launch Docker Desktop
4. Follow the on-screen instructions to complete setup

#### Linux
```
sudo apt update
sudo apt install docker.io docker-compose
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```
Log out and back in for group changes to take effect.

### DRAW Client Installation

1. Create a project directory and navigate to it:
```
mkdir draw-client
cd draw-client
```

> **IMPORTANT**: The datastore folder is the location where your DICOM files are stored and where the DRAW client will look for new files to process. This folder must exist and be accessible to Docker. The DRAW client will monitor this folder for new DICOM files and will also save the processed RTStruct files back to this location. Note that this can be a network storage folder where the DICOM data are saved before importing to the TPS. A periodic task will fetch new images from the directory and process them for autosegmentation.


2. Ensure that you have the correct folder path for the **datastore folder** in the volumes section. See the commented section in the docker-compose.yml file below. Ensure that the folder exists. Additionally if in Windows then change all \ to a / in the folder path. 

The other folders are as follows:

| Host Folder Name | Docker Folder Name | Purpose |
| ---- | ----- | ---- |
| staticfiles | /app/staticfiles | This folder stores the static files |
| dicom | /app/folders | This folder stores the dicom data that is being processed |
| yaml-templates | /app/yaml-templates | This folder has all the autosegmentation templates created for the DRAW client |

See the file example_docker-compose.yml file inside the docker_install_files folder repository and copy the contents into a new file called docker-compose.yml. 
Please note there is a docker-compose.yml file in the main repository which allows you to "BUILD" the docker image. The example_docker-compose.yml file allows you to "PULL" the latest image from the dockerhub repository.


3. Create a .env file in the same directory. Please make sure that the file name is correct and note the presence of the . before the name which indicates that this is a hidden file. See the file called .env.docker.example for the content that has to be included in this file.

  
> **Important**: Configuring the correct proxy settings is needed if you hospital connects to the internet through a proxy server. Please contact your IT personnel to get the complete string as it may require special authentication also. The above example is for a proxy which does not require authentication.

4. Create a nginx.conf file (required for the nginx container) by copying the contents of the  example_nginx.conf file in the repository

5. Start the services:
```
docker-compose up -d
```

6. Access the DRAW client interface at http://localhost:8001

7. To stop the services:
```
docker-compose down
```

## Alternate way

The alternate way is to use without docker. This requires a unix based machine as several components need to be run which are not possible on Windows. 

The following are the steps to run and install the application without docker assuming that a debian based distribution like Ubuntu is being used.

## Pre-requisites

### Install Python
1. Install Python 3.10+ (recommended for Django compatibility)
```
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

### Install RabbitMQ
1. Install RabbitMQ for the Celery message broker:
```
sudo apt install rabbitmq-server
sudo systemctl enable rabbitmq-server
sudo systemctl start rabbitmq-server
```

### Install PostgreSQL
1. Install PostgreSQL database:
```
sudo apt install postgresql postgresql-contrib
```

2. Create a database and user:
```
sudo -u postgres psql
CREATE DATABASE "draw-client";
CREATE USER postgres WITH PASSWORD 'postgres';
GRANT ALL PRIVILEGES ON DATABASE "draw-client" TO postgres;
\q
```

## Clone repository
1. Clone the DRAW client repository:
```
git clone https://github.com/chavi-india/draw-client-pipeline.git
cd draw-client-pipeline
```

## Create a python virtual environment
1. Create and activate a virtual environment:
```
python3 -m venv venv
source venv/bin/activate
```

## Install requirements
1. Install the required Python packages:
```
pip install -r requirements.txt
```

## Create a new environment variable file:

1. Create a .env file in the project root. You can copy the sample_env.txt file to get started.:
```
SECRET_KEY = &^&7stc^ijtq1e0a280=0w8g-luul^au^^13=p6ko1c8jwahn
DJANGO_DEBUG = True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost

DJANGO_DB_ENGINE=django.db.backends.postgresql # Add engine of the database
DJANGO_DB_NAME=draw-client # Add name of the database
DJANGO_DB_USER=postgres # Add username of the database
DJANGO_DB_PASSWORD= # Add password of the database
DJANGO_DB_HOST=localhost # Add host of the database
DJANGO_DB_PORT=5432 # Add port of the database


API_URL = http://draw.recode-with-r.com/api/models/
MODEL_API_URL = http://draw.recode-with-r.com/models
CELERY_BROKER_URL = pyamqp://guest:gues@localhost:5672

```

## Migrate the database
1. Run database migrations:
```
python manage.py migrate
```

## Create superuser
1. Create a Django admin superuser:
```
python manage.py createsuperuser --username admin --email admin@example.com
```

## Collect static files
1. Collect static files:
```
python manage.py collectstatic --noinput
```

## Run the application
1. Start the Django development server:
```
python manage.py runserver 0.0.0.0:8000
```

2. In a separate terminal, start Celery worker (with virtual environment activated):
```
source venv/bin/activate
celery -A draw_client worker -l INFO
```

3. In another terminal, start Celery beat for scheduled tasks:
```
source venv/bin/activate
celery -A draw_client beat -l INFO
```

4. Access the DRAW Client interface at http://localhost:8000

## Production deployment
For production deployment, it's recommended to use Gunicorn as the WSGI server and configure Nginx as a reverse proxy:

1. Install Gunicorn:
```
pip install gunicorn
```

2. Run with Gunicorn:
```
gunicorn draw_client.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

3. Configure Nginx as a reverse proxy (sample configuration):
```
server {
    listen 80;
    server_name your_domain.com;

    location /static/ {
        alias /path/to/draw-client-pipeline/static/;
        expires 7d;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}


