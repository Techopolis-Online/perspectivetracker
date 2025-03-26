import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perspectivetracker.settings')
django.setup()

from django.contrib.auth import get_user_model
from users.models import Role  # Import Role since we'll need it

User = get_user_model()

# Define the superuser credentials
username = 'admin'
email = 'admin@example.com'
password = 'Temp123!'  # Change this to a secure password

# Check if the user already exists
if not User.objects.filter(email=email).exists():
    print(f"Creating superuser {username} with email {email}")
    
    # Create the admin role if it doesn't exist
    admin_role, created = Role.objects.get_or_create(name='admin')
    
    # Create the superuser
    user = User.objects.create_superuser(
        username=username,
        email=email,
        password=password
    )
    
    # Set the role (if needed based on your model)
    user.role = admin_role
    user.save()
    
    print(f"Superuser created successfully: {username}")
else:
    print(f"User with email {email} already exists")

print("Done!") 