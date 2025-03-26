#!/usr/bin/env python
"""
Django management command to create a superuser.
To be used on Heroku with:
heroku run python create_admin.py
"""
import os
import django
from django.core.management import call_command

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perspectivetracker.settings')
django.setup()

# Define credentials as environment variables
os.environ['DJANGO_SUPERUSER_USERNAME'] = 'admin'
os.environ['DJANGO_SUPERUSER_EMAIL'] = 'admin@example.com'
os.environ['DJANGO_SUPERUSER_PASSWORD'] = 'Temp123!'

print("Creating superuser...")
try:
    # Use Django's built-in createsuperuser command with --noinput flag
    call_command('createsuperuser', interactive=False, verbosity=1, noinput=True)
    print("Superuser created successfully!")
except Exception as e:
    print(f"Error creating superuser: {e}")
    
print("Done!") 