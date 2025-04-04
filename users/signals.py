from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from social_django.models import UserSocialAuth
from users.models import Role
import logging

logger = logging.getLogger(__name__)

User = get_user_model()

@receiver(post_save, sender=UserSocialAuth)
def sync_auth0_user(sender, instance, created, **kwargs):
    """
    Automatically sync Auth0 user data when social auth record is created or updated
    """
    try:
        user = instance.user
        auth0_roles = instance.extra_data.get('roles', [])
        
        # Skip sync if user has been manually modified in admin
        if hasattr(user, 'manually_modified') and user.manually_modified:
            logger.info(f"Skipping Auth0 sync for manually modified user: {user.email}")
            return
        
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
            user.role != new_role or
            user.is_staff != is_staff or
            user.is_superuser != is_superuser
        )
        
        if needs_update:
            # Update user's role and permissions
            user.role = new_role
            user.is_staff = is_staff
            user.is_superuser = is_superuser
            
            # Ensure admins always have staff status and superusers always have staff access
            if user.role and user.role.name == 'admin':
                user.is_staff = True
                user.is_superuser = True
                logger.info(f"Ensuring admin {user.email} has staff and superuser status")
            
            if user.is_superuser:
                user.is_staff = True
                logger.info(f"Ensuring superuser {user.email} has staff access")
                
            user.save()
            
            logger.info(
                f"Auto-synced Auth0 user {user.email}: role={new_role.name}, "
                f"is_staff={user.is_staff}, is_superuser={user.is_superuser}"
            )
            
    except Exception as e:
        logger.error(f"Error auto-syncing Auth0 user: {str(e)}")

@receiver(pre_save, sender=User)
def ensure_admin_staff_status(sender, instance, **kwargs):
    """
    Ensure admins always have staff status and superusers always have staff access
    """
    # Skip if this is a new user
    if not instance.pk:
        return
        
    # Ensure admins always have staff status
    if instance.role and instance.role.name == 'admin':
        instance.is_staff = True
        instance.is_superuser = True
        logger.info(f"Ensuring admin {instance.email} has staff and superuser status")
    
    # Ensure superusers always have staff access
    if instance.is_superuser:
        instance.is_staff = True
        logger.info(f"Ensuring superuser {instance.email} has staff access")

@receiver(pre_save, sender=User)
def mark_user_as_manually_modified(sender, instance, **kwargs):
    """
    Mark user as manually modified when saved from admin
    """
    # Skip if this is a new user
    if not instance.pk:
        return
        
    # Get the original user from the database
    try:
        original_user = User.objects.get(pk=instance.pk)
        
        # Check if role, is_staff, or is_superuser has been changed
        if (original_user.role != instance.role or 
            original_user.is_staff != instance.is_staff or 
            original_user.is_superuser != instance.is_superuser):
            
            # Mark as manually modified
            instance.manually_modified = True
            logger.info(f"User {instance.email} marked as manually modified in admin")
            
    except User.DoesNotExist:
        pass

@receiver(pre_save, sender=User)
def sync_auth0_on_user_update(sender, instance, **kwargs):
    """
    Check if user is an Auth0 user and sync their data before saving.
    For manually modified users, preserve all manually modified fields.
    """
    try:
        # Skip if this is a new user
        if not instance.pk:
            return
            
        # Check if this is an Auth0 user
        auth0_user = UserSocialAuth.objects.filter(provider='auth0', user=instance).first()
        if not auth0_user:
            return
            
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
        
        # If user has been manually modified, preserve all manually modified fields
        if instance.manually_modified:
            logger.info(f"User {instance.email} is manually modified - preserving all manually modified fields")
            # Get the original user to check which fields were modified
            try:
                original_user = User.objects.get(pk=instance.pk)
                
                # Check if fields were modified by comparing with original values
                role_modified = original_user.role != instance.role
                staff_modified = original_user.is_staff != instance.is_staff
                superuser_modified = original_user.is_superuser != instance.is_superuser
                
                # Only update fields that weren't manually modified
                if not role_modified:
                    instance.role = new_role
                if not staff_modified:
                    instance.is_staff = is_staff
                if not superuser_modified:
                    instance.is_superuser = is_superuser
                    
                logger.info(
                    f"Field modification status for {instance.email}: "
                    f"role_modified={role_modified}, staff_modified={staff_modified}, "
                    f"superuser_modified={superuser_modified}"
                )
                    
            except User.DoesNotExist:
                pass
        else:
            # Update all fields
            instance.role = new_role
            instance.is_staff = is_staff
            instance.is_superuser = is_superuser
            
        # Ensure admins always have staff status and superusers always have staff access
        if instance.role and instance.role.name == 'admin':
            instance.is_staff = True
            instance.is_superuser = True
            logger.info(f"Ensuring admin {instance.email} has staff and superuser status after Auth0 sync")
        
        if instance.is_superuser:
            instance.is_staff = True
            logger.info(f"Ensuring superuser {instance.email} has staff access after Auth0 sync")
            
        logger.info(
            f"Auto-synced Auth0 user on update {instance.email}: "
            f"role={'preserved' if instance.manually_modified else new_role.name}, "
            f"is_staff={'preserved' if instance.manually_modified else is_staff}, "
            f"is_superuser={'preserved' if instance.manually_modified else is_superuser}"
        )
        
    except Exception as e:
        logger.error(f"Error auto-syncing Auth0 user on update: {str(e)}") 