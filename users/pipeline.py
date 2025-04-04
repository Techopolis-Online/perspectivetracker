import logging
from django.contrib.auth import get_user_model
from django.db import transaction
from users.models import Role
from django.conf import settings

logger = logging.getLogger(__name__)

User = get_user_model()

def get_user_role(backend, user, response, *args, **kwargs):
    """Assign user role based on Auth0 profile and ensure user sync"""
    try:
        with transaction.atomic():
            # Get or create default role
            default_role, _ = Role.objects.get_or_create(name='user')
            
            # Get Auth0 email
            auth0_email = response.get('email')
            if not auth0_email:
                logger.error("No email provided by Auth0")
                return None
                
            # Try to find existing user by email
            existing_user = User.objects.filter(email=auth0_email).first()
            
            if existing_user:
                logger.info(f"Found existing user: {auth0_email}")
                user = existing_user
                
                # Update user's information from Auth0
                user.first_name = response.get('given_name', user.first_name)
                user.last_name = response.get('family_name', user.last_name)
                
                # Check if user has admin role in Auth0
                auth0_roles = response.get('roles', [])
                if 'admin' in auth0_roles:
                    admin_role, _ = Role.objects.get_or_create(name='admin')
                    user.role = admin_role
                    user.is_staff = True
                    user.is_superuser = True
                elif 'staff' in auth0_roles:
                    staff_role, _ = Role.objects.get_or_create(name='staff')
                    user.role = staff_role
                    user.is_staff = True
                elif 'client' in auth0_roles:
                    client_role, _ = Role.objects.get_or_create(name='client')
                    user.role = client_role
                
                user.save()
            else:
                logger.info(f"Creating new user from Auth0: {auth0_email}")
                
                # Check Auth0 roles for new user
                auth0_roles = response.get('roles', [])
                role = default_role
                is_staff = False
                is_superuser = False
                
                if 'admin' in auth0_roles:
                    role, _ = Role.objects.get_or_create(name='admin')
                    is_staff = True
                    is_superuser = True
                elif 'staff' in auth0_roles:
                    role, _ = Role.objects.get_or_create(name='staff')
                    is_staff = True
                elif 'client' in auth0_roles:
                    role, _ = Role.objects.get_or_create(name='client')
                
                # Create new user with appropriate role and permissions
                user = User.objects.create(
                    email=auth0_email,
                    first_name=response.get('given_name', ''),
                    last_name=response.get('family_name', ''),
                    role=role,
                    is_staff=is_staff,
                    is_superuser=is_superuser
                )
            
            # Ensure social auth association
            social_auth = user.social_auth.filter(provider='auth0').first()
            if not social_auth:
                user.social_auth.create(
                    provider='auth0',
                    uid=response.get('sub'),
                    extra_data=response
                )
            else:
                social_auth.extra_data = response
                social_auth.save()
            
            logger.info(f"Successfully synced user with Auth0: {auth0_email}")
            return {'user': user}
            
    except Exception as e:
        logger.error(f"Error in get_user_role pipeline: {str(e)}")
        return None 