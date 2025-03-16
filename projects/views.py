from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.db.models import Count, Q
from .models import ProjectType, Project, Standard, Violation, ProjectViolation, ProjectStandard
from users.views import admin_required, staff_required
from .forms import ProjectForm, StandardForm, ViolationForm, ProjectViolationForm, ProjectTypeForm, ProjectStandardForm

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
    
    # Group violations by standard if this is an accessibility project
    grouped_violations = None
    if project.project_type.supports_standards:
        grouped_violations = {}
        for violation in violations:
            standard = violation.violation.standard
            if standard not in grouped_violations:
                grouped_violations[standard] = []
            grouped_violations[standard].append(violation)
    
    context = {
        'project': project,
        'project_standards': project_standards,
        'violations': violations,
        'grouped_violations': grouped_violations,
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
    """Return milestone choices for a project type as JSON"""
    try:
        project_type = ProjectType.objects.get(pk=pk)
        
        # Return the milestone choices or default choices if none defined
        if project_type.milestone_choices:
            # Make sure each milestone choice is a separate option
            choices = []
            for key, display in project_type.milestone_choices:
                # Skip empty values
                if not key or not display:
                    continue
                choices.append([key.strip(), display.strip()])
            return JsonResponse(choices, safe=False)
        else:
            # Return default choices
            default_choices = [
                ['design', 'Design Phase'],
                ['development', 'Development Phase'],
                ['testing', 'Testing Phase'],
                ['deployment', 'Deployment Phase']
            ]
            return JsonResponse(default_choices, safe=False)
    except ProjectType.DoesNotExist:
        return JsonResponse({'error': 'Project type not found'}, status=404)
