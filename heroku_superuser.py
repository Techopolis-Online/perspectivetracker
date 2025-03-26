import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perspectivetracker.settings')
django.setup()

from django.contrib.auth import get_user_model
from users.models import Role
from django.db import transaction

User = get_user_model()

def create_or_update_superuser():
    with transaction.atomic():
        # Get or create admin role
        admin_role, _ = Role.objects.get_or_create(name='admin')
        
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
            
            # Assign admin role
            user.role = admin_role
            user.save()
            
            print('Superuser created successfully!')
        else:
            # Update existing superuser
            user = User.objects.get(email='taylor@techopolis.online')
            user.set_password('Techopolis25@@')
            user.is_staff = True
            user.is_superuser = True
            user.role = admin_role
            user.save()
            print('Superuser updated successfully!')

if __name__ == '__main__':
    create_or_update_superuser() 