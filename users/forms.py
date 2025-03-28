from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Role, AdminSettings
from django.db import models

class UserRegistrationForm(UserCreationForm):
    """
    Form for admin users to create new user accounts
    """
    first_name = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    role = forms.ModelChoiceField(
        queryset=Role.objects.all(),
        required=False,
        empty_label="No specific role (basic user)",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    job_title = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    phone_number = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    bio = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))
    
    # Staff/Admin permissions
    is_staff = forms.BooleanField(
        required=False, 
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Designates whether the user can log into the admin site."
    )
    is_superuser = forms.BooleanField(
        required=False, 
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Designates that this user has all permissions without explicitly assigning them."
    )
    
    # Manager fields
    no_manager = forms.BooleanField(
        required=False, 
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Check if this user does not require a manager."
    )
    manager = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(is_staff=True),
        required=False, 
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Primary manager for this user."
    )
    
    class Meta:
        model = CustomUser
        fields = [
            'first_name', 'last_name', 'email', 'password1', 'password2',
            'role', 'job_title', 'phone_number', 'bio',
            'is_staff', 'is_superuser', 'no_manager', 'manager'
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Update the manager queryset to only include staff and admin users
        self.fields['manager'].queryset = CustomUser.objects.filter(
            models.Q(is_superuser=True) | 
            models.Q(role__name__in=['admin', 'staff'])
        )
        
        # Make password fields use Bootstrap styling
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})

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

class AdminProfileEditForm(forms.ModelForm):
    """
    Form for administrators to edit user profiles including manager assignment
    """
    profile_picture = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))
    bio = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))
    phone_number = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    job_title = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    
    # Manager fields - only available to administrators
    no_manager = forms.BooleanField(
        required=False, 
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Check if this user does not require a manager."
    )
    manager = forms.ModelChoiceField(
        queryset=CustomUser.objects.none(),  # Will be set in __init__
        required=False, 
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Primary manager for this user."
    )
    
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'profile_picture', 'bio', 'phone_number', 'job_title', 'no_manager', 'manager']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Update the manager queryset to only include staff and admin users
        self.fields['manager'].queryset = CustomUser.objects.filter(
            models.Q(is_superuser=True) | 
            models.Q(role__name__in=['admin', 'staff'])
        )

class AdminSettingsForm(forms.ModelForm):
    """Form for managing admin settings"""
    class Meta:
        model = AdminSettings
        fields = ['receive_all_emails']
        widgets = {
            'receive_all_emails': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class ManagerAssignmentForm(forms.ModelForm):
    """Form for assigning managers to users"""
    no_manager = forms.BooleanField(
        required=False, 
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Check if this user does not require a manager."
    )
    manager = forms.ModelChoiceField(
        queryset=CustomUser.objects.none(),  # Will be set in __init__
        required=False, 
        widget=forms.Select(attrs={'class': 'form-control select2'}),
        help_text="Primary manager for this user."
    )
    
    class Meta:
        model = CustomUser
        fields = ['manager']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Update the manager queryset to only include staff and admin users
        self.fields['manager'].queryset = CustomUser.objects.filter(
            models.Q(is_superuser=True) | 
            models.Q(role__name__in=['admin', 'staff'])
        )
