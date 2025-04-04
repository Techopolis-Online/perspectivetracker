from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models.signals import post_migrate
from django.dispatch import receiver

class Role(models.Model):
    ADMIN = 'admin'
    STAFF = 'staff'
    CLIENT = 'client'
    USER = 'user'

    ROLE_CHOICES = [
        (ADMIN, 'Administrator'),
        (STAFF, 'Techopolis Staff'),
        (CLIENT, 'Client'),
        (USER, 'User'),
    ]

    name = models.CharField(max_length=50, choices=ROLE_CHOICES, unique=True)

    def __str__(self):
        return self.name

    @classmethod
    def create_default_roles(cls):
        """Create default roles if they don't exist"""
        for role_name, role_display in cls.ROLE_CHOICES:
            cls.objects.get_or_create(
                name=role_name,
                defaults={'name': role_name}
            )

@receiver(post_migrate)
def create_default_roles(sender, **kwargs):
    """Signal handler to create default roles after migrations"""
    if sender.name == 'users':  # Only run for the users app
        Role.create_default_roles()

class AdminSettings(models.Model):
    """Model to store admin-specific settings"""
    receive_all_emails = models.BooleanField(
        default=True,
        help_text="Receive copies of all system emails (user registrations, role changes, system notifications, etc.)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Admin Settings"
        verbose_name_plural = "Admin Settings"

    def __str__(self):
        return "Admin Settings"

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        user = self.create_user(email, password, **extra_fields)
        
        # Assign admin role to superuser
        try:
            admin_role = Role.objects.get(name=Role.ADMIN)
            user.role = admin_role
            user.save(using=self._db)
        except Role.DoesNotExist:
            # Role doesn't exist yet (might be during initial migration)
            pass
            
        return user

class CustomUser(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, null=True, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    manager = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, 
                              related_name='direct_reports',
                              help_text="Primary manager for staff and superuser accounts")
    additional_managers = models.ManyToManyField('self', symmetrical=False, blank=True,
                                             related_name='additional_direct_reports',
                                             help_text="Additional managers for this user")
    no_manager = models.BooleanField(default=False, help_text="Check if this user does not require a manager")
    manually_modified = models.BooleanField(default=False, help_text="Indicates if user was manually modified in admin")

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def save(self, *args, **kwargs):
        # Check if this is a new user or if role/manager has changed
        is_new = self.pk is None
        if not is_new:
            old_instance = CustomUser.objects.get(pk=self.pk)
            role_changed = (not old_instance.role and self.role) or \
                          (old_instance.role and not self.role) or \
                          (old_instance.role and self.role and old_instance.role.name != self.role.name)
            manager_changed = old_instance.manager != self.manager
        else:
            role_changed = self.role is not None
            manager_changed = self.manager is not None
            
        # If user is a superuser, ensure they have admin role
        if self.is_superuser and (self.role is None or self.role.name != Role.ADMIN):
            try:
                admin_role = Role.objects.get(name=Role.ADMIN)
                self.role = admin_role
            except Role.DoesNotExist:
                # Role doesn't exist yet (might be during initial migration)
                pass
                
        # If no_manager is checked, clear the manager field
        if self.no_manager and self.manager:
            self.manager = None
                
        # Save the user
        super().save(*args, **kwargs)
        
        # If this is a new user, send welcome email for users with roles
        # (superuser, staff, admin, client) - basic users without roles don't get emails
        if is_new:
            from perspectivetracker.utils import send_user_created_email
            try:
                result = send_user_created_email(self)
                if result is None:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info(f"No welcome email sent to {self.email} (basic user without specific role)")
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to send welcome email to {self.email}: {str(e)}")
        
        # If role was changed for an existing user, send role change notification and role welcome email
        # This works for both Auth0 users and regular users
        if not is_new and role_changed:
            from perspectivetracker.utils import send_role_change_email, send_role_welcome_email
            import logging
            logger = logging.getLogger(__name__)
            
            try:
                old_role = old_instance.role
                new_role = self.role
                
                # Send the notification about the role change
                send_role_change_email(self, old_role, new_role)
                logger.info(f"Role change email sent to {self.email}: {old_role} -> {new_role}")
                
                # If user has been assigned a new role (not just removed from old role), send detailed welcome
                if new_role:
                    send_role_welcome_email(self, new_role)
                    logger.info(f"Role welcome email sent to {self.email} for role: {new_role}")
            except Exception as e:
                logger.error(f"Failed to send role change/welcome emails to {self.email}: {str(e)}")
                
        # If manager was changed, send notification emails
        if not is_new and manager_changed and self.manager:
            from perspectivetracker.utils import send_manager_assignment_email
            try:
                send_manager_assignment_email(self, old_instance.manager)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to send manager change email to {self.email}: {str(e)}")

    def __str__(self):
        return self.email
