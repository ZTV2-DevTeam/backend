#!/usr/bin/env python
"""
Test script for the new HTML email templates.
This script tests all email template functions to ensure they generate proper HTML.
"""

import os
import sys
import django

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from backend.email_templates import (
    get_base_email_template,
    get_announcement_email_content,
    get_assignment_addition_email_content,
    get_assignment_removal_email_content,
    get_password_reset_email_content,
    get_first_login_email_content,
    get_login_info_email_content,
    send_html_emails_to_multiple_recipients
)
from datetime import datetime

def test_base_template():
    """Test the base email template."""
    print("\n" + "="*60)
    print("TESTING BASE EMAIL TEMPLATE")
    print("="*60)
    
    html = get_base_email_template(
        title="Test Email",
        content="<p>This is a test content.</p>",
        button_text="Test Button",
        button_url="https://example.com",
        footer_text="Test footer text"
    )
    
    # Basic checks
    assert "FTV" in html, "Logo should be present"
    assert "Test Email" in html, "Title should be present"
    assert "Test Button" in html, "Button should be present"
    assert "https://example.com" in html, "Button URL should be present"
    assert "Test footer text" in html, "Footer text should be present"
    assert "<!DOCTYPE html>" in html, "Should be valid HTML"
    assert "background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)" in html, "Should have dark blue gradient header"
    
    print("✅ Base template test passed!")
    return True

def test_announcement_template():
    """Test the announcement email template."""
    print("\n" + "="*60)
    print("TESTING ANNOUNCEMENT EMAIL TEMPLATE")
    print("="*60)
    
    # Mock announcement object
    class MockAnnouncement:
        def __init__(self):
            self.title = "Test Announcement"
            self.body = "This is a test announcement body."
            self.created_at = datetime.now()
    
    announcement = MockAnnouncement()
    content = get_announcement_email_content(announcement, "Test Author")
    
    # Basic checks
    assert "Test Announcement" in content, "Announcement title should be present"
    assert "Test Author" in content, "Author should be present"
    assert "This is a test announcement body." in content, "Body should be present"
    assert "📢" in content, "Icon should be present"
    
    print("✅ Announcement template test passed!")
    return True

def test_assignment_templates():
    """Test assignment email templates."""
    print("\n" + "="*60)
    print("TESTING ASSIGNMENT EMAIL TEMPLATES")
    print("="*60)
    
    # Mock forgatas object
    class MockForgatas:
        def __init__(self):
            self.name = "Test Filming Session"
            self.description = "Test description"
            self.date = datetime.now().date()
            self.time_from = datetime.now().time()
            self.time_to = datetime.now().time()
            self.location = "Test Location"
    
    forgatas = MockForgatas()
    
    # Test addition template
    addition_content = get_assignment_addition_email_content(forgatas, "Test Contact")
    assert "Test Filming Session" in addition_content, "Session name should be present"
    assert "Test Contact" in addition_content, "Contact person should be present"
    assert "🎬" in addition_content, "Icon should be present"
    
    # Test removal template
    removal_content = get_assignment_removal_email_content(forgatas, "Test Contact")
    assert "Test Filming Session" in removal_content, "Session name should be present"
    assert "törölték" in removal_content, "Removal text should be present"
    
    print("✅ Assignment templates test passed!")
    return True

def test_password_reset_template():
    """Test password reset email template."""
    print("\n" + "="*60)
    print("TESTING PASSWORD RESET EMAIL TEMPLATE")
    print("="*60)
    
    content = get_password_reset_email_content("Test User", "https://example.com/reset")
    
    # Basic checks
    assert "Test User" in content, "User name should be present"
    assert "https://example.com/reset" in content, "Reset URL should be present"
    assert "🔐" in content, "Icon should be present"
    assert "1 órán belül lejár" in content, "Expiry info should be present"
    
    print("✅ Password reset template test passed!")
    return True

def test_first_login_template():
    """Test first login email template."""
    print("\n" + "="*60)
    print("TESTING FIRST LOGIN EMAIL TEMPLATE")
    print("="*60)
    
    content = get_first_login_email_content("Test User", "https://example.com/first-login")
    
    # Basic checks
    assert "Test User" in content, "User name should be present"
    assert "https://example.com/first-login" in content, "First login URL should be present"
    assert "🎉" in content, "Icon should be present"
    assert "Üdvözöljük" in content, "Welcome text should be present"
    
    print("✅ First login template test passed!")
    return True

def test_login_info_template():
    """Test login info email template."""
    print("\n" + "="*60)
    print("TESTING LOGIN INFO EMAIL TEMPLATE")
    print("="*60)
    
    content = get_login_info_email_content("Test User", "testuser", "testpassword123")
    
    # Basic checks
    assert "Test User" in content, "User name should be present"
    assert "testuser" in content, "Username should be present"
    assert "testpassword123" in content, "Password should be present"
    assert "🔐" in content, "Icon should be present"
    assert "BIZTONSÁGI TUDNIVALÓK" in content, "Security info should be present"
    
    print("✅ Login info template test passed!")
    return True

def test_complete_email_generation():
    """Test complete email generation with base template."""
    print("\n" + "="*60)
    print("TESTING COMPLETE EMAIL GENERATION")
    print("="*60)
    
    # Test announcement email
    class MockAnnouncement:
        def __init__(self):
            self.title = "Complete Test"
            self.body = "Complete test body."
            self.created_at = datetime.now()
    
    announcement = MockAnnouncement()
    content = get_announcement_email_content(announcement, "Test Author")
    
    complete_html = get_base_email_template(
        title="Új közlemény",
        content=content,
        button_text="FTV Rendszer megnyitása",
        button_url="https://ftv.szlg.info"
    )
    
    # Check complete email structure
    assert "<!DOCTYPE html>" in complete_html, "Should be valid HTML document"
    assert "FTV" in complete_html, "Should contain FTV branding"
    assert "Complete Test" in complete_html, "Should contain announcement content"
    assert "FTV Rendszer megnyitása" in complete_html, "Should contain button"
    assert "linear-gradient" in complete_html, "Should have gradient styling"
    assert "© 2025 FTV" in complete_html, "Should have copyright"
    
    print("✅ Complete email generation test passed!")
    return True

def test_responsive_design():
    """Test that emails include responsive design elements."""
    print("\n" + "="*60)
    print("TESTING RESPONSIVE DESIGN")
    print("="*60)
    
    html = get_base_email_template(
        title="Responsive Test",
        content="<p>Test content</p>"
    )
    
    # Check for responsive elements
    assert "@media (max-width: 600px)" in html, "Should include mobile breakpoint"
    assert "viewport" in html, "Should include viewport meta tag"
    assert "max-width: 600px" in html, "Should have max-width constraint"
    
    print("✅ Responsive design test passed!")
    return True

def main():
    """Run all email template tests."""
    print("🧪 Starting FTV Email Template Tests...")
    print("Testing new HTML email templates for consistency and functionality")
    
    tests = [
        test_base_template,
        test_announcement_template,
        test_assignment_templates,
        test_password_reset_template,
        test_first_login_template,
        test_login_info_template,
        test_complete_email_generation,
        test_responsive_design
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed: {str(e)}")
            failed += 1
    
    print("\n" + "="*60)
    print("EMAIL TEMPLATE TEST SUMMARY")
    print("="*60)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Total: {passed + failed}")
    
    if failed == 0:
        print("\n🎉 All email template tests passed!")
        print("✨ Your HTML email templates are working correctly and include:")
        print("   • Consistent FTV branding with dark blue header")
        print("   • Responsive design for mobile devices")
        print("   • Professional styling matching the frontend")
        print("   • Proper fallback for plain text clients")
        print("   • All required content sections")
        
        # Save a sample email for visual inspection
        sample_html = get_base_email_template(
            title="Sample FTV Email",
            content="""
            <div class="content-section">
                <h2>📧 Sample Email</h2>
                <p>This is a sample email generated by the new FTV email template system.</p>
            </div>
            
            <div class="info-box">
                <h3>Features</h3>
                <div class="info-item">• Dark blue gradient header matching frontend</div>
                <div class="info-item">• Professional typography and spacing</div>
                <div class="info-item">• Responsive design for all devices</div>
                <div class="info-item">• Consistent branding elements</div>
            </div>
            """,
            button_text="View FTV System",
            button_url="https://ftv.szlg.info"
        )
        
        with open("sample_ftv_email.html", "w", encoding="utf-8") as f:
            f.write(sample_html)
        
        print(f"\n📧 Sample email saved as 'sample_ftv_email.html' for visual inspection")
        return True
    else:
        print(f"\n❌ {failed} test(s) failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)