import os
import json
import django
from datetime import datetime
from django.core.serializers.json import DjangoJSONEncoder

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perspectivetracker.settings')
django.setup()

from clients.models import Client, ClientNote, ClientCoworker
from projects.models import Project, ProjectNote, ProjectStatus, ProjectType, Standard, Page
from users.models import CustomUser, Role

def backup_data():
    """Backup all data to JSON files"""
    # Create backups directory if it doesn't exist
    backup_dir = 'backups'
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    # Generate timestamp for backup files
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Backup data in order of dependencies
    models_data = {
        'roles': list(Role.objects.all().values()),
        'users': list(CustomUser.objects.all().values('id', 'email', 'first_name', 'last_name', 'role_id', 'is_staff', 'is_superuser')),
        'clients': list(Client.objects.all().values()),
        'client_notes': list(ClientNote.objects.all().values()),
        'client_coworkers': list(ClientCoworker.objects.all().values()),
        'projects': list(Project.objects.all().values()),
        'project_notes': list(ProjectNote.objects.all().values()),
        'project_statuses': list(ProjectStatus.objects.all().values()),
        'project_types': list(ProjectType.objects.all().values()),
        'standards': list(Standard.objects.all().values()),
        'pages': list(Page.objects.all().values()),
    }

    # Save each model's data to a separate JSON file
    for model_name, data in models_data.items():
        backup_file = os.path.join(backup_dir, f'{model_name}_{timestamp}.json')
        with open(backup_file, 'w') as f:
            json.dump(data, f, cls=DjangoJSONEncoder, indent=2)
        print(f"Backed up {model_name} to {backup_file}")

    print("All data has been backed up successfully!")

if __name__ == '__main__':
    backup_data() 