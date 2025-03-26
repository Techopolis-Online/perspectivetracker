release: python manage.py migrate --noinput && python create_roles.py && python heroku_superuser.py
web: gunicorn perspectivetracker.wsgi --log-file - 