import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perspectivetracker.settings')
django.setup()

from users.models import Role

# Create roles if they don't exist
roles = [
    (Role.ADMIN, 'Administrator'),
    (Role.STAFF, 'Techopolis Staff'),
    (Role.CLIENT, 'Client'),
    (Role.USER, 'User'),
]

for role_name, role_display in roles:
    Role.objects.get_or_create(name=role_name)
    print(f"Role '{role_name}' created or verified.")

print("All roles have been created or verified.") 