#!/usr/bin/env python
"""
Test script for email notifications in the FTV system.

This script tests the email notification functionality for:
1. Announcement creation and updates
2. Assignment (beosztás) changes

Run this script to verify email notifications are working properly.
"""

import os
import sys
import django
from datetime import datetime, date, time

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth.models import User
from api.models import Announcement, Forgatas, Beosztas, SzerepkorRelaciok, Szerepkor, Profile
from backend.api_modules.authentication import send_announcement_notification_email, send_assignment_change_notification_email

def test_announcement_email():
    """Test announcement email notification."""
    print("=" * 60)
    print("TESTING ANNOUNCEMENT EMAIL NOTIFICATION")
    print("=" * 60)
    
    try:
        # Find or create test users
        test_users = User.objects.filter(is_active=True)[:3]
        
        if len(test_users) < 2:
            print("❌ Not enough active users for testing. Need at least 2 users.")
            return False
        
        # Create a test announcement
        author = test_users[0]
        recipients = test_users[1:3]
        
        announcement = Announcement.objects.create(
            title="🧪 Test Email Notification - Közlemény",
            body="Ez egy teszt közlemény az email értesítő rendszer tesztelésére.\n\nHa ezt az emailt megkapja, akkor az értesítő rendszer működik!",
            author=author
        )
        
        # Add recipients
        announcement.cimzettek.set(recipients)
        
        print(f"✅ Created test announcement: {announcement.title}")
        print(f"📧 Author: {author.get_full_name()} ({author.email})")
        print(f"👥 Recipients: {[f'{u.get_full_name()} ({u.email})' for u in recipients]}")
        
        # Send email notification
        success = send_announcement_notification_email(announcement, list(recipients))
        
        if success:
            print("✅ Email notification sent successfully!")
        else:
            print("❌ Email notification failed!")
        
        # Clean up
        announcement.delete()
        print("🧹 Cleaned up test announcement")
        
        return success
        
    except Exception as e:
        print(f"❌ Error testing announcement email: {str(e)}")
        return False

def test_assignment_email():
    """Test assignment change email notification."""
    print("\n" + "=" * 60)
    print("TESTING ASSIGNMENT CHANGE EMAIL NOTIFICATION")
    print("=" * 60)
    
    try:
        # Find test users
        test_users = User.objects.filter(is_active=True)[:4]
        
        if len(test_users) < 3:
            print("❌ Not enough active users for testing. Need at least 3 users.")
            return False
        
        # Find or create a test forgatas
        forgatas = Forgatas.objects.filter(date__gte=date.today()).first()
        
        if not forgatas:
            print("❌ No future forgatas found for testing.")
            return False
        
        added_users = test_users[1:3]
        removed_users = [test_users[3]] if len(test_users) > 3 else []
        
        print(f"✅ Using test forgatas: {forgatas.name}")
        print(f"📅 Date: {forgatas.date} {forgatas.timeFrom}-{forgatas.timeTo}")
        print(f"➕ Added users: {[f'{u.get_full_name()} ({u.email})' for u in added_users]}")
        print(f"➖ Removed users: {[f'{u.get_full_name()} ({u.email})' for u in removed_users]}")
        
        # Send assignment change notification
        success = send_assignment_change_notification_email(
            forgatas, 
            added_users, 
            removed_users
        )
        
        if success:
            print("✅ Assignment change email notifications sent successfully!")
        else:
            print("❌ Assignment change email notifications failed!")
        
        return success
        
    except Exception as e:
        print(f"❌ Error testing assignment email: {str(e)}")
        return False

def test_email_settings():
    """Test email configuration."""
    print("\n" + "=" * 60)
    print("TESTING EMAIL CONFIGURATION")
    print("=" * 60)
    
    try:
        from django.conf import settings
        from django.core.mail import get_connection
        
        print(f"📧 EMAIL_BACKEND: {getattr(settings, 'EMAIL_BACKEND', 'NOT SET')}")
        print(f"🌐 EMAIL_HOST: {getattr(settings, 'EMAIL_HOST', 'NOT SET')}")
        print(f"🔌 EMAIL_PORT: {getattr(settings, 'EMAIL_PORT', 'NOT SET')}")
        print(f"🔒 EMAIL_USE_TLS: {getattr(settings, 'EMAIL_USE_TLS', 'NOT SET')}")
        print(f"👤 EMAIL_HOST_USER: {getattr(settings, 'EMAIL_HOST_USER', 'NOT SET')}")
        print(f"🔑 EMAIL_HOST_PASSWORD: {'***' if getattr(settings, 'EMAIL_HOST_PASSWORD', None) else 'NOT SET'}")
        print(f"📮 DEFAULT_FROM_EMAIL: {getattr(settings, 'DEFAULT_FROM_EMAIL', 'NOT SET')}")
        
        # Test connection
        try:
            connection = get_connection()
            connection.open()
            connection.close()
            print("✅ Email connection test successful!")
            return True
        except Exception as conn_error:
            print(f"❌ Email connection test failed: {str(conn_error)}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing email configuration: {str(e)}")
        return False

def main():
    """Run all email notification tests."""
    print("🧪 FTV EMAIL NOTIFICATION SYSTEM TEST")
    print("=" * 60)
    print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test email configuration first
    config_ok = test_email_settings()
    
    if not config_ok:
        print("\n❌ Email configuration issues detected. Please check your email settings.")
        return
    
    # Test announcement emails
    announcement_ok = test_announcement_email()
    
    # Test assignment emails
    assignment_ok = test_assignment_email()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"📧 Email Configuration: {'✅ OK' if config_ok else '❌ FAILED'}")
    print(f"📢 Announcement Emails: {'✅ OK' if announcement_ok else '❌ FAILED'}")
    print(f"🎬 Assignment Emails: {'✅ OK' if assignment_ok else '❌ FAILED'}")
    
    if all([config_ok, announcement_ok, assignment_ok]):
        print("\n🎉 ALL TESTS PASSED! Email notification system is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Please check the error messages above.")
    
    print(f"⏰ Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
