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
from api.models import Partner

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

# @api.get("/hello")
# def hello(request, name: str = "World"):
#     return f"Hello, {name}!"

# @api.get("/math")
# def math(request, a: int, b: int):
#     return {
#         "sum": a + b,
#         "difference": a - b,
#         "product": a * b,
#         "quotient": a / b if b != 0 else "Division by zero error"
#     }

# @api.get("/math/{a}and{b}")
# def math_path(request, a: int, b: int):
#     return {
#         "sum": a + b,
#         "difference": a - b,
#         "product": a * b,
#         "quotient": a / b if b != 0 else "Division by zero error"
#     }

# class HelloSchema(Schema):
#     name: str = "World"

# @api.post("/hello")
# def hello_post(request, data: HelloSchema):
#     return f"Hello, {data.name}!"

# Define a response Schema

# class UserSchema(Schema):
#     username: str
#     is_authenticated: bool
#     # Unauthenticated users don't have the following fields, so provide defaults
#     email: str = None
#     first_name: str = None
#     last_name: str = None

# @api.get("/me", response=UserSchema)
# def me(request):
#     user = request.user
#     return user

# Multiple response types

# class UserSchema(Schema):
#     username: str
#     email: str
#     first_name: str
#     last_name: str

# class ErrorSchema(Schema):
#     message: str

# @api.get("/me", response={200: UserSchema, 403: ErrorSchema})
# def me(request):
#     if not request.user.is_authenticated:
#         return 403, {"message": "You are not authenticated"}
#     return 200, request.user

@api.get("/partners", auth=jwt_auth)
def get_partners(request):
    partners = Partner.objects.all()

    response = [{"name": partner.name, "address": partner.address, "institution": partner.institution} for partner in partners]

    return response