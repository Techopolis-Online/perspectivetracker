import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perspectivetracker.settings')
django.setup()

from django.contrib.auth import get_user_model
from users.models import Role

User = get_user_model()

# Check if superuser exists
if not User.objects.filter(email='taylor@techopolis.online').exists():
    print('Creating superuser...')
    
    # Create the superuser
    user = User.objects.create_superuser(
        email='taylor@techopolis.online',
        first_name='Taylor',
        last_name='Arndt',
        password='Techopolis25@@'
    )
    
    print('Superuser created successfully!')
else:
    # Update existing superuser
    user = User.objects.get(email='taylor@techopolis.online')
    user.set_password('Techopolis25@@')
    user.is_staff = True
    user.is_superuser = True
    
    # Ensure admin role is assigned
    try:
        admin_role = Role.objects.get(name='admin')
        user.role = admin_role
    except Role.DoesNotExist:
        print('Admin role not found')
    
    user.save()
    print('Superuser updated successfully!') 