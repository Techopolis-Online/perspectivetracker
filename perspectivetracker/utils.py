"""
Utility functions for the Perspective Tracker project.
"""
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.urls import reverse
from django.core.mail import get_connection
from django.core.mail import EmailMultiAlternatives
from django.db import models
import datetime
import logging
from users.models import CustomUser, Role, AdminSettings


def send_email(subject, template_name, context, recipient_list, from_email=None):
    """
    Generic function to send emails using templates.
    
    Args:
        subject (str): Email subject
        template_name (str): Path to the HTML template
        context (dict): Context data for the template
        recipient_list (list): List of recipient email addresses
        from_email (str, optional): Sender email address. Defaults to DEFAULT_FROM_EMAIL.
    
    Returns:
        bool: True if email was sent successfully
    """
    return send_email_with_fallback(subject, template_name, context, recipient_list, from_email)


def send_project_created_email(request, project, recipient_list=None):
    """
    Send email notification when a new project is created.
    
    Args:
        request: HTTP request object
        project: Project instance
        recipient_list (list, optional): List of recipient email addresses.
            If None, sends to all assigned users.
    """
    if recipient_list is None:
        recipient_list = [user.email for user in project.assigned_to.all()]
        
    if not recipient_list:
        return False
        
    project_url = request.build_absolute_uri(
        reverse('projects:project_detail', kwargs={'pk': project.pk})
    )
    
    context = {
        'project': project,
        'client': project.client,
        'creator': project.created_by,
        'project_url': project_url,
    }
    
    return send_email(
        f'New Project Created: {project.name}',
        'emails/project_created.html',
        context,
        recipient_list
    )


def send_project_updated_email(request, project, updated_fields, recipient_list=None):
    """
    Send email notification when a project is updated.
    
    Args:
        request: HTTP request object
        project: Project instance
        updated_fields (list): List of fields that were updated
        recipient_list (list, optional): List of recipient email addresses.
            If None, sends to all assigned users.
    """
    if recipient_list is None:
        recipient_list = [user.email for user in project.assigned_to.all()]
        
    if not recipient_list:
        return False
        
    project_url = request.build_absolute_uri(
        reverse('projects:project_detail', kwargs={'pk': project.pk})
    )
    
    context = {
        'project': project,
        'client': project.client,
        'updater': request.user,
        'project_url': project_url,
        'updated_fields': updated_fields,
    }
    
    return send_email(
        f'Project Updated: {project.name}',
        'emails/project_updated.html',
        context,
        recipient_list
    )


def send_issue_created_email(request, issue, recipient_list=None):
    """
    Send email notification when a new issue is created.
    
    Args:
        request: HTTP request object
        issue: Issue instance
        recipient_list (list, optional): List of recipient email addresses.
            If None, sends to assigned user and project team.
    """
    if recipient_list is None:
        recipient_list = []
        # Add assigned user if exists
        if issue.assigned_to:
            recipient_list.append(issue.assigned_to.email)
        # Add project team members
        for user in issue.project.assigned_to.all():
            if user.email not in recipient_list:
                recipient_list.append(user.email)
                
    if not recipient_list:
        return False
        
    issue_url = request.build_absolute_uri(
        reverse('projects:issue_detail', kwargs={'project_id': issue.project.pk, 'pk': issue.pk})
    )
    
    context = {
        'issue': issue,
        'project': issue.project,
        'milestone': issue.milestone,
        'page': issue.page,
        'creator': issue.created_by,
        'issue_url': issue_url,
    }
    
    return send_email(
        f'New Issue Created: {issue.project.name}',
        'emails/issue_created.html',
        context,
        recipient_list
    )


def send_issue_updated_email(request, issue, updated_fields, recipient_list=None):
    """
    Send email notification when an issue is updated.
    
    Args:
        request: HTTP request object
        issue: Issue instance
        updated_fields (list): List of fields that were updated
        recipient_list (list, optional): List of recipient email addresses.
            If None, sends to assigned user and project team.
    """
    if recipient_list is None:
        recipient_list = []
        # Add assigned user if exists
        if issue.assigned_to:
            recipient_list.append(issue.assigned_to.email)
        # Add project team members
        for user in issue.project.assigned_to.all():
            if user.email not in recipient_list:
                recipient_list.append(user.email)
                
    if not recipient_list:
        return False
        
    issue_url = request.build_absolute_uri(
        reverse('projects:issue_detail', kwargs={'project_id': issue.project.pk, 'pk': issue.pk})
    )
    
    context = {
        'issue': issue,
        'project': issue.project,
        'milestone': issue.milestone,
        'page': issue.page,
        'updater': request.user,
        'issue_url': issue_url,
        'updated_fields': updated_fields,
    }
    
    return send_email(
        f'Issue Updated: {issue.project.name}',
        'emails/issue_updated.html',
        context,
        recipient_list
    )


def send_comment_notification_email(request, comment, recipient_list=None):
    """
    Send email notification when a new comment is added to an issue.
    
    Args:
        request: HTTP request object
        comment: Comment instance
        recipient_list (list, optional): List of recipient email addresses.
            If None, sends to assigned user and project team.
    """
    issue = comment.issue
    
    if recipient_list is None:
        recipient_list = []
        # Add assigned user if exists
        if issue.assigned_to:
            recipient_list.append(issue.assigned_to.email)
        # Add project team members
        for user in issue.project.assigned_to.all():
            if user.email not in recipient_list and user.email != comment.author.email:
                recipient_list.append(user.email)
                
    if not recipient_list:
        return False
        
    issue_url = request.build_absolute_uri(
        reverse('projects:issue_detail', kwargs={'project_id': issue.project.pk, 'pk': issue.pk})
    )
    
    context = {
        'comment': comment,
        'issue': issue,
        'project': issue.project,
        'milestone': issue.milestone,
        'author': comment.author,
        'issue_url': issue_url,
    }
    
    return send_email(
        f'New Comment on Issue: {issue.project.name}',
        'emails/comment_notification.html',
        context,
        recipient_list
    )


def send_milestone_created_email(request, milestone, recipient_list=None):
    """
    Send email notification when a new milestone is created.
    
    Args:
        request: HTTP request object
        milestone: Milestone instance
        recipient_list (list, optional): List of recipient email addresses.
            If None, sends to assigned user and project team.
    """
    if recipient_list is None:
        recipient_list = []
        # Add assigned user if exists
        if milestone.assigned_to:
            recipient_list.append(milestone.assigned_to.email)
        # Add project team members
        for user in milestone.project.assigned_to.all():
            if user.email not in recipient_list:
                recipient_list.append(user.email)
                
    if not recipient_list:
        return False
        
    milestone_url = request.build_absolute_uri(
        reverse('projects:milestone_detail', kwargs={'pk': milestone.pk})
    )
    
    context = {
        'milestone': milestone,
        'project': milestone.project,
        'creator': milestone.created_by,
        'milestone_url': milestone_url,
    }
    
    return send_email(
        f'New Milestone Created: {milestone.project.name}',
        'emails/milestone_created.html',
        context,
        recipient_list
    )


def send_milestone_updated_email(request, milestone, updated_fields, recipient_list=None):
    """
    Send email notification when a milestone is updated.
    
    Args:
        request: HTTP request object
        milestone: Milestone instance
        updated_fields (list): List of fields that were updated
        recipient_list (list, optional): List of recipient email addresses.
            If None, sends to assigned user and project team.
    """
    if recipient_list is None:
        recipient_list = []
        # Add assigned user if exists
        if milestone.assigned_to:
            recipient_list.append(milestone.assigned_to.email)
        # Add project team members
        for user in milestone.project.assigned_to.all():
            if user.email not in recipient_list:
                recipient_list.append(user.email)
                
    if not recipient_list:
        return False
        
    milestone_url = request.build_absolute_uri(
        reverse('projects:milestone_detail', kwargs={'pk': milestone.pk})
    )
    
    context = {
        'milestone': milestone,
        'project': milestone.project,
        'updater': request.user,
        'milestone_url': milestone_url,
        'updated_fields': updated_fields,
    }
    
    return send_email(
        f'Milestone Updated: {milestone.project.name}',
        'emails/milestone_updated.html',
        context,
        recipient_list
    )


def send_assignment_notification_email(request, obj, recipient_list=None):
    """
    Send email notification when a user is assigned to a project, issue, or milestone.
    
    Args:
        request: HTTP request object
        obj: The object (Project, Issue, or Milestone) the user is assigned to
        recipient_list (list, optional): List of recipient email addresses.
            If None, sends to the assigned user.
    """
    if recipient_list is None:
        if hasattr(obj, 'assigned_to'):
            if isinstance(obj.assigned_to, list) or hasattr(obj.assigned_to, 'all'):
                # For ManyToMany fields (like in Project)
                recipient_list = [user.email for user in obj.assigned_to.all()]
            else:
                # For ForeignKey fields (like in Issue or Milestone)
                recipient_list = [obj.assigned_to.email]
        else:
            return False
                
    if not recipient_list:
        return False
    
    # Determine object type and URL
    if obj.__class__.__name__ == 'Project':
        obj_type = 'Project'
        obj_url = request.build_absolute_uri(
            reverse('projects:project_detail', kwargs={'pk': obj.pk})
        )
    elif obj.__class__.__name__ == 'Issue':
        obj_type = 'Issue'
        obj_url = request.build_absolute_uri(
            reverse('projects:issue_detail', kwargs={'project_id': obj.project.pk, 'pk': obj.pk})
        )
    elif obj.__class__.__name__ == 'Milestone':
        obj_type = 'Milestone'
        obj_url = request.build_absolute_uri(
            reverse('projects:milestone_detail', kwargs={'pk': obj.pk})
        )
    else:
        return False
    
    context = {
        'object': obj,
        'object_type': obj_type,
        'assigner': request.user,
        'object_url': obj_url,
    }
    
    return send_email(
        f'You have been assigned to a {obj_type}: {obj}',
        'emails/assignment_notification.html',
        context,
        recipient_list
    )


def send_milestone_completed_email(request, milestone, recipient_list=None):
    """
    Send email notification when a milestone is marked as completed.
    
    Args:
        request: HTTP request object
        milestone: Milestone instance
        recipient_list (list, optional): List of recipient email addresses.
            If None, sends to assigned user, project team, and client contacts.
    """
    if recipient_list is None:
        recipient_list = []
        # Add assigned user if exists
        if milestone.assigned_to:
            recipient_list.append(milestone.assigned_to.email)
        # Add project team members
        for user in milestone.project.assigned_to.all():
            if user.email not in recipient_list:
                recipient_list.append(user.email)
        # Add client contacts if milestone is published
        if milestone.status == 'published':
            from clients.models import ClientCoworker
            client_coworkers = ClientCoworker.objects.filter(client=milestone.project.client)
            for coworker in client_coworkers:
                if coworker.user and coworker.user.email not in recipient_list:
                    recipient_list.append(coworker.user.email)
                
    if not recipient_list:
        return False
        
    milestone_url = request.build_absolute_uri(
        reverse('projects:milestone_detail', kwargs={'pk': milestone.pk})
    )
    
    # Calculate milestone statistics
    from projects.models import Issue
    total_issues = Issue.objects.filter(milestone=milestone).count()
    completed_issues = Issue.objects.filter(milestone=milestone, current_status='completed').count()
    completion_rate = 0
    if total_issues > 0:
        completion_rate = round((completed_issues / total_issues) * 100)
    
    stats = {
        'total_issues': total_issues,
        'completed_issues': completed_issues,
        'completion_rate': completion_rate
    }
    
    context = {
        'milestone': milestone,
        'project': milestone.project,
        'completer': request.user,
        'milestone_url': milestone_url,
        'stats': stats
    }
    
    return send_email(
        f'Milestone Completed: {milestone.project.name} - {milestone.name}',
        'emails/milestone_completed.html',
        context,
        recipient_list
    )


def send_task_notification_email(request, task, action_type, recipient_list=None):
    """
    Send email notification about a task (created, updated, completed, etc.).
    
    Args:
        request: HTTP request object
        task: Task instance
        action_type (str): Type of action (created, updated, completed, etc.)
        recipient_list (list, optional): List of recipient email addresses.
            If None, sends to assigned user and task list members.
    """
    if recipient_list is None:
        recipient_list = []
        # Add assigned user if exists
        if task.assigned_to:
            recipient_list.append(task.assigned_to.email)
        # Add task list members
        if hasattr(task.task_list, 'members'):
            for user in task.task_list.members.all():
                if user.email not in recipient_list and user != request.user:
                    recipient_list.append(user.email)
                
    if not recipient_list:
        return False
    
    # Build task URL - this will need to be adjusted based on your URL structure
    try:
        task_url = request.build_absolute_uri(
            reverse('projects:task_detail', kwargs={'pk': task.pk})
        )
    except:
        # Fallback if the URL can't be built
        task_url = request.build_absolute_uri('/')
    
    context = {
        'task': task,
        'action_type': action_type,
        'actor': request.user,
        'task_url': task_url,
    }
    
    return send_email(
        f'Task {action_type.title()}: {task.title}',
        'emails/task_notification.html',
        context,
        recipient_list
    )


def send_task_completed_email(request, task, recipient_list=None):
    """
    Send email notification when a task is marked as completed.
    
    Args:
        request: HTTP request object
        task: Task instance
        recipient_list (list, optional): List of recipient email addresses.
            If None, sends to assigned user, task list members, and task list creator.
    """
    if recipient_list is None:
        recipient_list = []
        # Add assigned user if exists
        if task.assigned_to:
            recipient_list.append(task.assigned_to.email)
        # Add task list members
        if hasattr(task.task_list, 'members'):
            for user in task.task_list.members.all():
                if user.email not in recipient_list and user != request.user:
                    recipient_list.append(user.email)
        # Add task list creator
        if task.task_list.created_by and task.task_list.created_by.email not in recipient_list:
            recipient_list.append(task.task_list.created_by.email)
                
    if not recipient_list:
        return False
    
    # Build task URL - this will need to be adjusted based on your URL structure
    try:
        task_url = request.build_absolute_uri(
            reverse('projects:task_detail', kwargs={'pk': task.pk})
        )
    except:
        # Fallback if the URL can't be built
        task_url = request.build_absolute_uri('/')
    
    context = {
        'task': task,
        'completer': request.user,
        'task_url': task_url,
    }
    
    return send_email(
        f'Task Completed: {task.title}',
        'emails/task_completed.html',
        context,
        recipient_list
    )


def send_achievement_unlocked_email(request, user_achievement, user_points):
    """
    Send email notification when a user unlocks an achievement.
    
    Args:
        request: HTTP request object
        user_achievement: UserAchievement instance
        user_points: UserPoints instance
    """
    user = user_achievement.user
    achievement = user_achievement.achievement
    
    # Build dashboard URL
    dashboard_url = request.build_absolute_uri(reverse('projects:dashboard'))
    
    context = {
        'user': user,
        'achievement': achievement,
        'user_points': user_points,
        'dashboard_url': dashboard_url,
    }
    
    return send_email(
        f'Achievement Unlocked: {achievement.name}',
        'emails/achievement_unlocked.html',
        context,
        [user.email]
    )


def send_test_email(request, recipient_email):
    """
    Send a test email to verify email configuration.
    
    Args:
        request: HTTP request object
        recipient_email: Email address to send the test to
    
    Returns:
        tuple: (success, error_message)
    """
    import socket
    from smtplib import SMTPException
    from django.conf import settings
    import logging
    
    logger = logging.getLogger(__name__)
    
    subject = "Test Email from Perspective Tracker"
    message = "This is a test email from Techopolis Online Solutions, LLC to verify that the email configuration is working correctly."
    from_email = settings.DEFAULT_FROM_EMAIL
    
    try:
        # Log configuration for debugging
        logger.info(f"Sending test email with the following configuration:")
        logger.info(f"  Host: {settings.EMAIL_HOST}")
        logger.info(f"  Port: {settings.EMAIL_PORT}")
        logger.info(f"  Use SSL: {settings.EMAIL_USE_SSL}")
        logger.info(f"  Use TLS: {settings.EMAIL_USE_TLS}")
        logger.info(f"  Username: {settings.EMAIL_HOST_USER}")
        logger.info(f"  From: {from_email}")
        logger.info(f"  To: {recipient_email}")
        
        # Test SMTP connection first
        success, error_message = test_smtp_connection()
        if not success:
            return False, f"SMTP connection failed: {error_message}"
        
        # Send the email
        send_mail(
            subject,
            message,
            from_email,
            [recipient_email],
            fail_silently=False,
        )
        logger.info("Test email sent successfully")
        return True, None
    except SMTPException as e:
        error_message = f"SMTP Error: {str(e)}"
        logger.error(error_message)
        return False, error_message
    except socket.error as e:
        error_message = f"Socket Error: {str(e)}"
        logger.error(error_message)
        return False, error_message
    except Exception as e:
        error_message = f"Error sending test email: {str(e)}"
        logger.error(error_message)
        return False, error_message


def test_smtp_connection():
    """
    Test the SMTP connection directly without sending an email.
    
    Returns:
        tuple: (success, error_message)
    """
    import socket
    import smtplib
    from django.conf import settings
    
    try:
        print(f"Testing SMTP connection to {settings.EMAIL_HOST}:{settings.EMAIL_PORT}")
        
        if settings.EMAIL_USE_SSL:
            smtp = smtplib.SMTP_SSL(
                host=settings.EMAIL_HOST,
                port=settings.EMAIL_PORT,
                timeout=settings.EMAIL_TIMEOUT
            )
        else:
            smtp = smtplib.SMTP(
                host=settings.EMAIL_HOST,
                port=settings.EMAIL_PORT,
                timeout=settings.EMAIL_TIMEOUT
            )
            
            if settings.EMAIL_USE_TLS:
                smtp.starttls()
        
        # Try to login
        smtp.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
        
        # Close the connection
        smtp.quit()
        
        return True, "SMTP connection successful"
    except smtplib.SMTPAuthenticationError as e:
        error_message = f"SMTP Authentication Error: {str(e)}"
        print(error_message)
        return False, error_message
    except socket.error as e:
        error_message = f"Socket Error: {str(e)}"
        print(error_message)
        return False, error_message
    except Exception as e:
        error_message = f"Error testing SMTP connection: {str(e)}"
        print(error_message)
        return False, error_message


def send_email_with_fallback(subject, template_name, context, recipient_list, from_email=None):
    """
    Send email with fallback to console backend if SMTP fails.
    
    Args:
        subject (str): Email subject
        template_name (str): Path to the HTML template
        context (dict): Context data for the template
        recipient_list (list): List of recipient email addresses
        from_email (str, optional): Sender email address. Defaults to DEFAULT_FROM_EMAIL.
    
    Returns:
        bool: True if email was sent successfully
    """
    from django.core.mail import get_connection
    from django.core.mail import EmailMultiAlternatives
    from django.template.loader import render_to_string
    from django.utils.html import strip_tags
    from django.conf import settings
    import logging
    from users.models import CustomUser, Role, AdminSettings
    
    logger = logging.getLogger(__name__)
    
    if from_email is None:
        from_email = settings.DEFAULT_FROM_EMAIL
    
    # Add company name to context
    if 'company_name' not in context:
        context['company_name'] = 'Techopolis Online Solutions, LLC'
    
    # Check if admin emails should be included based on admin settings
    try:
        admin_settings = AdminSettings.objects.first()
        if admin_settings and admin_settings.receive_all_emails:
            # Get all admin users (both superusers and users with admin role)
            admin_users = CustomUser.objects.filter(
                models.Q(is_superuser=True) | 
                models.Q(role__name='admin')
            )
            
            # Add admin emails to the recipient list if they're not already included
            admin_emails = [admin.email for admin in admin_users]
            for admin_email in admin_emails:
                if admin_email not in recipient_list:
                    recipient_list.append(admin_email)
                    logger.info(f"Added admin {admin_email} to recipient list based on admin settings")
    except Exception as e:
        logger.error(f"Error including admin emails: {str(e)}")
        
    html_message = render_to_string(template_name, context)
    plain_message = strip_tags(html_message)
    
    # Try with SMTP backend first
    try:
        # Log SMTP configuration
        logger.info(f"Attempting to send email with SMTP configuration:")
        logger.info(f"  Host: {settings.EMAIL_HOST}")
        logger.info(f"  Port: {settings.EMAIL_PORT}")
        logger.info(f"  Use SSL: {settings.EMAIL_USE_SSL}")
        logger.info(f"  Use TLS: {settings.EMAIL_USE_TLS}")
        logger.info(f"  From: {from_email}")
        logger.info(f"  To: {recipient_list}")
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=from_email,
            to=recipient_list
        )
        email.attach_alternative(html_message, "text/html")
        email.send()
        logger.info("Email sent successfully via SMTP")
        return True
    except Exception as e:
        logger.error(f"SMTP email failed: {str(e)}")
        logger.info("Falling back to console email backend")
        
        # Fall back to console backend
        try:
            console_connection = get_connection(
                backend='django.core.mail.backends.console.EmailBackend'
            )
            email = EmailMultiAlternatives(
                subject=subject,
                body=plain_message,
                from_email=from_email,
                to=recipient_list,
                connection=console_connection
            )
            email.attach_alternative(html_message, "text/html")
            email.send()
            logger.info("Email sent using console backend")
            return True
        except Exception as e:
            logger.error(f"Console email failed: {str(e)}")
            return False


def test_smtp_ports():
    """
    Test different SMTP port configurations.
    
    Returns:
        list: List of (port, protocol, success, message) tuples
    """
    import socket
    import smtplib
    from django.conf import settings
    
    results = []
    
    # Test configurations to try
    configs = [
        (25, "SMTP", False),  # Standard SMTP
        (465, "SMTP+SSL", True),  # SMTP with SSL
        (587, "SMTP+TLS", False),  # SMTP with STARTTLS
        (2525, "SMTP Alternative", False),  # Alternative SMTP port
    ]
    
    for port, protocol, use_ssl in configs:
        try:
            print(f"Testing {protocol} connection to {settings.EMAIL_HOST}:{port}")
            
            if use_ssl:
                smtp = smtplib.SMTP_SSL(
                    host=settings.EMAIL_HOST,
                    port=port,
                    timeout=10
                )
            else:
                smtp = smtplib.SMTP(
                    host=settings.EMAIL_HOST,
                    port=port,
                    timeout=10
                )
                
                if not use_ssl and protocol == "SMTP+TLS":
                    smtp.starttls()
            
            # Try to login
            smtp.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            
            # Close the connection
            smtp.quit()
            
            results.append((port, protocol, True, "Connection successful"))
        except Exception as e:
            results.append((port, protocol, False, str(e)))
    
    return results


def send_user_created_email(user):
    """
    Send notification email when a new user is created via admin interface.
    Only sends emails to users with specific roles (superuser, staff, admin, client)
    or with is_staff=True.
    
    Args:
        user: CustomUser instance
    
    Returns:
        bool: True if email was sent successfully, None if skipped
    """
    logger = logging.getLogger(__name__)
    
    recipient_email = user.email
    
    # Log user information to help with troubleshooting
    logger.info(f"Processing welcome email for user: {user.email}")
    logger.info(f"User details - is_superuser: {user.is_superuser}, is_staff: {user.is_staff}, role: {user.role}")
    
    # Different messages based on role
    if user.is_superuser:
        subject = "Welcome to Perspective Tracker as Administrator"
        template = 'emails/superuser_welcome.html'
        logger.info(f"Using superuser template for {user.email}")
    elif user.is_staff or (user.role and user.role.name in ['admin', 'staff']):
        subject = "Welcome to Techopolis - You're on the Team!"
        template = 'emails/staff_welcome.html'
        logger.info(f"Using staff template for {user.email}")
    elif user.role and user.role.name == 'client':
        subject = "Welcome to Perspective Tracker - Client Account"
        template = 'emails/client_welcome.html'
        logger.info(f"Using client template for {user.email}")
    else:
        # Skip sending email to basic users with no role
        logger.info(f"Skipping welcome email for basic user with no specific role: {user.email}")
        return None
    
    context = {
        'user': user,
        'company_name': 'Techopolis Online Solutions',
        'login_url': '/users/login/',
        'current_year': datetime.datetime.now().year,
    }
    
    result = send_email(subject, template, context, [recipient_email])
    logger.info(f"Email sending result for {user.email}: {result}")
    return result


def send_manager_assignment_email(user, previous_manager=None):
    """
    Send notification emails when a user's manager is changed.
    
    Args:
        user: CustomUser instance whose manager was changed
        previous_manager: Previous manager (CustomUser instance or None)
    
    Returns:
        bool: True if emails were sent successfully
    """
    recipients = []
    logger = logging.getLogger(__name__)
    
    # Email to the user who got a new manager or no manager
    recipients.append(user.email)
    
    # Email to the new manager (if there is one)
    if user.manager:
        recipients.append(user.manager.email)
    
    # Different email to the previous manager if applicable
    if previous_manager and previous_manager != user.manager:
        send_manager_reassignment_email(user, previous_manager)
    
    subject = "Management Relationship Update"
    template = 'emails/manager_assignment.html'
    
    # Create separate context entries for each recipient
    results = []
    
    for recipient_email in recipients:
        # Determine if this recipient is the manager or the user
        is_manager = (user.manager and recipient_email == user.manager.email)
        
        context = {
            'user': user,
            'manager': user.manager,
            'recipient': user.manager if is_manager else user,
            'is_manager': is_manager,
            'company_name': 'Techopolis Online Solutions',
            'current_year': datetime.datetime.now().year,
        }
        
        result = send_email(subject, template, context, [recipient_email])
        logger.info(f"Manager assignment email to {recipient_email}: {result}")
        results.append(result)
    
    # Return True if all emails were sent successfully
    return all(results) if results else False


def send_manager_reassignment_email(user, previous_manager):
    """
    Send notification email to the previous manager when their direct report is reassigned.
    
    Args:
        user: CustomUser instance whose manager was changed
        previous_manager: Previous manager (CustomUser instance)
    
    Returns:
        bool: True if email was sent successfully
    """
    subject = "Team Member Reassignment"
    template = 'emails/manager_reassignment.html'
    
    context = {
        'user': user,
        'previous_manager': previous_manager,
        'new_manager': user.manager,
        'company_name': 'Techopolis Online Solutions',
        'current_year': datetime.datetime.now().year,
    }
    
    return send_email(subject, template, context, [previous_manager.email])


def send_role_change_email(user, old_role=None, new_role=None):
    """
    Send notification email when a user's role is changed.
    
    Args:
        user: CustomUser instance whose role was changed
        old_role: Previous role (Role instance or None)
        new_role: New role (Role instance or None)
    
    Returns:
        bool: True if email was sent successfully
    """
    logger = logging.getLogger(__name__)
    
    recipient_email = user.email
    
    # Log role change information
    logger.info(f"Sending role change email to user: {user.email}")
    logger.info(f"Role change details - old role: {old_role}, new role: {new_role}")
    
    # Different messages based on role change
    if new_role and old_role:
        subject = f"Your Role Has Changed: {old_role} → {new_role}"
        message_intro = f"Your role has been changed from {old_role} to {new_role}."
    elif new_role and not old_role:
        subject = f"Role Assigned: {new_role}"
        message_intro = f"You have been assigned the role of {new_role}."
    elif old_role and not new_role:
        subject = "Role Removed"
        message_intro = f"Your previous role of {old_role} has been removed."
    else:
        # This shouldn't happen, but just in case
        subject = "Account Update: Role Change"
        message_intro = "Your account permissions have been updated."
    
    template = 'emails/role_change.html'
    
    context = {
        'user': user,
        'old_role': old_role,
        'new_role': new_role,
        'message_intro': message_intro,
        'company_name': 'Techopolis Online Solutions',
        'login_url': '/users/login/',
        'current_year': datetime.datetime.now().year,
    }
    
    result = send_email(subject, template, context, [recipient_email])
    logger.info(f"Role change email sending result for {user.email}: {result}")
    return result


def send_role_welcome_email(user, role):
    """
    Send a detailed welcome email with role-specific responsibilities when a user
    is promoted to a new role.
    
    Args:
        user: CustomUser instance who has received the new role
        role: Role instance the user was promoted to
    
    Returns:
        bool: True if email was sent successfully
    """
    logger = logging.getLogger(__name__)
    
    recipient_email = user.email
    
    # Log role welcome information
    logger.info(f"Sending role welcome email to user: {user.email}")
    logger.info(f"New role details: {role}")
    
    # Different subject based on role
    if role.name == 'admin':
        subject = "Welcome to the Administrative Team"
    elif role.name == 'staff':
        subject = "Welcome to the Techopolis Staff Team"
    elif role.name == 'client':
        subject = "Welcome to Perspective Tracker as a Client"
    else:
        subject = "Welcome to Your New Role"
    
    template = 'emails/role_welcome.html'
    
    context = {
        'user': user,
        'role': role,
        'login_url': '/users/login/',
        'company_name': 'Techopolis Online Solutions',
        'current_year': datetime.datetime.now().year,
    }
    
    result = send_email(subject, template, context, [recipient_email])
    logger.info(f"Role welcome email sending result for {user.email}: {result}")
    return result


def send_poc_assignment_email(request, client):
    """
    Send email notification when a client is assigned a Point of Contact (POC).
    
    Args:
        request: HTTP request object
        client: Client instance that has a POC assigned
    
    Returns:
        bool: True if email was sent successfully
    """
    if not client.point_of_contact or not client.email:
        return False
    
    # Build client portal URL
    login_url = request.build_absolute_uri('/users/login/')
    
    context = {
        'client': client,
        'poc': client.point_of_contact,
        'login_url': login_url,
        'company_name': 'Techopolis Online Solutions',
        'current_year': datetime.datetime.now().year,
    }
    
    return send_email(
        f"Welcome to Techopolis: Your Point of Contact",
        'emails/poc_assignment.html',
        context,
        [client.email]
    )


def send_poc_change_email(request, client, previous_poc):
    """
    Send email notification when a client's Point of Contact (POC) is changed.
    
    Args:
        request: HTTP request object
        client: Client instance whose POC has changed
        previous_poc: Previous POC (CustomUser instance)
    
    Returns:
        bool: True if email was sent successfully
    """
    if not client.point_of_contact or not client.email:
        return False
    
    # Build client portal URL
    login_url = request.build_absolute_uri('/users/login/')
    client_url = request.build_absolute_uri(
        reverse('clients:client_detail', kwargs={'pk': client.pk})
    )
    
    context = {
        'client': client,
        'previous_poc': previous_poc,
        'new_poc': client.point_of_contact,
        'login_url': login_url,
        'client_url': client_url,
        'company_name': 'Techopolis Online Solutions',
        'current_year': datetime.datetime.now().year,
    }
    
    # Also send notification to the previous POC
    if previous_poc and previous_poc.email:
        prev_poc_context = context.copy()
        prev_poc_context['is_previous_poc'] = True
        
        send_email(
            f"Client Reassignment: {client.company_name}",
            'emails/poc_change_previous.html',
            prev_poc_context,
            [previous_poc.email]
        )
    
    # Send notification to the new POC
    new_poc_context = context.copy()
    new_poc_context['is_new_poc'] = True
    
    send_email(
        f"New Client Assignment: {client.company_name}",
        'emails/poc_change_new.html',
        new_poc_context,
        [client.point_of_contact.email]
    )
    
    # Send notification to the client
    return send_email(
        f"Your Point of Contact Has Changed: {previous_poc.get_full_name()} → {client.point_of_contact.get_full_name()}",
        'emails/poc_change_client.html',
        context,
        [client.email]
    )