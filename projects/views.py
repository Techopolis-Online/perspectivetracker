from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.db.models import Count, Q
from .models import ProjectType, Project, Standard, Violation, ProjectViolation, ProjectStandard, Page, Milestone, Issue
from users.views import admin_required, staff_required
from .forms import ProjectForm, StandardForm, ViolationForm, ProjectViolationForm, ProjectTypeForm, ProjectStandardForm, PageForm, MilestoneForm, IssueForm, CommentForm

@login_required
def project_list(request):
    """Display list of projects"""
    # Filter projects based on user role
    if request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role and request.user.role.name in ['admin', 'staff']):
        projects = Project.objects.all()
    else:
        projects = Project.objects.filter(assigned_to=request.user)
    
    # Filter by project type if specified
    project_type_slug = request.GET.get('type')
    if project_type_slug:
        projects = projects.filter(project_type__slug=project_type_slug)
    
    # Get all project types for filter dropdown
    project_types = ProjectType.objects.all()
    
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
                pass
        
        if form.is_valid():
            project = form.save(commit=False)
            project.created_by = request.user
            project.save()
            form.save_m2m()  # Save many-to-many relationships
            messages.success(request, f"Project '{project.name}' created successfully.")
            return redirect('projects:project_detail', pk=project.pk)
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
            form.save()
            messages.success(request, f"Project '{project.name}' updated successfully.")
            return redirect('projects:project_detail', pk=project.pk)
    else:
        form = ProjectForm(instance=project)
    
    context = {
        'form': form,
        'project': project,
        'title': 'Update Project',
        'project_types': ProjectType.objects.all(),
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
        form = MilestoneForm(request.POST, instance=milestone, project=project)
        if form.is_valid():
            form.save()
            messages.success(request, f"Milestone '{milestone.name}' updated successfully.")
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
    
    context = {
        'milestone': milestone,
        'project': project,
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
        form = IssueForm(request.POST, instance=issue, project=project)
        if form.is_valid():
            form.save()
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
    
    # Check if user has access to this project
    if not (request.user.is_superuser or 
            (hasattr(request.user, 'role') and request.user.role and request.user.role.name in ['admin', 'staff']) or
            request.user in project.assigned_to.all()):
        return HttpResponseForbidden("You don't have permission to access this project.")
    
    # Get comments for this issue
    comments = issue.comments.all()
    
    # Handle comment form submission
    if request.method == 'POST':
        comment_form = CommentForm(request.POST, user=request.user)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.issue = issue
            comment.author = request.user
            comment.save()
            messages.success(request, 'Comment added successfully.')
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
