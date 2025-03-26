import os
import django
from django.db import transaction

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perspectivetracker.settings')
django.setup()

from users.models import Role

def create_roles():
    with transaction.atomic():
        # Create roles if they don't exist
        roles = [
            (Role.ADMIN, 'Administrator'),
            (Role.STAFF, 'Techopolis Staff'),
            (Role.CLIENT, 'Client'),
            (Role.USER, 'User'),
        ]

        for role_name, role_display in roles:
            role, created = Role.objects.get_or_create(
                name=role_name,
                defaults={'display_name': role_display}
            )
            if created:
                print(f"Role '{role_name}' created.")
            else:
                print(f"Role '{role_name}' already exists.")

        print("All roles have been created or verified.")

if __name__ == '__main__':
    create_roles() 