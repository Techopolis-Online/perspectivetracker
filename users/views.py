from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from .models import CustomUser, Role, AdminSettings
from django.contrib.auth.forms import AuthenticationForm
from django import forms
from django.urls import reverse
from perspectivetracker.utils import send_test_email, test_smtp_connection, test_smtp_ports
from django.conf import settings
import logging
from .forms import UserRegistrationForm, ProfileEditForm, AdminSettingsForm, ManagerAssignmentForm  # Import all forms
from django.db.models import Q

# Set up logger for Auth0 debugging
logger = logging.getLogger('auth0_debug')

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
    # Store user email before logout
    user_email = request.user.email if request.user.is_authenticated else None
    
    # Check if user is authenticated via Auth0
    auth0_user = request.user.social_auth.filter(provider='auth0').first()
    
    # Perform Django logout
    logout(request)
    
    # If user was authenticated with Auth0, redirect to Auth0 logout endpoint
    if auth0_user:
        domain = settings.SOCIAL_AUTH_AUTH0_DOMAIN
        client_id = settings.SOCIAL_AUTH_AUTH0_KEY
        return_to = request.build_absolute_uri(reverse('login'))
        
        # Construct the Auth0 logout URL with all required parameters
        auth0_logout_url = (
            f'https://{domain}/v2/logout'
            f'?client_id={client_id}'
            f'&returnTo={return_to}'
            f'&federated=true'
        )
        
        # Log the logout attempt using stored email
        if user_email:
            logger.info(f"Attempting Auth0 logout for user {user_email}")
        logger.info(f"Logout URL: {auth0_logout_url}")
        
        try:
            return redirect(auth0_logout_url)
        except Exception as e:
            logger.error(f"Error during Auth0 logout: {str(e)}")
            messages.error(request, "There was an error logging out from Auth0. Please try again.")
            return redirect('login')
    
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
    # Determine if the user is an admin or superuser
    is_admin = request.user.is_superuser or (request.user.role and request.user.role.name == Role.ADMIN)
    
    if request.method == 'POST':
        # Use the appropriate form class based on user role
        if is_admin:
            # Import AdminProfileEditForm here to avoid circular imports
            from .forms import AdminProfileEditForm
            form = AdminProfileEditForm(request.POST, request.FILES, instance=request.user)
        else:
            form = ProfileEditForm(request.POST, request.FILES, instance=request.user)
        
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated successfully.")
            return redirect('profile')
    else:
        # Use the appropriate form class based on user role
        if is_admin:
            # Import AdminProfileEditForm here to avoid circular imports
            from .forms import AdminProfileEditForm
            form = AdminProfileEditForm(instance=request.user)
        else:
            form = ProfileEditForm(instance=request.user)
    
    context = {
        'form': form,
        'is_admin': is_admin,
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

@login_required
@admin_required
def user_list(request):
    """View to list all users (for admin only)"""
    users = CustomUser.objects.all().order_by('last_name', 'first_name')
    
    # Filter by role if requested
    role_filter = request.GET.get('role', '')
    if role_filter:
        if role_filter == 'none':
            users = users.filter(role__isnull=True)
        else:
            users = users.filter(role__name=role_filter)
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        users = users.filter(
            Q(first_name__icontains=search_query) | 
            Q(last_name__icontains=search_query) | 
            Q(email__icontains=search_query) |
            Q(job_title__icontains=search_query)
        )
    
    context = {
        'users': users,
        'roles': Role.objects.all(),
        'current_role': role_filter,
        'search_query': search_query,
    }
    return render(request, 'users/user_list.html', context)

@login_required
@admin_required
def user_create(request):
    """View to create a new user (for admin only)"""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"User account for {user.email} created successfully.")
            return redirect('user_list')
    else:
        form = UserRegistrationForm()
    
    context = {
        'form': form,
        'title': 'Create New User',
    }
    return render(request, 'users/user_form.html', context)

@login_required
@admin_required
def user_edit(request, user_id):
    """View to edit an existing user (for admin only)"""
    user = get_object_or_404(CustomUser, id=user_id)
    
    if request.method == 'POST':
        # Use the user registration form but don't require password
        form = UserRegistrationForm(request.POST, instance=user)
        # Set password fields as not required for editing
        form.fields['password1'].required = False
        form.fields['password2'].required = False
        
        if form.is_valid():
            # Only set password if provided
            password1 = form.cleaned_data.get('password1')
            if password1:
                user.set_password(password1)
            
            # Save all fields including role
            user = form.save()
            
            messages.success(request, f"User account for {user.email} updated successfully.")
            return redirect('user_list')
    else:
        form = UserRegistrationForm(instance=user)
        # Set password fields as not required for editing
        form.fields['password1'].required = False
        form.fields['password2'].required = False
    
    context = {
        'form': form,
        'title': f'Edit User: {user.email}',
        'user': user,
    }
    return render(request, 'users/user_form.html', context)

@login_required
@admin_required
def user_delete(request, user_id):
    """View to delete a user (for admin only)"""
    user = get_object_or_404(CustomUser, id=user_id)
    
    # Prevent self-deletion
    if user == request.user:
        messages.error(request, "You cannot delete your own account.")
        return redirect('user_list')
    
    if request.method == 'POST':
        email = user.email
        user.delete()
        messages.success(request, f"User account for {email} deleted successfully.")
        return redirect('user_list')
    
    context = {
        'user': user,
    }
    return render(request, 'users/user_confirm_delete.html', context)

@login_required
@admin_required
def change_user_role(request, user_id):
    """View to change a user's role (for admin only)"""
    user = get_object_or_404(CustomUser, pk=user_id)
    
    # Don't allow changing superuser roles through this interface
    if user.is_superuser and request.user != user:
        messages.error(request, "Superuser roles cannot be modified through this interface.")
        return redirect('user_edit', user_id=user.pk)
    
    if request.method == 'POST':
        role_id = request.POST.get('role')
        
        try:
            if role_id:
                new_role = Role.objects.get(pk=role_id)
                user.role = new_role
                user.save()
                messages.success(request, f"{user.email}'s role has been changed to {new_role}.")
            else:
                user.role = None
                user.save()
                messages.success(request, f"{user.email}'s role has been removed.")
                
            # Redirect back to the user edit page
            return redirect('user_edit', user_id=user.pk)
            
        except Role.DoesNotExist:
            messages.error(request, "Invalid role selection.")
    
    # Get all available roles
    roles = Role.objects.all()
    
    context = {
        'user_to_edit': user,
        'roles': roles,
        'current_role': user.role,
    }
    
    return render(request, 'users/change_user_role.html', context)

@login_required
@admin_required
def admin_settings(request):
    """View to manage admin settings"""
    # Get or create settings for the current user
    settings, created = AdminSettings.objects.get_or_create()
    
    if request.method == 'POST':
        form = AdminSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, "Admin settings updated successfully.")
            return redirect('admin_settings')
    else:
        form = AdminSettingsForm(instance=settings)
    
    context = {
        'form': form,
        'title': 'Admin Settings',
    }
    return render(request, 'users/admin_settings.html', context)

@login_required
@admin_required
def manager_assignment_view(request):
    """View for bulk manager assignment (for admins only)"""
    from .forms import ManagerAssignmentForm
    from perspectivetracker.utils import send_manager_assignment_email
    
    # Get list of all users
    users = CustomUser.objects.all().order_by('last_name', 'first_name')
    
    # Filter users by search or role if provided
    search_query = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')
    
    if search_query:
        users = users.filter(
            Q(first_name__icontains=search_query) | 
            Q(last_name__icontains=search_query) | 
            Q(email__icontains=search_query)
        )
    
    if role_filter:
        if role_filter == 'none':
            users = users.filter(role__isnull=True)
        else:
            users = users.filter(role__name=role_filter)
    
    # Handle form submission for a specific user
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        if user_id:
            user = get_object_or_404(CustomUser, id=user_id)
            form = ManagerAssignmentForm(request.POST, instance=user)
            
            if form.is_valid():
                # Store the old manager for notification purposes
                old_manager = user.manager
                
                # Save the form
                user = form.save()
                
                # Send notification email if manager changed
                if user.manager != old_manager:
                    try:
                        send_manager_assignment_email(user, old_manager)
                        messages.info(request, f"Notification email sent to manager and user.")
                    except Exception as e:
                        logger.error(f"Error sending manager assignment email: {str(e)}")
                        messages.warning(request, "Manager updated but email notification could not be sent.")
                
                messages.success(request, f"Manager assignments updated for {user.email}")
                return redirect('manager_assignment')
        else:
            messages.error(request, "Invalid user selection.")
    
    # Get all available managers (staff and admin users)
    potential_managers = CustomUser.objects.filter(
        Q(is_superuser=True) | 
        Q(role__name__in=['admin', 'staff'])
    ).order_by('first_name', 'last_name')
    
    # Get all roles for filtering
    roles = Role.objects.all()
    
    context = {
        'users': users,
        'potential_managers': potential_managers,
        'roles': roles,
        'search_query': search_query,
        'current_role': role_filter,
        'title': 'Manager Assignment',
    }
    
    return render(request, 'users/manager_assignment.html', context)

@login_required
@admin_required
def assign_manager(request, user_id):
    """View to assign a manager to a specific user (for admins only)"""
    from .forms import ManagerAssignmentForm
    from perspectivetracker.utils import send_manager_assignment_email
    
    user = get_object_or_404(CustomUser, id=user_id)
    
    if request.method == 'POST':
        form = ManagerAssignmentForm(request.POST, instance=user)
        
        if form.is_valid():
            # Store the old manager for notification purposes
            old_manager = user.manager
            
            # Save the form
            user = form.save()
            
            # Send notification email if manager changed
            if user.manager != old_manager:
                try:
                    send_manager_assignment_email(user, old_manager)
                    messages.info(request, f"Notification email sent to manager and user.")
                except Exception as e:
                    logger.error(f"Error sending manager assignment email: {str(e)}")
                    messages.warning(request, "Manager updated but email notification could not be sent.")
            
            messages.success(request, f"Manager assignments updated for {user.email}")
            
            # Determine where to redirect based on where the user came from
            next_page = request.POST.get('next', 'user_edit')
            if next_page == 'manager_assignment':
                return redirect('manager_assignment')
            else:
                return redirect('user_edit', user_id=user.id)
    else:
        form = ManagerAssignmentForm(instance=user)
    
    context = {
        'form': form,
        'user': user,
        'title': f'Assign Manager: {user.email}',
        'next': request.GET.get('next', 'user_edit'),
    }
    
    return render(request, 'users/assign_manager.html', context)

@login_required
@admin_required
def user_direct_reports(request, user_id):
    """View to show a user's direct reports (for admins only)"""
    user = get_object_or_404(CustomUser, id=user_id)
    
    # Get direct reports (users where this user is the manager)
    direct_reports = CustomUser.objects.filter(manager=user).order_by('last_name', 'first_name')
    
    # Get all roles for filtering
    roles = Role.objects.all()
    
    context = {
        'user': user,
        'direct_reports': direct_reports,
        'roles': roles,
        'title': f"Direct Reports for {user.get_full_name()}",
    }
    
    return render(request, 'users/user_direct_reports.html', context)
