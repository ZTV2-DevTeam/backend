#!/usr/bin/env python
"""
Debug script for email configuration and testing.
This script helps identify email configuration issues.
"""

import os
import sys
import django

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth.models import User
from api.models import Announcement, Forgatas, Beosztas
from datetime import date, time, datetime, timedelta

def debug_email_settings():
    """Print all email-related settings for debugging."""
    print("="*60)
    print("EMAIL CONFIGURATION DEBUG")
    print("="*60)
    
    email_settings = [
        'EMAIL_BACKEND',
        'EMAIL_HOST',
        'EMAIL_PORT',
        'EMAIL_USE_TLS',
        'EMAIL_USE_SSL',
        'EMAIL_HOST_USER',
        'EMAIL_HOST_PASSWORD',
        'DEFAULT_FROM_EMAIL',
        'SERVER_EMAIL',
        'FRONTEND_URL'
    ]
    
    for setting in email_settings:
        value = getattr(settings, setting, 'NOT SET')
        if 'PASSWORD' in setting:
            # Mask password but show if it exists
            if value and value != 'NOT SET':
                value = f"***SET*** (length: {len(str(value))})"
            else:
                value = "***NOT SET***"
        print(f"{setting}: {value}")
    
    print("\nAll Django settings related to email:")
    all_settings = dir(settings)
    email_related = [s for s in all_settings if 'EMAIL' in s or 'MAIL' in s]
    for setting in email_related:
        value = getattr(settings, setting, 'NOT SET')
        if 'PASSWORD' in setting:
            if value and value != 'NOT SET':
                value = f"***SET*** (length: {len(str(value))})"
            else:
                value = "***NOT SET***"
        print(f"  {setting}: {value}")

def test_basic_email():
    """Test basic Django email functionality."""
    print("\n" + "="*60)
    print("BASIC EMAIL TEST")
    print("="*60)
    
    try:
        # Get admin user for testing
        admin_user = User.objects.filter(is_staff=True, email__isnull=False).exclude(email='').first()
        
        if not admin_user:
            print("[ERROR] No admin user with email found for testing")
            return False
        
        print(f"[DEBUG] Testing with admin user: {admin_user.username} ({admin_user.email})")
        
        subject = "FTV Email Test - Basic Functionality"
        message = f"""
        This is a test email from the FTV system.
        
        Test details:
        - Timestamp: {datetime.now().isoformat()}
        - User: {admin_user.username}
        - From: {settings.DEFAULT_FROM_EMAIL}
        
        If you receive this email, the basic email configuration is working.
        """
        
        print(f"[DEBUG] Sending test email...")
        print(f"[DEBUG] Subject: {subject}")
        print(f"[DEBUG] To: {admin_user.email}")
        print(f"[DEBUG] From: {settings.DEFAULT_FROM_EMAIL}")
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[admin_user.email],
            fail_silently=False,
        )
        
        print(f"[SUCCESS] Basic email sent successfully!")
        return True
        
    except Exception as e:
        print(f"[ERROR] Basic email test failed: {str(e)}")
        import traceback
        print(f"[ERROR] Full traceback: {traceback.format_exc()}")
        return False

def test_announcement_email():
    """Test announcement email notification."""
    print("\n" + "="*60)
    print("ANNOUNCEMENT EMAIL TEST")
    print("="*60)
    
    try:
        # Get admin user for testing
        admin_user = User.objects.filter(is_staff=True, email__isnull=False).exclude(email='').first()
        
        if not admin_user:
            print("[ERROR] No admin user with email found for testing")
            return False
        
        # Create a test announcement (don't save to database)
        test_announcement = Announcement(
            title="🧪 Test Announcement - Email Debug",
            body="This is a test announcement created for email debugging purposes. This announcement is not saved to the database.",
            author=admin_user,
            created_at=datetime.now()
        )
        
        print(f"[DEBUG] Testing announcement email with user: {admin_user.username} ({admin_user.email})")
        
        # Import and test the announcement email function
        from backend.api_modules.authentication import send_announcement_notification_email
        
        success = send_announcement_notification_email(test_announcement, [admin_user])
        
        if success:
            print(f"[SUCCESS] Announcement email test completed successfully!")
            return True
        else:
            print(f"[ERROR] Announcement email test failed!")
            return False
        
    except Exception as e:
        print(f"[ERROR] Announcement email test failed: {str(e)}")
        import traceback
        print(f"[ERROR] Full traceback: {traceback.format_exc()}")
        return False

def test_assignment_email():
    """Test assignment email notification."""
    print("\n" + "="*60)
    print("ASSIGNMENT EMAIL TEST")
    print("="*60)
    
    try:
        # Get admin user for testing
        admin_user = User.objects.filter(is_staff=True, email__isnull=False).exclude(email='').first()
        
        if not admin_user:
            print("[ERROR] No admin user with email found for testing")
            return False
        
        # Create a test forgatas (don't save to database)
        test_forgatas = Forgatas(
            name="🧪 Test Forgatas - Email Debug",
            description="This is a test forgatas created for email debugging purposes. This forgatas is not saved to the database.",
            date=date.today() + timedelta(days=1),
            timeFrom=time(14, 0),
            timeTo=time(16, 0),
            forgTipus="teszt"
        )
        
        print(f"[DEBUG] Testing assignment email with user: {admin_user.username} ({admin_user.email})")
        
        # Import and test the assignment email function
        from backend.api_modules.authentication import send_assignment_change_notification_email
        
        # Test both added and removed users
        success = send_assignment_change_notification_email(
            test_forgatas, 
            [admin_user],  # added users
            []  # removed users (empty for this test)
        )
        
        if success:
            print(f"[SUCCESS] Assignment email test completed successfully!")
            return True
        else:
            print(f"[ERROR] Assignment email test failed!")
            return False
        
    except Exception as e:
        print(f"[ERROR] Assignment email test failed: {str(e)}")
        import traceback
        print(f"[ERROR] Full traceback: {traceback.format_exc()}")
        return False

def main():
    """Run all email debug tests."""
    print("FTV EMAIL SYSTEM DEBUGGING")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 80)
    
    # Debug configuration
    debug_email_settings()
    
    # Test basic email
    basic_success = test_basic_email()
    
    # Test announcement email
    announcement_success = test_announcement_email()
    
    # Test assignment email
    assignment_success = test_assignment_email()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Basic Email Test: {'✅ PASSED' if basic_success else '❌ FAILED'}")
    print(f"Announcement Email Test: {'✅ PASSED' if announcement_success else '❌ FAILED'}")
    print(f"Assignment Email Test: {'✅ PASSED' if assignment_success else '❌ FAILED'}")
    
    if all([basic_success, announcement_success, assignment_success]):
        print("\n🎉 All email tests passed! Email system is working correctly.")
    else:
        print("\n⚠️  Some email tests failed. Check the debug output above for details.")
        print("\nCommon issues:")
        print("- Check your local_settings.py for correct SMTP configuration")
        print("- Verify EMAIL_HOST_USER and EMAIL_HOST_PASSWORD are set correctly")
        print("- Make sure EMAIL_USE_TLS=True for Gmail SMTP")
        print("- Check that DEFAULT_FROM_EMAIL is set to a valid email address")
        print("- Verify the admin user has a valid email address")

if __name__ == "__main__":
    main()
