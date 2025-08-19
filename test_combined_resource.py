#!/usr/bin/env python
"""
Quick test to verify that the UserProfileCombinedResource works without TypeError
"""

import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

django.setup()

from django.contrib.auth.models import User
from api.models import Profile, Osztaly, Tanev, Stab, RadioStab
from api.resources import UserProfileCombinedResource
import tablib
from datetime import date, datetime

def test_combined_resource():
    """Test the UserProfileCombinedResource"""
    print("Testing UserProfileCombinedResource...")
    
    # Clean up any existing test data
    User.objects.filter(username='test.combined').delete()
    
    # Create test data
    csv_data = """username,first_name,last_name,email,is_active,telefonszam,medias,admin_type,special_role,stab_name,radio_stab_team,osztaly_name
test.combined,Test,Combined,test@example.com,TRUE,+36301234567,TRUE,none,none,,,"""
    
    try:
        # Test the resource
        resource = UserProfileCombinedResource()
        dataset = tablib.Dataset().load(csv_data, format='csv', headers=True)
        
        print("Importing test data...")
        result = resource.import_data(dataset, dry_run=True)  # Dry run first
        
        if result.has_errors():
            print("DRY RUN - Import errors:")
            for error in result.row_errors():
                print(f"  Row {error[0]}: {error[1]}")
            return False
        else:
            print("✓ DRY RUN - No errors found")
            
        # Now do the actual import
        result = resource.import_data(dataset, dry_run=False)
        
        if result.has_errors():
            print("ACTUAL IMPORT - Import errors:")
            for error in result.row_errors():
                print(f"  Row {error[0]}: {error[1]}")
            return False
        else:
            print("✓ ACTUAL IMPORT - Success!")
            
        # Verify the data was created
        try:
            user = User.objects.get(username='test.combined')
            profile = Profile.objects.get(user=user)
            print(f"✓ User created: {user.get_full_name()} ({user.username})")
            print(f"✓ Profile created: {profile}")
            return True
        except (User.DoesNotExist, Profile.DoesNotExist) as e:
            print(f"✗ Error verifying data: {e}")
            return False
            
    except Exception as e:
        print(f"✗ Exception during import: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up
        User.objects.filter(username='test.combined').delete()

if __name__ == '__main__':
    print("=" * 50)
    print("UserProfileCombinedResource Test")
    print("=" * 50)
    
    success = test_combined_resource()
    
    print("=" * 50)
    if success:
        print("✓ TEST PASSED - No TypeError issues!")
    else:
        print("✗ TEST FAILED")
