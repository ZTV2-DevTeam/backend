"""
User management API endpoints.
Handles user profiles, radio students, and availability checking.
"""

from ninja import Schema
from django.contrib.auth.models import User
from api.models import Profile
from .auth import JWTAuth, ErrorSchema
from datetime import datetime

# ============================================================================
# Schemas
# ============================================================================

class UserProfileSchema(Schema):
    """Response schema for user profile data."""
    id: int
    username: str
    first_name: str
    last_name: str
    email: str
    telefonszam: str = None
    medias: bool
    admin_type: str
    stab_name: str = None
    radio_stab_name: str = None
    osztaly_name: str = None
    is_second_year_radio: bool = False

# ============================================================================
# Utility Functions
# ============================================================================

def create_user_profile_response(profile: Profile) -> dict:
    """
    Create standardized user profile response dictionary.
    
    Args:
        profile: Profile model instance
        
    Returns:
        Dictionary with user profile information
    """
    return {
        "id": profile.user.id,
        "username": profile.user.username,
        "first_name": profile.user.first_name,
        "last_name": profile.user.last_name,
        "email": profile.user.email,
        "telefonszam": profile.telefonszam,
        "medias": profile.medias,
        "admin_type": profile.admin_type,
        "stab_name": profile.stab.name if profile.stab else None,
        "radio_stab_name": f"{profile.radio_stab.name} ({profile.radio_stab.team_code})" if profile.radio_stab else None,
        "osztaly_name": str(profile.osztaly) if profile.osztaly else None,
        "is_second_year_radio": profile.is_second_year_radio_student
    }

def check_admin_permissions(user: User) -> tuple[bool, str]:
    """
    Check if user has admin permissions for user management.
    
    Args:
        user: Django User object
        
    Returns:
        Tuple of (has_permission, error_message)
    """
    try:
        profile = Profile.objects.get(user=user)
        if not profile.has_admin_permission('any'):
            return False, "Adminisztrátor jogosultság szükséges"
        return True, ""
    except Profile.DoesNotExist:
        return False, "Felhasználói profil nem található"

def filter_radio_students(profiles):
    """
    Filter profiles to get only second year radio students (9F).
    
    Args:
        profiles: QuerySet of Profile objects
        
    Returns:
        List of profile response dictionaries for 9F students
    """
    response = []
    
    for prof in profiles:
        if prof.is_second_year_radio_student or (prof.osztaly and prof.osztaly.szekcio.upper() == 'F'):
            current_year = datetime.now().year
            elso_felev = datetime.now().month >= 9
            
            if prof.osztaly:
                year_diff = current_year - prof.osztaly.startYear 
                year_diff += 8 if elso_felev else 7
                if year_diff == 9:  # 9F students
                    response.append(create_user_profile_response(prof))
    
    return response

# ============================================================================
# API Endpoints
# ============================================================================

def register_user_endpoints(api):
    """Register all user management endpoints with the API router."""
    
    @api.get("/users", auth=JWTAuth(), response={200: list[UserProfileSchema], 401: ErrorSchema})
    def get_all_users(request):
        """
        Get all users with their profiles.
        
        Requires admin permissions. Returns detailed information about all users
        including their profiles, stab assignments, and roles.
        
        Returns:
            200: List of all user profiles
            401: Authentication or permission failed
        """
        try:
            # Check if user has admin permissions
            has_permission, error_message = check_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            profiles = Profile.objects.select_related(
                'user', 'stab', 'radio_stab', 'osztaly'
            ).all()
            
            response = []
            for prof in profiles:
                response.append(create_user_profile_response(prof))
            
            return 200, response
        except Exception as e:
            return 401, {"message": f"Error fetching users: {str(e)}"}

    @api.get("/users/{user_id}", auth=JWTAuth(), response={200: UserProfileSchema, 401: ErrorSchema, 404: ErrorSchema})
    def get_user_details(request, user_id: int):
        """
        Get detailed information about a specific user.
        
        Requires admin permissions. Returns comprehensive profile information
        for the specified user.
        
        Args:
            user_id: Unique user identifier
            
        Returns:
            200: User profile details
            404: User not found
            401: Authentication or permission failed
        """
        try:
            # Check if user has admin permissions
            has_permission, error_message = check_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            user_profile = Profile.objects.select_related(
                'user', 'stab', 'radio_stab', 'osztaly'
            ).get(user__id=user_id)
            
            return 200, create_user_profile_response(user_profile)
        except Profile.DoesNotExist:
            return 404, {"message": "Felhasználó nem található"}
        except Exception as e:
            return 401, {"message": f"Error fetching user details: {str(e)}"}

    @api.get("/users/radio-students", auth=JWTAuth(), response={200: list[UserProfileSchema], 401: ErrorSchema})
    def get_radio_students(request):
        """
        Get all second year radio students (9F).
        
        Requires admin permissions. Returns profiles of students who are
        in their second year (9F class) and involved in radio activities.
        
        Returns:
            200: List of 9F student profiles
            401: Authentication or permission failed
        """
        try:
            # Check if user has admin permissions
            has_permission, error_message = check_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            # Get all profiles with F section
            profiles = Profile.objects.select_related(
                'user', 'stab', 'radio_stab', 'osztaly'
            ).filter(
                osztaly__szekcio='F'
            )
            
            # Filter for second year students
            response = filter_radio_students(profiles)
            
            return 200, response
        except Exception as e:
            return 401, {"message": f"Error fetching radio students: {str(e)}"}

    @api.get("/users/{user_id}/availability", auth=JWTAuth(), response={200: dict, 401: ErrorSchema, 404: ErrorSchema})
    def check_user_availability(request, user_id: int, start_datetime: str, end_datetime: str):
        """
        Check user availability during specific time period.
        
        Requires authentication. Checks if a user is available during the
        specified datetime range, considering absences and radio sessions.
        
        Args:
            user_id: Unique user identifier
            start_datetime: Start of time period (ISO format)
            end_datetime: End of time period (ISO format)
            
        Returns:
            200: Availability status with conflict details
            404: User not found
            401: Authentication failed
            400: Invalid datetime format
        """
        try:
            user_profile = Profile.objects.select_related('user').get(user__id=user_id)
            
            # Parse datetime strings
            try:
                start_dt = datetime.fromisoformat(start_datetime.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_datetime.replace('Z', '+00:00'))
            except ValueError as e:
                return 400, {"message": f"Hibás dátum formátum: {str(e)}"}
            
            is_available = user_profile.is_available_for_datetime(start_dt, end_dt)
            
            # Get conflicting items
            conflicts = []
            
            # Check absences
            from api.models import Tavollet, RadioSession
            absences = Tavollet.objects.filter(
                user=user_profile.user,
                start_date__lte=end_dt.date(),
                end_date__gte=start_dt.date(),
                denied=False
            )
            for absence in absences:
                conflicts.append({
                    "type": "absence",
                    "reason": absence.reason,
                    "start": absence.start_date.isoformat(),
                    "end": absence.end_date.isoformat()
                })
            
            # Check radio sessions if applicable
            if user_profile.is_second_year_radio_student:
                radio_sessions = RadioSession.objects.filter(
                    participants=user_profile.user,
                    date__gte=start_dt.date(),
                    date__lte=end_dt.date()
                ).select_related('radio_stab')
                
                for session in radio_sessions:
                    if session.overlaps_with_datetime(start_dt, end_dt):
                        conflicts.append({
                            "type": "radio_session",
                            "description": f"{session.radio_stab.name} rádiós összejátszás",
                            "date": session.date.isoformat(),
                            "time_from": session.time_from.isoformat(),
                            "time_to": session.time_to.isoformat()
                        })
            
            return 200, {
                "available": is_available,
                "user_id": user_id,
                "conflicts": conflicts,
                "is_radio_student": user_profile.is_second_year_radio_student
            }
            
        except Profile.DoesNotExist:
            return 404, {"message": "Felhasználó nem található"}
        except Exception as e:
            return 401, {"message": f"Error checking availability: {str(e)}"}
