from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from users.models import Role

class Command(BaseCommand):
    help = 'Creates a superuser account'

    def handle(self, *args, **options):
        User = get_user_model()
        
        if not User.objects.filter(email='taylor@techopolis.online').exists():
            self.stdout.write(self.style.SUCCESS('Creating superuser...'))
            
            # Create the superuser
            user = User.objects.create_user(
                email='taylor@techopolis.online',
                first_name='Taylor',
                last_name='Arndt',
                password='Techopolis25@@',
                is_staff=True,
                is_superuser=True,
            )
            
            # Assign admin role if it exists
            try:
                admin_role = Role.objects.get(name='admin')
                user.role = admin_role
                user.save()
                self.stdout.write(self.style.SUCCESS('Admin role assigned'))
            except Role.DoesNotExist:
                self.stdout.write(self.style.WARNING('Admin role not found'))
            
            self.stdout.write(self.style.SUCCESS('Superuser created successfully!'))
        else:
            self.stdout.write(self.style.SUCCESS('Superuser already exists')) 