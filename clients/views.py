from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.urls import reverse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from .models import Client, ClientNote, ClientCoworker
from .forms import ClientForm, ClientNoteForm, ClientCoworkerForm
from users.views import admin_required, staff_required
from users.models import CustomUser, Role
from django.db.models import Q, Count, Avg
import json
import uuid
from django.utils import timezone
from projects.models import Project
import logging
from django.db.models.functions import ExtractMonth

logger = logging.getLogger(__name__)

@login_required
def client_list(request):
    """View all clients"""
    # Admins and staff can see all clients
    if request.user.is_superuser or (request.user.role and request.user.role.name in ['admin', 'staff']):
        clients = Client.objects.all()
    # Clients can only see themselves
    elif request.user.role and request.user.role.name == 'client':
        # This assumes there's a link between user and client, which isn't in the model yet
        # You might need to adjust this based on your actual implementation
        return HttpResponseForbidden("Clients cannot access the client list.")
    # Regular users can't see clients
    else:
        # Check if user is a coworker for any clients
        coworker_clients = Client.objects.filter(
            coworkers__user=request.user,
            coworkers__status='active'
        )
        
        if coworker_clients.exists():
            clients = coworker_clients
        else:
            return HttpResponseForbidden("You don't have permission to view clients.")
    
    # Get staff users for the add/edit client forms
    staff_users = CustomUser.objects.filter(
        Q(role__name=Role.ADMIN) | Q(role__name=Role.STAFF) | Q(is_superuser=True)
    )
    
    return render(request, 'clients/client_list.html', {
        'clients': clients,
        'staff_users': staff_users
    })

@login_required
@staff_required
def client_create(request):
    """Create a new client"""
    # Get staff users for the form
    staff_users = CustomUser.objects.filter(
        Q(role__name=Role.ADMIN) | Q(role__name=Role.STAFF) | Q(is_superuser=True)
    )
    
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            client = form.save()
            messages.success(request, f"Client '{client.company_name}' created successfully!")
            
            # If it's an AJAX request, return a JSON response
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            
            # Otherwise, redirect to the client list
            return redirect('client_list')
        else:
            # If it's an AJAX request, return form errors
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    else:
        form = ClientForm()
    
    context = {
        'form': form,
        'title': 'Add New Client',
        'staff_users': staff_users
    }
    
    return render(request, 'clients/client_form.html', context)

@login_required
def client_detail(request, pk):
    """View a client's details"""
    client = get_object_or_404(Client, pk=pk)
    
    # Check permissions
    has_access = False
    is_admin = False
    
    if request.user.is_superuser or (request.user.role and request.user.role.name in ['admin', 'staff']):
        has_access = True
        is_admin = True
    elif request.user == client.point_of_contact:
        has_access = True
        is_admin = True
    else:
        # Check if user is a coworker
        try:
            coworker = ClientCoworker.objects.get(client=client, user=request.user, status='active')
            has_access = True
            if coworker.role == 'admin':
                is_admin = True
        except ClientCoworker.DoesNotExist:
            pass
    
    if not has_access:
        return HttpResponseForbidden("You don't have permission to view this client.")
    
    notes = client.notes.all()
    coworkers = client.coworkers.all()
    
    # Handle new note form
    if request.method == 'POST' and 'note_form' in request.POST:
        note_form = ClientNoteForm(request.POST)
        coworker_form = ClientCoworkerForm(client=client)
        
        if note_form.is_valid():
            note = note_form.save(commit=False)
            note.client = client
            note.author = request.user
            note.save()
            messages.success(request, "Note added successfully!")
            return redirect('client_detail', pk=client.pk)
    # Handle new coworker form
    elif request.method == 'POST' and 'coworker_form' in request.POST:
        coworker_form = ClientCoworkerForm(request.POST, client=client)
        note_form = ClientNoteForm()
        
        if coworker_form.is_valid():
            coworker = coworker_form.save()
            
            # Send invitation email
            send_coworker_invitation(request, coworker)
            
            messages.success(request, f"Invitation sent to {coworker.email} successfully!")
            return redirect('client_detail', pk=client.pk)
        else:
            # Add a message about contacting the point of contact
            if 'email' in coworker_form.errors:
                poc_name = client.point_of_contact.get_full_name() if client.point_of_contact else "your administrator"
                messages.error(request, f"For assistance with adding team members, please contact {poc_name}.")
    else:
        note_form = ClientNoteForm()
        coworker_form = ClientCoworkerForm(client=client)
    
    return render(request, 'clients/client_detail.html', {
        'client': client,
        'notes': notes,
        'coworkers': coworkers,
        'note_form': note_form,
        'coworker_form': coworker_form,
        'is_admin': is_admin
    })

@login_required
@staff_required
def client_update(request, pk):
    """Update a client's information"""
    client = get_object_or_404(Client, pk=pk)
    
    # Get staff users for the form
    staff_users = CustomUser.objects.filter(
        Q(role__name=Role.ADMIN) | Q(role__name=Role.STAFF) | Q(is_superuser=True)
    )
    
    if request.method == 'POST':
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, f"Client '{client.company_name}' updated successfully!")
            
            # If it's an AJAX request, return a JSON response
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            
            # Otherwise, redirect to the client detail page
            return redirect('client_detail', pk=client.pk)
        else:
            # If it's an AJAX request, return form errors
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    else:
        form = ClientForm(instance=client)
    
    context = {
        'form': form,
        'client': client,
        'title': 'Edit Client',
        'staff_users': staff_users
    }
    
    return render(request, 'clients/client_form.html', context)

@login_required
@admin_required
def client_delete(request, pk):
    """Delete a client"""
    client = get_object_or_404(Client, pk=pk)
    
    if request.method == 'POST':
        company_name = client.company_name
        client.delete()
        messages.success(request, f"Client '{company_name}' deleted successfully!")
        
        # If it's an AJAX request, return a JSON response
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        
        # Otherwise, redirect to the client list
        return redirect('client_list')
    
    return render(request, 'clients/client_confirm_delete.html', {'client': client})

@login_required
def note_create(request, client_pk):
    """Create a new note for a client"""
    client = get_object_or_404(Client, pk=client_pk)
    
    # Check permissions
    has_access = False
    
    if request.user.is_superuser or (request.user.role and request.user.role.name in ['admin', 'staff']):
        has_access = True
    elif request.user == client.point_of_contact:
        has_access = True
    else:
        # Check if user is a coworker with at least editor permissions
        try:
            coworker = ClientCoworker.objects.get(client=client, user=request.user, status='active')
            if coworker.role in ['admin', 'editor']:
                has_access = True
        except ClientCoworker.DoesNotExist:
            pass
    
    if not has_access:
        return HttpResponseForbidden("You don't have permission to add notes to this client.")
    
    if request.method == 'POST':
        form = ClientNoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.client = client
            note.author = request.user
            note.save()
            messages.success(request, "Note added successfully!")
            return redirect('client_detail', pk=client.pk)
    else:
        form = ClientNoteForm()
    
    return render(request, 'clients/note_form.html', {
        'form': form,
        'client': client,
        'title': 'Add Note'
    })

@login_required
def note_detail(request, pk):
    """View a note's details"""
    note = get_object_or_404(ClientNote, pk=pk)
    client = note.client
    
    # Check permissions
    has_access = False
    
    if request.user.is_superuser or (request.user.role and request.user.role.name in ['admin', 'staff']):
        has_access = True
    elif request.user == client.point_of_contact:
        has_access = True
    elif request.user == note.author:
        has_access = True
    else:
        # Check if user is a coworker with at least viewer permissions
        try:
            coworker = ClientCoworker.objects.get(client=client, user=request.user, status='active')
            has_access = True
        except ClientCoworker.DoesNotExist:
            pass
    
    if not has_access:
        return HttpResponseForbidden("You don't have permission to view this note.")
    
    return render(request, 'clients/note_detail.html', {
        'note': note,
        'client': client
    })

@login_required
def note_update(request, pk):
    """Update a note"""
    note = get_object_or_404(ClientNote, pk=pk)
    client = note.client
    
    # Check permissions
    has_access = False
    
    if request.user.is_superuser or (request.user.role and request.user.role.name in ['admin', 'staff']):
        has_access = True
    elif request.user == client.point_of_contact:
        has_access = True
    elif request.user == note.author:
        has_access = True
    else:
        # Check if user is a coworker with at least editor permissions
        try:
            coworker = ClientCoworker.objects.get(client=client, user=request.user, status='active')
            if coworker.role in ['admin', 'editor']:
                has_access = True
        except ClientCoworker.DoesNotExist:
            pass
    
    if not has_access:
        return HttpResponseForbidden("You don't have permission to edit this note.")
    
    if request.method == 'POST':
        form = ClientNoteForm(request.POST, instance=note)
        if form.is_valid():
            form.save()
            messages.success(request, "Note updated successfully!")
            return redirect('note_detail', pk=note.pk)
    else:
        form = ClientNoteForm(instance=note)
    
    return render(request, 'clients/note_form.html', {
        'form': form,
        'note': note,
        'client': client,
        'title': 'Edit Note'
    })

@login_required
def note_delete(request, pk):
    """Delete a client note"""
    note = get_object_or_404(ClientNote, pk=pk)
    client = note.client
    
    # Check permissions
    has_access = False
    
    if request.user.is_superuser or (request.user.role and request.user.role.name in ['admin', 'staff']):
        has_access = True
    elif request.user == client.point_of_contact:
        has_access = True
    elif request.user == note.author:
        has_access = True
    else:
        # Check if user is a coworker with admin permissions
        try:
            coworker = ClientCoworker.objects.get(client=client, user=request.user, status='active')
            if coworker.role == 'admin':
                has_access = True
        except ClientCoworker.DoesNotExist:
            pass
    
    if not has_access:
        return HttpResponseForbidden("You don't have permission to delete this note.")
    
    if request.method == 'POST':
        note.delete()
        messages.success(request, "Note deleted successfully!")
        return redirect('client_detail', pk=client.pk)
    
    return render(request, 'clients/note_confirm_delete.html', {'note': note})

@login_required
def coworker_delete(request, pk):
    """Remove a coworker from a client"""
    coworker = get_object_or_404(ClientCoworker, pk=pk)
    client = coworker.client
    
    # Check permissions
    has_access = False
    
    if request.user.is_superuser or (request.user.role and request.user.role.name in ['admin', 'staff']):
        has_access = True
    elif request.user == client.point_of_contact:
        has_access = True
    else:
        # Check if user is a coworker with admin permissions
        try:
            user_coworker = ClientCoworker.objects.get(client=client, user=request.user, status='active')
            if user_coworker.role == 'admin':
                has_access = True
        except ClientCoworker.DoesNotExist:
            pass
    
    # Allow users to remove themselves
    if request.user == coworker.user:
        has_access = True
    
    if not has_access:
        return HttpResponseForbidden("You don't have permission to remove this coworker.")
    
    if request.method == 'POST':
        user_name = f"{coworker.user.first_name} {coworker.user.last_name}"
        coworker.delete()
        messages.success(request, f"{user_name} has been removed from this client.")
        return redirect('client_detail', pk=client.pk)
    
    return render(request, 'clients/coworker_confirm_delete.html', {
        'coworker': coworker,
        'client': client
    })

@login_required
def coworker_update(request, pk):
    """Update a coworker's role"""
    coworker = get_object_or_404(ClientCoworker, pk=pk)
    client = coworker.client
    
    # Check permissions
    has_access = False
    
    if request.user.is_superuser or (request.user.role and request.user.role.name in ['admin', 'staff']):
        has_access = True
    elif request.user == client.point_of_contact:
        has_access = True
    else:
        # Check if user is a coworker with admin permissions
        try:
            user_coworker = ClientCoworker.objects.get(client=client, user=request.user, status='active')
            if user_coworker.role == 'admin':
                has_access = True
        except ClientCoworker.DoesNotExist:
            pass
    
    if not has_access:
        return HttpResponseForbidden("You don't have permission to update this coworker's role.")
    
    if request.method == 'POST':
        role = request.POST.get('role')
        if role in [r[0] for r in ClientCoworker.ROLE_CHOICES]:
            coworker.role = role
            coworker.save()
            messages.success(request, f"Role updated to {coworker.get_role_display()} for {coworker.user.first_name} {coworker.user.last_name}.")
        else:
            messages.error(request, "Invalid role selected.")
        
        return redirect('client_detail', pk=client.pk)
    
    return render(request, 'clients/coworker_update_form.html', {
        'coworker': coworker,
        'client': client,
        'role_choices': ClientCoworker.ROLE_CHOICES
    })

@login_required
def resend_invitation(request, pk):
    """Resend invitation to a coworker"""
    coworker = get_object_or_404(ClientCoworker, pk=pk)
    client = coworker.client
    
    # Check permissions
    has_access = False
    
    if request.user.is_superuser or (request.user.role and request.user.role.name in ['admin', 'staff']):
        has_access = True
    elif request.user == client.point_of_contact:
        has_access = True
    else:
        # Check if user is a coworker with admin permissions
        try:
            user_coworker = ClientCoworker.objects.get(client=client, user=request.user, status='active')
            if user_coworker.role == 'admin':
                has_access = True
        except ClientCoworker.DoesNotExist:
            pass
    
    if not has_access:
        return HttpResponseForbidden("You don't have permission to resend this invitation.")
    
    if request.method == 'POST':
        # Generate new token and update sent time
        coworker.invitation_token = str(uuid.uuid4())
        coworker.invitation_sent = timezone.now()
        coworker.save()
        
        # Send invitation email
        send_coworker_invitation(request, coworker)
        
        messages.success(request, f"Invitation resent to {coworker.user.email} successfully!")
        return redirect('client_detail', pk=client.pk)
    
    return render(request, 'clients/resend_invitation_confirm.html', {
        'coworker': coworker,
        'client': client
    })

def accept_invitation(request, token):
    """Accept an invitation to be a coworker for a client"""
    try:
        coworker = ClientCoworker.objects.get(invitation_token=token, status='pending')
    except ClientCoworker.DoesNotExist:
        messages.error(request, "Invalid or expired invitation.")
        return redirect('home')
    
    # Update status to active
    coworker.status = 'active'
    coworker.save()
    
    messages.success(request, f"You are now a {coworker.get_role_display()} for {coworker.client.company_name}.")
    
    # If user is logged in, redirect to client detail
    if request.user.is_authenticated:
        return redirect('client_detail', pk=coworker.client.pk)
    else:
        # Otherwise redirect to login
        return redirect('login')

def send_coworker_invitation(request, coworker):
    """Send invitation email to a coworker"""
    client = coworker.client
    user = coworker.user
    
    # Generate invitation URL
    invitation_url = request.build_absolute_uri(
        reverse('accept_invitation', kwargs={'token': coworker.invitation_token})
    )
    
    # Prepare email content
    context = {
        'user': user,
        'client': client,
        'role': coworker.get_role_display(),
        'invitation_url': invitation_url,
        'sender': request.user,
    }
    
    html_message = render_to_string('clients/email/invitation.html', context)
    plain_message = strip_tags(html_message)
    
    # Send email
    send_mail(
        f'Invitation to collaborate on {client.company_name}',
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=html_message,
        fail_silently=False,
    )
    
    return True

@login_required
def client_dashboard(request):
    """Display client dashboard with charts and progress"""
    # Get clients based on user role
    if request.user.is_superuser or (request.user.role and request.user.role.name in ['admin', 'staff']):
        # Admins and staff can see all clients
        clients = Client.objects.all()
        logger.info(f"Admin/Staff user {request.user.email} accessing dashboard - showing all clients")
    else:
        # Regular users can only see their assigned clients
        clients = Client.objects.filter(assigned_to=request.user)
        logger.info(f"Regular user {request.user.email} accessing dashboard - showing assigned clients")
    
    # Get project statistics based on user role
    if request.user.is_superuser or (request.user.role and request.user.role.name in ['admin', 'staff']):
        total_projects = Project.objects.all().count()
        active_projects = Project.objects.filter(status='active').count()
        completed_projects = Project.objects.filter(status='completed').count()
        status_distribution = Project.objects.values('status').annotate(count=Count('id'))
        completed_projects_data = Project.objects.filter(
            status='completed',
            completed_date__isnull=False
        )
        total_comments = ClientNote.objects.count()
    else:
        total_projects = Project.objects.filter(client__in=clients).count()
        active_projects = Project.objects.filter(client__in=clients, status='active').count()
        completed_projects = Project.objects.filter(client__in=clients, status='completed').count()
        status_distribution = Project.objects.filter(client__in=clients).values('status').annotate(count=Count('id'))
        completed_projects_data = Project.objects.filter(
            client__in=clients,
            status='completed',
            completed_date__isnull=False
        )
        total_comments = ClientNote.objects.filter(client__in=clients).count()
    
    # Calculate average completion time
    avg_completion_time = completed_projects_data.aggregate(
        avg_days=Avg('completed_date') - Avg('created_at')
    )['avg_days']
    
    # Get monthly completion data
    if request.user.is_superuser or (request.user.role and request.user.role.name in ['admin', 'staff']):
        monthly_completion = Project.objects.filter(
            status='completed',
            completed_date__isnull=False
        ).values('completed_date__month').annotate(count=Count('id'))
        
        # Get monthly comment data
        monthly_comments = ClientNote.objects.annotate(
            month=ExtractMonth('created_at')
        ).values('month').annotate(count=Count('id'))
    else:
        monthly_completion = Project.objects.filter(
            client__in=clients,
            status='completed',
            completed_date__isnull=False
        ).values('completed_date__month').annotate(count=Count('id'))
        
        # Get monthly comment data for assigned clients
        monthly_comments = ClientNote.objects.filter(
            client__in=clients
        ).annotate(
            month=ExtractMonth('created_at')
        ).values('month').annotate(count=Count('id'))
    
    # Prepare data for charts
    chart_data = {
        'status_distribution': list(status_distribution),
        'project_counts': {
            'total': total_projects,
            'active': active_projects,
            'completed': completed_projects
        },
        'avg_completion_time': avg_completion_time,
        'monthly_completion': list(monthly_completion),
        'monthly_comments': list(monthly_comments),
        'total_comments': total_comments
    }
    
    # Get additional admin-only data
    admin_data = {}
    if request.user.is_superuser or (request.user.role and request.user.role.name in ['admin', 'staff']):
        admin_data = {
            'total_clients': Client.objects.count(),
            'total_users': CustomUser.objects.count(),
            'recent_activities': Project.objects.order_by('-created_at')[:5],
            'top_clients': Client.objects.annotate(
                project_count=Count('project')
            ).order_by('-project_count')[:5],
            'recent_comments': ClientNote.objects.select_related('client', 'author').order_by('-created_at')[:5]
        }
    
    context = {
        'clients': clients,
        'chart_data': json.dumps(chart_data),
        'total_projects': total_projects,
        'active_projects': active_projects,
        'completed_projects': completed_projects,
        'avg_completion_time': avg_completion_time,
        'total_comments': total_comments,
        'is_admin': request.user.is_superuser or (request.user.role and request.user.role.name in ['admin', 'staff']),
        'admin_data': admin_data
    }
    
    return render(request, 'clients/dashboard.html', context)

@login_required
def get_client_progress_data(request, client_id):
    """API endpoint to get client progress data for charts"""
    client = get_object_or_404(Client, id=client_id, assigned_to=request.user)
    
    # Get project status distribution for this client
    status_distribution = Project.objects.filter(
        client=client
    ).values('status').annotate(count=Count('id'))
    
    # Get monthly project completion data
    monthly_completion = Project.objects.filter(
        client=client,
        status='completed',
        completed_date__isnull=False
    ).values('completed_date__month').annotate(count=Count('id'))
    
    data = {
        'status_distribution': list(status_distribution),
        'monthly_completion': list(monthly_completion)
    }
    
    return JsonResponse(data)
