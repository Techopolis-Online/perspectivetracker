from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from .models import CustomUser, Role
from django.contrib.auth.forms import AuthenticationForm
from django import forms
from django.urls import reverse
from perspectivetracker.utils import send_test_email, test_smtp_connection, test_smtp_ports
from django.conf import settings
import logging

# Set up logger for Auth0 debugging
logger = logging.getLogger('auth0_debug')

class ProfileEditForm(forms.ModelForm):
    profile_picture = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))
    bio = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))
    phone_number = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    job_title = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'profile_picture', 'bio', 'phone_number', 'job_title']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

def home_view(request):
    """Home page view"""
    return render(request, 'users/home.html')

def login_view(request):
    """Redirect to Auth0 login page"""
    logger.info("Auth0 login initiated")
    
    # Debug information
    logger.info(f"AUTH0_DOMAIN: {settings.SOCIAL_AUTH_AUTH0_DOMAIN}")
    logger.info(f"AUTH0_CLIENT_ID: {settings.SOCIAL_AUTH_AUTH0_KEY}")
    logger.info(f"AUTH0_CALLBACK_URL: {settings.SOCIAL_AUTH_AUTH0_REDIRECT_URI}")
    
    try:
        # Use try-except to catch potential errors
        return redirect('social:begin', 'auth0')
    except Exception as e:
        # Log any exceptions that occur
        logger.error(f"Error initiating Auth0 login: {str(e)}")
        messages.error(request, "There was an error initiating Auth0 login. Please try again.")
        return redirect('login_error')

def login_error_view(request):
    """Display login error page"""
    logger.error("Auth0 login error occurred")
    
    # Log detailed error information for server admins
    if request.GET:
        logger.error(f"Error query params: {request.GET}")
    
    # Log all settings related to Auth0
    logger.error(f"AUTH0_DOMAIN: {settings.SOCIAL_AUTH_AUTH0_DOMAIN}")
    logger.error(f"AUTH0_CLIENT_ID: {settings.SOCIAL_AUTH_AUTH0_KEY}")
    logger.error(f"AUTH0_CALLBACK_URL: {settings.SOCIAL_AUTH_AUTH0_REDIRECT_URI}")
    logger.error(f"HTTPS: {settings.SOCIAL_AUTH_REDIRECT_IS_HTTPS}")
    
    if hasattr(settings, 'SOCIAL_AUTH_PIPELINE'):
        logger.error(f"PIPELINE: {settings.SOCIAL_AUTH_PIPELINE}")
    
    # Use a generic message for the user, keep detailed information in server logs only
    messages.error(request, "There was an error logging in. Please try again or contact your administrator.")
    return render(request, 'users/login_error.html')

@login_required
def logout_view(request):
    """Log out the user and redirect to login page"""
    # Check if user is authenticated via Auth0
    auth0_user = request.user.social_auth.filter(provider='auth0').first()
    
    # Perform Django logout
    logout(request)
    
    # If user was authenticated with Auth0, redirect to Auth0 logout endpoint
    if auth0_user:
        domain = auth0_user.extra_data['auth0_domain']
        client_id = auth0_user.extra_data['auth0_client_id']
        return_to = request.build_absolute_uri(reverse('login'))
        auth0_logout_url = f'https://{domain}/v2/logout?client_id={client_id}&returnTo={return_to}'
        return redirect(auth0_logout_url)
    
    # Regular Django logout
    messages.success(request, "You have been logged out.")
    return redirect('login')

def has_role(user, role_name):
    """Check if user has the specified role"""
    # Superusers always have admin privileges
    if user.is_superuser and role_name == Role.ADMIN:
        return True
    return user.is_authenticated and user.role and user.role.name == role_name

def admin_required(view_func):
    """Decorator for views that require admin role"""
    def wrapper(request, *args, **kwargs):
        if has_role(request.user, Role.ADMIN):
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden("You don't have permission to access this page.")
    return wrapper

def staff_required(view_func):
    """Decorator for views that require staff role"""
    def wrapper(request, *args, **kwargs):
        if has_role(request.user, Role.ADMIN) or has_role(request.user, Role.STAFF):
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden("You don't have permission to access this page.")
    return wrapper

def client_required(view_func):
    """Decorator for views that require client role or higher"""
    def wrapper(request, *args, **kwargs):
        if (has_role(request.user, Role.ADMIN) or 
            has_role(request.user, Role.STAFF) or 
            has_role(request.user, Role.CLIENT)):
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden("You don't have permission to access this page.")
    return wrapper

@login_required
def profile_view(request):
    """Display user profile information (read-only)"""
    return render(request, 'users/profile.html')

@login_required
def edit_profile_view(request):
    """Edit user profile information"""
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated successfully.")
            return redirect('profile')
    else:
        form = ProfileEditForm(instance=request.user)
    
    context = {
        'form': form,
    }
    return render(request, 'users/edit_profile.html', context)

@login_required
def dashboard_view(request):
    """Display all activities of the current user with details"""
    from projects.models import Comment, IssueModification, Issue, Milestone, Project
    from django.db.models import Q
    
    # Get all comments made by the user
    user_comments = Comment.objects.filter(author=request.user).order_by('-created_at')
    
    # Get all issue modifications made by the user
    user_modifications = IssueModification.objects.filter(modified_by=request.user).order_by('-created_at')
    
    # Get issues assigned to the user
    assigned_issues = Issue.objects.filter(assigned_to=request.user).order_by('-updated_at')
    
    # Get milestones assigned to the user
    assigned_milestones = Milestone.objects.filter(assigned_to=request.user).order_by('-updated_at')
    
    # Get projects assigned to the user
    assigned_projects = Project.objects.filter(assigned_to=request.user).order_by('-updated_at')
    
    # Get projects created by the user
    created_projects = Project.objects.filter(created_by=request.user).order_by('-created_at')
    
    # Get issues created by the user
    created_issues = Issue.objects.filter(created_by=request.user).order_by('-created_at')
    
    # Get milestones created by the user
    created_milestones = Milestone.objects.filter(created_by=request.user).order_by('-created_at')
    
    context = {
        'user_comments': user_comments,
        'user_modifications': user_modifications,
        'assigned_issues': assigned_issues,
        'assigned_milestones': assigned_milestones,
        'assigned_projects': assigned_projects,
        'created_projects': created_projects,
        'created_issues': created_issues,
        'created_milestones': created_milestones,
    }
    
    return render(request, 'users/dashboard.html', context)

@login_required
@admin_required
def test_email(request):
    """View to test email configuration"""
    from django.conf import settings
    from perspectivetracker.utils import send_test_email, test_smtp_connection, test_smtp_ports
    
    if request.method == 'POST':
        action = request.POST.get('action', 'send_email')
        
        if action == 'test_connection':
            # Test SMTP connection only
            success, message = test_smtp_connection()
            if success:
                messages.success(request, f"SMTP connection test successful.")
            else:
                messages.error(request, f"SMTP connection test failed: {message}")
        elif action == 'test_ports':
            # Test different SMTP ports
            results = test_smtp_ports()
            
            # Check if any connection was successful
            any_success = any(success for _, _, success, _ in results)
            
            if any_success:
                messages.success(request, "Successfully connected to at least one SMTP port configuration.")
                
                # Add detailed results as info messages
                for port, protocol, success, message in results:
                    if success:
                        messages.info(request, f"✅ {protocol} (Port {port}): Connection successful")
                    else:
                        messages.info(request, f"❌ {protocol} (Port {port}): {message}")
            else:
                messages.error(request, "Failed to connect to any SMTP port configuration.")
                
                # Add detailed results as info messages
                for port, protocol, success, message in results:
                    messages.info(request, f"❌ {protocol} (Port {port}): {message}")
        else:
            # Send test email
            recipient_email = request.POST.get('email')
            if recipient_email:
                success, error_message = send_test_email(request, recipient_email)
                if success:
                    messages.success(request, f"Test email sent to {recipient_email} successfully.")
                else:
                    messages.error(request, f"Failed to send test email: {error_message}")
            else:
                messages.error(request, "Please provide an email address.")
        
        return redirect('test_email')
    
    # Get email configuration details
    context = {
        'email_backend': settings.EMAIL_BACKEND.split('.')[-1],
        'email_host': settings.EMAIL_HOST,
        'email_port': settings.EMAIL_PORT,
        'default_from_email': settings.DEFAULT_FROM_EMAIL,
        'use_ssl': settings.EMAIL_USE_SSL,
        'use_tls': settings.EMAIL_USE_TLS,
    }
    
    return render(request, 'users/test_email.html', context)
