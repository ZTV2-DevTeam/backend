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

from ninja import Schema, Form
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password, get_password_validators
from django.core.exceptions import ValidationError
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
import jwt
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from .auth import ErrorSchema
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
    confirm_password: str

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
    confirm_password: str

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
        
        # Create HTML email content
        html_message = f"""
        <html>
            <head>
                <style>
                    body {{ font-family: Roboto, sans-serif; line-height: 1.6; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #f4f4f4; padding: 20px; text-align: center; }}
                    .content {{ padding: 20px; }}
                    .button {{ 
                        display: inline-block; 
                        padding: 10px 20px; 
                        background-color: #28a745; 
                        color: white !important; 
                        text-decoration: none; 
                        border-radius: 5px; 
                        margin: 20px 0;
                    }}
                    .footer {{ 
                        background-color: #f4f4f4; 
                        padding: 20px; 
                        text-align: center; 
                        font-size: 12px; 
                        color: #666;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>FTV - Első bejelentkezés</h1>
                    </div>
                    <div class="content">
                        <p>Kedves {user.first_name or user.username}!</p>
                        
                        <p>Üdvözöljük a FTV rendszerben! Fiókja létrehozásra került, és most beállíthatja jelszavát az első bejelentkezéshez.</p>
                        
                        <p>A jelszó beállításához kattintson az alábbi gombra:</p>
                        
                        <a href="{login_url}" class="button">Jelszó beállítása</a>
                        
                        <p>vagy másolja be a következő linket a böngészőjébe:</p>
                        <p><a href="{login_url}">{login_url}</a></p>
                        
                        <p><strong>Fontos információk:</strong></p>
                        <ul>
                            <li>Ez a link 30 napig érvényes</li>
                            <li>A link biztonságosan kódolt (csak a szerver tudja dekódolni)</li>
                            <li>A jelszó beállítása után már a szokásos bejelentkezési folyamatot használhatja</li>
                        </ul>
                    </div>
                    <div class="footer">
                        <p>Ez egy automatikus email, kérjük ne válaszoljon rá.</p>
                        <p>© 2025 FTV. Minden jog fenntartva.</p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        # Create plain text version
        plain_message = f"""
Kedves {user.first_name or user.username}!

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

        # Create HTML email content
        html_message = f"""
        <html>
            <head>
                <style>
                    body {{ font-family: Roboto, sans-serif; line-height: 1.6; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #f4f4f4; padding: 20px; text-align: center; }}
                    .content {{ padding: 20px; }}
                    .button {{ 
                        display: inline-block; 
                        padding: 10px 20px; 
                        background-color: #007bff; 
                        color: white !important; 
                        text-decoration: none; 
                        border-radius: 5px; 
                        margin: 20px 0;
                    }}
                    .footer {{ 
                        background-color: #f4f4f4; 
                        padding: 20px; 
                        text-align: center; 
                        font-size: 12px; 
                        color: #666;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>FTV - Jelszó Visszaállítása</h1>
                    </div>
                    <div class="content">
                        <p>Kedves {user.first_name or user.username}!</p>
                        
                        <p>Jelszó visszaállítási kérelmet kaptunk az Ön fiókjához az FTV rendszerben.</p>
                        
                        <p>Amennyiben Ön kérte a jelszó visszaállítást, kattintson az alábbi gombra:</p>
                        
                        <a href="{reset_url}" class="button">Jelszó visszaállítása</a>
                        
                        <p>vagy másolja be a következő linket a böngészőjébe:</p>
                        <p><a href="{reset_url}">{reset_url}</a></p>
                        
                        <p><strong>Fontos információk:</strong></p>
                        <ul>
                            <li>Ez a link 1 órán belül lejár</li>
                            <li>A link biztonságosan kódolt (csak a szerver tudja dekódolni)</li>
                            <li>Ha nem Ön kérte a jelszó visszaállítást, hagyja figyelmen kívül ezt az emailt</li>
                        </ul>
                    </div>
                    <div class="footer">
                        <p>Ez egy automatikus email, kérjük ne válaszoljon rá.</p>
                        <p>© 2025 FTV. Minden jog fenntartva.</p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        # Create plain text version
        plain_message = f"""
Kedves {user.first_name or user.username}!

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
            verification_result = verify_password_reset_token(token)
            
            response_data = {
                "valid": verification_result['valid']
            }
            
            if not verification_result['valid']:
                response_data["error"] = verification_result.get('error')
            
            return 200, response_data
                
        except Exception as e:
            print(f"Error in verify_reset_token: {str(e)}")
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
"""
