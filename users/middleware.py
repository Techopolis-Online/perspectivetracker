from django.contrib.auth import get_user_model
from social_django.models import UserSocialAuth
from users.models import Role
import logging

logger = logging.getLogger(__name__)

User = get_user_model()

class Auth0SyncMiddleware:
    """
    Middleware to check and sync Auth0 roles on each request
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Process request
        response = self.get_response(request)
        
        # Only check for authenticated users
        if request.user.is_authenticated:
            try:
                # Check if this is an Auth0 user
                auth0_user = UserSocialAuth.objects.filter(provider='auth0', user=request.user).first()
                if not auth0_user:
                    return response
                
                # Skip sync if user has been manually modified in admin
                if hasattr(request.user, 'manually_modified') and request.user.manually_modified:
                    logger.info(f"Skipping Auth0 sync for manually modified user: {request.user.email}")
                    return response
                
                # Get Auth0 roles
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
                    request.user.role != new_role or
                    request.user.is_staff != is_staff or
                    request.user.is_superuser != is_superuser
                )
                
                if needs_update:
                    # Update user's role and permissions
                    request.user.role = new_role
                    request.user.is_staff = is_staff
                    request.user.is_superuser = is_superuser
                    
                    # Ensure admins always have staff status and superusers always have staff access
                    if request.user.role and request.user.role.name == 'admin':
                        request.user.is_staff = True
                        request.user.is_superuser = True
                        logger.info(f"Ensuring admin {request.user.email} has staff and superuser status")
                    
                    if request.user.is_superuser:
                        request.user.is_staff = True
                        logger.info(f"Ensuring superuser {request.user.email} has staff access")
                    
                    request.user.save()
                    
                    logger.info(
                        f"Auto-synced Auth0 user via middleware {request.user.email}: role={new_role.name}, "
                        f"is_staff={request.user.is_staff}, is_superuser={request.user.is_superuser}"
                    )
                    
            except Exception as e:
                logger.error(f"Error auto-syncing Auth0 user via middleware: {str(e)}")
        
        return response 