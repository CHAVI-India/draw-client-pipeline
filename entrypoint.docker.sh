#!/bin/bash

# Create the staticfiles directory if it doesn't exist and set ownership to appuser
mkdir -p staticfiles
mkdir -p static
chown -R appuser:appuser staticfiles

# Apply database migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Create superuser if it doesn't exist
python manage.py createsuperuser --noinput --username $DJANGO_SUPERUSER_USERNAME --email $DJANGO_SUPERUSER_EMAIL

# Check if we're running Celery worker
if [ "$1" = "celery" ]; then
    exec celery -A draw_client worker -l INFO
# Check if we're running Celery beat
elif [ "$1" = "celery-beat" ]; then
    exec celery -A draw_client beat -l INFO
# Default to running Django with Gunicorn
else
    exec python -m gunicorn draw_client.wsgi:application --bind 0.0.0.0:8000 --workers 3
fi