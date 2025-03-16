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
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        # Ensure status_choices is a list
        if not self.status_choices:
            self.status_choices = []
        # Ensure milestone_choices is a list
        if not self.milestone_choices:
            self.milestone_choices = []
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
        ('delayed', 'Delayed'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='milestones')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    due_date = models.DateField(null=True, blank=True)
    completed_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='created_milestones')
    
    def __str__(self):
        return f"{self.project.name} - {self.name}"
    
    class Meta:
        ordering = ['due_date', 'name']
