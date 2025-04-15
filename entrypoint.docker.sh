#!/bin/bash

# Create logs directory if it doesn't exist
mkdir -p /app/logs

# Set up symlinks for log files to Docker stdout/stderr
# Define log files that should go to stdout
STDOUT_LOGS=("app.log" "django.log" "debug.log" "info.log" "celery.log" "celery_beat.log")
# Define log files that should go to stderr
STDERR_LOGS=("error.log" "critical.log")

# Create symlinks for stdout logs
for log_file in "${STDOUT_LOGS[@]}"; do
    ln -sf /dev/stdout "/app/logs/$log_file"
    echo "Linked $log_file to stdout"
done

# Create symlinks for stderr logs
for log_file in "${STDERR_LOGS[@]}"; do
    ln -sf /dev/stderr "/app/logs/$log_file"
    echo "Linked $log_file to stderr"
done

# Ensure proper ownership of all files
chown -R appuser:appuser /app/logs

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