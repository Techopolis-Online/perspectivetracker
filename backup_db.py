import os
import subprocess
from datetime import datetime
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perspectivetracker.settings')
django.setup()

def backup_database():
    """Backup the database before deployment"""
    try:
        # Get database URL from environment
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            print("No DATABASE_URL found in environment")
            return False

        # Create backup directory if it doesn't exist
        backup_dir = 'backups'
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)

        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(backup_dir, f'backup_{timestamp}.sql')

        # Use pg_dump to create backup
        subprocess.run([
            'pg_dump',
            database_url,
            '-f', backup_file
        ], check=True)

        print(f"Database backup created successfully: {backup_file}")
        return True

    except Exception as e:
        print(f"Error creating database backup: {str(e)}")
        return False

if __name__ == '__main__':
    backup_database() 