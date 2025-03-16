from django.db import models
from django.utils.text import slugify
from clients.models import Client
from users.models import CustomUser

class ProjectType(models.Model):
    """Project type model (e.g., Accessibility, Beta App Review, App Development, Other)"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    slug = models.SlugField(max_length=100, unique=True)
    supports_standards = models.BooleanField(default=False, help_text="Whether this project type supports standards and violations")
    status_choices = models.JSONField(default=list, blank=True, help_text="List of status choices for this project type in format [['key', 'Display Name'], ...]")
    milestone_choices = models.JSONField(default=list, blank=True, help_text="List of milestone choices for this project type in format [['key', 'Display Name'], ...]")
    issue_fields = models.JSONField(default=list, blank=True, help_text="List of custom issue fields for this project type in format [{'name': 'field_name', 'type': 'field_type', 'required': true/false, 'choices': [['key', 'Display Name'], ...]}]")
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        # Ensure status_choices is a list
        if not self.status_choices:
            self.status_choices = []
        # Ensure milestone_choices is a list
        if not self.milestone_choices:
            self.milestone_choices = []
        # Ensure issue_fields is a list
        if not self.issue_fields:
            self.issue_fields = []
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name

class Project(models.Model):
    """Project model with status choices based on project type"""
    # Default status choices if project type doesn't define any
    DEFAULT_STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]
    
    name = models.CharField(max_length=200)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='projects')
    project_type = models.ForeignKey(ProjectType, on_delete=models.PROTECT, related_name='projects')
    status = models.CharField(max_length=50, default='not_started')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='created_projects')
    assigned_to = models.ManyToManyField(CustomUser, related_name='assigned_projects', blank=True)
    
    def __str__(self):
        return f"{self.name} ({self.client.company_name})"
    
    def get_status_choices(self):
        """Return status choices based on project type"""
        if self.project_type and self.project_type.status_choices:
            return self.project_type.status_choices
        return self.DEFAULT_STATUS_CHOICES
    
    def get_status_display(self):
        """Return the display value for the current status"""
        choices = self.get_status_choices()
        for key, display in choices:
            if key and key.strip() == self.status:
                return display.strip()
        return self.status
    
    class Meta:
        ordering = ['-created_at']

class Standard(models.Model):
    """Standard model (e.g., WCAG 2.1)"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    version = models.CharField(max_length=50, blank=True)
    url = models.URLField(blank=True, help_text="Link to the standard documentation")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='created_standards')
    
    def __str__(self):
        return f"{self.name} {self.version}".strip()
    
    class Meta:
        ordering = ['name', 'version']
        unique_together = ['name', 'version']

class Violation(models.Model):
    """Violation model (e.g., specific WCAG criteria)"""
    name = models.CharField(max_length=200)
    description = models.TextField()
    standard = models.ForeignKey(Standard, on_delete=models.CASCADE, related_name='violations')
    url = models.URLField(blank=True, help_text="Link to more information about this violation")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='created_violations')
    
    def __str__(self):
        return f"{self.name}"
    
    class Meta:
        ordering = ['standard', 'name']
        unique_together = ['standard', 'name']

class ProjectViolation(models.Model):
    """Instance of a violation in a project"""
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('fixed', 'Fixed'),
        ('wont_fix', 'Won\'t Fix'),
        ('not_applicable', 'Not Applicable'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='project_violations')
    violation = models.ForeignKey(Violation, on_delete=models.CASCADE, related_name='project_instances')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    notes = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True, help_text="Where in the application this violation was found")
    screenshot = models.ImageField(upload_to='violation_screenshots/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='reported_violations')
    assigned_to = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_violations')
    
    def __str__(self):
        return f"{self.project.name} - {self.violation.name}"
    
    class Meta:
        ordering = ['-created_at']

class ProjectStandard(models.Model):
    """Association between a project and a standard"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='project_standards')
    standard = models.ForeignKey(Standard, on_delete=models.CASCADE, related_name='project_instances')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='added_standards')
    
    def __str__(self):
        return f"{self.project.name} - {self.standard}"
    
    class Meta:
        ordering = ['standard__name', 'standard__version']
        constraints = [
            models.UniqueConstraint(fields=['project'], name='one_standard_per_project')
        ]

class Page(models.Model):
    """Page model for project pages (web, mobile, etc.)"""
    TYPE_CHOICES = [
        ('web', 'Web'),
        ('mobile', 'Mobile'),
        ('other', 'Other'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='pages')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    page_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='web')
    url = models.URLField(blank=True, help_text="URL for web pages")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='created_pages')
    
    def __str__(self):
        return f"{self.name} ({self.get_page_type_display()})"
    
    class Meta:
        ordering = ['name']
        unique_together = ['project', 'name']

class Milestone(models.Model):
    """Milestone model for project progress tracking"""
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('published', 'Published'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='milestones')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    milestone_type = models.CharField(max_length=50, blank=True, help_text="Type of milestone based on project type")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    assigned_to = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_milestones')
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    completed_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='created_milestones')
    
    def get_milestone_type_choices(self):
        """Return milestone type choices based on project type"""
        if self.project and self.project.project_type and self.project.project_type.milestone_choices:
            return self.project.project_type.milestone_choices
        return []
    
    def get_milestone_type_display(self):
        """Return the display value for the current milestone type"""
        choices = self.get_milestone_type_choices()
        for key, display in choices:
            if key and key.strip() == self.milestone_type:
                return display.strip()
        return self.milestone_type
    
    def __str__(self):
        return f"{self.project.name} - {self.name}"
    
    class Meta:
        ordering = ['due_date', 'name']

class Issue(models.Model):
    """Issue model for tracking issues in projects"""
    TOOL_CHOICES = [
        ('jaws', 'JAWS'),
        ('nvda', 'NVDA'),
        ('cca', 'CCA'),
        ('zoomtext', 'ZoomText'),
        ('voiceover', 'VoiceOver'),
        ('talkback', 'Talkback'),
        ('wave', 'WAVE'),
        ('accessibility_insights', 'Accessibility Insights'),
        ('other', 'Other'),
    ]
    
    IMPACT_CHOICES = [
        ('high', 'High'),
        ('low', 'Low'),
        ('best_practice', 'Best Practice'),
    ]
    
    STATUS_CHOICES = [
        ('pass', 'Pass'),
        ('fail', 'Fail'),
        ('qa', 'QA'),
        ('in_remediation', 'In Remediation'),
        ('ready_for_testing', 'Ready For Testing'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='issues')
    milestone = models.ForeignKey(Milestone, on_delete=models.CASCADE, related_name='issues')
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='issues')
    violation = models.ForeignKey(Violation, on_delete=models.CASCADE, related_name='issues', null=True, blank=True)
    issue_description = models.TextField()
    steps_to_reproduce = models.TextField()
    tool_or_method = models.CharField(max_length=50, choices=TOOL_CHOICES)
    user_impact = models.CharField(max_length=20, choices=IMPACT_CHOICES)
    user_impact_description = models.TextField()
    workarounds = models.TextField(blank=True)
    current_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='fail')
    attachment = models.FileField(upload_to='issue_attachments/', blank=True, null=True, help_text="File attachment for this issue")
    dynamic_fields = models.JSONField(default=dict, blank=True, help_text="Dynamic fields based on project type")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='created_issues')
    assigned_to = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_issues')
    
    def __str__(self):
        return f"{self.project.name} - {self.page.name} - {self.issue_description[:50]}"
    
    class Meta:
        ordering = ['-created_at']

class Comment(models.Model):
    """Comment model for issues"""
    COMMENT_TYPE_CHOICES = [
        ('internal', 'Internal'),
        ('external', 'External'),
    ]
    
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='comments')
    comment_type = models.CharField(max_length=10, choices=COMMENT_TYPE_CHOICES, default='external')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Comment by {self.author} on {self.issue}"
    
    class Meta:
        ordering = ['-created_at']

class IssueComment(models.Model):
    """Simple comment model for issues from milestone view"""
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name='issue_comments')
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='issue_comments')
    
    def __str__(self):
        return f"Comment on {self.issue} by {self.created_by}"
    
    class Meta:
        ordering = ['-created_at']
