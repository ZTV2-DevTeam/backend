#!/usr/bin/env python
"""
Debug password import issues
"""
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth.models import User
from django.contrib.auth import authenticate

def test_password_functionality():
    """Test password setting and authentication"""
    
    # Check if test user exists
    test_username = "jelszo.teszt2"
    try:
        user = User.objects.get(username=test_username)
        print(f"Found user: {user.username}")
        print(f"User password hash: {user.password}")
        print(f"Password hash length: {len(user.password)}")
        print(f"Has usable password: {user.has_usable_password()}")
        
        # Test authentication with known password
        test_password = "teszt8765!"
        auth_user = authenticate(username=test_username, password=test_password)
        if auth_user:
            print(f"✓ Authentication successful with password: {test_password}")
        else:
            print(f"✗ Authentication failed with password: {test_password}")
            
        # Test manual password setting
        print("\nTesting manual password setting...")
        user.set_password(test_password)
        user.save()
        print(f"New password hash: {user.password}")
        
        # Test authentication again
        auth_user = authenticate(username=test_username, password=test_password)
        if auth_user:
            print(f"✓ Authentication successful after manual set_password")
        else:
            print(f"✗ Authentication still failed after manual set_password")
            
    except User.DoesNotExist:
        print(f"User {test_username} not found")
        
        # Let's check what users exist
        print("\nExisting users:")
        for user in User.objects.all()[:10]:
            print(f"- {user.username}: {user.password[:50]}...")

if __name__ == "__main__":
    test_password_functionality()
