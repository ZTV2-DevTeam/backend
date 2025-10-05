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
        return True
    except Exception as e:
        print(f"Failed to send password reset email to {user.email}: {str(e)}")
        return False
