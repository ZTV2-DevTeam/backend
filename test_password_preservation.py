#!/usr/bin/env python
"""
Test script to verify that password preservation works correctly in admin forms
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth.models import User, Group
from api.admin import CustomUserChangeForm
from django.contrib.auth.hashers import check_password

def test_password_preservation():
    """Test that empty password field preserves existing password"""
    print("🧪 Testing password preservation...")
    
    # Create a test user
    test_username = 'test_password_user'
    test_password = 'original_password123'
    
    # Clean up any existing test user
    try:
        User.objects.get(username=test_username).delete()
    except User.DoesNotExist:
        pass
    
    # Create user with known password
    user = User.objects.create_user(
        username=test_username,
        email='test@example.com',
        password=test_password,
        first_name='Test',
        last_name='User'
    )
    original_hash = user.password
    print(f"✅ Created test user with password hash: {original_hash[:50]}...")
    
    # Verify original password works
    assert check_password(test_password, user.password), "Original password should work"
    print("✅ Original password verification successful")
    
    # Test 1: Save form with empty password (should preserve existing)
    print("\n🧪 Test 1: Empty password field should preserve existing password")
    form_data = {
        'username': test_username,
        'email': 'test@example.com',
        'first_name': 'Test',
        'last_name': 'User Modified',
        'password': '',  # Empty password
        'is_active': True,
        'is_staff': False,
        'is_superuser': False,
        'date_joined': user.date_joined,
    }
    
    form = CustomUserChangeForm(data=form_data, instance=user)
    if form.is_valid():
        saved_user = form.save()
        print(f"✅ Form saved successfully")
        print(f"   Original hash: {original_hash[:50]}...")
        print(f"   New hash:      {saved_user.password[:50]}...")
        
        # Verify password is preserved
        assert saved_user.password == original_hash, "Password hash should be preserved"
        print("✅ Password hash preserved correctly!")
        
        # Verify original password still works
        assert check_password(test_password, saved_user.password), "Original password should still work"
        print("✅ Original password still works!")
        
        # Verify other fields were updated
        assert saved_user.last_name == 'User Modified', "Other fields should be updated"
        print("✅ Other fields updated correctly!")
    else:
        print(f"❌ Form validation failed: {form.errors}")
        return False
    
    # Test 2: Save form with new password (should update)
    print("\n🧪 Test 2: New password field should update password")
    new_password = 'new_password456'
    form_data['password'] = new_password
    form_data['last_name'] = 'User Modified Again'
    
    form = CustomUserChangeForm(data=form_data, instance=saved_user)
    if form.is_valid():
        saved_user = form.save()
        print(f"✅ Form saved with new password")
        
        # Verify password was changed
        assert saved_user.password != original_hash, "Password hash should be different"
        print("✅ Password hash changed!")
        
        # Verify new password works
        assert check_password(new_password, saved_user.password), "New password should work"
        print("✅ New password works!")
        
        # Verify old password doesn't work
        assert not check_password(test_password, saved_user.password), "Old password should not work"
        print("✅ Old password correctly invalidated!")
    else:
        print(f"❌ Form validation failed: {form.errors}")
        return False
    
    # Clean up
    user.delete()
    print("\n🧹 Cleaned up test user")
    
    return True

def test_group_modification():
    """Test that modifying groups doesn't affect password"""
    print("\n🧪 Testing group modification doesn't affect password...")
    
    # Create a test user and group
    test_username = 'test_group_user'
    test_password = 'group_test_password123'
    
    # Clean up any existing test user
    try:
        User.objects.get(username=test_username).delete()
    except User.DoesNotExist:
        pass
    
    # Create test group
    test_group, created = Group.objects.get_or_create(name='Test Group')
    
    # Create user
    user = User.objects.create_user(
        username=test_username,
        email='group_test@example.com',
        password=test_password
    )
    original_hash = user.password
    print(f"✅ Created test user with password hash: {original_hash[:50]}...")
    
    # Add user to group using form (simulating admin interface)
    form_data = {
        'username': test_username,
        'email': 'group_test@example.com',
        'first_name': '',
        'last_name': '',
        'password': '',  # Empty password - should preserve existing
        'is_active': True,
        'is_staff': False,
        'is_superuser': False,
        'date_joined': user.date_joined,
        'groups': [test_group.id],  # Adding to group
    }
    
    form = CustomUserChangeForm(data=form_data, instance=user)
    if form.is_valid():
        saved_user = form.save()
        print(f"✅ User saved with group assignment")
        
        # Verify password is preserved
        assert saved_user.password == original_hash, "Password should be preserved when modifying groups"
        print("✅ Password preserved during group modification!")
        
        # Verify password still works
        assert check_password(test_password, saved_user.password), "Password should still work"
        print("✅ Password functionality preserved!")
        
        # Group assignment might require many-to-many handling, but password is preserved which is our main concern
        print("✅ Main test passed: Password preservation during form save!")
    else:
        print(f"❌ Form validation failed: {form.errors}")
        return False
    
    # Clean up
    user.delete()
    test_group.delete()
    print("🧹 Cleaned up test user and group")
    
    return True

if __name__ == '__main__':
    print("🚀 Starting password preservation tests...\n")
    
    try:
        success1 = test_password_preservation()
        success2 = test_group_modification()
        
        if success1 and success2:
            print("\n🎉 All tests passed! Password preservation is working correctly.")
        else:
            print("\n❌ Some tests failed. Check the output above.")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)