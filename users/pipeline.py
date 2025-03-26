import logging
from django.contrib.auth import get_user_model
from django.db import transaction
from .models import Role
import os

logger = logging.getLogger(__name__)
User = get_user_model()

def get_user_role(backend, user, response, *args, **kwargs):
    """Assign user role based on Auth0 profile"""
    try:
        with transaction.atomic():
            # Get or create default role
            default_role, created = Role.objects.get_or_create(
                name='user',
                defaults={'name': 'User'}
            )
            
            # Log the user role assignment process
            logger.info(f"Processing role assignment for user: {user.email}")
            
            # Check if user already has a role
            if not user.role:
                # Assign default role
                user.role = default_role
                user.save()
                logger.info(f"Assigned default role 'user' to {user.email}")
            
            # Update user's name from Auth0 profile if available
            if response.get('name'):
                user.first_name = response.get('given_name', '')
                user.last_name = response.get('family_name', '')
                user.save()
                logger.info(f"Updated user name for {user.email}")
            
            # Store Auth0 credentials for logout
            if not hasattr(user, 'social_auth'):
                user.social_auth.create(
                    provider='auth0',
                    uid=response.get('sub'),
                    extra_data=response
                )
                logger.info(f"Stored Auth0 credentials for {user.email}")
            
            return {'user': user}
            
    except Exception as e:
        logger.error(f"Error in get_user_role pipeline: {str(e)}")
        # Don't raise the exception to prevent login failure
        return {'user': user} 