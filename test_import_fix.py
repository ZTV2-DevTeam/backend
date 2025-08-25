#!/usr/bin/env python
"""
Test script to verify the user/profile import fix
"""
import os
import django
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth.models import User
from api.models import Profile
from api.resources import ProfileResource
from io import StringIO
import csv

def test_import():
    """Test the fixed import functionality"""
    
    # Sample data matching your CSV structure
    test_data = """id,username,first_name,last_name,email,password,is_active,is_staff,date_joined,osztaly_display,osztaly_name
,test.user.1,Test,User1,test.user1@example.com,testpass123,IGAZ,HAMIS,,10F,10F
,test.user.2,Test,User2,test.user2@example.com,testpass123,IGAZ,HAMIS,,10F,10F"""

    print("Testing import with fixed ProfileResource...")
    
    # Create CSV file-like object
    csv_data = StringIO(test_data)
    
    # Import using ProfileResource
    resource = ProfileResource()
    
    try:
        # Parse the CSV data
        import tablib
        dataset = tablib.Dataset()
        dataset.csv = test_data
        
        # Perform import
        result = resource.import_data(dataset, dry_run=False)
        
        if result.has_errors():
            print("Import errors found:")
            for error in result.base_errors:
                print(f"  Base error: {error.error}")
            for row_error in result.row_errors():
                print(f"  Row {row_error[0]}: {row_error[1]}")
        else:
            print("Import successful!")
            print(f"Total rows processed: {result.total_rows}")
            
            # Verify users were created
            for username in ['test.user.1', 'test.user.2']:
                try:
                    user = User.objects.get(username=username)
                    profile = Profile.objects.get(user=user)
                    print(f"✓ User {username} created with profile (ID: {profile.id})")
                except (User.DoesNotExist, Profile.DoesNotExist) as e:
                    print(f"✗ Error finding user/profile {username}: {e}")
                    
    except Exception as e:
        print(f"Error during import: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nCleaning up test data...")
    # Clean up
    for username in ['test.user.1', 'test.user.2']:
        try:
            user = User.objects.get(username=username)
            user.delete()  # This will also delete the profile due to CASCADE
            print(f"✓ Cleaned up {username}")
        except User.DoesNotExist:
            pass

if __name__ == "__main__":
    test_import()
