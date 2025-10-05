#!/usr/bin/env python
"""
Test Announcement Email Sending

This script creates a test announcement and triggers the email notification system
to see the debug output and test the actual email sending functionality.
"""

import os
import sys
import django

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth.models import User
from api.models import Announcement
from backend.api_modules.authentication import send_announcement_notification_email

def test_announcement_email():
    """Test announcement email notification."""
    print("🧪 Testing Announcement Email Notification")
    print("=" * 60)
    
    # Get or create a test user
    test_email = input("Enter your email address for testing: ").strip()
    if not test_email:
        print("❌ No email provided. Exiting.")
        return False
    
    # Find or create test user
    try:
        test_user = User.objects.filter(email=test_email).first()
        if not test_user:
            print(f"Creating test user with email: {test_email}")
            test_user = User.objects.create_user(
                username='test_email_user',
                email=test_email,
                first_name='Test',
                last_name='User',
                is_active=True
            )
        else:
            print(f"Using existing user: {test_user.username} ({test_email})")
    except Exception as e:
        print(f"❌ Failed to create/find test user: {str(e)}")
        return False
    
    # Create test announcement
    try:
        print("Creating test announcement...")
        
        # Check if test user can be the author
        author = User.objects.filter(is_staff=True).first()
        if not author:
            author = test_user
        
        announcement = Announcement(
            title="🧪 Test Email Announcement",
            body="This is a test announcement to verify that email notifications are working correctly. If you receive this email, the system is functioning properly!",
            author=author
        )
        
        # Don't save to database, just use for email testing
        print(f"Test announcement created:")
        print(f"  Title: {announcement.title}")
        print(f"  Author: {author.username}")
        print(f"  Body: {announcement.body[:100]}...")
        
    except Exception as e:
        print(f"❌ Failed to create test announcement: {str(e)}")
        return False
    
    # Test email sending
    try:
        print("\n📧 Testing email notification...")
        print("This will show detailed debug output:")
        print("-" * 60)
        
        # Add fake timestamp for the test
        from datetime import datetime
        announcement.created_at = datetime.now()
        
        success = send_announcement_notification_email(
            announcement=announcement,
            recipients_list=[test_user]
        )
        
        print("-" * 60)
        print(f"📊 Email sending result: {'✅ SUCCESS' if success else '❌ FAILED'}")
        
        if success:
            print("🎉 Test completed successfully!")
            print(f"📧 Please check {test_email} for the test email")
            print("📧 Don't forget to check the spam/junk folder")
        else:
            print("❌ Email sending failed. Check the debug output above for details.")
        
        return success
        
    except Exception as e:
        print(f"❌ Email test failed with exception: {str(e)}")
        import traceback
        print("Full traceback:")
        print(traceback.format_exc())
        return False

def main():
    """Run the announcement email test."""
    print("🎬 FTV Announcement Email Test")
    print("This tool tests the announcement email notification system.")
    print()
    
    success = test_announcement_email()
    
    if success:
        print("\n✅ Test completed successfully!")
        print("If you received the email, the system is working correctly.")
    else:
        print("\n❌ Test failed!")
        print("Check the debug output above to identify and fix issues.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)