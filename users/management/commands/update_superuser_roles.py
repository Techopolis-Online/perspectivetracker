from django.core.management.base import BaseCommand
from users.models import CustomUser, Role

class Command(BaseCommand):
    help = 'Updates all superusers to have the admin role'

    def handle(self, *args, **options):
        try:
            admin_role = Role.objects.get(name=Role.ADMIN)
            superusers = CustomUser.objects.filter(is_superuser=True)
            
            if not superusers.exists():
                self.stdout.write(self.style.WARNING('No superusers found in the system.'))
                return
            
            count = 0
            for user in superusers:
                if user.role is None or user.role.name != Role.ADMIN:
                    user.role = admin_role
                    user.save()
                    count += 1
                    self.stdout.write(self.style.SUCCESS(f'Updated {user.email} to admin role'))
            
            if count == 0:
                self.stdout.write(self.style.SUCCESS('All superusers already have admin role.'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Successfully updated {count} superuser(s) to admin role.'))
                
        except Role.DoesNotExist:
            self.stdout.write(self.style.ERROR('Admin role does not exist. Please run migrations first.')) 