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

2. Create a docker-compose.yml file with the following content:
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
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=draw-client
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
    image: ghcr.io/chavi-india/draw-client-pipeline:release
    container_name: django-docker
    depends_on:
      - db
    env_file:
      - .env.docker      
    volumes:
      - ./logs:/app/logs
      - ./static:/app/staticfiles
      - /path/to/your/datastore:/app/datastore  # Modify this to match your datastore path
    command: ["./entrypoint.docker.sh"]

  celery:
    image: ghcr.io/chavi-india/draw-client-pipeline:release
    container_name: celery-docker
    command: ["./entrypoint.docker.sh", "celery"]
    volumes:
      - ./static:/app/staticfiles
      - ./logs:/app/logs
    env_file:
      - .env.docker
    depends_on:
      - django-web
      - rabbitmq

  celery-beat:
    image: ghcr.io/chavi-india/draw-client-pipeline:release
    container_name: celery-beat-docker
    command: ["./entrypoint.docker.sh", "celery-beat"]
    volumes:
      - ./static:/app/staticfiles
      - ./logs:/app/logs
    env_file:
      - .env.docker
    depends_on:
      - django-web
      - rabbitmq

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
```

3. Create a .env.docker file in the same directory:
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

# Postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=draw-client

# API URLs
API_URL=https://draw.chavi.ai/api/models/
MODEL_API_URL=https://draw.chavi.ai/models

# Celery
CELERY_BROKER_URL=pyamqp://guest:guest@rabbitmq:5672

# Django Superuser
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_PASSWORD=admin
DJANGO_SUPERUSER_EMAIL=admin@example.com
```

4. Create the logs and static directories:
```
mkdir logs static
```

5. Create a basic nginx.conf file (required for the nginx container):
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

6. Start the services:
```
docker-compose up -d
```

7. Access the DRAW client interface at http://localhost:8001

8. To stop the services:
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

## Configure environment
1. Create a .env file in the project root. You can copy the sample_env.txt file to get started:
```
# Django Security
SECRET_KEY=your_secret_key_here
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000

# Django DB
DJANGO_DB_ENGINE=django.db.backends.postgresql
DJANGO_DB_NAME=draw-client
DJANGO_DB_USER=postgres
DJANGO_DB_PASSWORD=postgres
DJANGO_DB_HOST=localhost
DJANGO_DB_PORT=5432

# API URLs
API_URL=https://draw.chavi.ai/api/models/
MODEL_API_URL=https://draw.chavi.ai/models

# Celery
CELERY_BROKER_URL=pyamqp://guest:guest@localhost:5672

# Django Superuser
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_PASSWORD=admin
DJANGO_SUPERUSER_EMAIL=admin@example.com
```

## Create logs directory
1. Create a logs directory for application logging:
```
mkdir logs
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


