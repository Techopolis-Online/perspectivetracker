from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import CustomUser, Role
from .views import admin_required
import logging

# Set up logger
logger = logging.getLogger('auth0_debug')

@login_required
@admin_required
def user_role_change(request, user_id):
    """View to change a user's role (for admin only)"""
    user = get_object_or_404(CustomUser, id=user_id)
    
    # Check if this is an Auth0 user
    is_auth0_user = hasattr(user, 'social_auth') and user.social_auth.filter(provider='auth0').exists()
    
    if request.method == 'POST':
        role_id = request.POST.get('role')
        
        old_role = user.role
        
        if role_id:
            # Set the new role
            try:
                new_role = Role.objects.get(id=role_id)
                user.role = new_role
                user.save()
                messages.success(request, f"Role updated for {user.email}: {old_role} → {new_role}")
                
                # Log the role change
                logger.info(f"Admin {request.user.email} changed role for user {user.email}: {old_role} → {new_role}")
                
                if is_auth0_user:
                    messages.info(request, f"Note: This user authenticated via Auth0. Their role has been changed in our system.")
                
                return redirect('user_list')
            except Role.DoesNotExist:
                messages.error(request, "Invalid role selected.")
        else:
            # Remove the role
            user.role = None
            user.save()
            messages.success(request, f"Role removed for {user.email}")
            
            # Log the role change
            logger.info(f"Admin {request.user.email} removed role for user {user.email}")
            
            if is_auth0_user:
                messages.info(request, f"Note: This user authenticated via Auth0. Their role has been removed in our system.")
            
            return redirect('user_list')
    
    context = {
        'user': user,
        'roles': Role.objects.all(),
        'is_auth0_user': is_auth0_user,
    }
    return render(request, 'users/user_role_change.html', context)