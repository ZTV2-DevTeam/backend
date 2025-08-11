"""
FTV Authentication API Module

This module provides comprehensive authentication functionality for the FTV system,
including JWT-based authentication, password reset, and user session management.

Public API Overview:
==================

The authentication API provides secure access to the FTV system through JWT tokens.
All endpoints return JSON responses and use standard HTTP status codes.

Base URL: /api/

Public Endpoints (No Authentication Required):
- POST /login                    - User login with username/password
- POST /forgot-password          - Initiate password reset process
- GET  /verify-reset-token/{token} - Verify password reset token
- POST /reset-password           - Complete password reset

Protected Endpoints (JWT Token Required):
- GET  /profile                  - Get current user profile
- GET  /dashboard               - Access user dashboard
- POST /refresh-token           - Refresh JWT token
- POST /logout                  - User logout

Authentication Flow:
==================

1. Login with username/password to receive JWT token
2. Include token in Authorization header: "Bearer {token}"
3. Tokens expire after 1 hour - use refresh-token endpoint
4. For password reset: forgot-password → verify-reset-token → reset-password

Error Handling:
==============

All endpoints return consistent error responses:
- 200: Success
- 400: Bad request (validation errors)
- 401: Unauthorized (invalid credentials/token)
- 500: Server error

Example Usage:
=============

Login:
curl -X POST /api/login -d "username=testuser&password=password123"

Authenticated request:
curl -H "Authorization: Bearer {your-jwt-token}" /api/profile

Password reset:
curl -X POST /api/forgot-password -H "Content-Type: application/json" -d '{"email":"user@example.com"}'

For detailed examples and schemas, see the interactive documentation.
"""

from ninja import Schema, Form
from ninja.security import HttpBearer
from django.contrib.auth.models import User
from django.http import HttpRequest
import jwt
from django.conf import settings
from datetime import datetime, timedelta, timezone
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

# Configuration
TOKEN_EXPIRATION_TIME = timedelta(hours=1)

# ============================================================================
# JWT Authentication Class
# ============================================================================

class JWTAuth(HttpBearer):
    """JWT Bearer token authentication for API endpoints."""
    
    def authenticate(self, request: HttpRequest, token: str):
        """
        Authenticate user based on JWT token.
        
        Args:
            request: HTTP request object
            token: JWT token string
            
        Returns:
            User object if authentication successful, None otherwise
        """
        print(f"Authenticating token: {token[:20]}...")  # Debug: show first 20 chars
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            print(f"JWT payload decoded successfully: {payload}")  # Debug
            
            user_id = payload.get("user_id")
            if user_id:
                user = User.objects.get(id=user_id)
                if user.is_active:  # Check if user is active
                    print(f"User {user.username} authenticated successfully")  # Debug
                    return user
                else:
                    print(f"User {user.username} is not active")  # Debug
                    return None
            else:
                print("No user_id in JWT payload")  # Debug
                return None
                    
        except jwt.ExpiredSignatureError:
            print("JWT token has expired")
            return None
        except jwt.InvalidTokenError as e:
            print(f"JWT token is invalid: {e}")
            return None
        except User.DoesNotExist:
            print(f"User with id {user_id} does not exist")
            return None
        except Exception as e:
            print(f"Unexpected error in JWT authentication: {e}")
            return None
            
        return None

# ============================================================================
# Response Schemas
# ============================================================================

class LoginSchema(Schema):
    """Response schema for successful login."""
    token: str
    user_id: int
    username: str
    first_name: str
    last_name: str
    email: str

class ErrorSchema(Schema):
    """Standard error response schema."""
    message: str

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
    confirmPassword: str

class ResetPasswordResponse(Schema):
    """Response schema for password reset completion."""
    message: str

class VerifyTokenResponse(Schema):
    """Response schema for token verification."""
    valid: bool

# ============================================================================
# Utility Functions
# ============================================================================

def generate_jwt_token(user: User) -> str:
    """
    Generate JWT token for authenticated user.
    
    Args:
        user: Django User object
        
    Returns:
        JWT token string
    """
    payload = {
        "user_id": user.id,
        "username": user.username,
        "exp": datetime.now(timezone.utc) + TOKEN_EXPIRATION_TIME,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

def create_user_response(user: User, token: str = None) -> dict:
    """
    Create standardized user response dictionary.
    
    Args:
        user: Django User object
        token: Optional JWT token
        
    Returns:
        Dictionary with user information
    """
    return {
        "token": token or "current_session",
        "user_id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
    }

# ============================================================================
# API Endpoints
# ============================================================================

def register_auth_endpoints(api):
    """Register all authentication endpoints with the API router."""
    
    @api.post("/login", response={200: LoginSchema, 401: ErrorSchema})
    def login(request, username: Form[str], password: Form[str]):
        """
        User login endpoint.
        
        Authenticates user credentials and returns JWT token.
        
        Args:
            username: User's username
            password: User's password
            
        Returns:
            200: Login successful with token and user info
            401: Authentication failed
        """
        print(f"Login attempt for username: {username}")  # Debug print
        
        user = User.objects.filter(username=username).first()
        if not user:
            print(f"User {username} not found")  # Debug print
            return 401, {"message": "Unauthorized"}
            
        if not user.check_password(password):
            print(f"Invalid password for user {username}")  # Debug print
            return 401, {"message": "Unauthorized"}
            
        if not user.is_active:
            print(f"User {username} is not active")  # Debug print
            return 401, {"message": "Unauthorized"}

        token = generate_jwt_token(user)
        print(f"Login successful for user {username}, token generated")  # Debug print

        return 200, create_user_response(user, token)

    @api.get("/profile", auth=JWTAuth(), response={200: LoginSchema, 401: ErrorSchema})
    def get_profile(request):
        """
        Get current user's profile information.
        
        Requires valid JWT token in Authorization header.
        
        Returns:
            200: User profile information
            401: Authentication failed
        """
        user = request.auth  # This is the authenticated user from JWT
        return 200, create_user_response(user)

    @api.get("/dashboard", auth=JWTAuth())
    def dashboard(request):
        """
        Protected dashboard endpoint.
        
        Provides basic dashboard information for authenticated users.
        
        Returns:
            Dictionary with welcome message and user details
        """
        user = request.auth
        return {
            "message": f"Welcome to your dashboard, {user.username}!",
            "user_id": user.id,
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
        }

    @api.post("/refresh-token", auth=JWTAuth(), response={200: dict, 401: ErrorSchema})
    def refresh_token(request):
        """
        Refresh JWT token.
        
        Generates new token for authenticated user.
        
        Returns:
            200: New token generated
            401: Authentication failed
        """
        user = request.auth
        new_token = generate_jwt_token(user)
        
        return 200, {
            "token": new_token,
            "message": "Token refreshed successfully"
        }

    @api.post("/logout", auth=JWTAuth())
    def logout(request):
        """
        User logout endpoint.
        
        Note: JWT tokens cannot be invalidated server-side without a blacklist.
        Client should discard the token.
        
        Returns:
            Logout confirmation message
        """
        user = request.auth
        return {
            "message": f"Goodbye, {user.username}! Please discard your token.",
            "note": "JWT tokens cannot be invalidated server-side without a blacklist. Ensure your client discards the token."
        }

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
            # Import the utility functions
            from api.password_reset_utils import generate_password_reset_token, send_password_reset_email
            
            # Check if user exists with this email
            try:
                user = User.objects.get(email=data.email)
            except User.DoesNotExist:
                # For security reasons, don't reveal if email exists or not
                return 200, {"message": "Ha a megadott email cím regisztrált, akkor elküldtük a jelszó visszaállítási linket."}
            
            # Check if user is active
            if not user.is_active:
                return 200, {"message": "Ha a megadott email cím regisztrált, akkor elküldtük a jelszó visszaállítási linket."}
            
            # Generate JWT token for password reset
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
            from api.password_reset_utils import verify_password_reset_token
            
            # Verify the JWT token
            verification_result = verify_password_reset_token(token)
            
            return 200, {"valid": verification_result['valid']}
                
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
            from api.password_reset_utils import verify_password_reset_token
            
            # Validate password confirmation
            if data.password != data.confirmPassword:
                return 400, {"message": "A jelszavak nem egyeznek."}
            
            # Verify the JWT token
            verification_result = verify_password_reset_token(data.token)
            
            if not verification_result['valid']:
                error_message = verification_result.get('error', 'Érvénytelen token')
                if 'expired' in error_message.lower():
                    return 400, {"message": "A token lejárt. Kérjen új jelszó visszaállítási linket."}
                return 400, {"message": "Érvénytelen token."}
            
            user = verification_result['user']
            
            # Validate password strength (Django's built-in validators)
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

# ============================================================================
# Documentation
# ============================================================================

AUTH_USAGE_DOCS = """
How to use JWT Authentication:

1. Login to get a token:
   POST /api/login
   Content-Type: application/x-www-form-urlencoded
   Body: username=your_username&password=your_password
   
   Response: {"token": "eyJ0eXAiOiJKV1QiLCJhbGc...", "username": "...", ...}

2. Use the token in subsequent requests:
   GET /api/profile
   Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
   
   OR
   
   GET /api/dashboard
   Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...

3. JavaScript/Frontend example:
   const token = "eyJ0eXAiOiJKV1QiLCJhbGc...";
   fetch('/api/profile', {
     headers: {
       'Authorization': `Bearer ${token}`
     }
   })

4. Python requests example:
   import requests
   headers = {'Authorization': 'Bearer eyJ0eXAiOiJKV1QiLCJhbGc...'}
   response = requests.get('http://localhost:8000/api/profile', headers=headers)

Note: Tokens expire after 1 hour. You'll need to login again to get a new token.
"""
