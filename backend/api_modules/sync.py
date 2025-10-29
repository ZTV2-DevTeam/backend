"""
FTV Sync API Module - External System Integration

This module provides sync endpoints for external system integration (Igazoláskezelő).
Uses external access token authentication instead of JWT tokens.

Public API Overview:
==================

These endpoints are designed for the Igazoláskezelő (Attendance Management System) 
to sync attendance/absence records with FTV system.

Authentication:
==============

All endpoints require an external access token in the Authorization header:
Authorization: Bearer YOUR_EXTERNAL_ACCESS_TOKEN

The token is configured in local_settings.py as EXTERNAL_ACCESS_TOKEN.

Available Endpoints:
===================

GET /api/sync/osztalyok          - Get all classes
GET /api/sync/osztaly/{id}       - Get specific class details
GET /api/sync/hianyzasok/osztaly/{osztaly_id}  - Get all absences for a class
GET /api/sync/hianyzas/{id}      - Get specific absence details
GET /api/sync/hianyzasok/user/{user_id}        - Get all absences for a user
GET /api/sync/profile/{email}    - Get user profile by email

Common Key for Integration:
===========================

Email address is used as the common key between FTV and Igazoláskezelő systems.

Response Format:
===============

All endpoints return JSON data with consistent structure.
Errors return: {"detail": "error message"}

Security:
=========

- Token-based authentication (no user session required)
- Token stored securely in local_settings.py
- Separate from JWT authentication used by FTV frontend
- Read-only access (no data modification)
"""

from ninja import Schema, Router
from django.contrib.auth.models import User
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from typing import List, Optional
from datetime import datetime, date, time as dt_time
import local_settings

from api.models import (
    Osztaly, 
    Absence, 
    Profile,
    Tanev,
    Stab,
    RadioStab
)

# ============================================================================
# External Token Authentication
# ============================================================================

class ExternalTokenAuth:
    """
    Custom authentication class for external API access using bearer token.
    Validates against the EXTERNAL_ACCESS_TOKEN from local_settings.
    """
    
    def authenticate(self, request: HttpRequest, token: str):
        """
        Authenticate external API requests using bearer token.
        
        Args:
            request: The HTTP request object
            token: The bearer token from Authorization header
            
        Returns:
            True if token is valid, raises error otherwise
        """
        # Get the expected token from settings
        expected_token = getattr(local_settings, 'EXTERNAL_ACCESS_TOKEN', None)
        
        if not expected_token:
            raise Exception("External access token not configured in local_settings")
        
        # Compare tokens (constant-time comparison for security)
        if token == expected_token:
            return True
        
        raise Exception("Invalid external access token")

# ============================================================================
# Request/Response Schemas
# ============================================================================

class OsztalySchema(Schema):
    """Schema for class information."""
    id: int
    startYear: int
    szekcio: str
    current_name: str
    tanev_id: Optional[int] = None
    tanev_name: Optional[str] = None

class ProfileMinimalSchema(Schema):
    """Minimal profile schema for user information."""
    id: int
    user_id: int
    username: str
    email: str
    first_name: str
    last_name: str
    full_name: str
    telefonszam: Optional[str] = None
    osztaly_id: Optional[int] = None
    osztaly_name: Optional[str] = None
    stab_id: Optional[int] = None
    stab_name: Optional[str] = None
    radio_stab_id: Optional[int] = None
    radio_stab_name: Optional[str] = None

class ForgatDetailsSchema(Schema):
    """Schema for forgatas (filming session) details."""
    id: int
    name: str
    description: str
    date: date
    timeFrom: dt_time
    timeTo: dt_time
    location_name: Optional[str] = None

class AbsenceSchema(Schema):
    """Schema for absence (hiányzás) information."""
    id: int
    diak_id: int
    diak_username: str
    diak_email: str
    diak_full_name: str
    forgatas_id: int
    forgatas_details: Optional[ForgatDetailsSchema] = None
    date: date
    timeFrom: dt_time
    timeTo: dt_time
    excused: bool
    unexcused: bool
    auto_generated: bool
    student_extra_time_before: int
    student_extra_time_after: int
    student_edited: bool
    student_edit_timestamp: Optional[datetime] = None
    student_edit_note: Optional[str] = None
    affected_classes: List[int]

class ProfileDetailedSchema(Schema):
    """Detailed profile schema with full information."""
    id: int
    user_id: int
    username: str
    email: str
    first_name: str
    last_name: str
    full_name: str
    telefonszam: Optional[str] = None
    medias: bool
    osztaly_id: Optional[int] = None
    osztaly_name: Optional[str] = None
    stab_id: Optional[int] = None
    stab_name: Optional[str] = None
    radio_stab_id: Optional[int] = None
    radio_stab_name: Optional[str] = None
    admin_type: str
    special_role: str
    szerkeszto: bool
    is_admin: bool
    is_production_leader: bool

class ErrorSchema(Schema):
    """Schema for error responses."""
    detail: str

# ============================================================================
# Helper Functions
# ============================================================================

def serialize_osztaly(osztaly: Osztaly) -> dict:
    """Serialize Osztaly instance to dictionary."""
    return {
        'id': osztaly.id,
        'startYear': osztaly.startYear,
        'szekcio': osztaly.szekcio,
        'current_name': str(osztaly),
        'tanev_id': osztaly.tanev.id if osztaly.tanev else None,
        'tanev_name': str(osztaly.tanev) if osztaly.tanev else None
    }

def serialize_forgatas(forgatas) -> dict:
    """Serialize Forgatas instance to dictionary."""
    return {
        'id': forgatas.id,
        'name': forgatas.name,
        'description': forgatas.description,
        'date': forgatas.date,
        'timeFrom': forgatas.timeFrom,
        'timeTo': forgatas.timeTo,
        'location_name': forgatas.location.name if forgatas.location else None
    }

def serialize_absence(absence: Absence) -> dict:
    """Serialize Absence instance to dictionary."""
    return {
        'id': absence.id,
        'diak_id': absence.diak.id,
        'diak_username': absence.diak.username,
        'diak_email': absence.diak.email,
        'diak_full_name': absence.diak.get_full_name(),
        'forgatas_id': absence.forgatas.id,
        'forgatas_details': serialize_forgatas(absence.forgatas) if absence.forgatas else None,
        'date': absence.date,
        'timeFrom': absence.timeFrom,
        'timeTo': absence.timeTo,
        'excused': absence.excused,
        'unexcused': absence.unexcused,
        'auto_generated': absence.auto_generated,
        'student_extra_time_before': absence.student_extra_time_before,
        'student_extra_time_after': absence.student_extra_time_after,
        'student_edited': absence.student_edited,
        'student_edit_timestamp': absence.student_edit_timestamp,
        'student_edit_note': absence.student_edit_note,
        'affected_classes': absence.get_affected_classes()
    }

def serialize_profile_minimal(profile: Profile) -> dict:
    """Serialize Profile instance to minimal dictionary."""
    return {
        'id': profile.id,
        'user_id': profile.user.id,
        'username': profile.user.username,
        'email': profile.user.email,
        'first_name': profile.user.first_name,
        'last_name': profile.user.last_name,
        'full_name': profile.user.get_full_name(),
        'telefonszam': profile.telefonszam,
        'osztaly_id': profile.osztaly.id if profile.osztaly else None,
        'osztaly_name': str(profile.osztaly) if profile.osztaly else None,
        'stab_id': profile.stab.id if profile.stab else None,
        'stab_name': profile.stab.name if profile.stab else None,
        'radio_stab_id': profile.radio_stab.id if profile.radio_stab else None,
        'radio_stab_name': str(profile.radio_stab) if profile.radio_stab else None
    }

def serialize_profile_detailed(profile: Profile) -> dict:
    """Serialize Profile instance to detailed dictionary."""
    return {
        'id': profile.id,
        'user_id': profile.user.id,
        'username': profile.user.username,
        'email': profile.user.email,
        'first_name': profile.user.first_name,
        'last_name': profile.user.last_name,
        'full_name': profile.user.get_full_name(),
        'telefonszam': profile.telefonszam,
        'medias': profile.medias,
        'osztaly_id': profile.osztaly.id if profile.osztaly else None,
        'osztaly_name': str(profile.osztaly) if profile.osztaly else None,
        'stab_id': profile.stab.id if profile.stab else None,
        'stab_name': profile.stab.name if profile.stab else None,
        'radio_stab_id': profile.radio_stab.id if profile.radio_stab else None,
        'radio_stab_name': str(profile.radio_stab) if profile.radio_stab else None,
        'admin_type': profile.admin_type,
        'special_role': profile.special_role,
        'szerkeszto': profile.szerkeszto,
        'is_admin': profile.is_admin,
        'is_production_leader': profile.is_production_leader
    }

# ============================================================================
# API Router Registration
# ============================================================================

def register_sync_endpoints(api):
    """
    Register sync API endpoints with external token authentication.
    
    Args:
        api: The NinjaAPI instance to register endpoints with
    """
    
    # Create router with authentication
    router = Router(auth=ExternalTokenAuth())
    
    # ============================================================================
    # Osztály (Class) Endpoints
    # ============================================================================
    
    @router.get(
        "/osztalyok",
        response={200: List[OsztalySchema], 401: ErrorSchema},
        summary="Get all classes",
        description="Retrieve all classes in the system with their current names and school year information."
    )
    def get_osztalyok(request):
        """Get all classes."""
        osztalyok = Osztaly.objects.all().select_related('tanev')
        return 200, [serialize_osztaly(o) for o in osztalyok]
    
    @router.get(
        "/osztaly/{osztaly_id}",
        response={200: OsztalySchema, 404: ErrorSchema, 401: ErrorSchema},
        summary="Get class details",
        description="Retrieve detailed information for a specific class by ID."
    )
    def get_osztaly(request, osztaly_id: int):
        """Get specific class details."""
        osztaly = get_object_or_404(Osztaly.objects.select_related('tanev'), id=osztaly_id)
        return 200, serialize_osztaly(osztaly)
    
    # ============================================================================
    # Hiányzás (Absence) Endpoints
    # ============================================================================
    
    @router.get(
        "/hianyzasok/osztaly/{osztaly_id}",
        response={200: List[AbsenceSchema], 404: ErrorSchema, 401: ErrorSchema},
        summary="Get all absences for a class",
        description="Retrieve all absence records for students in a specific class."
    )
    def get_hianyzasok_by_osztaly(request, osztaly_id: int):
        """Get all absences for a class."""
        # Verify class exists
        osztaly = get_object_or_404(Osztaly, id=osztaly_id)
        
        # Get all users in this class
        users_in_class = User.objects.filter(profile__osztaly=osztaly)
        
        # Get all absences for these users
        absences = Absence.objects.filter(
            diak__in=users_in_class
        ).select_related('diak', 'forgatas', 'forgatas__location').order_by('-date', '-timeFrom')
        
        return 200, [serialize_absence(a) for a in absences]
    
    @router.get(
        "/hianyzas/{absence_id}",
        response={200: AbsenceSchema, 404: ErrorSchema, 401: ErrorSchema},
        summary="Get absence details",
        description="Retrieve detailed information for a specific absence record by ID."
    )
    def get_hianyzas(request, absence_id: int):
        """Get specific absence details."""
        absence = get_object_or_404(
            Absence.objects.select_related('diak', 'forgatas', 'forgatas__location'),
            id=absence_id
        )
        return 200, serialize_absence(absence)
    
    @router.get(
        "/hianyzasok/user/{user_id}",
        response={200: List[AbsenceSchema], 404: ErrorSchema, 401: ErrorSchema},
        summary="Get all absences for a user",
        description="Retrieve all absence records for a specific user by user ID."
    )
    def get_hianyzasok_by_user(request, user_id: int):
        """Get all absences for a user."""
        # Verify user exists
        user = get_object_or_404(User, id=user_id)
        
        # Get all absences for this user
        absences = Absence.objects.filter(
            diak=user
        ).select_related('diak', 'forgatas', 'forgatas__location').order_by('-date', '-timeFrom')
        
        return 200, [serialize_absence(a) for a in absences]
    
    # ============================================================================
    # Profile Endpoints
    # ============================================================================
    
    @router.get(
        "/profile/{email}",
        response={200: ProfileDetailedSchema, 404: ErrorSchema, 401: ErrorSchema},
        summary="Get user profile by email",
        description="Retrieve detailed user profile information using email address as the common key."
    )
    def get_profile_by_email(request, email: str):
        """Get user profile by email address."""
        # Find user by email
        user = get_object_or_404(User, email=email)
        
        # Get or create profile
        profile, created = Profile.objects.get_or_create(user=user)
        
        return 200, serialize_profile_detailed(profile)
    
    # Register the router with the main API
    api.add_router("/sync", router)


# ============================================================================
# Module Export
# ============================================================================

__all__ = ['register_sync_endpoints']
