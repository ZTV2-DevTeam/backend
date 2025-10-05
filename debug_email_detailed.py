#!/usr/bin/env python
"""
Debug Email Configuration and Test Email Sending

This script helps debug email configuration issues and tests email sending functionality.
It provides detailed diagnostic information and tests basic email functionality.
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
from datetime import datetime

def debug_email_configuration():
    """Debug and display email configuration."""
    print("=" * 80)
    print("EMAIL CONFIGURATION DEBUG")
    print("=" * 80)
    
    # Check all email-related settings
    email_settings = [
        'EMAIL_BACKEND',
        'EMAIL_HOST',
        'EMAIL_PORT',
        'EMAIL_USE_TLS',
        'EMAIL_USE_SSL',
        'EMAIL_HOST_USER',
        'EMAIL_HOST_PASSWORD',
        'DEFAULT_FROM_EMAIL'
    ]
    
    for setting in email_settings:
        value = getattr(settings, setting, 'NOT SET')
        if setting == 'EMAIL_HOST_PASSWORD':
            # Don't show the actual password
            display_value = 'SET' if value and value != 'NOT SET' else 'NOT SET'
            print(f"[CONFIG] {setting}: {display_value}")
        else:
            print(f"[CONFIG] {setting}: {value}")
    
    print("\n[CONFIG] Additional email settings:")
    print(f"[CONFIG] EMAIL_TIMEOUT: {getattr(settings, 'EMAIL_TIMEOUT', 'NOT SET')}")
    print(f"[CONFIG] EMAIL_SSL_CERTFILE: {getattr(settings, 'EMAIL_SSL_CERTFILE', 'NOT SET')}")
    print(f"[CONFIG] EMAIL_SSL_KEYFILE: {getattr(settings, 'EMAIL_SSL_KEYFILE', 'NOT SET')}")
    
    # Validate configuration
    print("\n[VALIDATION] Configuration validation:")
    
    if not getattr(settings, 'EMAIL_BACKEND', None):
        print("[ERROR] EMAIL_BACKEND not set!")
    elif settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend':
        print("[WARNING] Using console backend - emails will be printed to console only")
    elif settings.EMAIL_BACKEND == 'django.core.mail.backends.dummy.EmailBackend':
        print("[WARNING] Using dummy backend - emails will be discarded")
    elif settings.EMAIL_BACKEND == 'django.core.mail.backends.smtp.EmailBackend':
        print("[INFO] Using SMTP backend - emails will be sent via SMTP")
    
    if not getattr(settings, 'EMAIL_HOST', None):
        print("[ERROR] EMAIL_HOST not set!")
    
    if not getattr(settings, 'EMAIL_HOST_USER', None):
        print("[ERROR] EMAIL_HOST_USER not set!")
    
    if not getattr(settings, 'EMAIL_HOST_PASSWORD', None):
        print("[ERROR] EMAIL_HOST_PASSWORD not set!")
    
    if not getattr(settings, 'DEFAULT_FROM_EMAIL', None):
        print("[ERROR] DEFAULT_FROM_EMAIL not set!")
    
    # Gmail-specific checks
    if getattr(settings, 'EMAIL_HOST', '') == 'smtp.gmail.com':
        print("\n[GMAIL] Gmail-specific configuration:")
        if getattr(settings, 'EMAIL_PORT', None) == 587:
            print("[GMAIL] ✅ Port 587 is correct for Gmail with TLS")
        elif getattr(settings, 'EMAIL_PORT', None) == 465:
            print("[GMAIL] ⚠️ Port 465 requires EMAIL_USE_SSL=True (not EMAIL_USE_TLS)")
        else:
            print(f"[GMAIL] ❌ Port {getattr(settings, 'EMAIL_PORT', 'NOT SET')} may not work with Gmail")
        
        if getattr(settings, 'EMAIL_USE_TLS', False):
            print("[GMAIL] ✅ TLS is enabled")
        else:
            print("[GMAIL] ❌ TLS should be enabled for Gmail")
        
        print("[GMAIL] 📝 Remember to use an App Password, not your regular password!")
        print("[GMAIL] 📝 Generate App Password at: https://myaccount.google.com/apppasswords")

def test_smtp_connection():
    """Test SMTP connection without sending email."""
    print("\n" + "=" * 80)
    print("SMTP CONNECTION TEST")
    print("=" * 80)
    
    try:
        from django.core.mail import get_connection
        
        print("[SMTP] Testing SMTP connection...")
        
        connection = get_connection(
            backend=settings.EMAIL_BACKEND,
            host=getattr(settings, 'EMAIL_HOST', None),
            port=getattr(settings, 'EMAIL_PORT', None),
            username=getattr(settings, 'EMAIL_HOST_USER', None),
            password=getattr(settings, 'EMAIL_HOST_PASSWORD', None),
            use_tls=getattr(settings, 'EMAIL_USE_TLS', False),
            use_ssl=getattr(settings, 'EMAIL_USE_SSL', False),
        )
        
        print("[SMTP] Opening connection...")
        connection.open()
        print("[SMTP] ✅ Connection opened successfully!")
        
        print("[SMTP] Closing connection...")
        connection.close()
        print("[SMTP] ✅ Connection closed successfully!")
        
        return True
        
    except Exception as e:
        print(f"[SMTP] ❌ Connection failed: {str(e)}")
        print(f"[SMTP] Error type: {type(e).__name__}")
        
        # Specific error diagnostics
        error_str = str(e).lower()
        if "connection refused" in error_str:
            print("[SMTP] 🔧 DIAGNOSIS: SMTP server refused connection")
            print("[SMTP] - Check EMAIL_HOST and EMAIL_PORT")
            print("[SMTP] - Verify the SMTP server is running")
            print("[SMTP] - Check firewall settings")
        elif "authentication failed" in error_str or "invalid credentials" in error_str:
            print("[SMTP] 🔧 DIAGNOSIS: Authentication failed")
            print("[SMTP] - Check EMAIL_HOST_USER and EMAIL_HOST_PASSWORD")
            print("[SMTP] - For Gmail, use App Password instead of regular password")
        elif "tls" in error_str or "ssl" in error_str:
            print("[SMTP] 🔧 DIAGNOSIS: TLS/SSL issue")
            print("[SMTP] - Check EMAIL_USE_TLS and EMAIL_USE_SSL settings")
            print("[SMTP] - Verify SMTP server supports the selected encryption")
        elif "timeout" in error_str:
            print("[SMTP] 🔧 DIAGNOSIS: Connection timeout")
            print("[SMTP] - Check network connectivity")
            print("[SMTP] - Try a different EMAIL_PORT")
        
        return False

def test_basic_email():
    """Test sending a basic email."""
    print("\n" + "=" * 80)
    print("BASIC EMAIL TEST")
    print("=" * 80)
    
    # Get test recipient
    test_email = input("Enter test email address (or press Enter to skip): ").strip()
    if not test_email:
        print("[EMAIL] No test email provided, skipping basic email test")
        return False
    
    print(f"[EMAIL] Testing basic email to: {test_email}")
    
    subject = "FTV Email Test - Basic Functionality"
    message = f"""
Hello!

This is a test email from the FTV system.

Test details:
- Timestamp: {datetime.now().isoformat()}
- From: {settings.DEFAULT_FROM_EMAIL}
- Backend: {settings.EMAIL_BACKEND}

If you receive this email, the basic email configuration is working.

Best regards,
FTV System
    """
    
    try:
        print("[EMAIL] Sending test email...")
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[test_email],
            fail_silently=False,
        )
        
        print("[EMAIL] ✅ Test email sent successfully!")
        print("[EMAIL] Please check the recipient's inbox (and spam folder)")
        return True
        
    except Exception as e:
        print(f"[EMAIL] ❌ Failed to send test email: {str(e)}")
        print(f"[EMAIL] Error type: {type(e).__name__}")
        return False

def test_html_email():
    """Test sending an HTML email using the new template system."""
    print("\n" + "=" * 80)
    print("HTML EMAIL TEMPLATE TEST")
    print("=" * 80)
    
    # Get test recipient
    test_email = input("Enter test email address for HTML test (or press Enter to skip): ").strip()
    if not test_email:
        print("[HTML] No test email provided, skipping HTML email test")
        return False
    
    print(f"[HTML] Testing HTML email to: {test_email}")
    
    try:
        from backend.email_templates import get_base_email_template
        
        # Create test content
        content = """
        <div class="content-section">
            <h2>🧪 HTML Email Test</h2>
            <p>This is a test of the new FTV HTML email template system.</p>
            <p>If you can see this formatted email with the FTV branding, the HTML templates are working correctly!</p>
        </div>
        
        <div class="info-box">
            <h3>Test Details</h3>
            <div class="info-item"><strong>Timestamp:</strong> {timestamp}</div>
            <div class="info-item"><strong>Template:</strong> Base FTV Email Template</div>
            <div class="info-item"><strong>Status:</strong> HTML Email Support Active</div>
        </div>
        """.format(timestamp=datetime.now().isoformat())
        
        # Generate HTML email
        html_message = get_base_email_template(
            title="HTML Email Test",
            content=content,
            button_text="Visit FTV System",
            button_url="https://ftv.szlg.info"
        )
        
        # Plain text version
        plain_message = f"""
HTML Email Test

This is a test of the new FTV HTML email template system.

Test Details:
- Timestamp: {datetime.now().isoformat()}
- Template: Base FTV Email Template
- Status: HTML Email Support Active

If you receive this email, the HTML email templates are working correctly!

Visit: https://ftv.szlg.info
        """
        
        print("[HTML] Sending HTML email...")
        
        send_mail(
            subject="FTV HTML Email Test",
            message=plain_message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[test_email],
            fail_silently=False,
        )
        
        print("[HTML] ✅ HTML test email sent successfully!")
        print("[HTML] Please check the recipient's inbox for the formatted email")
        return True
        
    except Exception as e:
        print(f"[HTML] ❌ Failed to send HTML test email: {str(e)}")
        print(f"[HTML] Error type: {type(e).__name__}")
        return False

def main():
    """Run all email debugging tests."""
    print("🔍 FTV Email Debug and Test Tool")
    print("This tool will help diagnose email configuration issues.\n")
    
    # Debug configuration
    debug_email_configuration()
    
    # Test SMTP connection
    smtp_ok = test_smtp_connection()
    
    if not smtp_ok:
        print("\n❌ SMTP connection failed. Please fix configuration issues before testing emails.")
        return False
    
    # Test basic email
    basic_ok = test_basic_email()
    
    # Test HTML email
    html_ok = test_html_email()
    
    # Summary
    print("\n" + "=" * 80)
    print("EMAIL TESTING SUMMARY")
    print("=" * 80)
    print(f"SMTP Connection: {'✅ PASS' if smtp_ok else '❌ FAIL'}")
    print(f"Basic Email: {'✅ PASS' if basic_ok else '⏭️ SKIPPED'}")
    print(f"HTML Email: {'✅ PASS' if html_ok else '⏭️ SKIPPED'}")
    
    if smtp_ok and (basic_ok or html_ok):
        print("\n🎉 Email system is working!")
        print("You can now send emails from the FTV system.")
    else:
        print("\n❌ Email system has issues.")
        print("Please review the error messages above and fix the configuration.")
    
    return smtp_ok and (basic_ok or html_ok)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)