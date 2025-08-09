"""
Radio management API endpoints.
Handles radio stabs, radio sessions, and related functionality for second-year students (9F).
"""

from ninja import Schema
from django.contrib.auth.models import User
from api.models import RadioStab, RadioSession, Profile
from .auth import JWTAuth, ErrorSchema
from datetime import datetime

# ============================================================================
# Schemas
# ============================================================================

class RadioStabSchema(Schema):
    """Response schema for radio stab data."""
    id: int
    name: str
    team_code: str
    description: str = None
    member_count: int = 0

class RadioStabCreateSchema(Schema):
    """Request schema for creating new radio stab."""
    name: str
    team_code: str
    description: str = None

class RadioSessionSchema(Schema):
    """Response schema for radio session data."""
    id: int
    radio_stab: RadioStabSchema
    date: str
    time_from: str
    time_to: str
    description: str = None
    participant_count: int = 0

class RadioSessionCreateSchema(Schema):
    """Request schema for creating new radio session."""
    radio_stab_id: int
    date: str
    time_from: str
    time_to: str
    description: str = None
    participant_ids: list[int] = []

# ============================================================================
# Utility Functions
# ============================================================================

def create_radio_stab_response(radio_stab: RadioStab) -> dict:
    """
    Create standardized radio stab response dictionary.
    
    Args:
        radio_stab: RadioStab model instance
        
    Returns:
        Dictionary with radio stab information
    """
    return {
        "id": radio_stab.id,
        "name": radio_stab.name,
        "team_code": radio_stab.team_code,
        "description": radio_stab.description,
        "member_count": radio_stab.tagok.count()
    }

def create_radio_session_response(session: RadioSession) -> dict:
    """
    Create standardized radio session response dictionary.
    
    Args:
        session: RadioSession model instance
        
    Returns:
        Dictionary with radio session information
    """
    return {
        "id": session.id,
        "radio_stab": create_radio_stab_response(session.radio_stab),
        "date": session.date.isoformat(),
        "time_from": session.time_from.isoformat(),
        "time_to": session.time_to.isoformat(),
        "description": session.description,
        "participant_count": session.participants.count()
    }

def check_admin_permissions(user: User) -> tuple[bool, str]:
    """
    Check if user has admin permissions for radio management.
    
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

# ============================================================================
# API Endpoints
# ============================================================================

def register_radio_endpoints(api):
    """Register all radio-related endpoints with the API router."""
    
    @api.get("/radio-stabs", auth=JWTAuth(), response={200: list[RadioStabSchema], 401: ErrorSchema})
    def get_radio_stabs(request):
        """
        Get all radio stabs with member counts.
        
        Requires authentication. Returns information about all radio stabs
        including their member counts.
        
        Returns:
            200: List of all radio stabs
            401: Authentication failed
        """
        try:
            radio_stabs = RadioStab.objects.all()
            
            response = []
            for stab in radio_stabs:
                response.append(create_radio_stab_response(stab))
            
            return 200, response
        except Exception as e:
            return 401, {"message": f"Error fetching radio stabs: {str(e)}"}

    @api.post("/radio-stabs", auth=JWTAuth(), response={201: RadioStabSchema, 400: ErrorSchema, 401: ErrorSchema})
    def create_radio_stab(request, data: RadioStabCreateSchema):
        """
        Create new radio stab.
        
        Requires admin permissions. Creates a new radio stab with unique team code.
        
        Args:
            data: Radio stab creation data
            
        Returns:
            201: Radio stab created successfully
            400: Invalid data or duplicate team code
            401: Authentication or permission failed
        """
        try:
            # Check if user has admin permissions
            has_permission, error_message = check_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            radio_stab = RadioStab.objects.create(
                name=data.name,
                team_code=data.team_code,
                description=data.description
            )
            
            return 201, create_radio_stab_response(radio_stab)
        except Exception as e:
            if "UNIQUE constraint failed" in str(e) or "duplicate key" in str(e):
                return 400, {"message": "Ezzel a csapat kóddal már létezik rádiós stáb"}
            return 400, {"message": f"Error creating radio stab: {str(e)}"}

    @api.get("/radio-sessions", auth=JWTAuth(), response={200: list[RadioSessionSchema], 401: ErrorSchema})
    def get_radio_sessions(request, start_date: str = None, end_date: str = None):
        """
        Get radio sessions with optional date filtering.
        
        Requires authentication. Returns radio sessions, optionally filtered
        by start and end dates.
        
        Args:
            start_date: Optional start date filter (ISO format)
            end_date: Optional end date filter (ISO format)
            
        Returns:
            200: List of radio sessions
            401: Authentication failed
        """
        try:
            sessions = RadioSession.objects.select_related('radio_stab').all()
            
            if start_date:
                sessions = sessions.filter(date__gte=start_date)
            if end_date:
                sessions = sessions.filter(date__lte=end_date)
            
            response = []
            for session in sessions:
                response.append(create_radio_session_response(session))
            
            return 200, response
        except Exception as e:
            return 401, {"message": f"Error fetching radio sessions: {str(e)}"}

    @api.post("/radio-sessions", auth=JWTAuth(), response={201: RadioSessionSchema, 400: ErrorSchema, 401: ErrorSchema})
    def create_radio_session(request, data: RadioSessionCreateSchema):
        """
        Create new radio session.
        
        Requires admin permissions. Creates a new radio session and optionally
        assigns participants.
        
        Args:
            data: Radio session creation data
            
        Returns:
            201: Radio session created successfully
            400: Invalid data or radio stab not found
            401: Authentication or permission failed
        """
        try:
            # Check if user has admin permissions
            has_permission, error_message = check_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            # Get the radio stab
            try:
                radio_stab = RadioStab.objects.get(id=data.radio_stab_id)
            except RadioStab.DoesNotExist:
                return 400, {"message": "Rádiós stáb nem található"}
            
            # Create the session
            session = RadioSession.objects.create(
                radio_stab=radio_stab,
                date=data.date,
                time_from=data.time_from,
                time_to=data.time_to,
                description=data.description
            )
            
            # Add participants if provided
            if data.participant_ids:
                participants = User.objects.filter(id__in=data.participant_ids)
                session.participants.set(participants)
            
            return 201, create_radio_session_response(session)
        except Exception as e:
            return 400, {"message": f"Error creating radio session: {str(e)}"}
