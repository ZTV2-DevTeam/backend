#!/usr/bin/env python
"""
Simple test script for User password import functionality.
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
from api.resources import UserResource
from tabulate import Dataset


def test_user_password_import():
    """Test simple User password import"""
    print("🔐 Testing User password import...")
    
    # Clean up any existing test users first
    User.objects.filter(username__startswith='testpass').delete()
    
    # Sample CSV data with passwords
    csv_data = """username,first_name,last_name,email,password
testpass1,Test,Pass1,testpass1@example.com,mypassword123
testpass2,Test,Pass2,testpass2@example.com,"""
    
    # Create dataset
    dataset = Dataset()
    dataset.load(csv_data, format='csv')
    
    # Create resource
    resource = UserResource()
    
    try:
        print("📊 Testing import preview...")
        result = resource.import_data(dataset, dry_run=True)
        
        if result.has_errors():
            print("❌ Errors in preview:")
            for error in result.base_errors:
                print(f"   - {error.error}")
            for row_num, errors in result.row_errors():
                for error in errors:
                    print(f"   - Row {row_num}: {error.error}")
            return False
        else:
            print("✅ Preview successful")
        
        print("\n🔄 Performing actual import...")
        result = resource.import_data(dataset, dry_run=False)
        
        if result.has_errors():
            print("❌ Errors during import:")
            for error in result.base_errors:
                print(f"   - {error.error}")
            for row_num, errors in result.row_errors():
                for error in errors:
                    print(f"   - Row {row_num}: {error.error}")
            return False
        else:
            print("✅ Import successful!")
        
        # Test password authentication
        print("\n🔍 Testing password authentication...")
        
        # Test user with provided password
        user1 = User.objects.get(username='testpass1')
        if user1.check_password('mypassword123'):
            print("✅ testpass1: Password 'mypassword123' works correctly")
        else:
            print("❌ testpass1: Password 'mypassword123' failed")
            print(f"   - Has usable password: {user1.has_usable_password()}")
            print(f"   - Password hash: {user1.password[:50]}...")
        
        # Test user with generated password
        user2 = User.objects.get(username='testpass2')
        if user2.has_usable_password():
            print("✅ testpass2: Has usable password (auto-generated)")
        else:
            print("❌ testpass2: No usable password")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Clean up - delete test users
        print("\n🧹 Cleaning up test users...")
        User.objects.filter(username__startswith='testpass').delete()


if __name__ == '__main__':
    print("🧪 Starting simple password import test...")
    print("=" * 50)
    
    success = test_user_password_import()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ Test completed successfully!")
    else:
        print("❌ Test failed!")
