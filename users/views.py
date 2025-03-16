from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from .models import CustomUser, Role
from django.contrib.auth.forms import AuthenticationForm
from django import forms

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
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(email=email, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {user.first_name} {user.last_name}!")
                return redirect('home')
            else:
                messages.error(request, "Invalid email or password.")
        else:
            messages.error(request, "Invalid email or password.")
    else:
        form = AuthenticationForm()
    
    return render(request, 'users/login.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
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
            messages.success(request, "Profile updated successfully!")
            return redirect('profile')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ProfileEditForm(instance=request.user)
    
    return render(request, 'users/edit_profile.html', {'form': form})
