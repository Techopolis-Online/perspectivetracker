from django import forms
from .models import Client, ClientNote, ClientCoworker, Coworker
from users.models import CustomUser, Role
from django.db import models

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['company_name', 'contact_name', 'email', 'website', 'point_of_contact']
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter company name'}),
            'contact_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter contact name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email address'}),
            'website': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Enter website URL (optional)'}),
            'point_of_contact': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter point_of_contact to only show staff and admin users
        self.fields['point_of_contact'].queryset = CustomUser.objects.filter(
            role__name__in=[Role.ADMIN, Role.STAFF]
        )
        # Add labels with appropriate accessibility
        self.fields['company_name'].label = 'Company Name'
        self.fields['contact_name'].label = 'Contact Name'
        self.fields['email'].label = 'Email Address'
        self.fields['website'].label = 'Website (optional)'
        self.fields['point_of_contact'].label = 'Point of Contact'

class ClientNoteForm(forms.ModelForm):
    class Meta:
        model = ClientNote
        fields = ['title', 'content']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter note title'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Enter note content'}),
        }

class ClientCoworkerForm(forms.ModelForm):
    email = forms.EmailField(
        label="Email Address",
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = ClientCoworker
        fields = ['role']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.client = kwargs.pop('client', None)
        super().__init__(*args, **kwargs)
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        
        # Check if user exists
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            raise forms.ValidationError("No user found with this email address.")
        
        # Check if user is already a coworker for this client
        if self.client and ClientCoworker.objects.filter(client=self.client, user=user).exists():
            raise forms.ValidationError("This user is already associated with this client.")
        
        return email
    
    def save(self, commit=True):
        email = self.cleaned_data.get('email')
        user = CustomUser.objects.get(email=email)
        
        instance = super().save(commit=False)
        instance.user = user
        instance.client = self.client
        
        if commit:
            instance.save()
            # Send invitation
            instance.send_invitation()
        
        return instance

class CoworkerForm(forms.ModelForm):
    class Meta:
        model = Coworker
        fields = ['email', 'role']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter email address'
            }),
            'role': forms.Select(attrs={
                'class': 'form-select'
            }),
        }
        
    def clean_email(self):
        email = self.cleaned_data.get('email')
        client = self.initial.get('client')
        
        # Check if this email is already a coworker for this client
        if client and Coworker.objects.filter(client=client, email=email).exists():
            raise forms.ValidationError("This email is already associated with this client.")
            
        return email 