from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.utils.text import slugify
from .models import (
    Project, Standard, Violation, ProjectViolation, ProjectStandard, 
    Page, Milestone, Issue, Comment, IssueModification, ProjectType
)

@receiver(pre_save, sender=ProjectViolation)
def update_violation_timestamps(sender, instance, **kwargs):
    """Update timestamps when a project violation is modified"""
    if instance.pk:  # Only for existing instances
        instance.updated_at = timezone.now()

@receiver(post_save, sender=Issue)
def handle_issue_save(sender, instance, created, **kwargs):
    """Handle post-save operations for issues"""
    if created:
        # Create initial IssueModification for new issues
        IssueModification.objects.create(
            issue=instance,
            milestone=instance.milestone,
            modified_by=instance.created_by,
            modification_type='creation',
            new_value=instance.current_status
        )
    else:
        # Get the latest modification to avoid duplicate entries
        latest_mod = instance.modifications.first()
        if not latest_mod or latest_mod.new_value != instance.current_status:
            # Create modification only if status has changed
            IssueModification.objects.create(
                issue=instance,
                milestone=instance.milestone,
                modified_by=instance.created_by,
                modification_type='status_change',
                previous_value=latest_mod.new_value if latest_mod else None,
                new_value=instance.current_status
            )

@receiver(post_save, sender=Comment)
def handle_comment_save(sender, instance, created, **kwargs):
    """Handle post-save operations for comments"""
    if created and instance.issue:
        # Create IssueModification for new comments
        IssueModification.objects.create(
            issue=instance.issue,
            milestone=instance.issue.milestone,
            modified_by=instance.created_by,
            modification_type='comment',
            comment=instance
        )

@receiver(pre_save, sender=ProjectType)
def handle_project_type_slug(sender, instance, **kwargs):
    """Generate slug for project types if not provided"""
    if not instance.slug:
        instance.slug = slugify(instance.name)