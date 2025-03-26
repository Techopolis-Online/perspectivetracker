import os
import subprocess
import django
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perspectivetracker.settings')
django.setup()

def restore_database():
    """Restore the database from the latest backup"""
    try:
        # Get database URL from environment
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            print("No DATABASE_URL found in environment")
            return False

        # Get the latest backup file
        backup_dir = 'backups'
        if not os.path.exists(backup_dir):
            print("No backup directory found")
            return False

        backup_files = [f for f in os.listdir(backup_dir) if f.endswith('.sql')]
        if not backup_files:
            print("No backup files found")
            return False

        latest_backup = max(backup_files, key=lambda x: os.path.getctime(os.path.join(backup_dir, x)))
        backup_file = os.path.join(backup_dir, latest_backup)

        # Use psql to restore backup
        subprocess.run([
            'psql',
            database_url,
            '-f', backup_file
        ], check=True)

        print(f"Database restored successfully from: {backup_file}")
        return True

    except Exception as e:
        print(f"Error restoring database: {str(e)}")
        return False

if __name__ == '__main__':
    restore_database() 