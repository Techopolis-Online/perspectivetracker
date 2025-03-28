from django.core.management.base import BaseCommand, CommandError
from users.models import CustomUser, Role
from django.db import transaction
from social_django.models import UserSocialAuth
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Updates role for Auth0 users by email'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Email of the Auth0 user to update')
        parser.add_argument('role', type=str, help='New role name (admin, staff, client, user)')
        parser.add_argument('--all-users', action='store_true', help='Update all Auth0 users with matching email domain')
        parser.add_argument('--domain', type=str, help='Email domain to match when using --all-users')

    def handle(self, *args, **options):
        email = options['email']
        role_name = options['role']
        all_users = options.get('all_users', False)
        domain = options.get('domain', None)
        
        # Validate the role
        valid_roles = [choice[0] for choice in Role.ROLE_CHOICES]
        if role_name not in valid_roles:
            raise CommandError(f"Invalid role name. Choose from: {', '.join(valid_roles)}")
        
        try:
            # Get the target role
            role = Role.objects.get(name=role_name)
            
            # Start transaction
            with transaction.atomic():
                if all_users and domain:
                    # Get all Auth0 users with matching domain
                    auth0_users = UserSocialAuth.objects.filter(
                        provider='auth0',
                        user__email__endswith=f'@{domain}'
                    )
                    
                    if not auth0_users.exists():
                        self.stdout.write(self.style.WARNING(f"No Auth0 users found with email domain @{domain}"))
                        return
                    
                    count = 0
                    for auth0_user in auth0_users:
                        user = auth0_user.user
                        
                        # Skip users that already have the target role
                        if user.role and user.role.name == role_name:
                            self.stdout.write(f"User {user.email} already has role {role_name}")
                            continue
                            
                        # Update the user's role
                        old_role = user.role.name if user.role else 'None'
                        user.role = role
                        user.save()
                        count += 1
                        self.stdout.write(self.style.SUCCESS(f"Updated {user.email} from {old_role} to {role_name}"))
                    
                    self.stdout.write(self.style.SUCCESS(f"Successfully updated {count} Auth0 user(s) with domain @{domain}"))
                
                else:
                    # Get the specific user by email
                    try:
                        user = CustomUser.objects.get(email=email)
                        
                        # Check if this is an Auth0 user
                        auth0_user = UserSocialAuth.objects.filter(provider='auth0', user=user).first()
                        if not auth0_user:
                            self.stdout.write(self.style.WARNING(f"User {email} is not authenticated via Auth0"))
                        
                        # Check current role
                        if user.role and user.role.name == role_name:
                            self.stdout.write(self.style.SUCCESS(f"User {email} already has role {role_name}"))
                            return
                        
                        # Update the user's role
                        old_role = user.role.name if user.role else 'None'
                        user.role = role
                        user.save()
                        self.stdout.write(self.style.SUCCESS(f"Updated {email} from {old_role} to {role_name}"))
                        
                    except CustomUser.DoesNotExist:
                        raise CommandError(f"User with email {email} does not exist")
                        
        except Role.DoesNotExist:
            raise CommandError(f"Role '{role_name}' does not exist. Please run migrations first.")
        except Exception as e:
            logger.error(f"Error updating Auth0 user role: {str(e)}")
            raise CommandError(f"Failed to update role: {str(e)}")