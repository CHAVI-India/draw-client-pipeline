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


2. Ensure that you have the correct folder path for the **datastore folder**. See the commented section in the docker-compose.yml file below. Ensure that the folder exists. Additionally if in Windows then change all \ to a / in the folder path. 

The other folders are as follows:

| Host Folder Name | Docker Folder Name | Purpose |
| ---- | ----- | ---- |
| logs | /app/logs | This folder will have all the logs of the application |
| static | /app/static | This folder stores the static files |
| dicom | /app/folders | This folder stores the dicom data that is being processed |
| yaml-templates | /app/yaml-templates | This folder has all the autosegmentation templates created for the DRAW client |

Then create a docker-compose.yml file with the following content:
```yaml
services:
  db:
    image: postgres:17
    container_name: postgres-docker
    ports:
      - "5433:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    env_file:
      - .env.docker
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 5
  rabbitmq:
    image: rabbitmq:3.12-management
    container_name: rabbitmq-docker
    ports:
      - "5675:5672"
      - "15675:15672"
    environment:
      - RABBITMQ_DEFAULT_USER=guest
      - RABBITMQ_DEFAULT_PASS=guest

  django-web:
    image: chaviapp/drawclient:release
    container_name: django-docker
    depends_on:
      db:
        condition: service_healthy
    env_file:
      - .env.docker      
    volumes:
      - app_data:/app
      - ./logs:/app/logs
      - ./static:/app/static
      - ./dicom:/app/folders      
      - ./yaml-templates:/app/yaml-templates
      - "/mnt/share/dicom_processing_test/datastore:/app/datastore" # Modify this line to match the path of the datastore for the machine. Keep the /app/datastore path as it is as it will map to a specific directory inside the container.
    command: ["./entrypoint.docker.sh"]

  celery:
    image: chaviapp/drawclient:release
    container_name: celery-docker
    command: ["./entrypoint.docker.sh", "celery"]
    volumes:
      - app_data:/app
      - ./static:/app/static
      - ./logs:/app/logs
      - ./dicom:/app/folders      
      - ./yaml-templates:/app/yaml-templates
      - "/mnt/share/dicom_processing_test/datastore:/app/datastore" # Modify this line to match the path of the datastore for the machine. Keep the /app/datastore path as it is as it will map to a specific directory inside the container.
    env_file:
      - .env.docker
    depends_on:
      db:
        condition: service_healthy
      django-web:
        condition: service_started
      rabbitmq:
        condition: service_started

  celery-beat:
    image: chaviapp/drawclient:release
    container_name: celery-beat-docker
    command: ["./entrypoint.docker.sh", "celery-beat"]
    volumes:
      - app_data:/app
      - ./static:/app/static
      - ./logs:/app/logs
      - ./dicom:/app/folders      
      - ./yaml-templates:/app/yaml-templates  
      - "/mnt/share/dicom_processing_test/datastore:/app/datastore" # Modify this line to match the path of the datastore for the machine. Keep the /app/datastore path as it is as it will map to a specific directory inside the container.
    env_file:
      - .env.docker
    depends_on:
      db:
        condition: service_healthy
      django-web:
        condition: service_started
      rabbitmq:
        condition: service_started

  frontend-proxy:
    image: nginx:latest
    container_name: nginx-docker
    ports:
      - "8001:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./static:/static:ro
    depends_on:
      - django-web
volumes:
  postgres_data:
  app_data:
```

Please note there is a docker-compose.yml file in the repository which allows you to "BUILD" the docker image. The example docker-compose section above allows you to pull the latest image from the dockerhub repository.


3. Create a .env.docker file in the same directory. Please make sure that the file name is correct and note the presence of the . before the name which indicates that this is a hidden file.:

```
# Django Security
SECRET_KEY=your_secret_key_here
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:8001,http://127.0.0.1:8001

# Django DB
DJANGO_DB_ENGINE=django.db.backends.postgresql
DJANGO_DB_NAME=draw-client
DJANGO_DB_USER=postgres
DJANGO_DB_PASSWORD=postgres
DJANGO_DB_HOST=db
DJANGO_DB_PORT=5432

# Postgres (credentials for database. Ensure database username and password supplied here match what is provided to the section above).
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=draw-client

# API URLs (these URLs point to the server)
API_URL=https://draw.chavi.ai/api/models/
MODEL_API_URL=https://draw.chavi.ai/models

# Celery (Required for tasks)
CELERY_BROKER_URL=pyamqp://guest:guest@rabbitmq:5672

# Django Superuser (Used to create a superuser at the application start)
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_PASSWORD=admin
DJANGO_SUPERUSER_EMAIL=admin@example.com

# Proxy setting
# HTTP_PROXY = http://proxy.example.com:8080
# HTTPS_PROXY = http://proxy.example.com:8080
# NO_PROXY = localhost,127.0.0.1,db,rabbitmq

```

  
> **Important**: Configuring the correct proxy settings is needed if you hospital connects to the internet through a proxy server. Please contact your IT personnel to get the complete string as it may require special authentication also. The above example is for a proxy which does not require authentication.

4. Create a nginx.conf file (required for the nginx container):
```
# Sets the max number of simultaneous connections that can be opened by a worker process
events {
   worker_connections 1024;
}

http {
   server {
       include mime.types;
       default_type application/octet-stream;
       sendfile on;
       keepalive_timeout 65;
       listen 80;
       client_max_body_size 1024M; # Add this line to increase the maximum upload size to 1024MB

       # Requests to /static/ are served directly from the /static/ directory
       location /static/ {
           alias /static/;
           expires 7d;
       }

       # Configuration for serving media files
       # location /media/ {
       #     alias /home/app/web/mediafiles/;
       # }

       # Handles all other requests
       location / {
           # Forward requests to Django application
           proxy_pass http://django-web:8000;

           # Pass important headers to Django for proper request handling
           proxy_set_header Host $host;                          # Original host header
           proxy_set_header X-Real-IP $remote_addr;             # Client's real IP
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;  # Chain of IP addresses
           proxy_set_header X-Forwarded-Proto $scheme;          # Original protocol (http/https)
       }
   }
}
```

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


