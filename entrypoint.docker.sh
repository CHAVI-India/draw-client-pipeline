#!/bin/bash

# Update CA certificates if any are mounted
if [ -d "/usr/local/share/ca-certificates" ]; then
    update-ca-certificates
fi

# Create staticfiles directory if it doesn't exist and set permissions
mkdir -p /app/staticfiles
chown -R appuser:appuser /app/staticfiles

# Collect static files with proper permissions
python manage.py collectstatic --noinput
chown -R appuser:appuser /app/staticfiles

# Apply database migrations
python manage.py migrate

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

# Execute the main command
exec "$@"