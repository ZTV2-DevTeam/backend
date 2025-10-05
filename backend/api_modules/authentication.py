"""
FTV Authentication and Password Management API Module

This module provides comprehensive authentication and password management functionality,
including first-time login, password reset, and password validation endpoints.

Public API Overview:
==================

The authentication API provides secure access to the FTV system through JWT tokens
and specialized password management workflows.

Base URL: /api/

First Login Endpoints (No Authentication Required):
- POST /first-login/request-token      - Request first login token via email
- GET  /first-login/verify-token/{token} - Verify first login token
- POST /first-login/set-password       - Set initial password using token

Password Reset Endpoints (No Authentication Required):  
- POST /forgot-password                - Initiate password reset process
- GET  /verify-reset-token/{token}     - Verify password reset token
- POST /reset-password                 - Complete password reset

Password Validation Endpoints (No Authentication Required):
- GET  /password-validation/rules      - Get password validation requirements
- POST /password-validation/check      - Validate password against rules

Authentication Flow (First Login):
================================

1. Admin creates user account without password
2. User requests first-time login token via email
3. User receives email with secure JWT link (token is signed with secret key)
4. User verifies token validity (optional frontend check)
5. User sets password using token (JWT contains all necessary info, no DB lookup needed)

Authentication Flow (Password Reset):
===================================

1. User requests password reset with email address
2. If email exists, user receives password reset email with JWT token
3. User verifies token validity (optional frontend check)  
4. User sets new password using token (JWT contains all necessary info, no DB lookup needed)

Security Features:
=================

- Stateless JWT tokens with expiration (1 hour for reset, 30 days for first login)
- No database storage required - tokens are self-contained and signed with secret key
- Only the server can decode/verify tokens using the secret key
- Email verification required for both flows
- Password strength validation using Django's built-in validators
- Rate limiting protection (future enhancement)
- Cryptographically secure JWT token generation and verification

Error Handling:
==============

All endpoints return consistent error responses:
- 200: Success
- 400: Bad request (validation errors, invalid tokens)
- 404: User not found (masked for security in some cases)
- 500: Server error

For detailed examples and schemas, see the API documentation.
"""

from ninja import Schema, Form, Field
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password, get_password_validators
from django.core.exceptions import ValidationError
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
import jwt
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from .auth import JWTAuth, ErrorSchema
from api.models import Profile

# ============================================================================
# Request/Response Schemas
# ============================================================================

class FirstLoginRequestSchema(Schema):
    """Request schema for first login token request."""
    email: str

class FirstLoginRequestResponse(Schema):
    """Response schema for first login token request."""
    message: str

class FirstLoginVerifyResponse(Schema):
    """Response schema for first login token verification."""
    valid: bool
    error: Optional[str] = None
    user_info: Optional[Dict[str, Any]] = None

class FirstLoginSetPasswordRequest(Schema):
    """Request schema for setting password during first login."""
    token: str
    password: str
    confirm_password: str = Field(alias="confirmPassword")

class FirstLoginSetPasswordResponse(Schema):
    """Response schema for first login password setting."""
    message: str
    user: Optional[Dict[str, Any]] = None

class ForgotPasswordRequest(Schema):
    """Request schema for password reset initiation."""
    email: str

class ForgotPasswordResponse(Schema):
    """Response schema for password reset request."""
    message: str

class ResetPasswordRequest(Schema):
    """Request schema for password reset completion."""
    token: str
    password: str
    confirm_password: str = Field(alias="confirmPassword")

class ResetPasswordResponse(Schema):
    """Response schema for password reset completion."""
    message: str

class VerifyTokenResponse(Schema):
    """Response schema for token verification."""
    valid: bool
    error: Optional[str] = None

class PasswordValidationRulesResponse(Schema):
    """Response schema for password validation rules."""
    rules: List[Dict[str, Any]]
    minimum_length: int
    help_text: str

class PasswordValidationCheckRequest(Schema):
    """Request schema for password validation check."""
    password: str
    username: Optional[str] = None
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class PasswordValidationCheckResponse(Schema):
    """Response schema for password validation check."""
    valid: bool
    errors: List[str]

class ChangePasswordRequest(Schema):
    """Request schema for changing password."""
    old_password: str
    new_password: str
    confirm_new_password: str = Field(alias="confirmNewPassword")

class ChangePasswordResponse(Schema):
    """Response schema for password change."""
    message: str

# ============================================================================
# Token Generation and Verification Utilities
# ============================================================================

def generate_first_login_token(user_id: int) -> str:
    """
    Generate stateless JWT token for first-time login.
    
    The token is self-contained and signed with the secret key.
    No database storage is required - all necessary information is encoded in the JWT.
    
    Args:
        user_id: ID of the user
        
    Returns:
        JWT token string valid for 30 days (signed with secret key)
    """
    payload = {
        "user_id": user_id,
        "purpose": "first_login",
        "exp": datetime.utcnow() + timedelta(days=30),  # 30 days validity
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

def verify_first_login_token(token: str) -> dict:
    """
    Verify stateless first-time login token.
    
    Decodes and validates the JWT token using the secret key.
    No database lookup for token validation - everything is in the JWT payload.
    
    Args:
        token: JWT token string
        
    Returns:
        Dictionary with validation result and user information
    """
    try:
        # Decode and verify JWT token with secret key
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        
        if payload.get("purpose") != "first_login":
            return {"valid": False, "error": "Invalid token purpose"}
        
        user_id = payload.get("user_id")
        if not user_id:
            return {"valid": False, "error": "Invalid token payload"}
        
        try:
            # Only database lookup is for user info (not token validation)
            user = User.objects.get(id=user_id)
            
            if not user.is_active:
                return {"valid": False, "error": "User account is not active"}
            
            # Get profile for additional info
            try:
                profile = Profile.objects.get(user=user)
            except Profile.DoesNotExist:
                profile = None
                
            return {"valid": True, "user": user, "profile": profile}
        except User.DoesNotExist:
            return {"valid": False, "error": "User not found"}
            
    except jwt.ExpiredSignatureError:
        return {"valid": False, "error": "Token has expired"}
    except jwt.InvalidTokenError:
        return {"valid": False, "error": "Invalid token"}

def generate_password_reset_token(user_id: int) -> str:
    """
    Generate stateless JWT token for password reset.
    
    The token is self-contained and signed with the secret key.
    No database storage is required - all necessary information is encoded in the JWT.
    
    Args:
        user_id: ID of the user
        
    Returns:
        JWT token string valid for 1 hour (signed with secret key)
    """
    payload = {
        "user_id": user_id,
        "purpose": "password_reset",
        "exp": datetime.utcnow() + timedelta(seconds=settings.PASSWORD_RESET_TIMEOUT),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

def verify_password_reset_token(token: str) -> dict:
    """
    Verify stateless password reset token.
    
    Decodes and validates the JWT token using the secret key.
    No database lookup for token validation - everything is in the JWT payload.
    
    Args:
        token: JWT token string
        
    Returns:
        Dictionary with validation result and user information
    """
    try:
        # Decode and verify JWT token with secret key
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        
        if payload.get("purpose") != "password_reset":
            return {"valid": False, "error": "Invalid token purpose"}
        
        user_id = payload.get("user_id")
        if not user_id:
            return {"valid": False, "error": "Missing user ID"}
        
        try:
            # Only database lookup is for user info (not token validation)
            user = User.objects.get(id=user_id)
            if not user.is_active:
                return {"valid": False, "error": "User is not active"}
        except User.DoesNotExist:
            return {"valid": False, "error": "User does not exist"}
        
        return {"valid": True, "user_id": user_id, "user": user}
        
    except jwt.ExpiredSignatureError:
        return {"valid": False, "error": "Token has expired"}
    except jwt.InvalidTokenError:
        return {"valid": False, "error": "Invalid token"}

# ============================================================================
# Email Utilities
# ============================================================================

def send_first_login_email(user: User, token: str) -> bool:
    """
    Send first-time login email to user.
    
    Args:
        user: User instance
        token: First login token (JWT - self-contained, no DB storage needed)
        
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        print(f"[DEBUG] Starting email send process for user: {user.email}")
        
        # Get frontend URL from settings
        frontend_url = getattr(settings, 'FRONTEND_URL', 'https://ftv.szlg.info')
        print(f"[DEBUG] Frontend URL: {frontend_url}")
        
        # JWT token is already encoded and signed with secret key
        login_url = f"{frontend_url}/first-login?token={token}"
        print(f"[DEBUG] Generated login URL: {login_url[:100]}...")  # Truncate for security
        
        subject = "FTV - Első bejelentkezés és jelszó beállítás"
        print(f"[DEBUG] Email subject: {subject}")
        print(f"[DEBUG] Email recipient: {user.email}")
        print(f"[DEBUG] DEFAULT_FROM_EMAIL: {getattr(settings, 'DEFAULT_FROM_EMAIL', 'NOT SET')}")
        
        # Import email templates
        from backend.email_templates import (
            get_base_email_template, 
            get_first_login_email_content
        )
        
        # Get user name
        user_name = user.get_full_name() if user.get_full_name() else user.username
        
        # Generate email content using the new template system
        content = get_first_login_email_content(user_name, login_url)
        
        # Create complete HTML email
        html_message = get_base_email_template(
            title="Üdvözöljük az FTV rendszerben!",
            content=content,
            button_text="Jelszó beállítása",
            button_url=login_url
        )
        
        # Create plain text version
        plain_message = f"""
Kedves {user_name}!

Üdvözöljük a FTV rendszerben! Fiókja létrehozásra került, és most beállíthatja jelszavát az első bejelentkezéshez.

A jelszó beállításához kattintson a következő linkre:
{login_url}

Fontos információk:
- Ez a link 30 napig érvényes
- A link biztonságosan kódolt (csak a szerver tudja dekódolni)
- A jelszó beállítása után már a szokásos bejelentkezési folyamatot használhatja

Ez egy automatikus email, kérjük ne válaszoljon rá.

© 2025 FTV. Minden jog fenntartva.
        """
        
        print(f"[DEBUG] About to send email using Django send_mail...")
        print(f"[DEBUG] Email settings check - EMAIL_BACKEND: {getattr(settings, 'EMAIL_BACKEND', 'NOT SET')}")
        print(f"[DEBUG] Email settings check - EMAIL_HOST: {getattr(settings, 'EMAIL_HOST', 'NOT SET')}")
        print(f"[DEBUG] Email settings check - EMAIL_PORT: {getattr(settings, 'EMAIL_PORT', 'NOT SET')}")
        print(f"[DEBUG] Email settings check - EMAIL_USE_TLS: {getattr(settings, 'EMAIL_USE_TLS', 'NOT SET')}")
        
        send_mail(
            subject=subject,
            message=plain_message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        print(f"[DEBUG] Email sent successfully to {user.email}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send first login email to {user.email}: {str(e)}")
        print(f"[ERROR] Exception type: {type(e).__name__}")
        import traceback
        print(f"[ERROR] Full traceback: {traceback.format_exc()}")
        return False

def send_password_reset_email(user: User, reset_token: str) -> bool:
    """
    Send password reset email to user.
    
    Args:
        user: User instance
        reset_token: Password reset token (JWT - self-contained, no DB storage needed)
        
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        # Get frontend URL from settings
        frontend_url = getattr(settings, 'FRONTEND_URL', 'https://ftv.szlg.info')
        # JWT token is already encoded and signed with secret key
        reset_url = f"{frontend_url}/elfelejtett_jelszo/{reset_token}"

        subject = "FTV - Jelszó visszaállítása"

        # Import email templates
        from backend.email_templates import (
            get_base_email_template, 
            get_password_reset_email_content
        )
        
        # Get user name
        user_name = user.get_full_name() if user.get_full_name() else user.username
        
        # Generate email content using the new template system
        content = get_password_reset_email_content(user_name, reset_url)
        
        # Create complete HTML email
        html_message = get_base_email_template(
            title="Jelszó visszaállítása",
            content=content,
            button_text="Jelszó visszaállítása",
            button_url=reset_url
        )
        
        # Create plain text version
        plain_message = f"""
Kedves {user_name}!

Jelszó visszaállítási kérést kaptunk az Ön fiókjához a FTV rendszerben.

Amennyiben Ön kérte a jelszó visszaállítást, kattintson a következő linkre:
{reset_url}

Fontos információk:
- Ez a link 1 órán belül lejár
- A link biztonságosan kódolt (csak a szerver tudja dekódolni)
- Ha nem Ön kérte a jelszó visszaállítást, hagyja figyelmen kívül ezt az emailt

Ez egy automatikus email, kérjük ne válaszoljon rá.

© 2025 FTV. Minden jog fenntartva.
        """
        
        send_mail(
            subject=subject,
            message=plain_message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Failed to send password reset email to {user.email}: {str(e)}")
        return False

# ============================================================================
# Notification Email Utilities
# ============================================================================

def send_announcement_notification_email(announcement, recipients_list: list) -> bool:
    """
    Send announcement notification email to multiple recipients.
    
    Args:
        announcement: Announcement model instance
        recipients_list: List of User objects to send email to
        
    Returns:
        True if all emails sent successfully, False otherwise
    """
    try:
        print(f"[DEBUG] ========== ANNOUNCEMENT EMAIL DEBUG ==========")
        print(f"[DEBUG] Starting announcement email send process")
        print(f"[DEBUG] Announcement: {announcement.title}")
        print(f"[DEBUG] Recipients count: {len(recipients_list)}")
        
        # Debug email settings
        print(f"[DEBUG] Email backend: {getattr(settings, 'EMAIL_BACKEND', 'Not set')}")
        print(f"[DEBUG] SMTP host: {getattr(settings, 'EMAIL_HOST', 'Not set')}")
        print(f"[DEBUG] SMTP port: {getattr(settings, 'EMAIL_PORT', 'Not set')}")
        print(f"[DEBUG] Use TLS: {getattr(settings, 'EMAIL_USE_TLS', 'Not set')}")
        print(f"[DEBUG] From email: {getattr(settings, 'DEFAULT_FROM_EMAIL', 'Not set')}")
        
        # Get frontend URL from settings
        frontend_url = getattr(settings, 'FRONTEND_URL', 'https://ftv.szlg.info')
        print(f"[DEBUG] Frontend URL: {frontend_url}")
        
        # Filter recipients with valid email addresses
        recipient_emails = []
        for user in recipients_list:
            print(f"[DEBUG] Checking user: {user.username} (ID: {user.id})")
            print(f"[DEBUG] - Email: {user.email}")
            print(f"[DEBUG] - Is active: {user.is_active}")
            if user.email and user.is_active:
                recipient_emails.append(user.email.strip())
                print(f"[DEBUG] - Added to recipient list")
            else:
                print(f"[DEBUG] - Skipped (no email or inactive)")
        
        if not recipient_emails:
            print("[DEBUG] No valid email addresses found")
            return True  # No emails to send, but not an error
        
        print(f"[DEBUG] Valid email addresses: {len(recipient_emails)}")
        print(f"[DEBUG] Email list: {recipient_emails}")
        
        subject = f"FTV - Új közlemény: {announcement.title}"
        print(f"[DEBUG] Email subject: {subject}")
        
        # Author info
        author_name = announcement.author.get_full_name() if announcement.author else "FTV Rendszer"
        print(f"[DEBUG] Author: {author_name}")
        
        # Import email templates
        from backend.email_templates import (
            get_base_email_template, 
            get_announcement_email_content,
            send_html_emails_to_multiple_recipients
        )
        
        # Generate email content using the new template system
        content = get_announcement_email_content(announcement, author_name)
        
        # Create complete HTML email
        html_message = get_base_email_template(
            title="Új közlemény",
            content=content,
            button_text="FTV Rendszer megnyitása",
            button_url=frontend_url
        )
        
        # Create plain text version
        plain_message = f"""
📢 Új közlemény érkezett az FTV rendszerben

Cím: {announcement.title}
Feladó: {author_name}
Dátum: {announcement.created_at.strftime('%Y. %m. %d. %H:%M')}

Tartalom:
{announcement.body}

A teljes közlemény megtekintéséhez látogassa meg a FTV rendszert:
{frontend_url}

Ez egy automatikus értesítés az FTV rendszerből.
© 2025 FTV. Minden jog fenntartva.
        """
        
        print(f"[DEBUG] About to send announcement emails to {len(recipient_emails)} recipients using HTML template")
        print(f"[DEBUG] Recipients: {recipient_emails}")
        print(f"[DEBUG] From email: {settings.DEFAULT_FROM_EMAIL}")
        
        # Send HTML emails to multiple recipients
        try:
            successful_count, failed_emails = send_html_emails_to_multiple_recipients(
                subject=subject,
                html_content=html_message,
                plain_content=plain_message,
                recipient_emails=recipient_emails,
                from_email=settings.DEFAULT_FROM_EMAIL
            )
            
            print(f"[DEBUG] HTML email sending completed")
            print(f"[SUCCESS] Announcement emails sent to {successful_count}/{len(recipient_emails)} recipients")
            
            if failed_emails:
                print(f"[WARNING] Failed to send emails to: {failed_emails}")
            
            success = successful_count > 0
                
        except Exception as send_error:
            print(f"[ERROR] HTML email sending failed: {str(send_error)}")
            import traceback
            print(f"[ERROR] Full traceback: {traceback.format_exc()}")
            success = False
        
        print(f"[DEBUG] ========== ANNOUNCEMENT EMAIL DEBUG END ==========")
        return success
        
    except Exception as e:
        print(f"[ERROR] Failed to send announcement email: {str(e)}")
        import traceback
        print(f"[ERROR] Full traceback: {traceback.format_exc()}")
        return False

def send_assignment_change_notification_email(forgatas, added_users: list, removed_users: list) -> bool:
    """
    Send notification email for assignment changes.
    
    Args:
        forgatas: Forgatas model instance
        added_users: List of User objects who were added to the assignment
        removed_users: List of User objects who were removed from the assignment
        
    Returns:
        True if all emails sent successfully, False otherwise
    """
    try:
        print(f"[DEBUG] ========== ASSIGNMENT EMAIL DEBUG ==========")
        print(f"[DEBUG] Starting assignment change email notification")
        print(f"[DEBUG] Forgatas: {forgatas.name}")
        print(f"[DEBUG] Added users: {len(added_users)}")
        print(f"[DEBUG] Removed users: {len(removed_users)}")
        
        # Debug email settings
        print(f"[DEBUG] Email backend: {getattr(settings, 'EMAIL_BACKEND', 'Not set')}")
        print(f"[DEBUG] SMTP host: {getattr(settings, 'EMAIL_HOST', 'Not set')}")
        print(f"[DEBUG] SMTP port: {getattr(settings, 'EMAIL_PORT', 'Not set')}")
        print(f"[DEBUG] Use TLS: {getattr(settings, 'EMAIL_USE_TLS', 'Not set')}")
        print(f"[DEBUG] From email: {getattr(settings, 'DEFAULT_FROM_EMAIL', 'Not set')}")
        
        # Get frontend URL from settings
        frontend_url = getattr(settings, 'FRONTEND_URL', 'https://ftv.szlg.info')
        
        # Get full crew details from the assignment
        from api.models import Beosztas
        try:
            beosztas = Beosztas.objects.filter(forgatas=forgatas).first()
            full_crew = []
            crew_by_role = {}
            
            if beosztas:
                for relation in beosztas.szerepkor_relaciok.all():
                    user = relation.user
                    role = relation.szerepkor.name
                    
                    full_crew.append({
                        'name': user.get_full_name() or user.username,
                        'role': role
                    })
                    
                    if role not in crew_by_role:
                        crew_by_role[role] = []
                    crew_by_role[role].append(user.get_full_name() or user.username)
            
            print(f"[DEBUG] Full crew size: {len(full_crew)}")
            print(f"[DEBUG] Crew roles: {list(crew_by_role.keys())}")
            
        except Exception as e:
            print(f"[DEBUG] Could not get full crew details: {str(e)}")
            full_crew = []
            crew_by_role = {}
        
        success = True
        
        # Send notification to added users
        if added_users:
            print(f"[DEBUG] Processing {len(added_users)} added users")
            added_emails = []
            for user in added_users:
                print(f"[DEBUG] Checking added user: {user.username} (ID: {user.id})")
                print(f"[DEBUG] - Email: {user.email}")
                print(f"[DEBUG] - Is active: {user.is_active}")
                if user.email and user.is_active:
                    added_emails.append(user.email)
                    print(f"[DEBUG] - Added to email list")
                else:
                    print(f"[DEBUG] - Skipped (no email or inactive)")
            
            print(f"[DEBUG] Valid added user emails: {len(added_emails)}")
            print(f"[DEBUG] Added emails list: {added_emails}")
            
            if added_emails:
                subject = f"FTV - Új beosztás: {forgatas.name}"
                print(f"[DEBUG] Assignment addition email subject: {subject}")
                
                # Create crew list HTML
                crew_html = ""
                if crew_by_role:
                    crew_html = "<div style='background-color: #ecf0f1; padding: 15px; margin: 10px 0; border-radius: 5px;'>"
                    crew_html += "<h4 style='margin-top: 0; color: #2c3e50;'>🎬 Forgatási csapat:</h4>"
                    for role, members in crew_by_role.items():
                        crew_html += f"<p><strong>{role}:</strong> {', '.join(members)}</p>"
                    crew_html += "</div>"
                
                # Create crew list for plain text
                crew_text = ""
                if crew_by_role:
                    crew_text = "\n🎬 Forgatási csapat:\n"
                    for role, members in crew_by_role.items():
                        crew_text += f"{role}: {', '.join(members)}\n"
                    crew_text += "\n"
                
                html_message = f"""
                <html>
                    <head>
                        <style>
                            body {{ font-family: Roboto, sans-serif; line-height: 1.6; color: #333; }}
                            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                            .header {{ background-color: #27ae60; color: white; padding: 20px; text-align: center; }}
                            .content {{ padding: 20px; background-color: #f9f9f9; }}
                            .forgatas-info {{ 
                                background-color: white; 
                                padding: 20px; 
                                margin: 20px 0; 
                                border-left: 4px solid #27ae60; 
                                border-radius: 5px;
                            }}
                            .footer {{ 
                                background-color: #2c3e50; 
                                color: white; 
                                padding: 20px; 
                                text-align: center; 
                                font-size: 12px; 
                            }}
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <div class="header">
                                <h1>🎬 Új forgatási beosztás</h1>
                            </div>
                            <div class="content">
                                <p>Kedves Kollégák!</p>
                                
                                <p>Önt beosztották a következő forgatáshoz:</p>
                                
                                <div class="forgatas-info">
                                    <h3>{forgatas.name}</h3>
                                    <p><strong>Leírás:</strong> {forgatas.description}</p>
                                    <p><strong>Dátum:</strong> {forgatas.date.strftime('%Y. %m. %d.')}</p>
                                    <p><strong>Időpont:</strong> {forgatas.timeFrom.strftime('%H:%M')} - {forgatas.timeTo.strftime('%H:%M')}</p>
                                    {f'<p><strong>Helyszín:</strong> {forgatas.location.name}</p>' if forgatas.location else ''}
                                    {f'<p><strong>Kapcsolattartó:</strong> {forgatas.contactPerson.name}</p>' if forgatas.contactPerson else ''}
                                </div>
                                
                                {crew_html}
                                
                                <p>Kérjük, jegyezze fel a forgatás részleteit és készüljön fel a megadott időpontra!</p>
                                
                                <p>A részletes információkat a FTV rendszerben találja:</p>
                                <p><a href="{frontend_url}" target="_blank">{frontend_url}</a></p>
                            </div>
                            <div class="footer">
                                <p>Ez egy automatikus értesítés az FTV rendszerből.</p>
                                <p>© 2025 FTV. Minden jog fenntartva.</p>
                            </div>
                        </div>
                    </body>
                </html>
                """
                
                plain_message = f"""
🎬 Új forgatási beosztás

Kedves Kollégák!

Önt beosztották a következő forgatáshoz:

Forgatás: {forgatas.name}
Leírás: {forgatas.description}
Dátum: {forgatas.date.strftime('%Y. %m. %d.')}
Időpont: {forgatas.timeFrom.strftime('%H:%M')} - {forgatas.timeTo.strftime('%H:%M')}
{f'Helyszín: {forgatas.location.name}' if forgatas.location else ''}
{f'Kapcsolattartó: {forgatas.contactPerson.name}' if forgatas.contactPerson else ''}
{crew_text}
Kérjük, jegyezze fel a forgatás részleteit és készüljön fel a megadott időpontra!

A részletes információkat a FTV rendszerben találja:
{frontend_url}

Ez egy automatikus értesítés az FTV rendszerből.
© 2025 FTV. Minden jog fenntartva.
                """
                
                try:
                    print(f"[DEBUG] About to send assignment addition emails to {len(added_emails)} recipients using HTML template")
                    print(f"[DEBUG] Recipients: {added_emails}")
                    print(f"[DEBUG] From email: {settings.DEFAULT_FROM_EMAIL}")
                    
                    # Import email templates
                    from backend.email_templates import (
                        get_base_email_template, 
                        get_assignment_addition_email_content,
                        send_html_emails_to_multiple_recipients
                    )
                    
                    # Get contact person name
                    contact_person_name = forgatas.contactPerson.name if forgatas.contactPerson else "Rendszer adminisztrátor"
                    
                    # Generate email content using the new template system
                    content = get_assignment_addition_email_content(forgatas, contact_person_name)
                    
                    # Create complete HTML email
                    html_message = get_base_email_template(
                        title="Új forgatási beosztás",
                        content=content,
                        button_text="FTV Rendszer megnyitása",
                        button_url=frontend_url
                    )
                    
                    # Send HTML emails to multiple recipients
                    successful_count, failed_emails = send_html_emails_to_multiple_recipients(
                        subject=subject,
                        html_content=html_message,
                        plain_content=plain_message,
                        recipient_emails=added_emails,
                        from_email=settings.DEFAULT_FROM_EMAIL
                    )
                    
                    print(f"[DEBUG] Assignment addition HTML email sending completed")
                    print(f"[SUCCESS] Assignment addition emails sent to {successful_count}/{len(added_emails)} recipients")
                    
                    if failed_emails:
                        print(f"[WARNING] Failed to send emails to: {failed_emails}")
                        success = False
                        
                except Exception as e:
                    print(f"[ERROR] Failed to send assignment addition email: {str(e)}")
                    import traceback
                    print(f"[ERROR] Full traceback: {traceback.format_exc()}")
                    success = False
        
        # Send notification to removed users
        if removed_users:
            print(f"[DEBUG] Processing {len(removed_users)} removed users")
            removed_emails = []
            for user in removed_users:
                print(f"[DEBUG] Checking removed user: {user.username} (ID: {user.id})")
                print(f"[DEBUG] - Email: {user.email}")
                print(f"[DEBUG] - Is active: {user.is_active}")
                if user.email and user.is_active:
                    removed_emails.append(user.email)
                    print(f"[DEBUG] - Added to email list")
                else:
                    print(f"[DEBUG] - Skipped (no email or inactive)")
            
            print(f"[DEBUG] Valid removed user emails: {len(removed_emails)}")
            print(f"[DEBUG] Removed emails list: {removed_emails}")
            
            if removed_emails:
                subject = f"FTV - Beosztás módosítás: {forgatas.name}"
                print(f"[DEBUG] Assignment removal email subject: {subject}")
                
                # Create crew list HTML for removal email
                crew_html = ""
                if crew_by_role:
                    crew_html = "<div style='background-color: #ecf0f1; padding: 15px; margin: 10px 0; border-radius: 5px;'>"
                    crew_html += "<h4 style='margin-top: 0; color: #2c3e50;'>🎬 Jelenlegi forgatási csapat:</h4>"
                    for role, members in crew_by_role.items():
                        crew_html += f"<p><strong>{role}:</strong> {', '.join(members)}</p>"
                    crew_html += "</div>"
                
                # Create crew list for plain text
                crew_text = ""
                if crew_by_role:
                    crew_text = "\n🎬 Jelenlegi forgatási csapat:\n"
                    for role, members in crew_by_role.items():
                        crew_text += f"{role}: {', '.join(members)}\n"
                    crew_text += "\n"
                
                html_message = f"""
                <html>
                    <head>
                        <style>
                            body {{ font-family: Roboto, sans-serif; line-height: 1.6; color: #333; }}
                            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                            .header {{ background-color: #e74c3c; color: white; padding: 20px; text-align: center; }}
                            .content {{ padding: 20px; background-color: #f9f9f9; }}
                            .forgatas-info {{ 
                                background-color: white; 
                                padding: 20px; 
                                margin: 20px 0; 
                                border-left: 4px solid #e74c3c; 
                                border-radius: 5px;
                            }}
                            .footer {{ 
                                background-color: #2c3e50; 
                                color: white; 
                                padding: 20px; 
                                text-align: center; 
                                font-size: 12px; 
                            }}
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <div class="header">
                                <h1>📝 Beosztás módosítás</h1>
                            </div>
                            <div class="content">
                                <p>Kedves Kollégák!</p>
                                
                                <p>A beosztása módosításra került a következő forgatásnál:</p>
                                
                                <div class="forgatas-info">
                                    <h3>{forgatas.name}</h3>
                                    <p><strong>Dátum:</strong> {forgatas.date.strftime('%Y. %m. %d.')}</p>
                                    <p><strong>Időpont:</strong> {forgatas.timeFrom.strftime('%H:%M')} - {forgatas.timeTo.strftime('%H:%M')}</p>
                                </div>
                                
                                <p><strong>Önt eltávolították ebből a beosztásból.</strong></p>
                                <p>Már nem szükséges részt vennie ezen a forgatáson.</p>
                                
                                {crew_html}
                                
                                <p>Az aktuális beosztásokat a FTV rendszerben ellenőrizheti:</p>
                                <p><a href="{frontend_url}" target="_blank">{frontend_url}</a></p>
                            </div>
                            <div class="footer">
                                <p>Ez egy automatikus értesítés az FTV rendszerből.</p>
                                <p>© 2025 FTV. Minden jog fenntartva.</p>
                            </div>
                        </div>
                    </body>
                </html>
                """
                
                plain_message = f"""
📝 Beosztás módosítás

Kedves Kollégák!

A beosztása módosításra került a következő forgatásnál:

Forgatás: {forgatas.name}
Dátum: {forgatas.date.strftime('%Y. %m. %d.')}
Időpont: {forgatas.timeFrom.strftime('%H:%M')} - {forgatas.timeTo.strftime('%H:%M')}

Önt eltávolították ebből a beosztásból.
Már nem szükséges részt vennie ezen a forgatáson.
{crew_text}
Az aktuális beosztásokat a FTV rendszerben ellenőrizheti:
{frontend_url}

Ez egy automatikus értesítés az FTV rendszerből.
© 2025 FTV. Minden jog fenntartva.
                """

                try:
                    print(f"[DEBUG] About to send assignment removal emails to {len(removed_emails)} recipients using HTML template")
                    print(f"[DEBUG] Recipients: {removed_emails}")
                    print(f"[DEBUG] From email: {settings.DEFAULT_FROM_EMAIL}")
                    
                    # Import email templates
                    from backend.email_templates import (
                        get_base_email_template, 
                        get_assignment_removal_email_content,
                        send_html_emails_to_multiple_recipients
                    )
                    
                    # Get contact person name
                    contact_person_name = forgatas.contactPerson.name if forgatas.contactPerson else "Rendszer adminisztrátor"
                    
                    # Generate email content using the new template system
                    content = get_assignment_removal_email_content(forgatas, contact_person_name)
                    
                    # Create complete HTML email
                    html_message = get_base_email_template(
                        title="Forgatási beosztás módosítás",
                        content=content,
                        button_text="FTV Rendszer megnyitása",
                        button_url=frontend_url
                    )
                    
                    # Send HTML emails to multiple recipients
                    successful_count, failed_emails = send_html_emails_to_multiple_recipients(
                        subject=subject,
                        html_content=html_message,
                        plain_content=plain_message,
                        recipient_emails=removed_emails,
                        from_email=settings.DEFAULT_FROM_EMAIL
                    )
                    
                    print(f"[DEBUG] Assignment removal HTML email sending completed")
                    print(f"[SUCCESS] Assignment removal emails sent to {successful_count}/{len(removed_emails)} recipients")
                    
                    if failed_emails:
                        print(f"[WARNING] Failed to send emails to: {failed_emails}")
                        success = False
                        
                except Exception as e:
                    print(f"[ERROR] Failed to send assignment removal email: {str(e)}")
                    import traceback
                    print(f"[ERROR] Full traceback: {traceback.format_exc()}")
                    success = False
        
        print(f"[DEBUG] Assignment email notification process completed with success: {success}")
        print(f"[DEBUG] ========== ASSIGNMENT EMAIL DEBUG END ==========")
        return success
        
    except Exception as e:
        print(f"[ERROR] Failed to send assignment change notification email: {str(e)}")
        import traceback
        print(f"[ERROR] Full traceback: {traceback.format_exc()}")
        return False

# ============================================================================
# Password Validation Utilities
# ============================================================================

def get_password_validation_rules() -> dict:
    """
    Get password validation rules from Django settings.
    
    Returns:
        Dictionary with validation rules and requirements
    """
    validators = get_password_validators(settings.AUTH_PASSWORD_VALIDATORS)
    rules = []
    minimum_length = 8  # Default Django minimum
    
    for validator in validators:
        rule = {"name": validator.__class__.__name__}
        
        if hasattr(validator, 'get_help_text'):
            rule["help_text"] = validator.get_help_text()
        
        # Extract specific requirements
        if "MinimumLength" in rule["name"]:
            if hasattr(validator, 'min_length'):
                minimum_length = validator.min_length
                rule["min_length"] = minimum_length
        elif "UserAttributeSimilarity" in rule["name"]:
            rule["description"] = "A jelszó nem lehet túl hasonló a személyes adatokhoz"
        elif "CommonPassword" in rule["name"]:
            rule["description"] = "A jelszó nem lehet közismerten gyenge jelszó"
        elif "NumericPassword" in rule["name"]:
            rule["description"] = "A jelszó nem állhat csak számokból"
        
        rules.append(rule)
    
    return {
        "rules": rules,
        "minimum_length": minimum_length,
        "help_text": f"A jelszónak legalább {minimum_length} karakter hosszúnak kell lennie, és meg kell felelnie a biztonsági követelményeknek."
    }

def validate_password_strength(password: str, user_data: dict = None) -> dict:
    """
    Validate password strength using Django's validators.
    
    Args:
        password: Password to validate
        user_data: Optional user data for similarity checking
        
    Returns:
        Dictionary with validation result and error messages
    """
    errors = []
    
    # Create a mock user object for validation if user_data is provided
    mock_user = None
    if user_data:
        mock_user = User(
            username=user_data.get('username', ''),
            email=user_data.get('email', ''),
            first_name=user_data.get('first_name', ''),
            last_name=user_data.get('last_name', ''),
        )
    
    try:
        validate_password(password, mock_user)
        return {"valid": True, "errors": []}
    except ValidationError as e:
        return {"valid": False, "errors": list(e.messages)}

def change_user_password(user: User, old_password: str, new_password: str) -> dict:
    """
    Change user password after validating the old password.
    
    Args:
        user: User instance
        old_password: Current password to verify
        new_password: New password to set
        
    Returns:
        Dictionary with success status and message/error
    """
    try:
        print(f"[DEBUG] ========== CHANGE PASSWORD DEBUG ==========")
        print(f"[DEBUG] Attempting password change for user: {user.username} (ID: {user.id})")
        print(f"[DEBUG] User email: {user.email}")
        print(f"[DEBUG] User is_active: {user.is_active}")
        print(f"[DEBUG] User last_login: {user.last_login}")
        
        # Check if user is active
        if not user.is_active:
            print(f"[DEBUG] ❌ User {user.username} is not active")
            return {"success": False, "error": "A felhasználói fiók inaktív."}
        
        # Verify old password
        print(f"[DEBUG] Verifying old password for user {user.username}...")
        if not user.check_password(old_password):
            print(f"[DEBUG] ❌ Old password verification failed for user {user.username}")
            return {"success": False, "error": "A jelenlegi jelszó helytelen."}
        
        print(f"[DEBUG] ✅ Old password verified successfully for user {user.username}")
        
        # Validate new password strength
        print(f"[DEBUG] Validating new password strength...")
        try:
            validate_password(new_password, user)
            print(f"[DEBUG] ✅ New password meets strength requirements")
        except ValidationError as e:
            print(f"[DEBUG] ❌ New password validation failed: {e.messages}")
            return {"success": False, "error": " ".join(e.messages)}
        
        # Check if new password is different from old password
        if user.check_password(new_password):
            print(f"[DEBUG] ❌ New password is the same as old password")
            return {"success": False, "error": "Az új jelszónak különböznie kell a jelenlegi jelszótól."}
        
        # Set new password
        print(f"[DEBUG] Setting new password for user {user.username}...")
        user.set_password(new_password)
        user.save()
        
        print(f"[SUCCESS] Password changed successfully for user: {user.username}")
        print(f"[DEBUG] ========== CHANGE PASSWORD DEBUG END ==========")
        
        return {"success": True, "message": "A jelszó sikeresen módosításra került."}
        
    except Exception as e:
        print(f"[ERROR] Error in change_user_password: {str(e)}")
        import traceback
        print(f"[ERROR] Full traceback: {traceback.format_exc()}")
        print(f"[DEBUG] ========== CHANGE PASSWORD DEBUG END (ERROR) ==========")
        return {"success": False, "error": "Hiba történt a jelszó módosítása során."}

# ============================================================================
# API Endpoints
# ============================================================================

def register_authentication_endpoints(api):
    """Register all authentication and password management endpoints."""
    
    # ========================================================================
    # First Login Endpoints
    # ========================================================================
    
    @api.post("/first-login/request-token", response={200: FirstLoginRequestResponse, 400: ErrorSchema})
    def request_first_login_token(request, data: FirstLoginRequestSchema):
        """
        Request first-time login token via email.
        
        Sends a first-time login email if user exists and hasn't set password yet.
        
        Args:
            data: Request with email address
            
        Returns:
            200: Success message (always same for security)
            400: Error occurred
        """
        try:
            print(f"[DEBUG] First login token requested for email: {data.email}")
            
            # Check if user exists with this email
            try:
                user = User.objects.get(email=data.email)
                print(f"[DEBUG] User found: {user.username} (ID: {user.id})")
            except User.DoesNotExist:
                print(f"[DEBUG] User not found for email: {data.email}")
                # For security reasons, don't reveal if email exists or not
                return 200, {"message": "Ha a megadott email cím regisztrált, akkor elküldtük az első bejelentkezési linket."}
            
            # Check if user is active
            if not user.is_active:
                print(f"[DEBUG] User {user.username} is not active")
                return 200, {"message": "Ha a megadott email cím regisztrált, akkor elküldtük az első bejelentkezési linket."}
            
            print(f"[DEBUG] User {user.username} is active, proceeding to send first login email")
            
            # Ensure profile exists
            try:
                profile = Profile.objects.get(user=user)
                print(f"[DEBUG] Profile found for user {user.username}")
            except Profile.DoesNotExist:
                print(f"[DEBUG] Creating new profile for user {user.username}")
                # Create profile if it doesn't exist
                profile = Profile.objects.create(
                    user=user,
                    admin_type='none'
                )
            
            # Generate first login token
            print(f"[DEBUG] Generating first login token for user {user.username}")
            token = generate_first_login_token(user.id)
            print(f"[DEBUG] Token generated successfully (length: {len(token)})")
            
            # Send email with first login link
            print(f"[DEBUG] Attempting to send first login email to {user.email}")
            email_sent = send_first_login_email(user, token)
            
            if email_sent:
                print(f"[SUCCESS] First login email sent successfully to {user.email}")
            else:
                print(f"[ERROR] Failed to send first login email to {user.email}")
            
            # Always return the same message for security
            return 200, {"message": "Ha a megadott email cím regisztrált, akkor elküldtük az első bejelentkezési linket."}
            
        except Exception as e:
            print(f"[ERROR] Error in request_first_login_token: {str(e)}")
            import traceback
            print(f"[ERROR] Full traceback: {traceback.format_exc()}")
            return 400, {"message": "Hiba történt a kérés feldolgozása során."}
    
    @api.get("/first-login/verify-token/{token}", response={200: FirstLoginVerifyResponse, 400: ErrorSchema})
    def verify_first_login_token_endpoint(request, token: str):
        """
        Verify first-time login token validity.
        
        Args:
            token: First login token
            
        Returns:
            200: Token validity status and user info
            400: Error occurred
        """
        try:
            verification_result = verify_first_login_token(token)
            
            response_data = {
                "valid": verification_result['valid']
            }
            
            if not verification_result['valid']:
                response_data["error"] = verification_result.get('error')
            else:
                user = verification_result['user']
                response_data["user_info"] = {
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email
                }
            
            return 200, response_data
                
        except Exception as e:
            print(f"Error in verify_first_login_token: {str(e)}")
            return 400, {"message": "Hiba történt a token ellenőrzése során."}
    
    @api.post("/first-login/set-password", response={200: FirstLoginSetPasswordResponse, 400: ErrorSchema})
    def set_first_login_password(request, data: FirstLoginSetPasswordRequest):
        """
        Set password using first-time login token.
        
        Args:
            data: Request with token and password data
            
        Returns:
            200: Password set successfully
            400: Error occurred or invalid data
        """
        try:
            # Validate password confirmation
            if data.password != data.confirm_password:
                return 400, {"message": "A jelszavak nem egyeznek."}
            
            # Verify token
            verification_result = verify_first_login_token(data.token)
            if not verification_result['valid']:
                error_message = verification_result.get('error', 'Érvénytelen token')
                if 'expired' in error_message.lower():
                    return 400, {"message": "A token lejárt. Kérjen új első bejelentkezési linket."}
                return 400, {"message": "Érvénytelen token."}
            
            user = verification_result['user']
            profile = verification_result['profile']
            
            # Validate password strength
            try:
                validate_password(data.password, user)
            except ValidationError as e:
                return 400, {"message": " ".join(e.messages)}
            
            # Set password
            user.set_password(data.password)
            user.last_login = timezone.now()  # Set first login time
            user.save()
            
            print(f"First login password set successfully for user: {user.username}")
            
            return 200, {
                "message": "Jelszó sikeresen beállítva. Most már bejelentkezhet a rendszerbe.",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "full_name": user.get_full_name()
                }
            }
            
        except Exception as e:
            print(f"Error in set_first_login_password: {str(e)}")
            return 400, {"message": "Hiba történt a jelszó beállítása során."}
    
    # ========================================================================
    # Password Reset Endpoints
    # ========================================================================
    
    @api.post("/forgot-password", response={200: ForgotPasswordResponse, 400: ErrorSchema})
    def forgot_password(request, data: ForgotPasswordRequest):
        """
        Initiate password reset process.
        
        Sends password reset email if user exists.
        
        Args:
            data: Request with email address
            
        Returns:
            200: Success message (always same for security)
            400: Error occurred
        """
        try:
            # Check if user exists with this email
            try:
                user = User.objects.get(email=data.email)
            except User.DoesNotExist:
                # For security reasons, don't reveal if email exists or not
                return 200, {"message": "Ha a megadott email cím regisztrált, akkor elküldtük a jelszó visszaállítási linket."}
            
            # Check if user is active
            if not user.is_active:
                return 200, {"message": "Ha a megadott email cím regisztrált, akkor elküldtük a jelszó visszaállítási linket."}
            
            # Generate password reset token
            reset_token = generate_password_reset_token(user.id)
            
            # Send email with reset link
            email_sent = send_password_reset_email(user, reset_token)
            
            if email_sent:
                print(f"Password reset email sent successfully to {user.email}")
            else:
                print(f"Failed to send password reset email to {user.email}")
            
            # Always return the same message for security
            return 200, {"message": "Ha a megadott email cím regisztrált, akkor elküldtük a jelszó visszaállítási linket."}
            
        except Exception as e:
            print(f"Error in forgot_password: {str(e)}")
            return 400, {"message": "Hiba történt a kérés feldolgozása során."}

    @api.get("/verify-reset-token/{token}", response={200: VerifyTokenResponse, 400: ErrorSchema})
    def verify_reset_token(request, token: str):
        """
        Verify password reset token validity.
        
        Args:
            token: Password reset token
            
        Returns:
            200: Token validity status
            400: Error occurred
        """
        try:
            print(f"[DEBUG] ========== VERIFY RESET TOKEN DEBUG ==========")
            print(f"[DEBUG] Received token verification request")
            print(f"[DEBUG] Token (first 50 chars): {token[:50]}...")
            print(f"[DEBUG] Token length: {len(token)}")
            print(f"[DEBUG] Request method: {request.method}")
            print(f"[DEBUG] Request path: {request.get_full_path()}")
            
            # Decode token without verification to see payload
            import jwt
            try:
                unverified_payload = jwt.decode(token, options={"verify_signature": False})
                print(f"[DEBUG] Token payload (unverified): {unverified_payload}")
                
                # Check token structure
                if 'user_id' in unverified_payload:
                    print(f"[DEBUG] - User ID: {unverified_payload['user_id']}")
                if 'purpose' in unverified_payload:
                    print(f"[DEBUG] - Purpose: {unverified_payload['purpose']}")
                if 'exp' in unverified_payload:
                    exp_time = datetime.utcfromtimestamp(unverified_payload['exp'])
                    current_time = datetime.utcnow()
                    print(f"[DEBUG] - Expires at: {exp_time}")
                    print(f"[DEBUG] - Current time: {current_time}")
                    if current_time > exp_time:
                        print(f"[DEBUG] - ❌ TOKEN IS EXPIRED by {current_time - exp_time}")
                    else:
                        print(f"[DEBUG] - ✅ Token valid for {exp_time - current_time} more")
                if 'iat' in unverified_payload:
                    iat_time = datetime.utcfromtimestamp(unverified_payload['iat'])
                    print(f"[DEBUG] - Issued at: {iat_time}")
                    
            except Exception as decode_error:
                print(f"[DEBUG] Failed to decode token payload: {decode_error}")
            
            # Check current settings
            print(f"[DEBUG] Current SECRET_KEY (first 20 chars): {settings.SECRET_KEY[:20]}...")
            print(f"[DEBUG] SECRET_KEY length: {len(settings.SECRET_KEY)}")
            print(f"[DEBUG] PASSWORD_RESET_TIMEOUT: {settings.PASSWORD_RESET_TIMEOUT} seconds")
            
            # Try manual JWT verification to get detailed error
            try:
                manual_payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
                print(f"[DEBUG] ✅ Manual JWT verification successful: {manual_payload}")
            except jwt.ExpiredSignatureError:
                print(f"[DEBUG] ❌ Manual JWT verification: Token expired")
            except jwt.InvalidSignatureError:
                print(f"[DEBUG] ❌ Manual JWT verification: Signature mismatch (wrong SECRET_KEY)")
            except jwt.InvalidTokenError as jwt_error:
                print(f"[DEBUG] ❌ Manual JWT verification: Invalid token - {jwt_error}")
            except Exception as jwt_exception:
                print(f"[DEBUG] ❌ Manual JWT verification error: {jwt_exception}")
            
            print(f"[DEBUG] Calling verify_password_reset_token function...")
            verification_result = verify_password_reset_token(token)
            print(f"[DEBUG] Verification result: {verification_result}")
            
            response_data = {
                "valid": verification_result['valid']
            }
            
            if not verification_result['valid']:
                response_data["error"] = verification_result.get('error')
                print(f"[DEBUG] ❌ Token verification failed: {response_data['error']}")
            else:
                print(f"[DEBUG] ✅ Token verification successful")
                if 'user' in verification_result:
                    user = verification_result['user']
                    print(f"[DEBUG] - Verified user: {user.username} (ID: {user.id})")
                    print(f"[DEBUG] - User email: {user.email}")
                    print(f"[DEBUG] - User is_active: {user.is_active}")
            
            print(f"[DEBUG] Returning response: {response_data}")
            print(f"[DEBUG] ========== VERIFY RESET TOKEN DEBUG END ==========")
            return 200, response_data
                
        except Exception as e:
            print(f"[ERROR] Error in verify_reset_token: {str(e)}")
            print(f"[ERROR] Exception type: {type(e).__name__}")
            import traceback
            print(f"[ERROR] Full traceback: {traceback.format_exc()}")
            print(f"[DEBUG] ========== VERIFY RESET TOKEN DEBUG END (ERROR) ==========")
            return 400, {"message": "Hiba történt a token ellenőrzése során."}

    @api.post("/reset-password", response={200: ResetPasswordResponse, 400: ErrorSchema})
    def reset_password(request, data: ResetPasswordRequest):
        """
        Complete password reset process.
        
        Updates user password using valid reset token.
        
        Args:
            data: Reset request with token and new password
            
        Returns:
            200: Password reset successful
            400: Error occurred or invalid data
        """
        try:
            # Validate password confirmation
            if data.password != data.confirm_password:
                return 400, {"message": "A jelszavak nem egyeznek."}
            
            # Verify the JWT token
            verification_result = verify_password_reset_token(data.token)
            
            if not verification_result['valid']:
                error_message = verification_result.get('error', 'Érvénytelen token')
                if 'expired' in error_message.lower():
                    return 400, {"message": "A token lejárt. Kérjen új jelszó visszaállítási linket."}
                return 400, {"message": "Érvénytelen token."}
            
            user = verification_result['user']
            
            # Validate password strength
            try:
                validate_password(data.password, user)
            except ValidationError as e:
                return 400, {"message": " ".join(e.messages)}
            
            # Update user password
            user.set_password(data.password)
            user.save()
            
            print(f"Password reset successful for user: {user.username}")
            
            return 200, {"message": "A jelszó sikeresen módosításra került. Most már bejelentkezhet az új jelszavával."}
            
        except Exception as e:
            print(f"Error in reset_password: {str(e)}")
            return 400, {"message": "Hiba történt a jelszó módosítása során."}
    
    # ========================================================================
    # Password Validation Endpoints
    # ========================================================================
    
    @api.get("/password-validation/rules", response={200: PasswordValidationRulesResponse})
    def get_password_validation_rules_endpoint(request):
        """
        Get password validation rules and requirements.
        
        Returns:
            200: Password validation rules and help text
        """
        try:
            rules_data = get_password_validation_rules()
            return 200, rules_data
        except Exception as e:
            print(f"Error in get_password_validation_rules: {str(e)}")
            # Return minimal rules if there's an error
            return 200, {
                "rules": [
                    {
                        "name": "MinimumLengthValidator",
                        "min_length": 8,
                        "description": "A jelszónak legalább 8 karakter hosszúnak kell lennie"
                    }
                ],
                "minimum_length": 8,
                "help_text": "A jelszónak legalább 8 karakter hosszúnak kell lennie."
            }
    
    @api.post("/password-validation/check", response={200: PasswordValidationCheckResponse})
    def check_password_validation(request, data: PasswordValidationCheckRequest):
        """
        Validate password against Django's password validators.
        
        Args:
            data: Request with password and optional user data
            
        Returns:
            200: Validation result and error messages
        """
        try:
            user_data = {
                'username': data.username,
                'email': data.email,
                'first_name': data.first_name,
                'last_name': data.last_name
            } if any([data.username, data.email, data.first_name, data.last_name]) else None
            
            validation_result = validate_password_strength(data.password, user_data)
            return 200, validation_result
        except Exception as e:
            print(f"Error in check_password_validation: {str(e)}")
            return 200, {
                "valid": False,
                "errors": ["Hiba történt a jelszó ellenőrzése során."]
            }
    
    # ========================================================================
    # Authenticated Password Management Endpoints
    # ========================================================================
    
    @api.post("/change-password", auth=JWTAuth(), response={200: ChangePasswordResponse, 400: ErrorSchema, 401: ErrorSchema})
    def change_password(request, data: ChangePasswordRequest):
        """
        Change user password (requires authentication).
        
        Allows authenticated users to change their password by providing:
        - Current password for verification
        - New password meeting strength requirements
        - Confirmation of new password
        
        Args:
            data: Request with old password, new password, and confirmation
            
        Returns:
            200: Password changed successfully
            400: Validation error or invalid current password
            401: Authentication required
        """
        try:
            print(f"[DEBUG] ========== CHANGE PASSWORD ENDPOINT DEBUG ==========")
            print(f"[DEBUG] Change password request received")
            print(f"[DEBUG] Request method: {request.method}")
            print(f"[DEBUG] Request path: {request.get_full_path()}")
            
            # Get authenticated user
            user = request.auth
            if not user:
                print(f"[DEBUG] ❌ No authenticated user found")
                return 401, {"message": "Bejelentkezés szükséges."}
            
            print(f"[DEBUG] Authenticated user: {user.username} (ID: {user.id})")
            print(f"[DEBUG] User email: {user.email}")
            
            # Validate password confirmation
            if data.new_password != data.confirm_new_password:
                print(f"[DEBUG] ❌ New password confirmation mismatch")
                return 400, {"message": "Az új jelszavak nem egyeznek."}
            
            print(f"[DEBUG] ✅ Password confirmation validated")
            
            # Check if old password is provided
            if not data.old_password:
                print(f"[DEBUG] ❌ Old password not provided")
                return 400, {"message": "A jelenlegi jelszó megadása kötelező."}
            
            # Check if new password is provided
            if not data.new_password:
                print(f"[DEBUG] ❌ New password not provided")
                return 400, {"message": "Az új jelszó megadása kötelező."}
            
            print(f"[DEBUG] Calling change_user_password function...")
            
            # Attempt to change password
            result = change_user_password(user, data.old_password, data.new_password)
            
            if result["success"]:
                print(f"[SUCCESS] Password changed successfully for user: {user.username}")
                print(f"[DEBUG] ========== CHANGE PASSWORD ENDPOINT DEBUG END ==========")
                return 200, {"message": result["message"]}
            else:
                print(f"[DEBUG] ❌ Password change failed: {result['error']}")
                print(f"[DEBUG] ========== CHANGE PASSWORD ENDPOINT DEBUG END ==========")
                return 400, {"message": result["error"]}
                
        except Exception as e:
            print(f"[ERROR] Error in change_password endpoint: {str(e)}")
            print(f"[ERROR] Exception type: {type(e).__name__}")
            import traceback
            print(f"[ERROR] Full traceback: {traceback.format_exc()}")
            print(f"[DEBUG] ========== CHANGE PASSWORD ENDPOINT DEBUG END (ERROR) ==========")
            return 400, {"message": "Hiba történt a jelszó módosítása során."}

# ============================================================================
# Documentation
# ============================================================================

AUTHENTICATION_USAGE_DOCS = """
Authentication and Password Management API Usage:

FIRST LOGIN FLOW:
================

1. Request first login token:
   POST /api/first-login/request-token
   Content-Type: application/json
   Body: {"email": "user@example.com"}

2. Verify token (optional):
   GET /api/first-login/verify-token/{token}

3. Set password:
   POST /api/first-login/set-password
   Content-Type: application/json
   Body: {
     "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
     "password": "newpassword123",
     "confirm_password": "newpassword123"
   }

PASSWORD RESET FLOW:
===================

1. Request password reset:
   POST /api/forgot-password
   Content-Type: application/json
   Body: {"email": "user@example.com"}

2. Verify token (optional):
   GET /api/verify-reset-token/{token}

3. Reset password:
   POST /api/reset-password
   Content-Type: application/json
   Body: {
     "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
     "password": "newpassword123",
     "confirm_password": "newpassword123"
   }

AUTHENTICATED PASSWORD CHANGE:
=============================

Change password (requires authentication):
POST /api/change-password
Authorization: Bearer <jwt_token>
Content-Type: application/json
Body: {
  "old_password": "currentpassword",
  "new_password": "newpassword123",
  "confirmNewPassword": "newpassword123"
}

PASSWORD VALIDATION:
===================

1. Get validation rules:
   GET /api/password-validation/rules

2. Check password strength:
   POST /api/password-validation/check
   Content-Type: application/json
   Body: {
     "password": "testpassword",
     "username": "testuser",  // optional
     "email": "test@example.com"  // optional
   }

JavaScript Example:
==================

// Check password strength
const checkPassword = async (password) => {
  const response = await fetch('/api/password-validation/check', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password })
  });
  const result = await response.json();
  if (!result.valid) {
    console.log('Password errors:', result.errors);
  }
};

// First login
const setFirstPassword = async (token, password, confirmPassword) => {
  const response = await fetch('/api/first-login/set-password', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token, password, confirm_password: confirmPassword })
  });
  const result = await response.json();
  console.log(result.message);
};

// Change password (authenticated)
const changePassword = async (jwtToken, oldPassword, newPassword, confirmNewPassword) => {
  const response = await fetch('/api/change-password', {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${jwtToken}`
    },
    body: JSON.stringify({ 
      old_password: oldPassword, 
      new_password: newPassword, 
      confirmNewPassword: confirmNewPassword 
    })
  });
  const result = await response.json();
  console.log(result.message);
};
"""
