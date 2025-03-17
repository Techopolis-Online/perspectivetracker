release: python manage.py migrate && python create_roles.py && python heroku_superuser.py
web: gunicorn perspectivetracker.wsgi --log-file - 