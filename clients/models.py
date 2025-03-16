from django.db import models
from django.utils import timezone
from users.models import CustomUser, Role
from django.conf import settings
from django.urls import reverse
import uuid

class Client(models.Model):
    company_name = models.CharField(max_length=255)
    contact_name = models.CharField(max_length=255)
    email = models.EmailField()
    website = models.URLField(blank=True, null=True)
    
    # Point of Contact - must be a staff member or admin
    point_of_contact = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='clients_as_poc'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.company_name
    
    def get_absolute_url(self):
        return reverse('client_detail', kwargs={'pk': self.pk})
    
    class Meta:
        ordering = ['company_name']

class ClientCoworker(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('editor', 'Editor'),
        ('viewer', 'Viewer'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('declined', 'Declined'),
    ]
    
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='coworkers')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='client_associations')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='viewer')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    invitation_sent = models.DateTimeField(null=True, blank=True)
    invitation_token = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('client', 'user')
        
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.client.company_name} ({self.get_role_display()})"
    
    def send_invitation(self):
        # Set invitation sent time
        self.invitation_sent = timezone.now()
        # Generate a unique token for the invitation
        import uuid
        self.invitation_token = str(uuid.uuid4())
        self.save()
        
        # Return True to indicate success
        return True

class ClientNote(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='notes')
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='client_notes', null=True, blank=True)
    title = models.CharField(max_length=255)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('note_detail', kwargs={'pk': self.pk})
    
    class Meta:
        ordering = ['-created_at']

class Coworker(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('editor', 'Editor'),
        ('viewer', 'Viewer'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]
    
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='client_coworkers')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='coworker_clients',
        null=True,
        blank=True
    )
    email = models.EmailField()
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='viewer')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    invitation_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_invitations'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('client', 'email')
        
    def __str__(self):
        return f"{self.email} - {self.get_role_display()} for {self.client}"
