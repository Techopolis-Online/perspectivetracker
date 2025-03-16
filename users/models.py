from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

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

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def save(self, *args, **kwargs):
        # If user is a superuser, ensure they have admin role
        if self.is_superuser and (self.role is None or self.role.name != Role.ADMIN):
            try:
                admin_role = Role.objects.get(name=Role.ADMIN)
                self.role = admin_role
            except Role.DoesNotExist:
                # Role doesn't exist yet (might be during initial migration)
                pass
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email
