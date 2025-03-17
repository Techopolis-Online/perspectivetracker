release: python manage.py migrate && python manage.py create_superuser
web: gunicorn perspectivetracker.wsgi --log-file - 