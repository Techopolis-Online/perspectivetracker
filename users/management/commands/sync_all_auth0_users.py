from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from social_django.models import UserSocialAuth
from users.models import Role
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

User = get_user_model()

class Command(BaseCommand):
    help = 'Synchronize all Auth0 users with their roles and permissions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update all users, including manually modified fields',
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
                manually_modified_count = 0
                
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
                        (not user.manually_modified and (
                            user.role != new_role or
                            user.is_staff != is_staff or
                            user.is_superuser != is_superuser
                        )) or
                        (user.manually_modified and force)
                    )
                    
                    if needs_update:
                        # If user has been manually modified and force is not set, preserve all manually modified fields
                        if user.manually_modified and not force:
                            self.stdout.write(
                                f"User {user.email} is manually modified - preserving all manually modified fields"
                            )
                            # Get the original user to check which fields were modified
                            try:
                                original_user = User.objects.get(pk=user.pk)
                                
                                # Check if fields were modified by comparing with original values
                                role_modified = original_user.role != user.role
                                staff_modified = original_user.is_staff != user.is_staff
                                superuser_modified = original_user.is_superuser != user.is_superuser
                                
                                # Only update fields that weren't manually modified
                                if not role_modified:
                                    user.role = new_role
                                if not staff_modified:
                                    user.is_staff = is_staff
                                if not superuser_modified:
                                    user.is_superuser = is_superuser
                                    
                                self.stdout.write(
                                    f"Field modification status for {user.email}: "
                                    f"role_modified={role_modified}, staff_modified={staff_modified}, "
                                    f"superuser_modified={superuser_modified}"
                                )
                                    
                            except User.DoesNotExist:
                                pass
                            manually_modified_count += 1
                        else:
                            # Update all fields
                            user.role = new_role
                            user.is_staff = is_staff
                            user.is_superuser = is_superuser
                            
                            # If force is set, reset the manually_modified flag
                            if force and user.manually_modified:
                                user.manually_modified = False
                                self.stdout.write(
                                    self.style.WARNING(
                                        f"Resetting manually_modified flag for {user.email}"
                                    )
                                )
                        
                        # Ensure admins always have staff status and superusers always have staff access
                        if user.role and user.role.name == 'admin':
                            user.is_staff = True
                            user.is_superuser = True
                            self.stdout.write(
                                f"Ensuring admin {user.email} has staff and superuser status"
                            )
                        
                        if user.is_superuser:
                            user.is_staff = True
                            self.stdout.write(
                                f"Ensuring superuser {user.email} has staff access"
                            )
                        
                        user.save()
                        
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Updated {user.email}: "
                                f"role={'preserved' if user.manually_modified and not force else new_role.name}, "
                                f"is_staff={'preserved' if user.manually_modified and not force else is_staff}, "
                                f"is_superuser={'preserved' if user.manually_modified and not force else is_superuser}"
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
                        f"\nSync completed: {updated_count} users updated, {skipped_count} users skipped, "
                        f"{manually_modified_count} users with preserved fields"
                    )
                )
                
        except Exception as e:
            logger.error(f"Error syncing Auth0 users: {str(e)}")
            self.stdout.write(
                self.style.ERROR(f"Error syncing Auth0 users: {str(e)}")
            ) 