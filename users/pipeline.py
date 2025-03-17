from .models import Role
import os

def get_user_role(backend, user, response, *args, **kwargs):
    """
    Pipeline function to assign a default role to users authenticated via Auth0.
    By default, users are assigned the 'user' role.
    """
    if user and not user.role:
        try:
            # Assign default user role
            user_role = Role.objects.get(name=Role.USER)
            user.role = user_role
            user.save()
        except Role.DoesNotExist:
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
    
    # Store Auth0 domain and client ID for logout
    if backend.name == 'auth0':
        kwargs['social'].extra_data['auth0_domain'] = 'dev-pgdtb0w4qfk0kenr.us.auth0.com'
        kwargs['social'].extra_data['auth0_client_id'] = 'OPHq9XW5ne6MbUHdxFL04WqQBDcYFkTn'
        kwargs['social'].save()
    
    return {'user': user} 