release: python manage.py migrate --noinput && python manage.py migrate sessions --noinput && python create_roles.py && python heroku_superuser.py
web: gunicorn perspectivetracker.wsgi --log-file - 