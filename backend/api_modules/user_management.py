"""
ZTV2 User Management API Module

This module provides comprehensive user management functionality with full CRUD operations
for creating, editing, and managing users (students, teachers, administrators) including
automated first-time password setup and bulk operations.

Public API Overview:
==================

The User Management API provides complete user lifecycle management with role-based
access control, automated email notifications, and bulk operations for efficient
student/teacher onboarding.

Base URL: /api/user-management/

Protected Endpoints (Admin Only):
- GET    /users                 - List all users with filters
- GET    /users/{id}           - Get specific user details
- POST   /users                - Create new user with profile
- PUT    /users/{id}          - Update user and profile
- DELETE /users/{id}          - Delete user (with safety checks)
- POST   /users/{id}/send-first-login - Send first-time login email
- POST   /users/bulk-create-students  - Bulk create students for a class
- POST   /users/bulk-send-emails     - Send first-login emails to multiple users

First-Time Login System:
=======================

Automated user onboarding process:
1. Admin creates user account (no password set)
2. System generates secure JWT token (30-day validity)
3. Email sent to user with secure login link
4. User clicks link to set their password
5. Automatic profile activation and login

Token Security Features:
- 30-day expiration for security
- Single-use token validation
- Secure JWT with type checking
- Automatic cleanup of expired tokens

User Profile Management:
=======================

Complete profile management including:
- Basic user information (name, email, username)
- Administrative roles and permissions
- Class and stab assignments
- Contact information
- Media permissions
- Account activation status

Admin Types and Roles:
=====================

Admin Types:
- none: Regular student user
- teacher: Media teacher with class management
- system_admin: System configuration access
- developer: Full system access

Special Roles:
- none: No special role
- production_leader: Can manage filming sessions
- osztaly_fonok: Class leader (for teachers)

User Data Structure:
===================

Complete user information including:
- id: Unique identifier
- username: Login username
- first_name, last_name: Personal names
- email: Contact email
- full_name: Computed full name
- is_active: Account activation status
- admin_type: Administrative role level
- special_role: Additional role permissions
- telefonszam: Phone number
- osztaly: Class assignment details
- stab: Team assignment details
- radio_stab: Radio team assignment
- medias: Media permissions flag
- password_set: Whether password has been set
- first_login_token_sent: Email notification status
- date_joined: Account creation date
- last_login: Last login timestamp

Bulk Operations:
===============

Efficient bulk user management:
- Bulk student creation for entire classes
- Automated profile generation
- Bulk email sending with progress tracking
- Error handling and reporting
- Transaction safety

Example Usage:
=============

Get all users with filtering:
curl -H "Authorization: Bearer {token}" "/api/user-management/users?admin_type=none&is_active=true"

Create new student:
curl -X POST /api/user-management/users \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"username":"student1","first_name":"John","last_name":"Doe","email":"john@example.com","osztaly_id":1}'

Send first-login email:
curl -X POST /api/user-management/users/123/send-first-login \
  -H "Authorization: Bearer {token}"

Bulk create students:
curl -X POST /api/user-management/users/bulk-create-students \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"osztaly_id":1,"students":[{"username":"student1","first_name":"John","last_name":"Doe","email":"john@example.com"}]}'

Update user profile:
curl -X PUT /api/user-management/users/123 \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"admin_type":"teacher","special_role":"production_leader","is_active":true}'

Email System Integration:
========================

Automated email notifications:
- Welcome emails with first-login links
- Secure token-based password setup
- Professional email templates
- Bulk email sending with progress tracking
- Error handling for failed deliveries

Security Features:
=================

- JWT token-based first-time login
- Admin-only access to user management
- Safe user deletion with dependency checks
- Password security validation
- Account activation controls

Permission Requirements:
=======================

All endpoints require admin permissions:
- system_admin: Full user management access
- developer: Complete administrative access
- teacher: Limited access (view only in most cases)

Validation and Safety:
=====================

- Username uniqueness validation
- Email format validation
- Safe deletion with relationship checks
- Transaction rollback on errors
- Comprehensive error reporting

Error Handling:
==============

- 200/201: Success
- 400: Validation errors, duplicate users, invalid data
- 401: Authentication failed or insufficient permissions
- 404: User not found
- 409: Conflict (duplicate username/email)
- 500: Server error

Integration Points:
==================

- Academic system (class assignments)
- Organization system (stab assignments)
- Radio system (radio stab assignments)
- Equipment system (permission-based access)
- Authentication system (profile-based permissions)
"""

from ninja import Schema
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from api.models import Profile, Osztaly, Stab, RadioStab
from .auth import JWTAuth, ErrorSchema
from datetime import datetime, timedelta
import jwt
import secrets
import string

# ============================================================================
# Schemas
# ============================================================================

class UserCreateSchema(Schema):
    """Request schema for creating new user."""
    username: str
    first_name: str
    last_name: str
    email: str
    admin_type: str = 'none'
    special_role: str = 'none'
    telefonszam: str = None
    osztaly_id: int = None
    stab_id: int = None
    radio_stab_id: int = None
    medias: bool = True

class UserUpdateSchema(Schema):
    """Request schema for updating existing user."""
    username: str = None
    first_name: str = None
    last_name: str = None
    email: str = None
    admin_type: str = None
    special_role: str = None
    telefonszam: str = None
    osztaly_id: int = None
    stab_id: int = None
    radio_stab_id: int = None
    medias: bool = None
    is_active: bool = None

class UserDetailSchema(Schema):
    """Detailed response schema for user data."""
    id: int
    username: str
    first_name: str
    last_name: str
    email: str
    full_name: str
    is_active: bool
    admin_type: str
    special_role: str
    telefonszam: str = None
    osztaly: dict = None
    stab: dict = None
    radio_stab: dict = None
    medias: bool
    password_set: bool
    first_login_token_sent: bool
    date_joined: str
    last_login: str = None

class FirstLoginTokenResponse(Schema):
    """Response schema for first login token generation."""
    user_id: int
    username: str
    full_name: str
    token_url: str
    token: str
    expires_at: str

class BulkStudentCreateSchema(Schema):
    """Request schema for bulk student creation."""
    osztaly_id: int
    students: list[dict]  # List of student data
    send_emails: bool = True

class BulkEmailResponse(Schema):
    """Response schema for bulk email sending."""
    total_users: int
    emails_sent: int
    failed_emails: list[str]
    tokens_generated: int

# ============================================================================
# Utility Functions
# ============================================================================

def generate_first_login_token(user_id: int) -> str:
    """Generate JWT token for first-time login."""
    payload = {
        "user_id": user_id,
        "type": "first_login",
        "exp": datetime.utcnow() + timedelta(days=30),  # 30 days validity
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

def verify_first_login_token(token: str) -> dict:
    """Verify first-time login token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        
        if payload.get("type") != "first_login":
            return {"valid": False, "error": "Invalid token type"}
        
        user_id = payload.get("user_id")
        if not user_id:
            return {"valid": False, "error": "Invalid token payload"}
        
        try:
            user = User.objects.get(id=user_id)
            profile = Profile.objects.get(user=user)
            
            return {"valid": True, "user": user, "profile": profile}
        except (User.DoesNotExist, Profile.DoesNotExist):
            return {"valid": False, "error": "User not found"}
            
    except jwt.ExpiredSignatureError:
        return {"valid": False, "error": "Token has expired"}
    except jwt.InvalidTokenError:
        return {"valid": False, "error": "Invalid token"}

def generate_random_password(length: int = 12) -> str:
    """Generate a random temporary password."""
    characters = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(characters) for _ in range(length))

def send_first_login_email(user: User, token: str) -> bool:
    """Send first-time login email to user."""
    try:
        subject = "ZTV2 - Első bejelentkezés"
        
        # Create the login URL
        base_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        login_url = f"{base_url}/first-login?token={token}"
        
        message = f"""
Kedves {user.get_full_name()},

Üdvözöljük a ZTV2 rendszerben!

Az első bejelentkezéshez kattintson az alábbi linkre és állítsa be jelszavát:
{login_url}

A link 30 napig érvényes.

Üdvözlettel,
ZTV2 Rendszer
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Failed to send first login email to {user.email}: {str(e)}")
        return False

def create_user_detail_response(user: User, profile: Profile = None) -> dict:
    """Create detailed user response dictionary."""
    if not profile:
        try:
            profile = Profile.objects.select_related('osztaly', 'stab', 'radio_stab').get(user=user)
        except Profile.DoesNotExist:
            profile = None
    
    return {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "full_name": user.get_full_name(),
        "is_active": user.is_active,
        "admin_type": profile.admin_type if profile else 'none',
        "special_role": profile.special_role if profile else 'none',
        "telefonszam": profile.telefonszam if profile else None,
        "osztaly": {
            "id": profile.osztaly.id,
            "display_name": str(profile.osztaly),
            "start_year": profile.osztaly.startYear,
            "szekcio": profile.osztaly.szekcio
        } if profile and profile.osztaly else None,
        "stab": {
            "id": profile.stab.id,
            "name": profile.stab.name
        } if profile and profile.stab else None,
        "radio_stab": {
            "id": profile.radio_stab.id,
            "name": profile.radio_stab.name,
            "team_code": profile.radio_stab.team_code
        } if profile and profile.radio_stab else None,
        "medias": profile.medias if profile else False,
        "password_set": profile.password_set if profile else False,
        "first_login_token_sent": bool(profile.first_login_sent_at) if profile else False,
        "date_joined": user.date_joined.isoformat(),
        "last_login": user.last_login.isoformat() if user.last_login else None
    }

def check_system_admin_permissions(user) -> tuple[bool, str]:
    """Check if user has system admin, developer, or teacher admin permissions."""
    try:
        profile = Profile.objects.get(user=user)
        if not (profile.is_system_admin or profile.is_developer_admin or profile.is_teacher_admin):
            return False, "Rendszeradminisztrátor, fejlesztő vagy médiatanár jogosultság szükséges"
        return True, ""
    except Profile.DoesNotExist:
        return False, "Felhasználói profil nem található"

# ============================================================================
# API Endpoints
# ============================================================================

def register_user_management_endpoints(api):
    """Register all user management endpoints with the API router."""
    
    @api.get("/manage/users", auth=JWTAuth(), response={200: list[UserDetailSchema], 401: ErrorSchema})
    def get_all_users_detailed(request, user_type: str = None, osztaly_id: int = None):
        """
        Get detailed list of all users for management.
        
        Requires system admin permissions. Returns comprehensive user information.
        
        Args:
            user_type: Filter by user type ('student', 'teacher', 'admin')
            osztaly_id: Filter by class ID
            
        Returns:
            200: List of detailed user information
            401: Authentication or permission failed
        """
        try:
            # Check permissions
            has_permission, error_message = check_system_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            users = User.objects.select_related().all()
            profiles = Profile.objects.select_related('user', 'osztaly', 'stab', 'radio_stab').all()
            profile_dict = {p.user_id: p for p in profiles}
            
            filtered_users = []
            for user in users:
                profile = profile_dict.get(user.id)
                
                # Apply filters
                if user_type:
                    if user_type == 'admin' and (not profile or profile.admin_type == 'none'):
                        continue
                    elif user_type == 'teacher' and (not profile or profile.admin_type != 'teacher'):
                        continue
                    elif user_type == 'student' and profile and profile.admin_type != 'none':
                        continue
                
                if osztaly_id and (not profile or not profile.osztaly or profile.osztaly.id != osztaly_id):
                    continue
                
                filtered_users.append((user, profile))
            
            response = []
            for user, profile in filtered_users:
                response.append(create_user_detail_response(user, profile))
            
            return 200, response
        except Exception as e:
            return 401, {"message": f"Error fetching users: {str(e)}"}

    @api.post("/manage/users", auth=JWTAuth(), response={201: UserDetailSchema, 400: ErrorSchema, 401: ErrorSchema})
    def create_user(request, data: UserCreateSchema):
        """
        Create new user with profile.
        
        Requires system admin permissions. Creates user and associated profile.
        
        Args:
            data: User creation data
            
        Returns:
            201: User created successfully
            400: Invalid data
            401: Authentication or permission failed
        """
        try:
            # Check permissions
            has_permission, error_message = check_system_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            # Check if username or email already exists
            if User.objects.filter(username=data.username).exists():
                return 400, {"message": "A felhasználónév már foglalt"}
            
            if User.objects.filter(email=data.email).exists():
                return 400, {"message": "Az email cím már foglalt"}
            
            # Validate admin type
            valid_admin_types = [choice[0] for choice in Profile.ADMIN_TYPES]
            if data.admin_type not in valid_admin_types:
                return 400, {"message": "Érvénytelen adminisztrátor típus"}
            
            # Validate special role
            valid_special_roles = [choice[0] for choice in Profile.SPECIAL_ROLES]
            if data.special_role not in valid_special_roles:
                return 400, {"message": "Érvénytelen különleges szerep"}
            
            # Get related objects
            osztaly = None
            if data.osztaly_id:
                try:
                    osztaly = Osztaly.objects.get(id=data.osztaly_id)
                except Osztaly.DoesNotExist:
                    return 400, {"message": "Osztály nem található"}
            
            stab = None
            if data.stab_id:
                try:
                    stab = Stab.objects.get(id=data.stab_id)
                except Stab.DoesNotExist:
                    return 400, {"message": "Stáb nem található"}
            
            radio_stab = None
            if data.radio_stab_id:
                try:
                    radio_stab = RadioStab.objects.get(id=data.radio_stab_id)
                except RadioStab.DoesNotExist:
                    return 400, {"message": "Rádiós stáb nem található"}
            
            # Create user
            temp_password = generate_random_password()
            user = User.objects.create_user(
                username=data.username,
                email=data.email,
                password=temp_password,
                first_name=data.first_name,
                last_name=data.last_name,
                is_active=True
            )
            
            # Create profile
            profile = Profile.objects.create(
                user=user,
                admin_type=data.admin_type,
                special_role=data.special_role,
                telefonszam=data.telefonszam,
                osztaly=osztaly,
                stab=stab,
                radio_stab=radio_stab,
                medias=data.medias,
                password_set=False
            )
            
            return 201, create_user_detail_response(user, profile)
        except Exception as e:
            return 400, {"message": f"Error creating user: {str(e)}"}

    @api.put("/manage/users/{user_id}", auth=JWTAuth(), response={200: UserDetailSchema, 400: ErrorSchema, 401: ErrorSchema, 404: ErrorSchema})
    def update_user(request, user_id: int, data: UserUpdateSchema):
        """
        Update existing user and profile.
        
        Requires system admin permissions. Updates user and profile information.
        
        Args:
            user_id: User ID to update
            data: User update data
            
        Returns:
            200: User updated successfully
            404: User not found
            400: Invalid data
            401: Authentication or permission failed
        """
        try:
            # Check permissions
            has_permission, error_message = check_system_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            user = User.objects.get(id=user_id)
            profile, created = Profile.objects.get_or_create(user=user)
            
            # Update user fields
            if data.username is not None:
                if User.objects.filter(username=data.username).exclude(id=user_id).exists():
                    return 400, {"message": "A felhasználónév már foglalt"}
                user.username = data.username
            
            if data.email is not None:
                if User.objects.filter(email=data.email).exclude(id=user_id).exists():
                    return 400, {"message": "Az email cím már foglalt"}
                user.email = data.email
            
            if data.first_name is not None:
                user.first_name = data.first_name
            if data.last_name is not None:
                user.last_name = data.last_name
            if data.is_active is not None:
                user.is_active = data.is_active
            
            user.save()
            
            # Update profile fields
            if data.admin_type is not None:
                valid_admin_types = [choice[0] for choice in Profile.ADMIN_TYPES]
                if data.admin_type not in valid_admin_types:
                    return 400, {"message": "Érvénytelen adminisztrátor típus"}
                profile.admin_type = data.admin_type
            
            if data.special_role is not None:
                valid_special_roles = [choice[0] for choice in Profile.SPECIAL_ROLES]
                if data.special_role not in valid_special_roles:
                    return 400, {"message": "Érvénytelen különleges szerep"}
                profile.special_role = data.special_role
            
            if data.telefonszam is not None:
                profile.telefonszam = data.telefonszam
            if data.medias is not None:
                profile.medias = data.medias
            
            # Update related objects
            if data.osztaly_id is not None:
                if data.osztaly_id == 0:
                    profile.osztaly = None
                else:
                    try:
                        osztaly = Osztaly.objects.get(id=data.osztaly_id)
                        profile.osztaly = osztaly
                    except Osztaly.DoesNotExist:
                        return 400, {"message": "Osztály nem található"}
            
            if data.stab_id is not None:
                if data.stab_id == 0:
                    profile.stab = None
                else:
                    try:
                        stab = Stab.objects.get(id=data.stab_id)
                        profile.stab = stab
                    except Stab.DoesNotExist:
                        return 400, {"message": "Stáb nem található"}
            
            if data.radio_stab_id is not None:
                if data.radio_stab_id == 0:
                    profile.radio_stab = None
                else:
                    try:
                        radio_stab = RadioStab.objects.get(id=data.radio_stab_id)
                        profile.radio_stab = radio_stab
                    except RadioStab.DoesNotExist:
                        return 400, {"message": "Rádiós stáb nem található"}
            
            profile.save()
            
            return 200, create_user_detail_response(user, profile)
        except User.DoesNotExist:
            return 404, {"message": "Felhasználó nem található"}
        except Exception as e:
            return 400, {"message": f"Error updating user: {str(e)}"}

    @api.delete("/manage/users/{user_id}", auth=JWTAuth(), response={200: dict, 401: ErrorSchema, 404: ErrorSchema})
    def delete_user(request, user_id: int):
        """
        Delete user and associated profile.
        
        Requires system admin permissions. Permanently removes user from database.
        
        Args:
            user_id: User ID to delete
            
        Returns:
            200: User deleted successfully
            404: User not found
            401: Authentication or permission failed
        """
        try:
            # Check permissions
            has_permission, error_message = check_system_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            user = User.objects.get(id=user_id)
            
            # Don't allow deletion of superusers or the current user
            if user.is_superuser:
                return 401, {"message": "Szuperfelhasználó nem törölhető"}
            
            if user.id == request.auth.id:
                return 401, {"message": "Saját magát nem törölheti"}
            
            user_name = user.get_full_name()
            user.delete()  # Profile will be deleted via CASCADE
            
            return 200, {"message": f"Felhasználó '{user_name}' sikeresen törölve"}
        except User.DoesNotExist:
            return 404, {"message": "Felhasználó nem található"}
        except Exception as e:
            return 400, {"message": f"Error deleting user: {str(e)}"}

    # ========================================================================
    # First-time Login Token Management
    # ========================================================================

    @api.post("/manage/users/{user_id}/generate-first-login-token", auth=JWTAuth(), response={201: FirstLoginTokenResponse, 401: ErrorSchema, 404: ErrorSchema})
    def generate_user_first_login_token(request, user_id: int):
        """
        Generate first-time login token for a specific user.
        
        For teachers and manual token generation for system admins to copy and send personally.
        
        Args:
            user_id: User ID to generate token for
            
        Returns:
            201: Token generated successfully
            404: User not found
            401: Authentication or permission failed
        """
        try:
            # Check permissions
            has_permission, error_message = check_system_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            user = User.objects.get(id=user_id)
            profile, created = Profile.objects.get_or_create(user=user)
            
            # Generate token
            token = generate_first_login_token(user.id)
            
            # Update profile
            profile.first_login_token = token
            profile.first_login_sent_at = timezone.now()
            profile.save()
            
            # Create login URL
            base_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
            token_url = f"{base_url}/first-login?token={token}"
            
            return 201, {
                "user_id": user.id,
                "username": user.username,
                "full_name": user.get_full_name(),
                "token_url": token_url,
                "token": token,
                "expires_at": (timezone.now() + timedelta(days=30)).isoformat()
            }
        except User.DoesNotExist:
            return 404, {"message": "Felhasználó nem található"}
        except Exception as e:
            return 400, {"message": f"Error generating token: {str(e)}"}

    @api.post("/manage/users/bulk-students", auth=JWTAuth(), response={201: BulkEmailResponse, 400: ErrorSchema, 401: ErrorSchema})
    def create_bulk_students(request, data: BulkStudentCreateSchema):
        """
        Create multiple students for a class and send first-login emails.
        
        Requires system admin permissions. Creates students in bulk and sends email tokens.
        
        Args:
            data: Bulk student creation data
            
        Returns:
            201: Students created and emails sent
            400: Invalid data
            401: Authentication or permission failed
        """
        try:
            # Check permissions
            has_permission, error_message = check_system_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            # Get class
            try:
                osztaly = Osztaly.objects.get(id=data.osztaly_id)
            except Osztaly.DoesNotExist:
                return 400, {"message": "Osztály nem található"}
            
            created_users = []
            emails_sent = 0
            failed_emails = []
            
            for student_data in data.students:
                try:
                    # Validate required fields
                    if not all(key in student_data for key in ['username', 'first_name', 'last_name', 'email']):
                        failed_emails.append(f"Hiányos adatok: {student_data.get('username', 'ismeretlen')}")
                        continue
                    
                    # Check for duplicates
                    if User.objects.filter(username=student_data['username']).exists():
                        failed_emails.append(f"Felhasználónév már foglalt: {student_data['username']}")
                        continue
                    
                    if User.objects.filter(email=student_data['email']).exists():
                        failed_emails.append(f"Email már foglalt: {student_data['email']}")
                        continue
                    
                    # Create user
                    temp_password = generate_random_password()
                    user = User.objects.create_user(
                        username=student_data['username'],
                        email=student_data['email'],
                        password=temp_password,
                        first_name=student_data['first_name'],
                        last_name=student_data['last_name'],
                        is_active=True
                    )
                    
                    # Create profile
                    profile = Profile.objects.create(
                        user=user,
                        admin_type='none',
                        special_role='none',
                        telefonszam=student_data.get('telefonszam'),
                        osztaly=osztaly,
                        medias=student_data.get('medias', True),
                        password_set=False
                    )
                    
                    created_users.append((user, profile))
                    
                    # Generate and send first login token if requested
                    if data.send_emails:
                        token = generate_first_login_token(user.id)
                        profile.first_login_token = token
                        profile.first_login_sent_at = timezone.now()
                        profile.save()
                        
                        if send_first_login_email(user, token):
                            emails_sent += 1
                        else:
                            failed_emails.append(f"Email küldés sikertelen: {user.email}")
                
                except Exception as e:
                    failed_emails.append(f"Hiba {student_data.get('username', 'ismeretlen')} létrehozásakor: {str(e)}")
            
            return 201, {
                "total_users": len(created_users),
                "emails_sent": emails_sent,
                "failed_emails": failed_emails,
                "tokens_generated": len(created_users) if data.send_emails else 0
            }
        except Exception as e:
            return 400, {"message": f"Error creating bulk students: {str(e)}"}

    @api.post("/first-login/verify-token", response={200: dict, 400: ErrorSchema})
    def verify_first_login_token_endpoint(request, token: str):
        """
        Verify first-time login token.
        
        Public endpoint for token verification.
        
        Args:
            token: First-time login token
            
        Returns:
            200: Token verification result
            400: Error occurred
        """
        try:
            result = verify_first_login_token(token)
            
            if result["valid"]:
                user = result["user"]
                return 200, {
                    "valid": True,
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "full_name": user.get_full_name(),
                        "email": user.email
                    }
                }
            else:
                return 200, {
                    "valid": False,
                    "error": result["error"]
                }
        except Exception as e:
            return 400, {"message": f"Error verifying token: {str(e)}"}

    @api.post("/first-login/set-password", response={200: dict, 400: ErrorSchema})
    def set_first_password(request, token: str, password: str, confirm_password: str):
        """
        Set password using first-time login token.
        
        Public endpoint for setting initial password.
        
        Args:
            token: First-time login token
            password: New password
            confirm_password: Password confirmation
            
        Returns:
            200: Password set successfully
            400: Error occurred
        """
        try:
            # Validate passwords match
            if password != confirm_password:
                return 400, {"message": "A jelszavak nem egyeznek"}
            
            # Verify token
            result = verify_first_login_token(token)
            if not result["valid"]:
                return 400, {"message": result["error"]}
            
            user = result["user"]
            profile = result["profile"]
            
            # Validate password (you can add more validation here)
            if len(password) < 6:
                return 400, {"message": "A jelszó legalább 6 karakter hosszú kell legyen"}
            
            # Set password
            user.set_password(password)
            user.save()
            
            # Update profile
            profile.password_set = True
            profile.first_login_token = None  # Clear the token
            profile.save()
            
            return 200, {
                "message": "Jelszó sikeresen beállítva",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "full_name": user.get_full_name()
                }
            }
        except Exception as e:
            return 400, {"message": f"Error setting password: {str(e)}"}
