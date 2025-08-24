#!/usr/bin/env python
"""
Test script for password import functionality with django-import-export.

This script tests the new password functionality in UserResource and UserProfileCombinedResource.
"""

import os
import sys
import django
from pathlib import Path

# Add the project directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from api.resources import UserResource, UserProfileCombinedResource
from api.models import Profile
from io import StringIO
import csv
from tabulate import Dataset


def test_user_resource_password_import():
    """Test UserResource with password import"""
    print("🔐 Testing UserResource with password import...")
    
    # Sample CSV data with passwords
    csv_data = """username,first_name,last_name,email,password,is_active
testuser1,Test,User1,testuser1@example.com,password123,TRUE
testuser2,Test,User2,testuser2@example.com,,TRUE
testuser3,Test,User3,testuser3@example.com,mypass456,TRUE"""
    
    # Create dataset
    dataset = Dataset()
    dataset.load(csv_data, format='csv')
    
    # Create resource
    resource = UserResource()
    
    try:
        # Test import
        result = resource.import_data(dataset, dry_run=True)
        
        print(f"📊 Import preview:")
        print(f"   - Total rows: {len(dataset)}")
        print(f"   - Has errors: {result.has_errors()}")
        
        if result.has_errors():
            print("❌ Errors found:")
            for error in result.base_errors:
                print(f"   - {error.error}")
            for error in result.row_errors():
                print(f"   - Row {error[0]}: {error[1]}")
        else:
            print("✅ No errors found in preview")
            
            # Actually import the data
            print("\n🔄 Performing actual import...")
            result = resource.import_data(dataset, dry_run=False)
            
            if result.has_errors():
                print("❌ Errors during import:")
                for error in result.base_errors:
                    print(f"   - {error.error}")
            else:
                print("✅ Import successful!")
                
                # Test password authentication
                print("\n🔍 Testing password authentication...")
                for row in dataset.dict:
                    username = row['username']
                    password = row['password']
                    
                    try:
                        user = User.objects.get(username=username)
                        
                        if password:
                            # Test with provided password
                            auth_user = authenticate(username=username, password=password)
                            if auth_user:
                                print(f"✅ {username}: Password authentication successful")
                            else:
                                print(f"❌ {username}: Password authentication failed")
                        else:
                            print(f"ℹ️  {username}: No password provided, random password generated")
                        
                        # Check if password is set
                        if user.has_usable_password():
                            print(f"✅ {username}: Has usable password")
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
        User.objects.filter(username__startswith='testuser').delete()


def test_combined_resource_password_import():
    """Test UserProfileCombinedResource with password import"""
    print("\n🔐 Testing UserProfileCombinedResource with password import...")
    
    # Sample CSV data with passwords
    csv_data = """username,first_name,last_name,email,password,is_active,telefonszam,admin_type,medias
combuser1,Combined,User1,combuser1@example.com,combpass123,TRUE,+36301111111,none,TRUE
combuser2,Combined,User2,combuser2@example.com,,TRUE,+36302222222,teacher,TRUE
combuser3,Combined,User3,combuser3@example.com,secure789,TRUE,+36303333333,none,TRUE"""
    
    # Create dataset
    dataset = Dataset()
    dataset.load(csv_data, format='csv')
    
    # Create resource
    resource = UserProfileCombinedResource()
    
    try:
        # Test import
        result = resource.import_data(dataset, dry_run=True)
        
        print(f"📊 Import preview:")
        print(f"   - Total rows: {len(dataset)}")
        print(f"   - Has errors: {result.has_errors()}")
        
        if result.has_errors():
            print("❌ Errors found:")
            for error in result.base_errors:
                print(f"   - {error.error}")
            for error in result.row_errors():
                print(f"   - Row {error[0]}: {error[1]}")
        else:
            print("✅ No errors found in preview")
            
            # Actually import the data
            print("\n🔄 Performing actual import...")
            result = resource.import_data(dataset, dry_run=False)
            
            if result.has_errors():
                print("❌ Errors during import:")
                for error in result.base_errors:
                    print(f"   - {error.error}")
            else:
                print("✅ Import successful!")
                
                # Test password authentication and profile creation
                print("\n🔍 Testing password authentication and profiles...")
                for row in dataset.dict:
                    username = row['username']
                    password = row['password']
                    
                    try:
                        user = User.objects.get(username=username)
                        
                        # Check if profile was created
                        try:
                            profile = Profile.objects.get(user=user)
                            print(f"✅ {username}: Profile created with admin_type: {profile.admin_type}")
                        except Profile.DoesNotExist:
                            print(f"❌ {username}: Profile not created")
                        
                        if password:
                            # Test with provided password
                            auth_user = authenticate(username=username, password=password)
                            if auth_user:
                                print(f"✅ {username}: Password authentication successful")
                            else:
                                print(f"❌ {username}: Password authentication failed")
                        else:
                            print(f"ℹ️  {username}: No password provided, random password generated")
                        
                        # Check if password is set
                        if user.has_usable_password():
                            print(f"✅ {username}: Has usable password")
                        else:
                            print(f"❌ {username}: No usable password")
                            
                    except User.DoesNotExist:
                        print(f"❌ {username}: User not found")
                        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up - delete test users and profiles
        print("\n🧹 Cleaning up test users and profiles...")
        users = User.objects.filter(username__startswith='combuser')
        Profile.objects.filter(user__in=users).delete()
        users.delete()


def test_password_export():
    """Test that passwords are not exported in plain text"""
    print("\n🔒 Testing password export security...")
    
    # Create a test user with a password
    user = User.objects.create_user(
        username='exporttest',
        email='exporttest@example.com',
        password='secret123',
        first_name='Export',
        last_name='Test'
    )
    
    try:
        resource = UserResource()
        dataset = resource.export()
        
        # Find our test user in the export
        for row in dataset.dict:
            if row.get('username') == 'exporttest':
                password_field = row.get('password', 'NOT_FOUND')
                if password_field == '*** HIDDEN ***':
                    print("✅ Password field properly hidden in export")
                elif password_field == 'NOT_FOUND':
                    print("ℹ️  Password field not included in export")
                else:
                    print(f"❌ Password field exposed in export: {password_field}")
                break
        else:
            print("❌ Test user not found in export")
            
    except Exception as e:
        print(f"❌ Export test failed: {e}")
    
    finally:
        # Clean up
        user.delete()


def main():
    """Run all password import tests"""
    print("🧪 Starting password import functionality tests...")
    print("=" * 60)
    
    try:
        test_user_resource_password_import()
        test_combined_resource_password_import()
        test_password_export()
        
        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
