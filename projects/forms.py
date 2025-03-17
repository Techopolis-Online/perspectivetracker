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
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'size': '6',
            'style': 'height: auto;'
        }),
        label="Assigned Project Staff",
        help_text="Select multiple Techopolis staff members to assign to this project"
    )
    
    assigned_clients = UserModelMultipleChoiceField(
        queryset=CustomUser.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'size': '6',
            'style': 'height: auto;'
        }),
        label="Assigned Client Team",
        help_text="Select multiple client team members to assign to this project"
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
        self.project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)
        
        if self.project:
            # Get all standards
            all_standards = Standard.objects.all().order_by('name', 'version')
            
            # Check if project already has a standard
            has_standard = ProjectStandard.objects.filter(project=self.project).exists()
            
            if has_standard and not self.instance.pk:
                # If creating a new standard association and project already has one
                self.fields['standard'].widget.attrs['disabled'] = True
                self.fields['standard'].help_text = "This project already has a standard. Please remove it first before adding a new one."
            else:
                self.fields['standard'].queryset = all_standards
        else:
            self.fields['standard'].queryset = Standard.objects.none()

class PageForm(forms.ModelForm):
    class Meta:
        model = Page
        fields = ['name', 'description', 'page_type', 'url']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'page_type': forms.Select(attrs={'class': 'form-select', 'id': 'id_page_type'}),
            'url': forms.URLInput(attrs={'class': 'form-control', 'id': 'id_url'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)
        
        # Add JavaScript to show/hide URL field based on page type
        self.fields['page_type'].widget.attrs.update({
            'onchange': 'toggleUrlField()'
        })
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.project:
            instance.project = self.project
        
        if commit:
            instance.save()
        return instance

class MilestoneForm(forms.ModelForm):
    assigned_to = UserModelChoiceField(
        queryset=CustomUser.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Assigned To",
        help_text="Select staff member responsible for this milestone"
    )
    
    class Meta:
        model = Milestone
        fields = ['name', 'milestone_type', 'description', 'status', 'assigned_to', 'start_date', 'due_date', 'completed_date']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'milestone_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'completed_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)
        
        # Set up assigned_to field to show only staff users
        staff_users = CustomUser.objects.filter(
            models.Q(role__name__in=['admin', 'staff']) | models.Q(is_superuser=True)
        ).order_by('first_name', 'last_name')
        self.fields['assigned_to'].queryset = staff_users
        
        # If project has custom milestone types, use those for milestone_type field
        if self.project and self.project.project_type and self.project.project_type.milestone_choices:
            milestone_choices = self.project.project_type.milestone_choices
            # Ensure choices are properly formatted
            formatted_milestone_choices = []
            for key, display in milestone_choices:
                if key and display:  # Skip empty values
                    formatted_milestone_choices.append((key.strip(), display.strip()))
            if formatted_milestone_choices:
                self.fields['milestone_type'] = forms.ChoiceField(
                    choices=[('', '---------')] + formatted_milestone_choices,
                    required=False,
                    widget=forms.Select(attrs={'class': 'form-select'})
                )
        
        # Use standard status choices from Milestone model
        self.fields['status'].choices = Milestone.STATUS_CHOICES
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.project:
            instance.project = self.project
        
        if commit:
            instance.save()
        return instance

class IssueForm(forms.ModelForm):
    assigned_to = UserModelChoiceField(
        queryset=CustomUser.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = Issue
        fields = [
            'milestone', 'page', 'violation', 'issue_description', 
            'steps_to_reproduce', 'tool_or_method', 'user_impact', 
            'user_impact_description', 'workarounds', 'current_status', 
            'assigned_to', 'attachment'
        ]
        widgets = {
            'milestone': forms.Select(attrs={'class': 'form-select'}),
            'page': forms.Select(attrs={'class': 'form-select'}),
            'violation': forms.Select(attrs={'class': 'form-select'}),
            'issue_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'steps_to_reproduce': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'tool_or_method': forms.Select(attrs={'class': 'form-select'}),
            'user_impact': forms.Select(attrs={'class': 'form-select'}),
            'user_impact_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'workarounds': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'current_status': forms.Select(attrs={'class': 'form-select'}),
            'attachment': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)
        
        # Filter assigned_to to only show users assigned to the project
        self.fields['assigned_to'].queryset = CustomUser.objects.filter(
            is_active=True
        ).filter(
            models.Q(role__name__in=['admin', 'staff']) | models.Q(is_superuser=True)
        ).order_by('first_name', 'last_name')
        
        if self.project:
            # Filter milestones to only show milestones from this project
            self.fields['milestone'].queryset = Milestone.objects.filter(
                project=self.project
            ).order_by('name')
            
            # Filter pages to only show pages from this project
            self.fields['page'].queryset = Page.objects.filter(
                project=self.project
            ).order_by('name')
            
            # Filter violations based on project standards
            if self.project.project_type.supports_standards:
                # Get standards associated with this project
                project_standards = ProjectStandard.objects.filter(project=self.project).values_list('standard_id', flat=True)
                
                if project_standards:
                    # Get violations from standards associated with this project
                    violations = Violation.objects.filter(
                        standard_id__in=project_standards
                    ).select_related('standard').order_by('standard__name', 'name')
                    
                    # Group violations by standard for the dropdown
                    standard_groups = {}
                    for violation in violations:
                        standard_name = f"{violation.standard.name} {violation.standard.version}".strip()
                        if standard_name not in standard_groups:
                            standard_groups[standard_name] = []
                        standard_groups[standard_name].append((violation.id, violation.name))
                    
                    # Add "No Violation Applicable" option
                    choices = [('', 'No Violation Applicable')]
                    
                    # Add grouped choices
                    for standard, violations in standard_groups.items():
                        choices.append((standard, violations))
                    
                    # Set the choices
                    self.fields['violation'].widget = forms.Select(
                        attrs={'class': 'form-select'},
                        choices=choices
                    )
                    self.fields['violation'].required = False
                else:
                    # No standards associated with this project yet
                    self.fields['violation'].queryset = Violation.objects.none()
                    self.fields['violation'].required = False
                    self.fields['violation'].help_text = "No standards are associated with this project."
            else:
                # Project type doesn't support standards
                self.fields['violation'].queryset = Violation.objects.none()
                self.fields['violation'].required = False
                self.fields['violation'].widget.attrs['disabled'] = True
            
            # Add dynamic fields based on project type
            if self.project.project_type.issue_fields:
                instance = kwargs.get('instance')
                dynamic_values = {}
                
                # If editing an existing issue, get the dynamic field values
                if instance and instance.dynamic_fields:
                    dynamic_values = instance.dynamic_fields
                
                # Add each custom field to the form
                for field_config in self.project.project_type.issue_fields:
                    field_name = field_config.get('name')
                    field_type = field_config.get('type')
                    field_required = field_config.get('required', False)
                    field_choices = field_config.get('choices', [])
                    field_label = field_config.get('label', field_name.replace('_', ' ').title())
                    field_help_text = field_config.get('help_text', '')
                    
                    # Skip milestone and page fields as they're handled by the model fields
                    if field_name in ['milestone', 'page_scenario']:
                        continue
                    
                    # Create the appropriate form field based on type
                    if field_type == 'text':
                        self.fields[f'dynamic_{field_name}'] = forms.CharField(
                            required=field_required,
                            label=field_label,
                            help_text=field_help_text,
                            widget=forms.TextInput(attrs={'class': 'form-control'})
                        )
                    elif field_type == 'textarea':
                        self.fields[f'dynamic_{field_name}'] = forms.CharField(
                            required=field_required,
                            label=field_label,
                            help_text=field_help_text,
                            widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
                        )
                    elif field_type == 'select':
                        choices = [('', '---------')] + field_choices
                        self.fields[f'dynamic_{field_name}'] = forms.ChoiceField(
                            choices=choices,
                            required=field_required,
                            label=field_label,
                            help_text=field_help_text,
                            widget=forms.Select(attrs={'class': 'form-select'})
                        )
                    elif field_type == 'checkbox':
                        self.fields[f'dynamic_{field_name}'] = forms.BooleanField(
                            required=field_required,
                            label=field_label,
                            help_text=field_help_text,
                            widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
                        )
                    elif field_type == 'radio':
                        self.fields[f'dynamic_{field_name}'] = forms.ChoiceField(
                            choices=field_choices,
                            required=field_required,
                            label=field_label,
                            help_text=field_help_text,
                            widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
                        )
                    elif field_type == 'date':
                        self.fields[f'dynamic_{field_name}'] = forms.DateField(
                            required=field_required,
                            label=field_label,
                            help_text=field_help_text,
                            widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
                        )
                        
                        # Set today's date as default for date_logged field
                        if field_name == 'date_logged' and not instance:
                            self.fields[f'dynamic_{field_name}'].initial = datetime.date.today()
                    elif field_type == 'file':
                        self.fields[f'dynamic_{field_name}'] = forms.FileField(
                            required=field_required,
                            label=field_label,
                            help_text=field_help_text,
                            widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
                        )
                    
                    # Set initial value if editing an existing issue
                    if field_name in dynamic_values:
                        self.fields[f'dynamic_{field_name}'].initial = dynamic_values.get(field_name)
                
                # If this is an accessibility project type with predefined fields,
                # hide the default fields and use the dynamic ones instead
                if any(field.get('name') in ['issue_description', 
                                           'steps_to_reproduce', 'tool_or_method', 'user_impact'] 
                       for field in self.project.project_type.issue_fields):
                    # These fields will be handled by the dynamic fields
                    for field_name in ['issue_description', 'steps_to_reproduce', 
                                      'tool_or_method', 'user_impact', 
                                      'user_impact_description', 'workarounds', 
                                      'current_status', 'violation']:
                        if field_name in self.fields:
                            self.fields[field_name].widget = forms.HiddenInput()
                            self.fields[field_name].required = False
        else:
            # No project provided
            self.fields['milestone'].queryset = Milestone.objects.none()
            self.fields['page'].queryset = Page.objects.none()
            self.fields['violation'].queryset = Violation.objects.none()
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Collect dynamic field values
        dynamic_fields = {}
        
        if self.project and self.project.project_type.issue_fields:
            for field_config in self.project.project_type.issue_fields:
                field_name = field_config.get('name')
                form_field_name = f'dynamic_{field_name}'
                
                # Handle special case for page_scenario field
                if field_name == 'page_scenario' and 'page' in cleaned_data:
                    page = cleaned_data.get('page')
                    if page:
                        dynamic_fields[field_name] = page.id
                # Handle special case for milestone field
                elif field_name == 'milestone' and 'milestone' in cleaned_data:
                    milestone = cleaned_data.get('milestone')
                    if milestone:
                        dynamic_fields[field_name] = milestone.id
                # Handle file uploads
                elif field_config.get('type') == 'file' and form_field_name in cleaned_data:
                    # For file fields, we store the file name rather than the file object
                    file_obj = cleaned_data.get(form_field_name)
                    if file_obj:
                        dynamic_fields[field_name] = file_obj.name
                # Handle regular dynamic fields
                elif form_field_name in cleaned_data:
                    value = cleaned_data.get(form_field_name)
                    
                    # Convert date objects to string for JSON storage
                    if isinstance(value, (datetime.date, datetime.datetime)):
                        value = value.isoformat()
                        
                    dynamic_fields[field_name] = value
        
        # Store the dynamic fields
        self.dynamic_fields = dynamic_fields
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.project:
            instance.project = self.project
        
        # Map dynamic fields to model fields if using predefined accessibility fields
        if self.project and self.project.project_type.issue_fields:
            # Check if this is an accessibility project type with predefined fields
            has_accessibility_fields = any(
                field.get('name') in ['issue_description', 
                                     'steps_to_reproduce', 'tool_or_method', 'user_impact'] 
                for field in self.project.project_type.issue_fields
            )
            
            if has_accessibility_fields and hasattr(self, 'dynamic_fields'):
                # Map dynamic fields to model fields
                field_mapping = {
                    'issue_description': 'dynamic_issue_description',
                    'steps_to_reproduce': 'dynamic_steps_to_reproduce',
                    'tool_or_method': 'dynamic_tool_or_method',
                    'user_impact': 'dynamic_user_impact',
                    'user_impact_description': 'dynamic_user_impact_description',
                    'workarounds': 'dynamic_workarounds',
                    'current_status': 'dynamic_current_status'
                }
                
                for model_field, dynamic_field in field_mapping.items():
                    if dynamic_field[8:] in self.dynamic_fields:  # Remove 'dynamic_' prefix
                        setattr(instance, model_field, self.dynamic_fields[dynamic_field[8:]])
        
        # Save dynamic fields
        if hasattr(self, 'dynamic_fields'):
            instance.dynamic_fields = self.dynamic_fields
            
            # Handle file uploads
            for field_config in self.project.project_type.issue_fields:
                if field_config.get('type') == 'file':
                    field_name = field_config.get('name')
                    form_field_name = f'dynamic_{field_name}'
                    
                    if form_field_name in self.files:
                        file_obj = self.files[form_field_name]
                        # Store file path or handle file upload as needed
                        # This depends on how you want to store files in your application
                        # For now, we're just storing the file name in dynamic_fields
        
        # Handle the model's attachment field
        if 'attachment' in self.files:
            instance.attachment = self.files['attachment']
        
        if commit:
            instance.save()
        return instance

class CommentForm(forms.ModelForm):
    """Form for adding comments to issues"""
    class Meta:
        model = Comment
        fields = ['text', 'comment_type']
        widgets = {
            'text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Add your comment here...'}),
            'comment_type': forms.Select(attrs={'class': 'form-select'})
        }
        
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Only staff and admins can create internal comments
        if self.user and not (self.user.is_superuser or 
                             (hasattr(self.user, 'role') and 
                              self.user.role and 
                              self.user.role.name in ['admin', 'staff'])):
            self.fields['comment_type'].widget = forms.HiddenInput()
            self.fields['comment_type'].initial = 'external'

class IssueStatusForm(forms.ModelForm):
    """A simplified form for updating just the status of an issue"""
    
    class Meta:
        model = Issue
        fields = ['current_status']
        widgets = {
            'current_status': forms.Select(attrs={'class': 'form-select form-select-lg'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['current_status'].label = "Change Status" 