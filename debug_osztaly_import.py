#!/usr/bin/env python
"""
Debug script for osztaly import issues
"""

import os
import sys
import django
from datetime import datetime

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

django.setup()

from django.contrib.auth.models import User
from api.models import Profile, Osztaly
from api.resources import ProfileResource, OsztalyWidget
import tablib

def test_osztaly_widget():
    """Test the OsztalyWidget with '10F' input"""
    print("=== Testing OsztalyWidget ===")
    
    widget = OsztalyWidget(Osztaly)
    
    try:
        result = widget.clean("10F")
        print(f"✓ OsztalyWidget.clean('10F') returned: {result}")
        print(f"  - startYear: {result.startYear}")
        print(f"  - szekcio: {result.szekcio}")
        return result
    except Exception as e:
        print(f"✗ OsztalyWidget.clean('10F') failed: {e}")
        return None

def check_existing_osztaly():
    """Check what Osztaly records exist"""
    print("\n=== Existing Osztaly Records ===")
    
    osztaly_records = Osztaly.objects.all()
    print(f"Total Osztaly records: {osztaly_records.count()}")
    
    for osztaly in osztaly_records:
        print(f"  - {osztaly.startYear}-{osztaly.szekcio} (id: {osztaly.id})")
    
    # Check specifically for 2022-F
    f_2022 = Osztaly.objects.filter(startYear=2022, szekcio='F').first()
    if f_2022:
        print(f"\n✓ Found 2022-F class: {f_2022} (id: {f_2022.id})")
    else:
        print("\n✗ No 2022-F class found")

def test_import_logic():
    """Test the actual import logic"""
    print("\n=== Testing Import Logic ===")
    
    # Create test CSV data with both columns
    csv_data = """username,first_name,last_name,email,is_active,telefonszam,medias,admin_type,special_role,stab_name,radio_stab_team,osztaly_name,osztaly_display
test.debug1,Test,Debug1,test.debug1@example.com,TRUE,+36301111111,TRUE,none,none,,,10F,
test.debug2,Test,Debug2,test.debug2@example.com,TRUE,+36302222222,TRUE,none,none,,,,10F"""
    
    print("CSV data to import:")
    print(csv_data)
    print()
    
    # Clean up any existing test users
    User.objects.filter(username__startswith='test.debug').delete()
    
    # Import the data
    resource = ProfileResource()
    dataset = tablib.Dataset().load(csv_data, format='csv', headers=True)
    
    print("Importing data...")
    try:
        result = resource.import_data(dataset, dry_run=False)
        
        if result.has_errors():
            print("Import errors:")
            for error in result.row_errors():
                print(f"  Row {error[0]}: {error[1]}")
        else:
            print("✓ Import completed successfully!")
        
        # Check the results
        print("\n=== Verifying Results ===")
        
        for username in ['test.debug1', 'test.debug2']:
            try:
                user = User.objects.get(username=username)
                profile = Profile.objects.get(user=user)
                
                print(f"\nUser: {user.get_full_name()} ({username})")
                print(f"  - Profile exists: ✓")
                
                if profile.osztaly:
                    print(f"  - Osztaly: ✓ {profile.osztaly} (id: {profile.osztaly.id})")
                else:
                    print(f"  - Osztaly: ✗ Not assigned")
                    
            except User.DoesNotExist:
                print(f"✗ User {username} was not created")
            except Profile.DoesNotExist:
                print(f"✗ Profile for {username} was not created")
                
    except Exception as e:
        print(f"✗ Import failed: {e}")

def main():
    """Run all debug tests"""
    print("=== Debug Osztaly Import Issues ===")
    print(f"Current date: {datetime.now()}")
    print(f"Current year: {datetime.now().year}")
    print(f"Current month: {datetime.now().month}")
    print()
    
    check_existing_osztaly()
    test_osztaly_widget()
    test_import_logic()

if __name__ == '__main__':
    main()
