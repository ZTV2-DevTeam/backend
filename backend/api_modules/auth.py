"""
FTV Authentication API Module

This module provides basic JWT authentication functionality for the FTV system.
For comprehensive password management (first login, password reset), see the 
authentication module.

Public API Overview:
==================

Base URL: /api/

Basic Authentication Endpoints:
- POST /login                    - User login with username/password  
- GET  /profile                  - Get current user profile
- GET  /dashboard               - Access user dashboard
- POST /refresh-token           - Refresh JWT token
- POST /logout                  - User logout

Authentication Flow:
==================

1. Login with username/password to receive JWT token
2. Include token in Authorization header: "Bearer {token}"
3. Tokens expire after 8 hours - use refresh-token endpoint

For password reset and first-time login, use the authentication module endpoints:
- /first-login/* endpoints for first-time password setup
- /forgot-password and /reset-password endpoints for password reset
- /password-validation/* endpoints for password strength checking

Error Handling:
==============

All endpoints return consistent error responses:
- 200: Success
- 401: Unauthorized (invalid credentials/token)
- 500: Server error

Example Usage:
=============

Login:
curl -X POST /api/login -d "username=testuser&password=password123"

Authenticated request:
curl -H "Authorization: Bearer {your-jwt-token}" /api/profile

For detailed examples and schemas, see the interactive documentation.
"""

from ninja import Schema, Form
from ninja.security import HttpBearer
from django.contrib.auth.models import User
from django.http import HttpRequest
import jwt
from django.conf import settings
from datetime import datetime, timedelta, timezone

# Configuration
TOKEN_EXPIRATION_TIME = timedelta(hours=8)  # Extended to 8 hours for better user experience

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
            print(f"JWT payload decoded successfully: user_id={payload.get('user_id')}")  # Debug
            
            user_id = payload.get("user_id")
            if user_id:
                user = User.objects.get(id=user_id)
                if not user.is_active:  # Check if user is active
                    print(f"User {user.username} is not active")  # Debug
                    return None
                # Az aktuális tanévhez nem tartozó (nem tanár/admin) diákok
                # tokenjét is elutasítjuk, hogy a régi tokennel se lehessen
                # bejutni a rendszer erőforrásaiba.
                allowed, deny_reason = is_user_allowed_for_current_tanev(user)
                if not allowed:
                    print(f"User {user.username} not allowed for current tanev: {deny_reason}")
                    return None
                print(f"User {user.username} authenticated successfully")  # Debug
                user.last_login = datetime.now()
                user.save(update_fields=["last_login"])
                return user
            else:
                print("No user_id in JWT payload")  # Debug
                return None
                    
        except jwt.ExpiredSignatureError:
            print("JWT token has expired - user should refresh or re-login")
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

# ============================================================================
# Utility Functions
# ============================================================================

def is_user_allowed_for_current_tanev(user: User) -> tuple[bool, str]:
    """Ellenőrzi, hogy egy felhasználó bejelentkezhet-e az aktuális tanév alapján.

    A rendszer több ``Tanev`` objektumot is kezel egyidejűleg, ezért ez a
    függvény azt vizsgálja, hogy a felhasználó osztálya benne van-e a
    jelenleg aktív tanév ``osztalyok`` M2M kapcsolatában. Kivételek:
    tanárok, adminisztrátorok, osztályfőnökök (illetve a Django staff/
    superuser) mindig beléphetnek, mert az ő szerepük nincs egyetlen
    tanévhez kötve.

    Args:
        user: A hitelesített ``auth.User`` példány

    Returns:
        Tuple ``(allowed, reason)``. ``allowed`` True, ha bejelentkezhet;
        egyébként ``reason`` egy magyar nyelvű, felhasználónak megjeleníthető
        üzenet.
    """
    # Django-szintű privilegizált fiókok mindig beléphetnek.
    if user.is_superuser or user.is_staff:
        return True, ""

    try:
        from api.models import Profile, Tanev, Osztaly
    except Exception as e:  # pragma: no cover - very unlikely
        print(f"is_user_allowed_for_current_tanev import error: {e}")
        return True, ""

    # Adminisztrátorok/tanárok/osztályfőnökök szintén mindig beléphetnek.
    try:
        profile = Profile.objects.select_related('osztaly').get(user=user)
    except Profile.DoesNotExist:
        # Nincs profil -> nem diák, engedjük bejelentkezni (pl. új admin).
        return True, ""

    if profile.is_admin:
        return True, ""
    if Osztaly.objects.filter(osztaly_fonokei=user).exists():
        return True, ""

    active_tanev = Tanev.get_active()
    if active_tanev is None:
        # Nincs beállított aktív tanév: nem tudjuk kikényszeríteni a
        # korlátozást, ezért a régi viselkedést tartjuk és engedjük belépni.
        return True, ""

    if profile.osztaly is None:
        return False, (
            "A felhasználó nincs osztályhoz rendelve, ezért az aktuális tanévben "
            "nem jelentkezhet be. Fordulj a médiatanárhoz."
        )

    if not active_tanev.osztalyok.filter(pk=profile.osztaly_id).exists():
        return False, (
            "A felhasználó osztálya nem tartozik az aktuális tanévhez, ezért "
            "a bejelentkezés le van tiltva."
        )

    return True, ""


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
    from backend.api_modules.users import get_or_create_user_profile_response

    profile_response = get_or_create_user_profile_response(user)

    return {
        "token": token or "current_session",
        "user_id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        **profile_response,  # Merge profile response fields
    }

# ============================================================================
# API Endpoints
# ============================================================================

def register_auth_endpoints(api):
    """Register all authentication endpoints with the API router."""
    
    @api.post("/login", response={200: LoginSchema, 401: ErrorSchema, 403: ErrorSchema})
    def login(request, username: Form[str], password: Form[str]):
        """
        User login endpoint.
        
        Authenticates user credentials and returns JWT token.

        Note: A rendszer csak azoknak a diákoknak engedi a bejelentkezést,
        akiknek az osztálya az aktuálisan aktív tanévhez van rendelve.
        Tanárok, adminisztrátorok és osztályfőnökök mindig beléphetnek,
        függetlenül a tanévi hozzárendelésektől.
        
        Args:
            username: User's username
            password: User's password
            
        Returns:
            200: Login successful with token and user info
            401: Authentication failed
            403: Login denied (user is not in the current school year)
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

        # Csak az aktuális tanévhez tartozó diákok jelentkezhetnek be.
        # A tanárok/adminok/osztályfőnökök kivételek.
        allowed, deny_reason = is_user_allowed_for_current_tanev(user)
        if not allowed:
            print(f"User {username} not allowed for current tanev: {deny_reason}")
            return 403, {"message": deny_reason}

        # Update user's last login timestamp on successful authentication
        from django.utils import timezone
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        token = generate_jwt_token(user)
        print(f"Login successful for user {username}, token generated, last_login updated")  # Debug print

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

Note: Tokens expire after 8 hours. You can use /api/refresh-token to get a new token,
or login again if needed.

For password management (reset, first login), use the authentication module endpoints:
- POST /api/first-login/request-token
- POST /api/first-login/set-password  
- POST /api/forgot-password
- POST /api/reset-password
- GET /api/password-validation/rules
"""
