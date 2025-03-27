python manage.py collectstatic --noinput
python manage.py migrate
python manage.py createsuperuser --noinput --username admin --email admin@example.com
python manage.py celery draw_client worker --loglevel=info
python manage.py celery draw_client beat --loglevel=info
python -m gunicorn draw_client.wsgi:application --bind 0.0.0.0:8000 --workers 3 --threads 2 --worker-class gthread --timeout 120 --keep-alive 5 --max-requests 1000 --max-requests-jitter 50 --log-level info --access-logfile - --error-logfile -