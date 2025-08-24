#!/usr/bin/env python
"""
Test script to verify that Django import-export properly handles
the osztaly (class) field for students in the Profile model.

This script tests:
1. Creating sample Osztaly objects
2. Testing the OsztalyWidget with various input formats
3. Importing profiles with osztaly assignments
4. Verifying the import worked correctly
"""

import os
import sys
import django
from datetime import datetime, date

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

django.setup()

from django.contrib.auth.models import User
from api.models import Profile, Osztaly, Tanev, Stab, RadioStab
from api.resources import UserProfileCombinedResource, OsztalyWidget
from import_export import resources
import tablib


def setup_test_data():
    """Create test data for osztaly import testing"""
    print("=== Setting up test data ===")
    
    # Create a current school year
    current_year = datetime.now().year
    tanev, created = Tanev.objects.get_or_create(
        start_date=date(current_year, 9, 1),
        end_date=date(current_year + 1, 6, 15)
    )
    if created:
        print(f"✓ Created school year: {tanev}")
    else:
        print(f"✓ Using existing school year: {tanev}")
    
    # Create test osztaly objects
    test_classes = [
        (2023, 'F'),  # 9F in current system
        (2022, 'F'),  # 10F in current system
        (2021, 'A'),  # Regular A class
        (2020, 'B'),  # Regular B class
    ]
    
    for start_year, szekcio in test_classes:
        osztaly, created = Osztaly.objects.get_or_create(
            startYear=start_year,
            szekcio=szekcio,
            defaults={'tanev': tanev}
        )
        if created:
            print(f"✓ Created class: {osztaly} (startYear={start_year}, szekcio={szekcio})")
        else:
            print(f"✓ Using existing class: {osztaly} (startYear={start_year}, szekcio={szekcio})")
    
    # Create test stabs and radio stabs if they don't exist
    stab, created = Stab.objects.get_or_create(name='Test Stab')
    if created:
        print(f"✓ Created stab: {stab}")
    
    radio_stab, created = RadioStab.objects.get_or_create(
        team_code='A1',
        defaults={'name': 'Test A1 Radio Team'}
    )
    if created:
        print(f"✓ Created radio stab: {radio_stab}")
    
    print()


def test_osztaly_widget():
    """Test the OsztalyWidget with various input formats"""
    print("=== Testing OsztalyWidget ===")
    
    widget = OsztalyWidget(Osztaly)
    
    test_cases = [
        # Format: (input_value, expected_result_description)
        ('2023-F', 'Should find 2023 F class'),
        ('9F', 'Should find current 9F class (2023-F)'),
        ('10F', 'Should find current 10F class (2022-F)'),
        ('2021-A', 'Should find 2021 A class'),
        ('21A', 'Should find 2021 A class (shorthand)'),
        ('2020-B', 'Should find 2020 B class'),
        ('20B', 'Should find 2020 B class (shorthand)'),
    ]
    
    for input_value, description in test_cases:
        try:
            result = widget.clean(input_value)
            if result:
                print(f"✓ '{input_value}' -> {result} ({description})")
                
                # Test rendering back
                rendered = widget.render(result)
                print(f"  Renders as: '{rendered}'")
            else:
                print(f"✗ '{input_value}' -> None ({description})")
        except Exception as e:
            print(f"✗ '{input_value}' -> ERROR: {e} ({description})")
    
    print()


def test_profile_import():
    """Test importing profiles with osztaly assignments"""
    print("=== Testing Profile Import ===")
    
    # Create test CSV data
    csv_data = """username,first_name,last_name,email,is_active,telefonszam,medias,admin_type,special_role,stab_name,radio_stab_team,osztaly_name
test.student1,Test,Student1,test1@example.com,TRUE,+36301111111,TRUE,none,none,Test Stab,,9F
test.student2,Test,Student2,test2@example.com,TRUE,+36302222222,TRUE,none,none,,A1,10F
test.student3,Test,Student3,test3@example.com,TRUE,+36303333333,TRUE,none,none,,,2021-A
test.teacher,Test,Teacher,teacher@example.com,TRUE,+36304444444,FALSE,teacher,none,,,"""
    
    print("CSV data to import:")
    print(csv_data)
    print()
    
    # Clean up any existing test users
    User.objects.filter(username__startswith='test.').delete()
    
    # Import the data
    resource = UserProfileCombinedResource()
    dataset = tablib.Dataset().load(csv_data, format='csv', headers=True)
    
    print("Importing data...")
    try:
        result = resource.import_data(dataset, dry_run=False)
        
        if result.has_errors():
            print("Import errors:")
            for error in result.row_errors():
                print(f"  Row {error[0]}: {error[1]}")
            print()
        else:
            print("✓ Import completed successfully!")
            print()
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return
    
    # Verify the imported data
    print("=== Verifying imported profiles ===")
    
    test_cases = [
        ('test.student1', '9F', 'Test Stab', None),
        ('test.student2', '10F', None, 'A1'),
        ('test.student3', '2021-A', None, None),
        ('test.teacher', None, None, None),
    ]
    
    for username, expected_class, expected_stab, expected_radio_stab in test_cases:
        try:
            user = User.objects.get(username=username)
            profile = Profile.objects.get(user=user)
            
            print(f"User: {user.get_full_name()} ({username})")
            
            # Check osztaly
            if expected_class:
                if profile.osztaly:
                    actual_class = str(profile.osztaly)
                    if expected_class in actual_class or actual_class in expected_class:
                        print(f"  ✓ Class: {actual_class} (expected: {expected_class})")
                    else:
                        print(f"  ✗ Class: {actual_class} (expected: {expected_class})")
                else:
                    print(f"  ✗ Class: None (expected: {expected_class})")
            else:
                if profile.osztaly:
                    print(f"  ✗ Class: {profile.osztaly} (expected: None)")
                else:
                    print(f"  ✓ Class: None")
            
            # Check stab
            if expected_stab:
                if profile.stab and profile.stab.name == expected_stab:
                    print(f"  ✓ Stab: {profile.stab.name}")
                else:
                    print(f"  ✗ Stab: {profile.stab} (expected: {expected_stab})")
            
            # Check radio stab
            if expected_radio_stab:
                if profile.radio_stab and profile.radio_stab.team_code == expected_radio_stab:
                    print(f"  ✓ Radio stab: {profile.radio_stab.team_code}")
                else:
                    print(f"  ✗ Radio stab: {profile.radio_stab} (expected: {expected_radio_stab})")
            
            print()
            
        except User.DoesNotExist:
            print(f"✗ User {username} was not created")
        except Profile.DoesNotExist:
            print(f"✗ Profile for {username} was not created")
        except Exception as e:
            print(f"✗ Error checking {username}: {e}")


def main():
    """Run all tests"""
    print("Django Import-Export Osztaly Field Test")
    print("=" * 50)
    print()
    
    setup_test_data()
    test_osztaly_widget()
    test_profile_import()
    
    print("=" * 50)
    print("Test completed!")


if __name__ == '__main__':
    main()
