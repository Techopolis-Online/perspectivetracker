import logging
from django.contrib.auth import get_user_model
from django.db import transaction
from users.models import Role

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
                user.save()
            else:
                logger.info(f"Creating new user from Auth0: {auth0_email}")
                # Create new user with default role
                user = User.objects.create(
                    email=auth0_email,
                    first_name=response.get('given_name', ''),
                    last_name=response.get('family_name', ''),
                    role=default_role
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