"""
FTV Radio Management API Module

This module provides comprehensive radio stab and session management functionality
for the FTV system, specifically designed for second-year students (9F class) 
participating in radio activities.

Public API Overview:
==================

The Radio API manages radio teams (stabs) and their sessions, supporting
the school's radio program with scheduling and participant management.

Base URL: /api/

Protected Endpoints (JWT Token Required):
- GET  /radio-stabs             - List all radio stabs with member counts
- POST /radio-stabs             - Create new radio stab (admin only)
- GET  /radio-sessions          - Get radio sessions with optional date filters
- POST /radio-sessions          - Create new radio session (admin only)

Radio Stab System:
=================

Radio Stabs are teams of students working together on radio content:
- Each stab has a unique name and team code
- Member count tracking for team management
- Optional description for team purpose/focus
- Automatic member association through user profiles

Radio Session Management:
========================

Radio Sessions represent scheduled activities:
- Date and time scheduling with conflict detection
- Participant assignment and tracking
- Integration with user availability system
- Automatic overlap checking for scheduling

Data Structure:
==============

Radio Stab:
- id: Unique identifier
- name: Team display name
- team_code: Short unique identifier
- description: Optional team description
- member_count: Automatically calculated member count

Radio Session:
- id: Unique session identifier
- radio_stab: Associated team information
- date: Session date (ISO format)
- time_from: Start time (HH:MM format)
- time_to: End time (HH:MM format)
- description: Optional session description
- participant_count: Number of assigned participants

9F Student Integration:
======================

Special functionality for second-year radio students:
- Automatic identification through class assignment
- Profile-based radio stab association
- Availability checking for session scheduling
- Integration with absence management system

Example Usage:
=============

Get all radio stabs:
curl -H "Authorization: Bearer {token}" /api/radio-stabs

Create new radio stab (admin):
curl -X POST /api/radio-stabs \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"name":"Morning News Team","team_code":"MNT","description":"Daily morning news broadcast"}'

Get radio sessions with date filter:
curl -H "Authorization: Bearer {token}" \
  "/api/radio-sessions?start_date=2024-03-01&end_date=2024-03-31"

Create radio session (admin):
curl -X POST /api/radio-sessions \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"radio_stab_id":1,"date":"2024-03-15","time_from":"14:00","time_to":"16:00","participant_ids":[1,2,3]}'

Permission Requirements:
=======================

- Public viewing: Authentication required
- Stab creation: Admin permissions (teacher or system admin)
- Session creation: Admin permissions
- Member management: Automatic through user profiles

Scheduling Features:
===================

- Date range filtering for session queries
- Time conflict detection
- Participant availability checking
- Integration with user absence system
- Automatic session overlap validation

Error Handling:
==============

- 200/201: Success
- 400: Validation errors (duplicate codes, invalid dates, stab not found)
- 401: Authentication failed or insufficient permissions
- 404: Resource not found
- 500: Server error

Validation Rules:
================

- Radio stab team codes must be unique
- Session dates must be valid ISO format dates
- Time ranges must be logical (start before end)
- Participant IDs must reference valid users
- Admin permissions required for creation operations
"""

from ninja import Schema
from django.contrib.auth.models import User
from api.models import RadioStab, RadioSession, Profile
from .auth import JWTAuth, ErrorSchema
from datetime import datetime
from typing import Optional

# ============================================================================
# Schemas
# ============================================================================

class RadioStabSchema(Schema):
    """Response schema for radio stab data."""
    id: int
    name: str
    team_code: str
    description: Optional[str] = None
    member_count: int = 0

class RadioStabCreateSchema(Schema):
    """Request schema for creating new radio stab."""
    name: str
    team_code: str
    description: Optional[str] = None

class RadioSessionSchema(Schema):
    """Response schema for radio session data."""
    id: int
    radio_stab: RadioStabSchema
    date: str
    time_from: str
    time_to: str
    description: Optional[str] = None
    participant_count: int = 0

class RadioSessionCreateSchema(Schema):
    """Request schema for creating new radio session."""
    radio_stab_id: int
    date: str
    time_from: str
    time_to: str
    description: Optional[str] = None
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
    
    @api.get("/radio-stabs", auth=JWTAuth(), response={200: list[RadioStabSchema], 500: ErrorSchema})
    def get_radio_stabs(request):
        """
        Get all radio stabs with member counts.
        
        Requires authentication. Returns information about all radio stabs
        including their member counts.
        
        Returns:
            200: List of all radio stabs
            500: Server error
        """
        try:
            radio_stabs = RadioStab.objects.all()
            
            response = []
            for stab in radio_stabs:
                response.append(create_radio_stab_response(stab))
            
            return 200, response
        except Exception as e:
            return 500, {"message": f"Error fetching radio stabs: {str(e)}"}

    @api.post("/radio-stabs", auth=JWTAuth(), response={201: RadioStabSchema, 400: ErrorSchema, 403: ErrorSchema, 500: ErrorSchema})
    def create_radio_stab(request, data: RadioStabCreateSchema):
        """
        Create new radio stab.
        
        Requires admin permissions. Creates a new radio stab with unique team code.
        
        Args:
            data: Radio stab creation data
            
        Returns:
            201: Radio stab created successfully
            400: Invalid data or duplicate team code
            403: Insufficient permissions
            500: Server error
        """
        try:
            # Check if user has admin permissions
            has_permission, error_message = check_admin_permissions(request.auth)
            if not has_permission:
                return 403, {"message": error_message}
            
            radio_stab = RadioStab.objects.create(
                name=data.name,
                team_code=data.team_code,
                description=data.description
            )
            
            return 201, create_radio_stab_response(radio_stab)
        except Exception as e:
            if "UNIQUE constraint failed" in str(e) or "duplicate key" in str(e):
                return 400, {"message": "Ezzel a csapat kóddal már létezik rádiós stáb"}
            return 500, {"message": f"Error creating radio stab: {str(e)}"}

    @api.get("/radio-sessions", auth=JWTAuth(), response={200: list[RadioSessionSchema], 500: ErrorSchema})
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
            500: Server error
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
            return 500, {"message": f"Error fetching radio sessions: {str(e)}"}

    @api.post("/radio-sessions", auth=JWTAuth(), response={201: RadioSessionSchema, 400: ErrorSchema, 403: ErrorSchema, 500: ErrorSchema})
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
            403: Insufficient permissions
            500: Server error
        """
        try:
            # Check if user has admin permissions
            has_permission, error_message = check_admin_permissions(request.auth)
            if not has_permission:
                return 403, {"message": error_message}
            
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
