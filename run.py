import os
import sys
from pathlib import Path

def run_development():
    """Run the development server with development settings"""
    os.environ['DJANGO_ENV'] = 'development'
    os.environ['DEBUG'] = 'True'
    os.environ['SECURE_SSL_REDIRECT'] = 'False'
    os.environ['SOCIAL_AUTH_REDIRECT_IS_HTTPS'] = 'False'
    # Force disable SSL redirect
    print("Starting development server with SSL disabled...")
    os.system('python manage.py runserver --nothreading --insecure 0.0.0.0:8000')

def run_production():
    """Run the production server with production settings"""
    os.environ['DJANGO_ENV'] = 'production'
    os.system('gunicorn perspectivetracker.wsgi --log-file - --workers 2 --timeout 120 --access-logfile - --error-logfile - --capture-output --enable-stdio-inheritance')

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'prod':
        run_production()
    else:
        run_development() 