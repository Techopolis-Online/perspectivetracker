"""
Script to run Django development server with SSL completely disabled
"""
import os
import sys
import subprocess

if __name__ == '__main__':
    # Set all environment variables to disable SSL
    os.environ['DJANGO_ENV'] = 'development'
    os.environ['DEBUG'] = 'True'
    os.environ['SECURE_SSL_REDIRECT'] = 'False'
    os.environ['SOCIAL_AUTH_REDIRECT_IS_HTTPS'] = 'False'
    os.environ['HTTPS'] = 'off'
    os.environ['wsgi.url_scheme'] = 'http'
    
    # Remove any SSL proxy headers
    os.environ.pop('HTTP_X_FORWARDED_PROTO', None)
    
    print("Starting Django server with SSL completely disabled...")
    print("Once running, access the site at: http://localhost:8000")
    
    # Run Django server with SSL disabled
    cmd = [
        sys.executable,
        'manage.py',
        'runserver',
        '--insecure',
        '0.0.0.0:8000'
    ]
    
    subprocess.run(cmd, env=os.environ) 