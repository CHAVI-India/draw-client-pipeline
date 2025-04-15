#!/bin/bash

# Create staticfiles directory if it doesn't exist
mkdir -p /app/staticfiles

chown -R appuser:appuser /app/staticfiles

# Run Django commands as appuser
su appuser -c "python manage.py collectstatic --noinput"
su appuser -c "python manage.py migrate"
su appuser -c "python manage.py createsuperuser --noinput --username $DJANGO_SUPERUSER_USERNAME --email $DJANGO_SUPERUSER_EMAIL || true"

# Check if we're running Celery worker
if [ "$1" = "celery" ]; then
    exec su appuser -c "celery -A draw_client worker -l INFO"
# Check if we're running Celery beat
elif [ "$1" = "celery-beat" ]; then
    exec su appuser -c "celery -A draw_client beat -l INFO"
# Default to running Django with Gunicorn
else
    exec su appuser -c "python -m gunicorn draw_client.wsgi:application --bind 0.0.0.0:8000 --workers 3"
fi