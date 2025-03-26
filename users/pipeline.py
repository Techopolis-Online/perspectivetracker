from .models import Role
import os
import logging

logger = logging.getLogger(__name__)

def get_user_role(backend, user, response, *args, **kwargs):
    """
    Pipeline function to assign a default role to users authenticated via Auth0.
    By default, users are assigned the 'user' role.
    """
    logger.info(f"Processing user role assignment for user {user.email}")
    
    if user and not user.role:
        try:
            # Assign default user role
            user_role = Role.objects.get(name=Role.USER)
            user.role = user_role
            user.save()
            logger.info(f"Assigned default 'user' role to {user.email}")
        except Role.DoesNotExist:
            logger.error(f"Default 'user' role not found in database")
            # Role doesn't exist yet (might be during initial migration)
            pass
    
    # Set user's name from Auth0 profile if available
    if backend.name == 'auth0' and user:
        if 'name' in kwargs.get('details', {}):
            name_parts = kwargs['details']['name'].split(' ', 1)
            if len(name_parts) > 0 and not user.first_name:
                user.first_name = name_parts[0]
            if len(name_parts) > 1 and not user.last_name:
                user.last_name = name_parts[1]
            user.save()
            logger.info(f"Updated user name for {user.email}")
    
    # Store Auth0 domain and client ID for logout
    if backend.name == 'auth0':
        kwargs['social'].extra_data['auth0_domain'] = os.environ.get('AUTH0_DOMAIN', 'dev-pgdtb0w4qfk0kenr.us.auth0.com')
        kwargs['social'].extra_data['auth0_client_id'] = os.environ.get('AUTH0_CLIENT_ID', 'OPHq9XW5ne6MbUHdxFL04WqQBDcYFkTn')
        kwargs['social'].save()
        logger.info(f"Stored Auth0 credentials for {user.email}")
    
    return {'user': user} 