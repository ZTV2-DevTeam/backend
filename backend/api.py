from ninja import NinjaAPI, Schema, Form
from ninja.security import HttpBearer
from django.contrib.auth.models import User, Group
from django.db import models
from django.http import HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import jwt
from django.conf import settings
from datetime import datetime, timedelta
from api.models import *
from django.core.mail import send_mail
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone

token_expiration_time: timedelta = timedelta(hours=1)  # Token expiration time

# JWT Authentication Class
class JWTAuth(HttpBearer):
    def authenticate(self, request: HttpRequest, token: str):
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

jwt_auth = JWTAuth()
api = NinjaAPI(csrf=False)  # Disable CSRF for API endpoints

@api.get("/hello")
def hello(request, name: str = "World"):
    return f"Hello, {name}!"

@api.get("/test-auth")
def test_auth(request):
    """Test endpoint to check if basic API is working"""
    return {
        "message": "API is working!",
        "user_authenticated": request.user.is_authenticated if hasattr(request, 'user') else False,
        "timestamp": datetime.utcnow().isoformat()
    }

class LoginSchema(Schema):
    token: str
    user_id: int
    username: str
    first_name: str
    last_name: str
    email: str

class ErrorSchema(Schema):
    message: str

class ForgotPasswordRequest(Schema):
    email: str

class ForgotPasswordResponse(Schema):
    message: str

class ResetPasswordRequest(Schema):
    token: str
    password: str
    confirmPassword: str

class ResetPasswordResponse(Schema):
    message: str

class VerifyTokenResponse(Schema):
    valid: bool

# class CreateUserSchema(Schema):
#     username: str
#     password: str
#     email: str = ""
#     first_name: str = ""
#     last_name: str = ""

# @api.post("/create-user", response={201: LoginSchema, 400: ErrorSchema})
# def create_user(request, data: CreateUserSchema):
#     """Create a new user for testing purposes"""
#     try:
#         # Check if user already exists
#         if User.objects.filter(username=data.username).exists():
#             return 400, {"message": "User already exists"}
        
#         # Create new user
#         user = User.objects.create_user(
#             username=data.username,
#             password=data.password,
#             email=data.email,
#             first_name=data.first_name,
#             last_name=data.last_name
#         )
        
#         # Generate token for the new user
#         payload = {
#             "user_id": user.id,
#             "username": user.username,
#             "exp": datetime.utcnow() + token_expiration_time,
#             "iat": datetime.utcnow(),
#         }
#         token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        
#         return 201, {
#             "token": token,
#             "user_id": user.id,
#             "username": user.username,
#             "first_name": user.first_name,
#             "last_name": user.last_name,
#             "email": user.email,
#         }
#     except Exception as e:
#         return 400, {"message": f"Error creating user: {str(e)}"}

@api.post("/login", response={200: LoginSchema, 401: ErrorSchema})
def login(request, username: Form[str], password: Form[str]):
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

    payload = {
        "user_id": user.id,
        "username": user.username,
        "exp": datetime.utcnow() + token_expiration_time,
        "iat": datetime.utcnow(),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    print(f"Login successful for user {username}, token generated")  # Debug print

    return 200, {
        "token": token,
        "user_id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
    }

# Protected endpoint example - requires JWT token
@api.get("/profile", auth=jwt_auth, response={200: LoginSchema, 401: ErrorSchema})
def get_profile(request):
    """Get current user's profile - requires JWT token"""
    user = request.auth  # This is the authenticated user from JWT
    return 200, {
        "token": "current_session",  # You might want to generate a new token or return empty
        "user_id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
    }

# Another protected endpoint example
@api.get("/dashboard", auth=jwt_auth)
def dashboard(request):
    """Protected dashboard endpoint"""
    user = request.auth
    return {
        "message": f"Welcome to your dashboard, {user.username}!",
        "user_id": user.id,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
    }

"""
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

# Token refresh endpoint
@api.post("/refresh-token", auth=jwt_auth, response={200: dict, 401: ErrorSchema})
def refresh_token(request):
    """Refresh the JWT token - requires valid existing token"""
    user = request.auth
    
    payload = {
        "user_id": user.id,
        "username": user.username,
        "exp": datetime.utcnow() + token_expiration_time,
        "iat": datetime.utcnow(),
    }
    new_token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    
    return 200, {
        "token": new_token,
        "message": "Token refreshed successfully"
    }

# Logout endpoint (informational - JWT tokens can't be truly invalidated without a blacklist)
@api.post("/logout", auth=jwt_auth)
def logout(request):
    """Logout endpoint - client should discard the token"""
    user = request.auth
    return {
        "message": f"Goodbye, {user.username}! Please discard your token.",
        "note": "JWT tokens cannot be invalidated server-side without a blacklist. Ensure your client discards the token."
    }

class PartnerSchema(Schema):
    id: int
    name: str
    address: str = ""
    institution: str = None
    imageURL: str = None

class PartnerCreateSchema(Schema):
    name: str
    address: str = ""
    institution: str = None
    imageURL: str = None

class PartnerUpdateSchema(Schema):
    name: str = None
    address: str = None
    institution: str = None
    imageURL: str = None

# Partner Endpoints

@api.get("/partners", response={200: list[PartnerSchema], 401: ErrorSchema})
def get_partners(request):
    """
    GET /api/partners
    Purpose: Fetch all partners
    """
    try:
        partners = Partner.objects.select_related('institution').all()
        
        response = []
        for partner in partners:
            response.append({
                "id": partner.id,
                "name": partner.name,
                "address": partner.address or "",
                "institution": partner.institution.name if partner.institution else None,
                "imageURL": partner.imgUrl
            })
        
        return 200, response
    except Exception as e:
        return 401, {"message": f"Error fetching partners: {str(e)}"}

@api.get("/partners/{partner_id}", response={200: PartnerSchema, 401: ErrorSchema, 404: ErrorSchema})
def get_partner(request, partner_id: int):
    """
    GET /api/partners/{id}
    Purpose: Fetch a single partner by ID
    """
    try:
        partner = Partner.objects.select_related('institution').get(id=partner_id)
        
        return 200, {
            "id": partner.id,
            "name": partner.name,
            "address": partner.address or "",
            "institution": partner.institution.name if partner.institution else None,
            "imageURL": partner.imgUrl
        }
    except Partner.DoesNotExist:
        return 404, {"message": "Partner not found"}
    except Exception as e:
        return 401, {"message": f"Error fetching partner: {str(e)}"}

@api.post("/partners", auth=jwt_auth, response={201: PartnerSchema, 400: ErrorSchema, 401: ErrorSchema})
def create_partner(request, data: PartnerCreateSchema):
    """
    POST /api/partners
    Purpose: Create a new partner
    """
    try:
        # Handle institution lookup if provided
        institution_obj = None
        if data.institution:
            institution_obj, created = PartnerTipus.objects.get_or_create(name=data.institution)
        
        partner = Partner.objects.create(
            name=data.name,
            address=data.address or "",
            institution=institution_obj,
            imgUrl=data.imageURL
        )
        
        return 201, {
            "id": partner.id,
            "name": partner.name,
            "address": partner.address or "",
            "institution": partner.institution.name if partner.institution else None,
            "imageURL": partner.imgUrl
        }
    except Exception as e:
        if "UNIQUE constraint failed" in str(e) or "duplicate key" in str(e):
            return 400, {"message": "Partner with this name already exists"}
        return 400, {"message": f"Error creating partner: {str(e)}"}

@api.put("/partners/{partner_id}", auth=jwt_auth, response={200: PartnerSchema, 400: ErrorSchema, 401: ErrorSchema, 404: ErrorSchema})
def update_partner(request, partner_id: int, data: PartnerUpdateSchema):
    """
    PUT /api/partners/{id}
    Purpose: Update an existing partner
    """
    try:
        partner = Partner.objects.get(id=partner_id)
        
        # Update fields only if they are provided (not None)
        if data.name is not None:
            partner.name = data.name
        if data.address is not None:
            partner.address = data.address
        if data.imageURL is not None:
            partner.imgUrl = data.imageURL
        if data.institution is not None:
            if data.institution == "":
                partner.institution = None
            else:
                institution_obj, created = PartnerTipus.objects.get_or_create(name=data.institution)
                partner.institution = institution_obj
        
        partner.save()
        
        return 200, {
            "id": partner.id,
            "name": partner.name,
            "address": partner.address or "",
            "institution": partner.institution.name if partner.institution else None,
            "imageURL": partner.imgUrl
        }
    except Partner.DoesNotExist:
        return 404, {"message": "Partner not found"}
    except Exception as e:
        if "UNIQUE constraint failed" in str(e) or "duplicate key" in str(e):
            return 400, {"message": "Partner with this name already exists"}
        return 400, {"message": f"Error updating partner: {str(e)}"}

@api.delete("/partners/{partner_id}", auth=jwt_auth, response={200: dict, 401: ErrorSchema, 404: ErrorSchema})
def delete_partner(request, partner_id: int):
    """
    DELETE /api/partners/{id}
    Purpose: Delete a specific partner
    """
    try:
        partner = Partner.objects.get(id=partner_id)
        partner_name = partner.name
        partner.delete()
        
        return 200, {"message": f"Partner '{partner_name}' deleted successfully"}
    except Partner.DoesNotExist:
        return 404, {"message": "Partner not found"}
    except Exception as e:
        return 400, {"message": f"Error deleting partner: {str(e)}"}

# Password Reset Endpoints

@api.post("/forgot-password", response={200: ForgotPasswordResponse, 400: ErrorSchema})
def forgot_password(request, data: ForgotPasswordRequest):
    """
    POST /api/forgot-password
    Purpose: Request password reset token via email
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
    GET /api/verify-reset-token/{token}
    Purpose: Verify if reset token is valid
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
    POST /api/reset-password
    Purpose: Reset user password using valid token
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