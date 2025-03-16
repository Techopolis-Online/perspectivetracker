from django import forms
from .models import Project, Standard, Violation, ProjectViolation, ProjectType, ProjectStandard
from users.models import CustomUser
import json
from django.db import models

class ProjectTypeForm(forms.ModelForm):
    status_choices_text = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 6}),
        required=False,
        help_text="Enter each status choice on a new line in the format: key, Display Name"
    )
    
    milestone_choices_text = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 6}),
        required=False,
        help_text="Enter each milestone choice on a new line in the format: key, Display Name"
    )
    
    class Meta:
        model = ProjectType
        fields = ['name', 'description', 'supports_standards']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'supports_standards': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get('instance')
        
        # Convert status_choices from JSON to text format for editing
        if instance and instance.status_choices:
            items = []
            for key, display in instance.status_choices:
                items.append(f"{key}, {display}")
            self.fields['status_choices_text'].initial = "\n".join(items)
            
        # Convert milestone_choices from JSON to text format for editing
        if instance and instance.milestone_choices:
            items = []
            for key, display in instance.milestone_choices:
                items.append(f"{key}, {display}")
            self.fields['milestone_choices_text'].initial = "\n".join(items)
    
    def clean_status_choices_text(self):
        text = self.cleaned_data.get('status_choices_text', '')
        if not text.strip():
            return []
        
        # Split by lines first, then by commas
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        choices = []
        
        for line in lines:
            # Split by first comma only
            parts = [part.strip() for part in line.split(',', 1)]
            if len(parts) != 2:
                raise forms.ValidationError(f"Invalid format in line '{line}'. Use format: key, Display Name")
            
            key, display = parts
            if not key or not display:
                raise forms.ValidationError(f"Both key and display name must be provided in line '{line}'")
            
            choices.append([key, display])
        
        # Check for duplicate keys
        keys = [choice[0] for choice in choices]
        if len(keys) != len(set(keys)):
            raise forms.ValidationError("Duplicate keys found. Each key must be unique.")
        
        print(f"Processed status choices: {choices}")  # Debug print
        return choices
    
    def clean_milestone_choices_text(self):
        text = self.cleaned_data.get('milestone_choices_text', '')
        if not text.strip():
            return []
        
        # Split by lines first, then by commas
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        choices = []
        
        for line in lines:
            # Split by first comma only
            parts = [part.strip() for part in line.split(',', 1)]
            if len(parts) != 2:
                raise forms.ValidationError(f"Invalid format in line '{line}'. Use format: key, Display Name")
            
            key, display = parts
            if not key or not display:
                raise forms.ValidationError(f"Both key and display name must be provided in line '{line}'")
            
            choices.append([key, display])
        
        # Check for duplicate keys
        keys = [choice[0] for choice in choices]
        if len(keys) != len(set(keys)):
            raise forms.ValidationError("Duplicate keys found. Each key must be unique.")
            
        return choices
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.status_choices = self.cleaned_data.get('status_choices_text', [])
        instance.milestone_choices = self.cleaned_data.get('milestone_choices_text', [])
        
        if commit:
            instance.save()
            
        return instance

# Custom ModelMultipleChoiceField that displays first and last name
class UserModelMultipleChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        # Include email as a unique identifier if first and last name are the same
        if obj.first_name and obj.last_name:
            return f"{obj.first_name} {obj.last_name} ({obj.email})"
        else:
            return obj.email

class ProjectForm(forms.ModelForm):
    assigned_staff = UserModelMultipleChoiceField(
        queryset=CustomUser.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-select'}),
        label="Assigned Project Staff",
        help_text="Select Techopolis staff members to assign to this project"
    )
    
    assigned_clients = UserModelMultipleChoiceField(
        queryset=CustomUser.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-select'}),
        label="Assigned Client Team",
        help_text="Select client team members to assign to this project"
    )
    
    class Meta:
        model = Project
        fields = ['name', 'client', 'project_type', 'status', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'client': forms.Select(attrs={'class': 'form-select'}),
            'project_type': forms.Select(attrs={'class': 'form-select', 'id': 'id_project_type'}),
            'status': forms.Select(attrs={'class': 'form-select', 'id': 'id_status'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set up staff users (admin and staff roles, plus superusers)
        self.fields['assigned_staff'].queryset = CustomUser.objects.filter(
            is_active=True
        ).filter(
            # Include users with admin or staff roles
            models.Q(role__name__in=['admin', 'staff']) |
            # Include superusers
            models.Q(is_superuser=True)
        ).distinct().order_by('first_name', 'last_name')
        
        # Set up client users (client role)
        self.fields['assigned_clients'].queryset = CustomUser.objects.filter(
            is_active=True,
            role__name='client'
        ).order_by('first_name', 'last_name')
        
        # Pre-select assigned users if editing an existing project
        instance = kwargs.get('instance')
        if instance:
            # Get staff users (including superusers)
            staff_users = instance.assigned_to.filter(
                models.Q(role__name__in=['admin', 'staff']) |
                models.Q(is_superuser=True)
            ).distinct()
            
            self.fields['assigned_staff'].initial = staff_users
            self.fields['assigned_clients'].initial = instance.assigned_to.filter(
                role__name='client'
            )
        
        # Set status choices based on project type if instance exists
        if instance and instance.project_type:
            choices = instance.get_status_choices()
            # Ensure choices are properly formatted
            formatted_choices = []
            for key, display in choices:
                if key and display:  # Skip empty values
                    formatted_choices.append((key.strip(), display.strip()))
            self.fields['status'].choices = formatted_choices
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        if commit:
            instance.save()
            
            # Clear existing assignments and add the new ones
            instance.assigned_to.clear()
            
            # Add staff users
            for staff in self.cleaned_data.get('assigned_staff', []):
                instance.assigned_to.add(staff)
            
            # Add client users
            for client in self.cleaned_data.get('assigned_clients', []):
                instance.assigned_to.add(client)
            
        return instance

# Custom ModelChoiceField that displays first and last name
class UserModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        # Include email as a unique identifier if first and last name are the same
        if obj.first_name and obj.last_name:
            return f"{obj.first_name} {obj.last_name} ({obj.email})"
        else:
            return obj.email

class StandardForm(forms.ModelForm):
    class Meta:
        model = Standard
        fields = ['name', 'description', 'version', 'url']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'version': forms.TextInput(attrs={'class': 'form-control'}),
            'url': forms.URLInput(attrs={'class': 'form-control'}),
        }

class ViolationForm(forms.ModelForm):
    class Meta:
        model = Violation
        fields = ['name', 'description', 'url', 'standard']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'url': forms.URLInput(attrs={'class': 'form-control'}),
            'standard': forms.Select(attrs={'class': 'form-select'}),
        }

class ProjectViolationForm(forms.ModelForm):
    assigned_to = UserModelChoiceField(
        queryset=CustomUser.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = ProjectViolation
        fields = ['violation', 'status', 'notes', 'location', 'screenshot', 'assigned_to']
        widgets = {
            'violation': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'screenshot': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)
        
        # Filter assigned_to to only show users assigned to the project
        self.fields['assigned_to'].queryset = CustomUser.objects.filter(
            is_active=True
        ).exclude(
            role__isnull=True
        ).order_by('first_name', 'last_name')
        
        # Filter violations based on project type if it supports standards
        if project and project.project_type.supports_standards:
            # Get standards associated with this project
            project_standards = ProjectStandard.objects.filter(project=project).values_list('standard_id', flat=True)
            
            if project_standards:
                # Get violations only from standards associated with this project
                violations = Violation.objects.filter(
                    standard_id__in=project_standards
                ).select_related('standard').order_by('standard__name', 'standard__version', 'name')
                
                # Group violations by standard for the dropdown
                standard_groups = {}
                for violation in violations:
                    standard_name = f"{violation.standard.name} {violation.standard.version}".strip()
                    if standard_name not in standard_groups:
                        standard_groups[standard_name] = []
                    standard_groups[standard_name].append((violation.id, violation.name))
                
                # Create grouped choices for the dropdown
                grouped_choices = [(standard, violations) for standard, violations in standard_groups.items()]
                
                # Set the grouped choices
                self.fields['violation'].widget = forms.Select(
                    attrs={'class': 'form-select'},
                    choices=grouped_choices
                )
            else:
                # No standards associated with this project yet
                self.fields['violation'].queryset = Violation.objects.none()
                self.fields['violation'].widget.attrs['disabled'] = True
                self.fields['violation'].help_text = "You must add standards to the project before adding violations."
        else:
            self.fields['violation'].queryset = Violation.objects.none()

class ProjectStandardForm(forms.ModelForm):
    class Meta:
        model = ProjectStandard
        fields = ['standard']
        widgets = {
            'standard': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)
        
        if project:
            # Get all standards
            all_standards = Standard.objects.all().order_by('name', 'version')
            
            # Check if project already has a standard
            has_standard = ProjectStandard.objects.filter(project=project).exists()
            
            if has_standard and not self.instance.pk:
                # If creating a new standard association and project already has one
                self.fields['standard'].widget.attrs['disabled'] = True
                self.fields['standard'].help_text = "This project already has a standard. Please remove it first before adding a new one."
            else:
                self.fields['standard'].queryset = all_standards
        else:
            self.fields['standard'].queryset = Standard.objects.none() 