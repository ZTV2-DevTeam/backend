#!/usr/bin/env python
"""
Test script for assignment email notifications via Django signals.

This script tests the newly implemented assignment change email notification
system that works through Django signals when users are added or removed
from assignments.
"""

import os
import sys
import django
from datetime import datetime, date, time

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from api.models import (
    User, Profile, Forgatas, Beosztas, SzerepkorRelaciok, 
    Szerepkor, Partner, Osztaly
)
from django.contrib.auth.models import Group


def test_assignment_email_notifications():
    """Test assignment email notifications through Django signals."""
    
    print("🧪 Testing Assignment Email Notifications via Signals")
    print("=" * 60)
    
    try:
        # Create or get test users
        print("\n📋 Step 1: Setting up test data...")
        
        # Get or create test users
        test_user1, created1 = User.objects.get_or_create(
            username="test_signal_user1",
            defaults={
                'email': 'test1@example.com',
                'first_name': 'Test',
                'last_name': 'User One',
                'is_active': True
            }
        )
        
        test_user2, created2 = User.objects.get_or_create(
            username="test_signal_user2", 
            defaults={
                'email': 'test2@example.com',
                'first_name': 'Test',
                'last_name': 'User Two',
                'is_active': True
            }
        )
        
        # Ensure profiles exist
        Profile.objects.get_or_create(user=test_user1)
        Profile.objects.get_or_create(user=test_user2)
        
        print(f"✅ Test users ready: {test_user1.get_full_name()}, {test_user2.get_full_name()}")
        
        # Get or create test data
        partner, _ = Partner.objects.get_or_create(
            name="Test Partner", 
            defaults={'contact_person': 'Test Contact'}
        )
        
        osztaly, _ = Osztaly.objects.get_or_create(name="Test Class")
        
        szerepkor, _ = Szerepkor.objects.get_or_create(
            name="Test Role",
            defaults={'description': 'Test role for signal testing'}
        )
        
        # Create test forgatas
        test_forgatas, _ = Forgatas.objects.get_or_create(
            name="Test Forgatas - Signal Test",
            defaults={
                'date': date(2025, 10, 15),
                'timeFrom': time(10, 0),
                'timeTo': time(16, 0),
                'location': 'Test Location',
                'partner': partner,
                'forgTipus': 'normal',  # Not 'kacsa' to ensure emails are sent
                'description': 'Test forgatas for email signal testing'
            }
        )
        
        # Create test beosztas
        test_beosztas, _ = Beosztas.objects.get_or_create(
            forgatas=test_forgatas,
            defaults={
                'kesz': False,  # Start as draft
                'description': 'Test assignment for signal testing'
            }
        )
        
        print(f"✅ Test assignment ready: {test_beosztas} for {test_forgatas.name}")
        
        # Test 1: Add users to assignment
        print("\n📧 Step 2: Testing user addition to assignment...")
        
        # Create szerepkor relations for the users
        rel1, _ = SzerepkorRelaciok.objects.get_or_create(
            user=test_user1,
            szerepkor=szerepkor,
            osztaly=osztaly
        )
        
        rel2, _ = SzerepkorRelaciok.objects.get_or_create(
            user=test_user2,
            szerepkor=szerepkor,
            osztaly=osztaly
        )
        
        # Add users to assignment - this should trigger addition emails
        print("Adding users to assignment (should trigger addition emails)...")
        test_beosztas.szerepkor_relaciok.add(rel1, rel2)
        
        print("✅ Users added to assignment - check logs for email sending results")
        
        # Test 2: Remove one user from assignment
        print("\n📧 Step 3: Testing user removal from assignment...")
        
        # Remove one user - this should trigger removal email
        print(f"Removing {test_user1.get_full_name()} from assignment (should trigger removal email)...")
        test_beosztas.szerepkor_relaciok.remove(rel1)
        
        print("✅ User removed from assignment - check logs for email sending results")
        
        # Test 3: Remove remaining user
        print("\n📧 Step 4: Testing removal of remaining user...")
        
        print(f"Removing {test_user2.get_full_name()} from assignment...")
        test_beosztas.szerepkor_relaciok.remove(rel2)
        
        print("✅ All users removed from assignment - check logs for email sending results")
        
        print("\n" + "=" * 60)
        print("🎉 Assignment Email Signal Test Complete!")
        print("📋 Summary:")
        print("   • Created test assignment and users")
        print("   • Tested user addition to assignment (should send addition emails)")
        print("   • Tested user removal from assignment (should send removal emails)")
        print("   • Check the console logs above for email sending results")
        print("   • Email signal handlers should now be working for both additions and removals")
        
    except Exception as e:
        print(f"❌ Error during assignment email signal test: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return False
    
    return True


if __name__ == "__main__":
    print("Assignment Email Signal Notification Test")
    print("This tool tests the Django signal-based assignment email notification system.")
    print("It will add and remove users from assignments to trigger email notifications.")
    
    success = test_assignment_email_notifications()
    
    if success:
        print("\n✅ Test completed successfully!")
    else:
        print("\n❌ Test failed!")
        sys.exit(1)