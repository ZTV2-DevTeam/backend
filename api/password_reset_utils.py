import jwt
import uuid
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def generate_password_reset_token(user_id: int) -> str:
    """
    Generate a JWT token for password reset
    
    Args:
        user_id: The ID of the user requesting password reset
        
    Returns:
        JWT token string
    """
    payload = {
        'user_id': user_id,
        'purpose': 'password_reset',
        'exp': datetime.utcnow() + timedelta(seconds=settings.PASSWORD_RESET_TIMEOUT),
        'iat': datetime.utcnow(),
        'jti': str(uuid.uuid4())  # Unique token ID
    }
    
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')


def verify_password_reset_token(token: str) -> dict:
    """
    Verify and decode password reset token
    
    Args:
        token: JWT token string
        
    Returns:
        dict with 'valid' boolean and 'user_id' if valid
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        
        # Check if token is for password reset
        if payload.get('purpose') != 'password_reset':
            return {'valid': False, 'error': 'Invalid token purpose'}
        
        user_id = payload.get('user_id')
        if not user_id:
            return {'valid': False, 'error': 'Missing user ID'}
        
        # Check if user exists and is active
        try:
            user = User.objects.get(id=user_id)
            if not user.is_active:
                return {'valid': False, 'error': 'User is not active'}
        except User.DoesNotExist:
            return {'valid': False, 'error': 'User does not exist'}
        
        return {'valid': True, 'user_id': user_id, 'user': user}
        
    except jwt.ExpiredSignatureError:
        return {'valid': False, 'error': 'Token has expired'}
    except jwt.InvalidTokenError:
        return {'valid': False, 'error': 'Invalid token'}
    except Exception as e:
        return {'valid': False, 'error': str(e)}


def send_password_reset_email(user: User, reset_token: str, frontend_url: str = "https://ftv.szlg.info"):
    """
    Send password reset email to user
    
    Args:
        user: User instance
        reset_token: JWT token for password reset
        frontend_url: Base URL of the frontend application
    """
    reset_url = f"{frontend_url}/elfelejtett_jelszo/{reset_token}"

    subject = "FTV - Jelszó visszaállítása"

    # Create HTML email content
    html_message = f"""
    <html>
        <head>
            <style>
                body {{ font-family: Roboto, sans-serif; line-height: 1.6; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #f4f4f4; padding: 20px; text-align: center; display: flex; justify-content: around; align-items: center; }}
                .header svg {{ max-width: 50px; }}
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
                        <li>A link csak egyszer használható</li>
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
- A link csak egyszer használható
- Ha nem Ön kérte a jelszó visszaállítást, hagyja figyelmen kívül ezt az emailt

Ez egy automatikus email, kérjük ne válaszoljon rá.

© 2025 FTV. Minden jog fenntartva.
    """
    
    try:
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
