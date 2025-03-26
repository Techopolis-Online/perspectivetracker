from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.db.models import Count, Q
from .models import ProjectType, Project, Standard, Violation, ProjectViolation, ProjectStandard, Page, Milestone, Issue, Comment, IssueModification
from users.views import admin_required, staff_required
from .forms import ProjectForm, StandardForm, ViolationForm, ProjectViolationForm, ProjectTypeForm, ProjectStandardForm, PageForm, MilestoneForm, IssueForm, CommentForm, IssueStatusForm
from perspectivetracker.utils import (
    send_project_created_email, 
    send_project_updated_email,
    send_issue_created_email,
    send_issue_updated_email,
    send_comment_notification_email,
    send_milestone_created_email,
    send_milestone_updated_email,
    send_milestone_completed_email,
    send_assignment_notification_email
)
import logging

logger = logging.getLogger(__name__)

@login_required
def project_list(request):
    """Display list of projects"""
    logger.info(f"User {request.user.email} accessing project list")
    logger.info(f"User role: {request.user.role.name if hasattr(request.user, 'role') and request.user.role else 'None'}")
    logger.info(f"User is superuser: {request.user.is_superuser}")
    
    # Get all projects first for debugging
    all_projects = Project.objects.all()
    logger.info(f"Total projects in database: {all_projects.count()}")
    
    # Filter projects based on user role
    if request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role and request.user.role.name in ['admin', 'staff']):
        projects = Project.objects.all()
        logger.info(f"User has admin/staff role, showing all projects")
    else:
        projects = Project.objects.filter(assigned_to=request.user)
        logger.info(f"User has regular role, showing only assigned projects")
        logger.info(f"User's assigned projects: {[p.name for p in projects]}")
    
    # Filter by project type if specified
    project_type_slug = request.GET.get('type')
    if project_type_slug:
        projects = projects.filter(project_type__slug=project_type_slug)
        logger.info(f"Filtered projects by type: {project_type_slug}")
    
    # Get all project types for filter dropdown
    project_types = ProjectType.objects.all()
    
    # Log the number of projects visible to the user
    logger.info(f"Number of projects visible to user: {projects.count()}")
    
    context = {
        'projects': projects,
        'project_types': project_types,
        'current_type': project_type_slug,
    }
    return render(request, 'projects/project_list.html', context)

@login_required
def project_detail(request, pk):
    """Display project details"""
    project = get_object_or_404(Project, pk=pk)
    
    # Check if user has access to this project
    if not (request.user.is_superuser or 
            (hasattr(request.user, 'role') and request.user.role and request.user.role.name in ['admin', 'staff']) or
            request.user in project.assigned_to.all()):
        return HttpResponseForbidden("You don't have permission to access this project.")
    
    # Get project standards
    project_standards = ProjectStandard.objects.filter(project=project).select_related('standard')
    
    # Get project violations
    violations = ProjectViolation.objects.filter(project=project)
    
    # Get project pages
    pages = Page.objects.filter(project=project).order_by('name')
    
    # Get project milestones
    milestones = Milestone.objects.filter(project=project).order_by('due_date', 'name')
    
    # Get accessibility issues
    issues = Issue.objects.filter(project=project).order_by('-created_at')
    
    # Get team members
    team_members = project.assigned_to.all()
    
    # Separate staff and client team members
    staff_members = [member for member in team_members if member.is_superuser or 
                    (hasattr(member, 'role') and member.role and member.role.name in ['admin', 'staff'])]
    staff_members.sort(key=lambda x: x.first_name)
    
    client_members = [member for member in team_members if hasattr(member, 'role') and 
                     member.role and member.role.name == 'client']
    client_members.sort(key=lambda x: x.first_name)
    
    # Group violations by standard
    grouped_violations = {}
    for violation in violations:
        standard = violation.violation.standard
        if standard not in grouped_violations:
            grouped_violations[standard] = []
        grouped_violations[standard].append(violation)
    
    context = {
        'project': project,
        'project_standards': project_standards,
        'grouped_violations': grouped_violations,
        'pages': pages,
        'milestones': milestones,
        'issues': issues,
        'team_members': team_members,
        'staff_members': staff_members,
        'client_members': client_members,
    }
    return render(request, 'projects/project_detail.html', context)

@login_required
@staff_required
def project_create(request):
    """Create a new project"""
    logger.info(f"User {request.user.email} attempting to create a project")
    logger.info(f"User role: {request.user.role.name if hasattr(request.user, 'role') and request.user.role else 'None'}")
    
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        
        # Get project type and set status choices
        project_type_id = request.POST.get('project_type')
        if project_type_id:
            try:
                project_type = ProjectType.objects.get(id=project_type_id)
                temp_project = Project(project_type=project_type)
                form.fields['status'].choices = temp_project.get_status_choices()
            except ProjectType.DoesNotExist:
                logger.error(f"Project type with ID {project_type_id} not found")
                pass
        
        if form.is_valid():
            project = form.save(commit=False)
            project.created_by = request.user
            project.save()
            form.save_m2m()  # Save many-to-many relationships
            
            # Log project creation and assignments
            logger.info(f"Created new project '{project.name}' by user {request.user.email}")
            logger.info(f"Project assigned to users: {[user.email for user in project.assigned_to.all()]}")
            logger.info(f"Project created_by: {project.created_by.email}")
            
            # Send email notification
            send_project_created_email(request, project)
            
            messages.success(request, f"Project '{project.name}' created successfully.")
            return redirect('projects:project_detail', pk=project.pk)
        else:
            logger.error(f"Project creation form validation failed: {form.errors}")
    else:
        form = ProjectForm()
    
    context = {
        'form': form,
        'title': 'Create Project',
        'project_types': ProjectType.objects.all(),
    }
    return render(request, 'projects/project_form.html', context)

@login_required
@staff_required
def project_update(request, pk):
    """Update an existing project"""
    project = get_object_or_404(Project, pk=pk)
    
    if request.method == 'POST':
        # Store original values for comparison
        original_data = {
            'name': project.name,
            'client': project.client,
            'project_type': project.project_type,
            'status': project.status,
            'notes': project.notes,
            'assigned_to': list(project.assigned_to.all()),
        }
        
        form = ProjectForm(request.POST, instance=project)
        
        # Get project type and set status choices
        project_type_id = request.POST.get('project_type')
        if project_type_id:
            try:
                project_type = ProjectType.objects.get(id=project_type_id)
                temp_project = Project(project_type=project_type)
                form.fields['status'].choices = temp_project.get_status_choices()
            except ProjectType.DoesNotExist:
                pass
        
        if form.is_valid():
            updated_project = form.save()
            
            # Determine what fields were updated
            updated_fields = []
            if original_data['name'] != updated_project.name:
                updated_fields.append(f"Name changed from '{original_data['name']}' to '{updated_project.name}'")
            if original_data['client'] != updated_project.client:
                updated_fields.append(f"Client changed from '{original_data['client']}' to '{updated_project.client}'")
            if original_data['project_type'] != updated_project.project_type:
                updated_fields.append(f"Project type changed from '{original_data['project_type']}' to '{updated_project.project_type}'")
            if original_data['status'] != updated_project.status:
                updated_fields.append(f"Status changed from '{project.get_status_display()}' to '{updated_project.get_status_display()}'")
            if original_data['notes'] != updated_project.notes:
                updated_fields.append("Notes were updated")
                
            # Check for changes in assigned users
            current_assigned = set(updated_project.assigned_to.all())
            original_assigned = set(original_data['assigned_to'])
            
            if current_assigned != original_assigned:
                added_users = current_assigned - original_assigned
                removed_users = original_assigned - current_assigned
                
                if added_users:
                    user_names = ", ".join([user.get_full_name() or user.email for user in added_users])
                    updated_fields.append(f"Added users: {user_names}")
                    
                    # Send assignment notifications to newly added users
                    for user in added_users:
                        send_assignment_notification_email(request, updated_project, [user.email])
                        
                if removed_users:
                    user_names = ", ".join([user.get_full_name() or user.email for user in removed_users])
                    updated_fields.append(f"Removed users: {user_names}")
            
            # Send email notification if there were changes
            if updated_fields:
                send_project_updated_email(request, updated_project, updated_fields)
            
            messages.success(request, f"Project '{updated_project.name}' updated successfully.")
            return redirect('projects:project_detail', pk=updated_project.pk)
    else:
        form = ProjectForm(instance=project)
    
    context = {
        'form': form,
        'project': project,
        'title': 'Update Project',
    }
    return render(request, 'projects/project_form.html', context)

@login_required
@admin_required
def project_delete(request, pk):
    """Delete a project"""
    project = get_object_or_404(Project, pk=pk)
    
    if request.method == 'POST':
        project_name = project.name
        project.delete()
        messages.success(request, f"Project '{project_name}' deleted successfully.")
        return redirect('projects:project_list')
    
    context = {
        'project': project,
    }
    return render(request, 'projects/project_confirm_delete.html', context)

@login_required
@admin_required
def standard_list(request):
    """Display list of standards"""
    standards = Standard.objects.all()
    
    context = {
        'standards': standards,
    }
    return render(request, 'projects/standard_list.html', context)

@login_required
@admin_required
def standard_detail(request, pk):
    """Display standard details"""
    standard = get_object_or_404(Standard, pk=pk)
    violations = Violation.objects.filter(standard=standard)
    
    context = {
        'standard': standard,
        'violations': violations,
    }
    return render(request, 'projects/standard_detail.html', context)

@login_required
@admin_required
def standard_create(request):
    """Create a new standard"""
    if request.method == 'POST':
        form = StandardForm(request.POST)
        if form.is_valid():
            standard = form.save(commit=False)
            standard.created_by = request.user
            standard.save()
            messages.success(request, f"Standard '{standard}' created successfully.")
            return redirect('projects:standard_detail', pk=standard.pk)
    else:
        form = StandardForm()
    
    context = {
        'form': form,
        'title': 'Create Standard',
    }
    return render(request, 'projects/standard_form.html', context)

@login_required
@admin_required
def standard_update(request, pk):
    """Update an existing standard"""
    standard = get_object_or_404(Standard, pk=pk)
    
    if request.method == 'POST':
        form = StandardForm(request.POST, instance=standard)
        if form.is_valid():
            form.save()
            messages.success(request, f"Standard '{standard}' updated successfully.")
            return redirect('projects:standard_detail', pk=standard.pk)
    else:
        form = StandardForm(instance=standard)
    
    context = {
        'form': form,
        'standard': standard,
        'title': 'Update Standard',
    }
    return render(request, 'projects/standard_form.html', context)

@login_required
@admin_required
def standard_delete(request, pk):
    """Delete a standard"""
    standard = get_object_or_404(Standard, pk=pk)
    
    if request.method == 'POST':
        standard_name = str(standard)
        standard.delete()
        messages.success(request, f"Standard '{standard_name}' deleted successfully.")
        return redirect('projects:standard_list')
    
    context = {
        'standard': standard,
    }
    return render(request, 'projects/standard_confirm_delete.html', context)

@login_required
@admin_required
def violation_create(request, standard_id):
    """Create a new violation for a standard"""
    standard = get_object_or_404(Standard, pk=standard_id)
    
    if request.method == 'POST':
        form = ViolationForm(request.POST)
        if form.is_valid():
            violation = form.save(commit=False)
            violation.standard = standard
            violation.created_by = request.user
            violation.save()
            messages.success(request, f"Violation '{violation.name}' created successfully.")
            return redirect('projects:standard_detail', pk=standard.pk)
    else:
        form = ViolationForm(initial={'standard': standard})
    
    context = {
        'form': form,
        'standard': standard,
        'title': 'Create Violation',
    }
    return render(request, 'projects/violation_form.html', context)

@login_required
@admin_required
def violation_update(request, pk):
    """Update an existing violation"""
    violation = get_object_or_404(Violation, pk=pk)
    
    if request.method == 'POST':
        form = ViolationForm(request.POST, instance=violation)
        if form.is_valid():
            form.save()
            messages.success(request, f"Violation '{violation.name}' updated successfully.")
            return redirect('projects:standard_detail', pk=violation.standard.pk)
    else:
        form = ViolationForm(instance=violation)
    
    context = {
        'form': form,
        'violation': violation,
        'standard': violation.standard,
        'title': 'Update Violation',
    }
    return render(request, 'projects/violation_form.html', context)

@login_required
@admin_required
def violation_delete(request, pk):
    """Delete a violation"""
    violation = get_object_or_404(Violation, pk=pk)
    standard = violation.standard
    
    if request.method == 'POST':
        violation_name = violation.name
        violation.delete()
        messages.success(request, f"Violation '{violation_name}' deleted successfully.")
        return redirect('projects:standard_detail', pk=standard.pk)
    
    context = {
        'violation': violation,
        'standard': standard,
    }
    return render(request, 'projects/violation_confirm_delete.html', context)

@login_required
def project_violation_create(request, project_id):
    """Create a new project violation"""
    project = get_object_or_404(Project, pk=project_id)
    
    # Check if user has access to this project
    if not (request.user.is_superuser or 
            (hasattr(request.user, 'role') and request.user.role and request.user.role.name in ['admin', 'staff']) or
            request.user in project.assigned_to.all()):
        return HttpResponseForbidden("You don't have permission to access this project.")
    
    # Check if project has standards
    if project.project_type.supports_standards:
        project_standards = ProjectStandard.objects.filter(project=project).exists()
        if not project_standards:
            messages.error(request, "You must add standards to the project before creating issues.")
            return redirect('projects:project_detail', pk=project.pk)
    
    if request.method == 'POST':
        form = ProjectViolationForm(request.POST, request.FILES, project=project)
        if form.is_valid():
            project_violation = form.save(commit=False)
            project_violation.project = project
            project_violation.created_by = request.user
            project_violation.save()
            messages.success(request, "Issue created successfully.")
            return redirect('projects:project_detail', pk=project.pk)
    else:
        form = ProjectViolationForm(project=project)
    
    context = {
        'form': form,
        'project': project,
        'title': 'Create Issue',
    }
    return render(request, 'projects/project_violation_form.html', context)

@login_required
def project_violation_update(request, pk):
    """Update an existing project violation"""
    project_violation = get_object_or_404(ProjectViolation, pk=pk)
    project = project_violation.project
    
    # Check if user has access to this project
    if not (request.user.is_superuser or 
            (hasattr(request.user, 'role') and request.user.role and request.user.role.name in ['admin', 'staff']) or
            request.user in project.assigned_to.all() or
            request.user == project_violation.assigned_to):
        return HttpResponseForbidden("You don't have permission to update this issue.")
    
    if request.method == 'POST':
        form = ProjectViolationForm(request.POST, request.FILES, instance=project_violation, project=project)
        if form.is_valid():
            form.save()
            messages.success(request, "Issue updated successfully.")
            return redirect('projects:project_detail', pk=project.pk)
    else:
        form = ProjectViolationForm(instance=project_violation, project=project)
    
    context = {
        'form': form,
        'project_violation': project_violation,
        'project': project,
        'title': 'Update Issue',
    }
    return render(request, 'projects/project_violation_form.html', context)

@login_required
def project_violation_delete(request, pk):
    """Delete a project violation"""
    project_violation = get_object_or_404(ProjectViolation, pk=pk)
    project = project_violation.project
    
    # Check if user has access to this project
    if not (request.user.is_superuser or 
            (hasattr(request.user, 'role') and request.user.role and request.user.role.name in ['admin', 'staff'])):
        return HttpResponseForbidden("You don't have permission to delete this issue.")
    
    if request.method == 'POST':
        project_violation.delete()
        messages.success(request, "Issue deleted successfully.")
        return redirect('projects:project_detail', pk=project.pk)
    
    context = {
        'project_violation': project_violation,
        'project': project,
    }
    return render(request, 'projects/project_violation_confirm_delete.html', context)

@login_required
def project_standard_create(request, project_id):
    """Add a standard to a project"""
    project = get_object_or_404(Project, pk=project_id)
    
    # Check if user has access to this project
    if not (request.user.is_superuser or 
            (hasattr(request.user, 'role') and request.user.role and request.user.role.name in ['admin', 'staff']) or
            request.user in project.assigned_to.all()):
        return HttpResponseForbidden("You don't have permission to access this project.")
    
    # Check if project already has a standard
    if ProjectStandard.objects.filter(project=project).exists():
        messages.error(request, "This project already has a standard. Please remove it first before adding a new one.")
        return redirect('projects:project_detail', pk=project.pk)
    
    if request.method == 'POST':
        form = ProjectStandardForm(request.POST, project=project)
        if form.is_valid():
            project_standard = form.save(commit=False)
            project_standard.project = project
            project_standard.created_by = request.user
            project_standard.save()
            messages.success(request, "Standard added to project successfully.")
            return redirect('projects:project_detail', pk=project.pk)
    else:
        form = ProjectStandardForm(project=project)
    
    context = {
        'form': form,
        'project': project,
        'title': 'Add Standard to Project',
    }
    return render(request, 'projects/project_standard_form.html', context)

@login_required
def project_standard_delete(request, pk):
    """Remove a standard from a project"""
    project_standard = get_object_or_404(ProjectStandard, pk=pk)
    project = project_standard.project
    
    # Check if user has access to this project
    if not (request.user.is_superuser or 
            (hasattr(request.user, 'role') and request.user.role and request.user.role.name in ['admin', 'staff']) or
            request.user in project.assigned_to.all()):
        return HttpResponseForbidden("You don't have permission to remove this standard.")
    
    if request.method == 'POST':
        standard_name = str(project_standard.standard)
        project_standard.delete()
        messages.success(request, f"Standard '{standard_name}' removed from project successfully.")
        return redirect('projects:project_detail', pk=project.pk)
    
    context = {
        'project_standard': project_standard,
        'project': project,
    }
    return render(request, 'projects/project_standard_confirm_delete.html', context)

@login_required
@admin_required
def project_type_list(request):
    """Display list of project types"""
    project_types = ProjectType.objects.all()
    
    context = {
        'project_types': project_types,
        'title': 'Project Types',
    }
    return render(request, 'projects/project_type_list.html', context)

@login_required
@admin_required
def project_type_create(request):
    """Create a new project type"""
    if request.method == 'POST':
        form = ProjectTypeForm(request.POST)
        if form.is_valid():
            project_type = form.save()
            messages.success(request, f"Project type '{project_type.name}' created successfully.")
            return redirect('projects:project_type_list')
    else:
        form = ProjectTypeForm()
    
    context = {
        'form': form,
        'title': 'Create Project Type',
    }
    return render(request, 'projects/project_type_form.html', context)

@login_required
@admin_required
def project_type_update(request, pk):
    """Update an existing project type"""
    project_type = get_object_or_404(ProjectType, pk=pk)
    
    if request.method == 'POST':
        form = ProjectTypeForm(request.POST, instance=project_type)
        if form.is_valid():
            form.save()
            messages.success(request, f"Project type '{project_type.name}' updated successfully.")
            return redirect('projects:project_type_list')
    else:
        form = ProjectTypeForm(instance=project_type)
    
    context = {
        'form': form,
        'project_type': project_type,
        'title': 'Update Project Type',
    }
    return render(request, 'projects/project_type_form.html', context)

@login_required
@admin_required
def project_type_delete(request, pk):
    """Delete a project type"""
    project_type = get_object_or_404(ProjectType, pk=pk)
    
    # Check if there are any projects using this project type
    if Project.objects.filter(project_type=project_type).exists():
        messages.error(request, f"Cannot delete project type '{project_type.name}' because it is being used by one or more projects.")
        return redirect('projects:project_type_list')
    
    if request.method == 'POST':
        project_type_name = project_type.name
        project_type.delete()
        messages.success(request, f"Project type '{project_type_name}' deleted successfully.")
        return redirect('projects:project_type_list')
    
    context = {
        'project_type': project_type,
    }
    return render(request, 'projects/project_type_confirm_delete.html', context)

@login_required
def project_type_status_choices(request, pk):
    """Return status choices for a project type as JSON"""
    try:
        project_type = ProjectType.objects.get(pk=pk)
        
        # Return the status choices or default choices if none defined
        if project_type.status_choices:
            # Make sure each status choice is a separate option and no duplicates
            choices = []
            seen_keys = set()
            
            for key, display in project_type.status_choices:
                # Skip empty values or duplicates
                key = key.strip() if key else ""
                display = display.strip() if display else ""
                
                if not key or not display or key in seen_keys:
                    continue
                
                choices.append([key, display])
                seen_keys.add(key)
                
            print(f"Returning status choices for project type {project_type.name}: {choices}")
            return JsonResponse(choices, safe=False)
        else:
            # Return default choices
            default_choices = [
                ['not_started', 'Not Started'],
                ['in_progress', 'In Progress'],
                ['completed', 'Completed']
            ]
            print(f"Returning default status choices for project type {project_type.name}: {default_choices}")
            return JsonResponse(default_choices, safe=False)
    except ProjectType.DoesNotExist:
        return JsonResponse({'error': 'Project type not found'}, status=404)

@login_required
def project_type_milestone_choices(request, pk):
    """API endpoint to get milestone choices for a project type"""
    project_type = get_object_or_404(ProjectType, pk=pk)
    
    # Get milestone choices from project type
    milestone_choices = []
    if project_type.milestone_choices:
        milestone_choices = project_type.milestone_choices
    
    # Format for select options
    options = []
    for key, display in milestone_choices:
        if key and display:  # Skip empty values
            options.append({
                'value': key.strip(),
                'text': display.strip()
            })
    
    # If no custom choices, return default choices
    if not options:
        for key, display in Milestone.STATUS_CHOICES:
            options.append({
                'value': key,
                'text': display
            })
    
    return JsonResponse({'options': options})

# Page views
@login_required
def page_create(request, project_id):
    """Create a new page for a project"""
    project = get_object_or_404(Project, pk=project_id)
    
    # Check if user has permission to add pages to this project
    if not (request.user.is_superuser or 
            (hasattr(request.user, 'role') and request.user.role and request.user.role.name in ['admin', 'staff']) or
            request.user in project.assigned_to.all()):
        return HttpResponseForbidden("You don't have permission to add pages to this project.")
    
    if request.method == 'POST':
        form = PageForm(request.POST, project=project)
        if form.is_valid():
            page = form.save(commit=False)
            page.project = project
            page.created_by = request.user
            page.save()
            messages.success(request, f"Page '{page.name}' created successfully.")
            return redirect('projects:project_detail', pk=project.id)
    else:
        form = PageForm(project=project)
    
    context = {
        'form': form,
        'project': project,
        'title': 'Add Page',
    }
    return render(request, 'projects/page_form.html', context)

@login_required
def page_update(request, pk):
    """Update an existing page"""
    page = get_object_or_404(Page, pk=pk)
    project = page.project
    
    # Check if user has permission to edit this page
    if not (request.user.is_superuser or 
            (hasattr(request.user, 'role') and request.user.role and request.user.role.name in ['admin', 'staff']) or
            request.user in project.assigned_to.all()):
        return HttpResponseForbidden("You don't have permission to edit this page.")
    
    if request.method == 'POST':
        form = PageForm(request.POST, instance=page, project=project)
        if form.is_valid():
            form.save()
            messages.success(request, f"Page '{page.name}' updated successfully.")
            return redirect('projects:project_detail', pk=project.id)
    else:
        form = PageForm(instance=page, project=project)
    
    context = {
        'form': form,
        'project': project,
        'page': page,
        'title': 'Edit Page',
    }
    return render(request, 'projects/page_form.html', context)

@login_required
def page_delete(request, pk):
    """Delete a page"""
    page = get_object_or_404(Page, pk=pk)
    project = page.project
    
    # Check if user has permission to delete this page
    if not (request.user.is_superuser or 
            (hasattr(request.user, 'role') and request.user.role and request.user.role.name == 'admin')):
        return HttpResponseForbidden("You don't have permission to delete this page.")
    
    if request.method == 'POST':
        page_name = page.name
        page.delete()
        messages.success(request, f"Page '{page_name}' deleted successfully.")
        return redirect('projects:project_detail', pk=project.id)
    
    context = {
        'page': page,
        'project': project,
    }
    return render(request, 'projects/page_confirm_delete.html', context)

# Milestone views
@login_required
def milestone_create(request, project_id):
    """Create a new milestone for a project"""
    project = get_object_or_404(Project, pk=project_id)
    
    # Check if user has permission to add milestones to this project
    if not (request.user.is_superuser or 
            (hasattr(request.user, 'role') and request.user.role and request.user.role.name in ['admin', 'staff'])):
        return HttpResponseForbidden("You don't have permission to add milestones to this project.")
    
    if request.method == 'POST':
        form = MilestoneForm(request.POST, project=project)
        if form.is_valid():
            milestone = form.save(commit=False)
            milestone.project = project
            milestone.created_by = request.user
            milestone.save()
            
            # Send email notification
            send_milestone_created_email(request, milestone)
            
            messages.success(request, f"Milestone '{milestone.name}' created successfully.")
            return redirect('projects:project_detail', pk=project.id)
    else:
        form = MilestoneForm(project=project)
    
    context = {
        'form': form,
        'project': project,
        'title': 'Add Milestone',
    }
    return render(request, 'projects/milestone_form.html', context)

@login_required
def milestone_update(request, pk):
    """Update an existing milestone"""
    milestone = get_object_or_404(Milestone, pk=pk)
    project = milestone.project
    
    # Check if user has permission to edit this milestone
    if not (request.user.is_superuser or 
            (hasattr(request.user, 'role') and request.user.role and request.user.role.name in ['admin', 'staff'])):
        return HttpResponseForbidden("You don't have permission to edit this milestone.")
    
    if request.method == 'POST':
        # Store original values for comparison
        original_data = {
            'name': milestone.name,
            'description': milestone.description,
            'status': milestone.status,
            'milestone_type': milestone.milestone_type,
            'start_date': milestone.start_date,
            'due_date': milestone.due_date,
            'completed_date': milestone.completed_date,
            'assigned_to': milestone.assigned_to,
        }
        
        form = MilestoneForm(request.POST, instance=milestone, project=project)
        if form.is_valid():
            updated_milestone = form.save()
            
            # Determine what fields were updated
            updated_fields = []
            if original_data['name'] != updated_milestone.name:
                updated_fields.append(f"Name changed from '{original_data['name']}' to '{updated_milestone.name}'")
            if original_data['description'] != updated_milestone.description:
                updated_fields.append("Description was updated")
            if original_data['status'] != updated_milestone.status:
                updated_fields.append(f"Status changed from '{milestone.get_status_display()}' to '{updated_milestone.get_status_display()}'")
            if original_data['milestone_type'] != updated_milestone.milestone_type:
                updated_fields.append(f"Type changed")
            if original_data['start_date'] != updated_milestone.start_date:
                updated_fields.append(f"Start date was updated")
            if original_data['due_date'] != updated_milestone.due_date:
                updated_fields.append(f"Due date was updated")
            if original_data['completed_date'] != updated_milestone.completed_date:
                updated_fields.append(f"Completed date was updated")
            if original_data['assigned_to'] != updated_milestone.assigned_to:
                updated_fields.append(f"Assigned user was changed")
                
                # If a new user was assigned, send them a notification
                if updated_milestone.assigned_to and updated_milestone.assigned_to != original_data['assigned_to']:
                    send_assignment_notification_email(request, updated_milestone, [updated_milestone.assigned_to.email])
            
            # Send email notification if there were changes
            if updated_fields:
                send_milestone_updated_email(request, updated_milestone, updated_fields)
            
            # Check if milestone was marked as completed
            if original_data['status'] != 'completed' and updated_milestone.status == 'completed':
                # Set completed date if not already set
                if not updated_milestone.completed_date:
                    from django.utils import timezone
                    updated_milestone.completed_date = timezone.now().date()
                    updated_milestone.save()
                
                # Send milestone completion email
                send_milestone_completed_email(request, updated_milestone)
            
            messages.success(request, f"Milestone '{updated_milestone.name}' updated successfully.")
            return redirect('projects:project_detail', pk=project.id)
    else:
        form = MilestoneForm(instance=milestone, project=project)
    
    context = {
        'form': form,
        'project': project,
        'milestone': milestone,
        'title': 'Edit Milestone',
    }
    return render(request, 'projects/milestone_form.html', context)

@login_required
def milestone_delete(request, pk):
    """Delete a milestone"""
    milestone = get_object_or_404(Milestone, pk=pk)
    project = milestone.project
    
    # Check if user has permission to delete this milestone
    if not (request.user.is_superuser or 
            (hasattr(request.user, 'role') and request.user.role and request.user.role.name == 'admin')):
        return HttpResponseForbidden("You don't have permission to delete this milestone.")
    
    if request.method == 'POST':
        milestone_name = milestone.name
        milestone.delete()
        messages.success(request, f"Milestone '{milestone_name}' deleted successfully.")
        return redirect('projects:project_detail', pk=project.id)
    
    context = {
        'milestone': milestone,
        'project': project,
    }
    return render(request, 'projects/milestone_confirm_delete.html', context)

@login_required
@admin_required
def milestone_publish(request, pk):
    """Publish a completed milestone"""
    milestone = get_object_or_404(Milestone, pk=pk)
    project = milestone.project
    
    # Check if milestone is completed
    if milestone.status != 'completed':
        messages.error(request, f"Milestone '{milestone.name}' must be completed before it can be published.")
        return redirect('projects:project_detail', pk=project.id)
    
    # Update milestone status to published
    milestone.status = 'published'
    milestone.save()
    
    messages.success(request, f"Milestone '{milestone.name}' has been published successfully.")
    return redirect('projects:project_detail', pk=project.id)

@login_required
def milestone_detail(request, pk):
    """Display milestone details"""
    milestone = get_object_or_404(Milestone, pk=pk)
    project = milestone.project
    
    # Check if user has access to this project
    if not (request.user.is_superuser or 
            (hasattr(request.user, 'role') and request.user.role and request.user.role.name in ['admin', 'staff']) or
            request.user in project.assigned_to.all()):
        return HttpResponseForbidden("You don't have permission to access this milestone.")
    
    # Check if user is a client and milestone is not published
    is_client = (hasattr(request.user, 'role') and 
                request.user.role and 
                request.user.role.name == 'client')
    
    # Get all issues that need testing for this project
    issues_needing_testing = project.issues.filter(current_status='ready_for_testing')
    
    # Get all issues in this milestone
    milestone_issues = milestone.issues.all()
    
    # Get recently modified issues in this milestone (last 7 days)
    from datetime import datetime, timedelta
    recent_date = datetime.now() - timedelta(days=7)
    
    # Get unique issues that have been modified recently
    recent_modifications = IssueModification.objects.filter(
        milestone=milestone,
        created_at__gte=recent_date
    ).order_by('-created_at')
    
    # Get unique issues from modifications
    modified_issue_ids = recent_modifications.values_list('issue_id', flat=True).distinct()
    recently_modified_issues = Issue.objects.filter(id__in=modified_issue_ids)
    
    # Hide issues from clients if milestone is not published
    if is_client and milestone.status != 'published':
        issues_needing_testing = Issue.objects.none()  # Empty queryset for clients
        milestone_issues = Issue.objects.none()  # Empty queryset for clients
        recently_modified_issues = Issue.objects.none()  # Empty queryset for clients
        
    context = {
        'milestone': milestone,
        'project': project,
        'issues_needing_testing': issues_needing_testing,
        'milestone_issues': milestone_issues,
        'recently_modified_issues': recently_modified_issues,
        'recent_modifications': recent_modifications,
        'is_client': is_client,
        'is_published': milestone.status == 'published',
    }
    return render(request, 'projects/milestone_detail.html', context)

@login_required
def issue_create(request, project_id):
    """Create a new issue for a project"""
    project = get_object_or_404(Project, pk=project_id)
    
    # Check if user has access to this project
    if not (request.user.is_superuser or 
            (hasattr(request.user, 'role') and request.user.role and request.user.role.name in ['admin', 'staff']) or
            request.user in project.assigned_to.all()):
        return HttpResponseForbidden("You don't have permission to access this project.")
    
    if request.method == 'POST':
        form = IssueForm(request.POST, project=project)
        if form.is_valid():
            issue = form.save(commit=False)
            issue.project = project
            issue.created_by = request.user
            issue.save()
            
            # Send email notification
            send_issue_created_email(request, issue)
            
            messages.success(request, 'Issue created successfully.')
            return redirect('projects:project_detail', pk=project.id)
    else:
        form = IssueForm(project=project)
    
    context = {
        'form': form,
        'project': project,
    }
    
    return render(request, 'projects/issue_form.html', context)

@login_required
def issue_edit(request, project_id, pk):
    """Edit an existing issue"""
    project = get_object_or_404(Project, pk=project_id)
    issue = get_object_or_404(Issue, pk=pk, project=project)
    
    # Check if user has access to this project
    if not (request.user.is_superuser or 
            (hasattr(request.user, 'role') and request.user.role and request.user.role.name in ['admin', 'staff']) or
            request.user in project.assigned_to.all()):
        return HttpResponseForbidden("You don't have permission to access this project.")
    
    if request.method == 'POST':
        # Store original values for comparison
        original_data = {
            'title': issue.title if hasattr(issue, 'title') else '',
            'issue_description': issue.issue_description,
            'steps_to_reproduce': issue.steps_to_reproduce,
            'current_status': issue.current_status,
            'user_impact': issue.user_impact,
            'user_impact_description': issue.user_impact_description,
            'milestone': issue.milestone,
            'page': issue.page,
            'assigned_to': issue.assigned_to,
            'violation': issue.violation if hasattr(issue, 'violation') else None,
        }
        
        form = IssueForm(request.POST, instance=issue, project=project)
        if form.is_valid():
            updated_issue = form.save()
            
            # Determine what fields were updated
            updated_fields = []
            if hasattr(issue, 'title') and original_data['title'] != updated_issue.title:
                updated_fields.append(f"Title was updated")
            if original_data['issue_description'] != updated_issue.issue_description:
                updated_fields.append("Description was updated")
            if original_data['steps_to_reproduce'] != updated_issue.steps_to_reproduce:
                updated_fields.append("Steps to reproduce were updated")
            if original_data['current_status'] != updated_issue.current_status:
                updated_fields.append(f"Status changed from '{issue.get_current_status_display()}' to '{updated_issue.get_current_status_display()}'")
            if original_data['user_impact'] != updated_issue.user_impact:
                updated_fields.append(f"User impact was updated")
            if original_data['user_impact_description'] != updated_issue.user_impact_description:
                updated_fields.append(f"User impact description was updated")
            if original_data['milestone'] != updated_issue.milestone:
                updated_fields.append(f"Milestone was updated")
            if original_data['page'] != updated_issue.page:
                updated_fields.append(f"Page was updated")
            if original_data['assigned_to'] != updated_issue.assigned_to:
                updated_fields.append(f"Assigned user was changed")
                
                # If a new user was assigned, send them a notification
                if updated_issue.assigned_to and updated_issue.assigned_to != original_data['assigned_to']:
                    send_assignment_notification_email(request, updated_issue, [updated_issue.assigned_to.email])
            
            if hasattr(issue, 'violation') and original_data['violation'] != updated_issue.violation:
                updated_fields.append(f"Violation was updated")
            
            # Send email notification if there were changes
            if updated_fields:
                send_issue_updated_email(request, updated_issue, updated_fields)
            
            messages.success(request, 'Issue updated successfully.')
            return redirect('projects:project_detail', pk=project.id)
    else:
        form = IssueForm(instance=issue, project=project)
    
    context = {
        'form': form,
        'project': project,
        'issue': issue,
    }
    
    return render(request, 'projects/issue_form.html', context)

@login_required
def issue_delete(request, project_id, pk):
    """Delete an issue"""
    project = get_object_or_404(Project, pk=project_id)
    issue = get_object_or_404(Issue, pk=pk, project=project)
    
    # Check if user has access to this project
    if not (request.user.is_superuser or 
            (hasattr(request.user, 'role') and request.user.role and request.user.role.name in ['admin', 'staff'])):
        return HttpResponseForbidden("You don't have permission to delete this issue.")
    
    if request.method == 'POST':
        issue.delete()
        messages.success(request, 'Issue deleted successfully.')
        return redirect('projects:project_detail', pk=project.id)
    
    context = {
        'object': issue,
        'project': project,
    }
    return render(request, 'projects/issue_confirm_delete.html', context)

@login_required
def issue_detail(request, project_id, pk):
    """Display issue details"""
    project = get_object_or_404(Project, pk=project_id)
    issue = get_object_or_404(Issue, pk=pk, project=project)
    
    # Check if user is a client
    is_client = (hasattr(request.user, 'role') and 
                request.user.role and 
                request.user.role.name == 'client')
    
    # Check if milestone is published
    milestone_published = issue.milestone and issue.milestone.status == 'published'
    
    # If user is a client and milestone is not published, deny access
    if is_client and not milestone_published:
        messages.warning(request, "This issue is currently under internal review and not yet available.")
        return redirect('projects:project_detail', pk=project.id)
    
    # Check if user has access to this project
    if not (request.user.is_superuser or 
            (hasattr(request.user, 'role') and request.user.role and request.user.role.name in ['admin', 'staff']) or
            request.user in project.assigned_to.all()):
        return HttpResponseForbidden("You don't have permission to access this project.")
    
    # Get comments for this issue
    comments = issue.comments.all()
    
    # Handle POST requests
    if request.method == 'POST':
        # Check if this is a "Mark as Ready for Testing" action
        if request.POST.get('action') == 'mark_ready_for_testing':
            # Check if user has permission to mark as ready for testing
            if not (request.user.is_superuser or 
                   (request.user.is_authenticated and 
                   hasattr(request.user, 'role') and 
                   request.user.role and 
                   request.user.role.name != 'standard')):
                return HttpResponseForbidden("You don't have permission to mark this issue as ready for testing.")
            
            # Store the old status for the response
            old_status = issue.get_current_status_display()
            old_status_value = issue.current_status
            
            # Update the issue status
            issue.current_status = 'ready_for_testing'
            issue.save()
            
            # Add a system comment about the status change
            comment = Comment.objects.create(
                issue=issue,
                author=request.user,
                text=f"Status changed to Ready for Testing by {request.user.get_full_name()}",
                comment_type='external',
                status_changed=True,
                previous_status=old_status_value,
                new_status='ready_for_testing'
            )
            
            # Record the modification
            IssueModification.objects.create(
                issue=issue,
                milestone=issue.milestone,
                modified_by=request.user,
                modification_type='status_change',
                previous_value=old_status_value,
                new_value='ready_for_testing',
                comment=comment
            )
            
            # If this is an AJAX request, return JSON response
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Issue marked as Ready for Testing.',
                    'old_status': old_status
                })
            
            # Otherwise redirect to the issue detail page
            messages.success(request, 'Issue marked as Ready for Testing.')
            return redirect('projects:issue_detail', project_id=project.id, pk=issue.id)
        
        # Handle comment form submission
        comment_form = CommentForm(request.POST, user=request.user)
        if comment_form.is_valid():
            # Check if status is being updated
            new_status = request.POST.get('current_status')
            status_changed = False
            old_status_value = issue.current_status
            old_status_display = issue.get_current_status_display()
            
            # If status is being changed, update the issue
            if new_status and new_status != issue.current_status:
                issue.current_status = new_status
                issue.save()
                status_changed = True
            
            # Create the comment
            comment = comment_form.save(commit=False)
            comment.issue = issue
            comment.author = request.user
            comment.milestone = issue.milestone
            
            # If status was changed, add that to the comment text and set status change fields
            if status_changed:
                status_message = f"\n\nStatus changed from '{old_status_display}' to '{issue.get_current_status_display()}'."
                if comment.text:
                    comment.text += status_message
                else:
                    comment.text = status_message.strip()
                
                comment.status_changed = True
                comment.previous_status = old_status_value
                comment.new_status = new_status
            
            comment.save()
            
            # Record the modification
            if status_changed:
                IssueModification.objects.create(
                    issue=issue,
                    milestone=issue.milestone,
                    modified_by=request.user,
                    modification_type='status_change',
                    previous_value=old_status_value,
                    new_value=new_status,
                    comment=comment
                )
            
            # Also record comment as a modification
            IssueModification.objects.create(
                issue=issue,
                milestone=issue.milestone,
                modified_by=request.user,
                modification_type='comment',
                new_value=comment.text,
                comment=comment
            )
            
            # Send email notification
            send_comment_notification_email(request, comment)
            
            # Check if this is an AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # Determine if user can see internal comments
                can_see_internal = request.user.is_superuser or (
                    hasattr(request.user, 'role') and 
                    request.user.role and 
                    request.user.role.name in ['admin', 'staff']
                )
                
                # Render the comments list to HTML
                from django.template.loader import render_to_string
                comments_html = render_to_string('projects/includes/comments_list.html', {
                    'comments': issue.comments.all(),
                    'can_see_internal': can_see_internal,
                    'issue': issue,
                    'project': project,
                })
                
                return JsonResponse({
                    'success': True,
                    'message': 'Comment added successfully.',
                    'html': comments_html
                })
            
            messages.success(request, 'Comment added successfully.')
            
            # Redirect back to the referring page
            referer = request.META.get('HTTP_REFERER')
            if referer and 'milestones' in referer:
                return redirect(referer)
                
            return redirect('projects:issue_detail', project_id=project.id, pk=issue.id)
    else:
        comment_form = CommentForm(user=request.user)
    
    # Determine if user can see internal comments
    can_see_internal = request.user.is_superuser or (
        hasattr(request.user, 'role') and 
        request.user.role and 
        request.user.role.name in ['admin', 'staff']
    )
    
    context = {
        'issue': issue,
        'project': project,
        'comments': comments,
        'comment_form': comment_form,
        'can_see_internal': can_see_internal,
    }
    
    return render(request, 'projects/issue_detail.html', context)

@login_required
def issue_update_status(request, project_id, pk):
    """Update just the status of an issue"""
    project = get_object_or_404(Project, pk=project_id)
    issue = get_object_or_404(Issue, pk=pk, project=project)
    
    # Check if user has access to this project
    if not (request.user.is_superuser or 
            (hasattr(request.user, 'role') and request.user.role and request.user.role.name in ['admin', 'staff']) or
            request.user in project.assigned_to.all()):
        return HttpResponseForbidden("You don't have permission to access this project.")
    
    if request.method == 'POST':
        form = IssueStatusForm(request.POST, instance=issue)
        if form.is_valid():
            # Get the old status for the comment
            old_status = issue.get_current_status_display()
            old_status_value = issue.current_status
            
            # Save the form
            updated_issue = form.save()
            
            # Add a system comment about the status change
            comment = Comment.objects.create(
                issue=issue,
                author=request.user,
                text=f"Status changed from '{old_status}' to '{updated_issue.get_current_status_display()}' by {request.user.get_full_name()}",
                comment_type='external',
                status_changed=True,
                previous_status=old_status_value,
                new_status=updated_issue.current_status,
                milestone=issue.milestone
            )
            
            # Record the modification
            IssueModification.objects.create(
                issue=issue,
                milestone=issue.milestone,
                modified_by=request.user,
                modification_type='status_change',
                previous_value=old_status_value,
                new_value=updated_issue.current_status,
                comment=comment
            )
            
            # Send email notification for the comment
            send_comment_notification_email(request, comment)
            
            # Also send issue updated email
            updated_fields = [f"Status changed from '{old_status}' to '{updated_issue.get_current_status_display()}'"]
            send_issue_updated_email(request, updated_issue, updated_fields)
            
            # Check if this is an AJAX request
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f"Status updated to {updated_issue.get_current_status_display()}",
                    'new_status': updated_issue.current_status,
                    'new_status_display': updated_issue.get_current_status_display()
                })
            else:
                messages.success(request, f"Status updated to {updated_issue.get_current_status_display()}")
                return redirect('projects:issue_detail', project_id=project.id, pk=issue.pk)
        else:
            # Handle form errors
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                }, status=400)
            else:
                messages.error(request, "Error updating status. Please try again.")
                return redirect('projects:issue_detail', project_id=project.id, pk=issue.pk)
    
    # If not POST, redirect to issue detail
    return redirect('projects:issue_detail', project_id=project.id, pk=issue.pk)

@login_required
def mark_issue_ready_for_testing(request, project_id, pk):
    """Mark an issue as ready for testing"""
    if request.method != 'POST':
        return HttpResponseForbidden("Only POST requests are allowed.")
    
    project = get_object_or_404(Project, pk=project_id)
    issue = get_object_or_404(Issue, pk=pk, project=project)
    
    # Check if user has access to this project
    if not (request.user.is_superuser or 
            (hasattr(request.user, 'role') and request.user.role and request.user.role.name in ['admin', 'staff', 'client']) or
            request.user in project.assigned_to.all()):
        return HttpResponseForbidden("You don't have permission to access this project.")
    
    # Check if user has permission to mark as ready for testing
    if not (request.user.is_superuser or 
           (request.user.is_authenticated and 
           hasattr(request.user, 'role') and 
           request.user.role and 
           request.user.role.name != 'standard')):
        return HttpResponseForbidden("You don't have permission to mark this issue as ready for testing.")
    
    # Store the old status for the response
    old_status = issue.get_current_status_display()
    old_status_value = issue.current_status
    
    # Update the issue status
    issue.current_status = 'ready_for_testing'
    issue.save()
    
    # Add a system comment about the status change
    comment = Comment.objects.create(
        issue=issue,
        author=request.user,
        text=f"Status changed to Ready for Testing by {request.user.get_full_name()}",
        comment_type='external',
        status_changed=True,
        previous_status=old_status_value,
        new_status='ready_for_testing',
        milestone=issue.milestone
    )
    
    # Record the modification
    IssueModification.objects.create(
        issue=issue,
        milestone=issue.milestone,
        modified_by=request.user,
        modification_type='status_change',
        previous_value=old_status_value,
        new_value='ready_for_testing',
        comment=comment
    )
    
    # Return JSON response
    return JsonResponse({
        'success': True,
        'message': 'Issue marked as Ready for Testing.',
        'old_status': old_status
    })

@login_required
def issues_needing_testing(request, project_id, milestone_id):
    """Display issues that need testing for a specific project and milestone"""
    project = get_object_or_404(Project, pk=project_id)
    milestone = get_object_or_404(Milestone, pk=milestone_id)
    
    # Check if user has access to this project and is staff/admin/superuser
    if not (request.user.is_superuser or 
            (hasattr(request.user, 'role') and request.user.role and request.user.role.name in ['admin', 'staff'])):
        return HttpResponseForbidden("You don't have permission to access this page.")
    
    # Get all issues that need testing for this project
    issues_needing_testing = project.issues.filter(current_status='ready_for_testing')
    
    context = {
        'project': project,
        'milestone': milestone,
        'issues_needing_testing': issues_needing_testing,
    }
    return render(request, 'projects/issues_needing_testing.html', context)

@login_required
def issue_comment(request, project_id, pk):
    """Add a comment to an issue"""
    project = get_object_or_404(Project, pk=project_id)
    issue = get_object_or_404(Issue, pk=pk, project=project)
    
    # Check if user has access to this project
    if not (request.user.is_superuser or 
            (hasattr(request.user, 'role') and request.user.role and request.user.role.name in ['admin', 'staff']) or
            request.user in project.assigned_to.all()):
        return HttpResponseForbidden("You don't have permission to comment on this issue.")
    
    if request.method == 'POST':
        comment_text = request.POST.get('comment', '').strip()
        if comment_text:
            # Create a comment for the issue
            comment = IssueComment.objects.create(
                issue=issue,
                comment=comment_text,
                created_by=request.user
            )
            messages.success(request, "Comment added successfully.")
        else:
            messages.error(request, "Comment cannot be empty.")
    
    # Redirect back to the milestone detail page if that's where the user came from
    referer = request.META.get('HTTP_REFERER', '')
    if 'milestones' in referer:
        milestone_id = issue.milestone.id
        return redirect('projects:milestone_detail', pk=milestone_id)
    
    # Otherwise redirect to the issue detail page
    return redirect('projects:issue_detail', project_id=project_id, pk=pk)
