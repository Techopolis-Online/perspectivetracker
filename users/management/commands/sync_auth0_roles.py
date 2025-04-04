from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from social_django.models import UserSocialAuth
from users.models import Role
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

User = get_user_model()

class Command(BaseCommand):
    help = 'Synchronize Auth0 roles with Django users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update all users, even if roles match',
        )

    def handle(self, *args, **options):
        force = options['force']
        
        try:
            with transaction.atomic():
                # Get all Auth0 users
                auth0_users = UserSocialAuth.objects.filter(provider='auth0')
                
                if not auth0_users.exists():
                    self.stdout.write(self.style.WARNING('No Auth0 users found'))
                    return
                
                updated_count = 0
                skipped_count = 0
                
                for auth0_user in auth0_users:
                    user = auth0_user.user
                    auth0_roles = auth0_user.extra_data.get('roles', [])
                    
                    # Determine the appropriate role based on Auth0 roles
                    new_role = None
                    is_staff = False
                    is_superuser = False
                    
                    if 'admin' in auth0_roles:
                        new_role, _ = Role.objects.get_or_create(name='admin')
                        is_staff = True
                        is_superuser = True
                    elif 'staff' in auth0_roles:
                        new_role, _ = Role.objects.get_or_create(name='staff')
                        is_staff = True
                    elif 'client' in auth0_roles:
                        new_role, _ = Role.objects.get_or_create(name='client')
                    else:
                        new_role, _ = Role.objects.get_or_create(name='user')
                    
                    # Check if update is needed
                    needs_update = (
                        force or
                        user.role != new_role or
                        user.is_staff != is_staff or
                        user.is_superuser != is_superuser
                    )
                    
                    if needs_update:
                        # Update user's role and permissions
                        user.role = new_role
                        user.is_staff = is_staff
                        user.is_superuser = is_superuser
                        user.save()
                        
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Updated {user.email}: role={new_role.name}, "
                                f"is_staff={is_staff}, is_superuser={is_superuser}"
                            )
                        )
                        updated_count += 1
                    else:
                        self.stdout.write(
                            f"Skipped {user.email}: already has correct role and permissions"
                        )
                        skipped_count += 1
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\nSync completed: {updated_count} users updated, {skipped_count} users skipped"
                    )
                )
                
        except Exception as e:
            logger.error(f"Error syncing Auth0 roles: {str(e)}")
            self.stdout.write(
                self.style.ERROR(f"Error syncing Auth0 roles: {str(e)}")
            ) 