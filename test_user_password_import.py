#!/usr/bin/env python
"""
Simple test script for UserResource password import functionality.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from api.resources import UserResource
from tabulate import Dataset


def test_user_password_import():
    """Test UserResource with password import"""
    print("🔐 Testing UserResource password import...")
    
    # Clean up any existing test users first
    User.objects.filter(username__startswith='pwtest').delete()
    
    # Sample CSV data with passwords
    csv_data = """username,first_name,last_name,email,is_active
pwtest1,Password,Test1,pwtest1@example.com,TRUE
pwtest2,Password,Test2,pwtest2@example.com,TRUE"""
    
    # Test with password column
    csv_with_password = """username,first_name,last_name,email,password,is_active
pwtest3,Password,Test3,pwtest3@example.com,mypassword123,TRUE
pwtest4,Password,Test4,pwtest4@example.com,anotherpass456,TRUE"""
    
    # Create resource
    resource = UserResource()
    
    try:
        print("\n📋 Test 1: Import without password column")
        dataset1 = Dataset()
        dataset1.load(csv_data, format='csv')
        
        result1 = resource.import_data(dataset1, dry_run=False)
        
        if result1.has_errors():
            print("❌ Errors during import:")
            for error in result1.base_errors:
                print(f"   - {error.error}")
        else:
            print("✅ Import successful!")
            
            # Check users were created
            for username in ['pwtest1', 'pwtest2']:
                try:
                    user = User.objects.get(username=username)
                    print(f"✅ {username}: User created")
                    
                    if user.has_usable_password():
                        print(f"✅ {username}: Has usable password (auto-generated)")
                    else:
                        print(f"❌ {username}: No usable password")
                        
                except User.DoesNotExist:
                    print(f"❌ {username}: User not found")
        
        print("\n📋 Test 2: Import with password column")
        dataset2 = Dataset()
        dataset2.load(csv_with_password, format='csv')
        
        result2 = resource.import_data(dataset2, dry_run=False)
        
        if result2.has_errors():
            print("❌ Errors during import:")
            for error in result2.base_errors:
                print(f"   - {error.error}")
        else:
            print("✅ Import successful!")
            
            # Test password authentication
            test_cases = [
                ('pwtest3', 'mypassword123'),
                ('pwtest4', 'anotherpass456')
            ]
            
            for username, password in test_cases:
                try:
                    user = User.objects.get(username=username)
                    print(f"✅ {username}: User created")
                    
                    if user.has_usable_password():
                        print(f"✅ {username}: Has usable password")
                        
                        # Test authentication
                        auth_user = authenticate(username=username, password=password)
                        if auth_user:
                            print(f"✅ {username}: Password authentication successful!")
                        else:
                            print(f"❌ {username}: Password authentication failed!")
                            
                        # Also try wrong password
                        wrong_auth = authenticate(username=username, password='wrongpassword')
                        if not wrong_auth:
                            print(f"✅ {username}: Wrong password correctly rejected")
                        else:
                            print(f"❌ {username}: Wrong password incorrectly accepted")
                    else:
                        print(f"❌ {username}: No usable password")
                        
                except User.DoesNotExist:
                    print(f"❌ {username}: User not found")
                    
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up - delete test users
        print("\n🧹 Cleaning up test users...")
        User.objects.filter(username__startswith='pwtest').delete()


if __name__ == '__main__':
    test_user_password_import()
