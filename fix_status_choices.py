import os
import django
import json

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'perspectivetracker.settings')
django.setup()

from projects.models import ProjectType

# Find all project types
project_types = ProjectType.objects.all()
print(f"Found {len(project_types)} project types:")

# Find the accessibility project type
try:
    pt = ProjectType.objects.get(name='accessibility')
    print(f"Found project type: {pt.name}")
    print(f"Current status choices: {pt.status_choices}")
    
    # Set the correct status choices with each item on a separate line
    new_status_choices = [
        ["audit", "Audit"],
        ["remediation", "Remediation"],
        ["qa", "QA"],
        ["monitoring", "Monitoring"],
        ["statement_in_progress", "Accessibility Statement In Progress"],
        ["statement_given", "Accessibility Statement Given"]
    ]
    
    # Update the project type
    pt.status_choices = new_status_choices
    pt.save()
    
    print(f"Updated status choices for {pt.name}: {pt.status_choices}")
    print("Done!")
except ProjectType.DoesNotExist:
    print("Project type 'accessibility' not found.")

for pt in project_types:
    print(f"\nID: {pt.id}, Name: {pt.name}")
    print(f"Current status choices: {json.dumps(pt.status_choices, indent=2)}")
    
    # Determine which status choices to use based on project type
    if pt.name.lower() == 'accessibility':
        new_status_choices = [
            ["audit", "Audit"],
            ["remediation", "Remediation"],
            ["qa", "QA"],
            ["monitoring", "Monitoring"],
            ["statement_in_progress", "Accessibility Statement In Progress"],
            ["statement_given", "Accessibility Statement Given"]
        ]
        print(f"Using accessibility status choices for {pt.name}")
    else:
        # For other project types, check if they have valid choices already
        if pt.status_choices and len(pt.status_choices) > 0 and all(len(choice) == 2 for choice in pt.status_choices):
            # Check for any combined choices
            has_combined = any(len(choice) >= 2 and isinstance(choice[1], str) and ',' in choice[1] for choice in pt.status_choices)
            
            if has_combined:
                new_status_choices = [
                    ["not_started", "Not Started"],
                    ["in_progress", "In Progress"],
                    ["completed", "Completed"]
                ]
                print(f"Found combined choices in {pt.name}, using default status choices")
            else:
                # Keep existing choices if they look valid
                new_status_choices = pt.status_choices
                print(f"Keeping existing status choices for {pt.name}")
        else:
            # Use default choices if current choices are invalid
            new_status_choices = [
                ["not_started", "Not Started"],
                ["in_progress", "In Progress"],
                ["completed", "Completed"]
            ]
            print(f"Using default status choices for {pt.name}")
    
    # Update the project type if choices have changed
    if new_status_choices != pt.status_choices:
        pt.status_choices = new_status_choices
        pt.save()
        print(f"Updated status choices for {pt.name}: {json.dumps(pt.status_choices, indent=2)}")
    else:
        print(f"No changes needed for {pt.name}")

print("\nDone!") 