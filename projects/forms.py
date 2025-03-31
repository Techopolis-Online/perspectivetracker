from django import forms
from .models import Project, Standard, Violation, ProjectViolation, ProjectType, ProjectStandard, Page, Milestone, Issue, Comment
from users.models import CustomUser
import json
from django.db import models
import datetime

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
    
    use_predefined_accessibility_fields = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Use predefined accessibility issue fields (Page, Violation, Issue Description, Steps, Tool/Method, User Impact, etc.)"
    )
    
    issue_fields_text = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 8}),
        required=False,
        help_text="Enter each issue field in JSON format, one per line. Example: {\"name\": \"field_name\", \"type\": \"text\", \"required\": true}"
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
            
        # Check if instance has predefined accessibility fields
        if instance and instance.issue_fields:
            # Check if the issue fields match the predefined accessibility fields
            # This is a simple check - we just look for some key field names
            field_names = [field.get('name') for field in instance.issue_fields]
            has_accessibility_fields = all(name in field_names for name in [
                'page_scenario', 'violation_type', 'issue_description', 
                'steps_to_reproduce', 'tool_or_method', 'user_impact'
            ])
            
            self.fields['use_predefined_accessibility_fields'].initial = has_accessibility_fields
            
            # Only convert to text format if not using predefined fields
            if not has_accessibility_fields:
                items = []
                for field in instance.issue_fields:
                    items.append(json.dumps(field))
                self.fields['issue_fields_text'].initial = "\n".join(items)
    
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
    
    def clean_issue_fields_text(self):
        text = self.cleaned_data.get('issue_fields_text', '')
        if not text.strip():
            return []
        
        # Split by lines and parse each line as JSON
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        fields = []
        
        for i, line in enumerate(lines):
            try:
                field = json.loads(line)
                if not isinstance(field, dict):
                    raise forms.ValidationError(f"Line {i+1} is not a valid JSON object")
                
                # Validate required fields
                if 'name' not in field:
                    raise forms.ValidationError(f"Field in line {i+1} is missing 'name' property")
                if 'type' not in field:
                    raise forms.ValidationError(f"Field in line {i+1} is missing 'type' property")
                
                # Validate field type
                valid_types = ['text', 'textarea', 'select', 'checkbox', 'radio', 'date']
                if field['type'] not in valid_types:
                    raise forms.ValidationError(f"Field type '{field['type']}' in line {i+1} is not valid. Valid types are: {', '.join(valid_types)}")
                
                # If type is select or radio, ensure choices are provided
                if field['type'] in ['select', 'radio'] and ('choices' not in field or not field['choices']):
                    raise forms.ValidationError(f"Field in line {i+1} has type '{field['type']}' but no choices are provided")
                
                fields.append(field)
            except json.JSONDecodeError:
                raise forms.ValidationError(f"Line {i+1} is not valid JSON: {line}")
        
        return fields
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.status_choices = self.cleaned_data.get('status_choices_text', [])
        instance.milestone_choices = self.cleaned_data.get('milestone_choices_text', [])
        
        # Handle predefined accessibility fields
        if self.cleaned_data.get('use_predefined_accessibility_fields'):
            # Define the predefined accessibility issue fields
            predefined_fields = [
                {
                    "name": "milestone", 
                    "type": "select", 
                    "required": True, 
                    "label": "Milestone"
                    # Milestone choices will be loaded from the project's milestones list
                },
                {
                    "name": "page_scenario", 
                    "type": "select", 
                    "required": True, 
                    "label": "Page / Scenario"
                    # Page choices will be loaded from the project's pages list
                },
                {
                    "name": "issue_description", 
                    "type": "textarea", 
                    "required": True, 
                    "label": "Issue Description"
                },
                {
                    "name": "steps_to_reproduce", 
                    "type": "textarea", 
                    "required": True, 
                    "label": "Steps"
                },
                {
                    "name": "tool_or_method", 
                    "type": "select", 
                    "required": True, 
                    "label": "Tool or Method",
                    "choices": [
                        ["jaws", "JAWS"],
                        ["nvda", "NVDA"],
                        ["cca", "CCA"],
                        ["zoomtext", "ZoomText"],
                        ["voiceover", "VoiceOver"],
                        ["talkback", "Talkback"],
                        ["wave", "WAVE"],
                        ["accessibility_insights", "Accessibility Insights"],
                        ["other", "Other"]
                    ]
                },
                {
                    "name": "user_impact", 
                    "type": "select", 
                    "required": True, 
                    "label": "User Impact",
                    "choices": [
                        ["high", "High"],
                        ["low", "Low"],
                        ["best_practice", "Best Practice"]
                    ]
                },
                {
                    "name": "user_impact_description", 
                    "type": "textarea", 
                    "required": True, 
                    "label": "User Impact Description"
                },
                {
                    "name": "workarounds", 
                    "type": "textarea", 
                    "required": False, 
                    "label": "Workarounds"
                },
                {
                    "name": "current_status", 
                    "type": "select", 
                    "required": True, 
                    "label": "Current Status",
                    "choices": [
                        ["pass", "Pass"],
                        ["fail", "Fail"],
                        ["qa", "QA"],
                        ["in_remediation", "In Remediation"],
                        ["ready_for_testing", "Ready For Testing"]
                    ]
                },
                {
                    "name": "date_logged", 
                    "type": "date", 
                    "required": True, 
                    "label": "Date"
                },
                {
                    "name": "attachments", 
                    "type": "file", 
                    "required": False, 
                    "label": "Attachments"
                }
            ]
            
            # Set the predefined fields
            instance.issue_fields = predefined_fields
        elif self.cleaned_data.get('issue_fields_text'):
            # Parse custom issue fields from text input
            instance.issue_fields = self.cleaned_data.get('issue_fields_text', [])
        
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
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        label="Assigned Project Staff",
        help_text="Select Techopolis staff members to assign to this project"
    )
    
    assigned_clients = UserModelMultipleChoiceField(
        queryset=CustomUser.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
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

class ProjectStandardForm(forms.ModelForm):
    class Meta:
        model = ProjectStandard
        fields = ['standard']
        widgets = {
            'standard': forms.Select(attrs={'class': 'form-select'}),
        }
        
    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Store the project for later use
        self.project = project
        
        # If we're showing this form for a specific project that requires standards
        if project and project.project_type and project.project_type.supports_standards:
            # Exclude standards already associated with the project
            existing_standards = ProjectStandard.objects.filter(project=project).values_list('standard', flat=True)
            self.fields['standard'].queryset = Standard.objects.exclude(id__in=existing_standards)

class ProjectViolationForm(forms.ModelForm):
    assigned_to = UserModelChoiceField(
        queryset=CustomUser.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = ProjectViolation
        fields = ['violation', 'status', 'notes', 'location', 'assigned_to']
        widgets = {
            'violation': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set up for assigned_to field
        self.fields['assigned_to'].queryset = CustomUser.objects.filter(
            is_active=True
        ).filter(
            models.Q(role__name__in=['admin', 'staff']) |
            models.Q(is_superuser=True)
        ).distinct().order_by('first_name', 'last_name')

class PageForm(forms.ModelForm):
    class Meta:
        model = Page
        fields = ['name', 'description', 'page_type', 'url']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'page_type': forms.Select(attrs={'class': 'form-select'}),
            'url': forms.URLInput(attrs={'class': 'form-control'}),
        }

class MilestoneForm(forms.ModelForm):
    class Meta:
        model = Milestone
        fields = ['name', 'description', 'milestone_type', 'status', 'assigned_to', 'start_date', 'due_date']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'milestone_type': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)
        
        # Set up for assigned_to field
        self.fields['assigned_to'].queryset = CustomUser.objects.filter(
            is_active=True
        ).filter(
            models.Q(role__name__in=['admin', 'staff']) |
            models.Q(is_superuser=True)
        ).distinct().order_by('first_name', 'last_name')
        
        # Set milestone type choices based on project type if project exists
        if project and project.project_type and project.project_type.milestone_choices:
            choices = [(key, display) for key, display in project.project_type.milestone_choices]
            self.fields['milestone_type'].widget.choices = [('', '----------')] + choices
        elif self.instance and self.instance.project and self.instance.project.project_type and self.instance.project.project_type.milestone_choices:
            choices = [(key, display) for key, display in self.instance.project.project_type.milestone_choices]
            self.fields['milestone_type'].widget.choices = [('', '----------')] + choices

class IssueForm(forms.ModelForm):
    class Meta:
        model = Issue
        fields = [
            'milestone', 'page', 'violation', 'issue_description', 
            'steps_to_reproduce', 'tool_or_method', 'user_impact', 
            'user_impact_description', 'workarounds', 'current_status', 
            'attachment', 'assigned_to'
        ]
        widgets = {
            'milestone': forms.Select(attrs={'class': 'form-select'}),
            'page': forms.Select(attrs={'class': 'form-select'}),
            'violation': forms.Select(attrs={'class': 'form-select'}),
            'issue_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'steps_to_reproduce': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'tool_or_method': forms.Select(attrs={'class': 'form-select'}),
            'user_impact': forms.Select(attrs={'class': 'form-select'}),
            'user_impact_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'workarounds': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'current_status': forms.Select(attrs={'class': 'form-select'}),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)
        
        # Set up for assigned_to field
        self.fields['assigned_to'].queryset = CustomUser.objects.filter(
            is_active=True
        ).filter(
            models.Q(role__name__in=['admin', 'staff']) |
            models.Q(is_superuser=True)
        ).distinct().order_by('first_name', 'last_name')
        
        # Filter milestone and page options by project
        if project:
            self.fields['milestone'].queryset = Milestone.objects.filter(project=project)
            self.fields['page'].queryset = Page.objects.filter(project=project)
        
        # If instance exists, filter by its project
        elif self.instance and self.instance.project:
            self.fields['milestone'].queryset = Milestone.objects.filter(project=self.instance.project)
            self.fields['page'].queryset = Page.objects.filter(project=self.instance.project)

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['comment_type', 'text', 'milestone']
        widgets = {
            'comment_type': forms.Select(attrs={'class': 'form-select'}),
            'text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'milestone': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        issue = kwargs.pop('issue', None)
        super().__init__(*args, **kwargs)
        
        # Filter milestone options by project
        if issue and issue.project:
            self.fields['milestone'].queryset = Milestone.objects.filter(project=issue.project)
        elif self.instance and self.instance.issue and self.instance.issue.project:
            self.fields['milestone'].queryset = Milestone.objects.filter(project=self.instance.issue.project)

class IssueStatusForm(forms.Form):
    """A simple form for updating the status of an issue"""
    status = forms.ChoiceField(
        choices=Issue.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    comment = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False
    )