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

Full Sync:
GET /api/sync/full                           - Full sync (all classes and all users)

Base Sync:
GET /api/sync/base                           - Base sync (all classes + only student users)

Class Endpoints:
GET /api/sync/osztalyok                      - Get all classes
GET /api/sync/osztaly/year/{start_year}      - Get all users for a specific class by start year

Absence Endpoints:
GET /api/sync/hianyzas/{id}                  - Get specific absence details
GET /api/sync/hianyzasok/user/{user_id}      - Get all absences for a user

Profile Endpoints:
GET /api/sync/profile/{email}                - Get user profile by email
GET /api/sync/user/email/{email}             - Get user details by email

Common Key for Integration:
===========================

Email address is used as the common key between FTV and Igazoláskezelő systems.

Response Format:
===============

All endpoints return JSON data with consistent structure.
Errors return: {"detail": "error message"}

Performance Monitoring:
======================

Add ?debug-performance=true to any endpoint to get performance metrics in response.

Security:
=========

- Token-based authentication (no user session required)
- Token stored securely in local_settings.py
- Separate from JWT authentication used by FTV frontend
- Read-only access (no data modification)
"""

from ninja import Schema, Router
from ninja.security import HttpBearer
from django.contrib.auth.models import User
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.db.models import Prefetch
from typing import List, Optional, Dict, Any
from datetime import datetime, date, time as dt_time
import time
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
# Performance Monitoring
# ============================================================================

class PerformanceMonitor:
    """Track performance metrics for API calls."""
    
    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        self.metrics = {}
        self.start_time = time.time() if enabled else None
    
    def start_timer(self, key: str):
        """Start timing a specific operation."""
        if self.enabled:
            self.metrics[f"{key}_start"] = time.time()
    
    def end_timer(self, key: str):
        """End timing and record duration."""
        if self.enabled:
            start_key = f"{key}_start"
            if start_key in self.metrics:
                duration = time.time() - self.metrics[start_key]
                self.metrics[key] = round(duration * 1000, 2)  # Convert to ms
                del self.metrics[start_key]
    
    def record_count(self, key: str, count: int):
        """Record a count metric."""
        if self.enabled:
            self.metrics[key] = count
    
    def get_results(self) -> Dict[str, Any]:
        """Get all performance metrics."""
        if not self.enabled:
            return {}
        
        total_duration = time.time() - self.start_time
        return {
            "total_duration_ms": round(total_duration * 1000, 2),
            "metrics": self.metrics
        }

# ============================================================================
# External Token Authentication
# ============================================================================

class ExternalTokenAuth(HttpBearer):
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
            True if token is valid, None otherwise (which triggers 401 error)
        """
        # Get the expected token from settings
        expected_token = getattr(local_settings, 'EXTERNAL_ACCESS_TOKEN', None)
        
        if not expected_token:
            return None  # Token not configured
        
        # Compare tokens (constant-time comparison for security)
        if token == expected_token:
            return token  # Return token to indicate success
        
        return None  # Invalid token

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

class BaseSyncSchema(Schema):
    """Schema for base sync data (classes + student users)."""
    osztalyok: List[OsztalySchema]
    students: List[ProfileMinimalSchema]
    performance: Optional[Dict[str, Any]] = None

class FullSyncSchema(Schema):
    """Schema for full sync data (classes + all users)."""
    osztalyok: List[OsztalySchema]
    users: List[ProfileMinimalSchema]
    performance: Optional[Dict[str, Any]] = None

class OsztalyUsersSchema(Schema):
    """Schema for osztaly users data."""
    osztaly: OsztalySchema
    students: List[ProfileMinimalSchema]
    performance: Optional[Dict[str, Any]] = None

# ============================================================================
# Helper Functions
# ============================================================================

def is_student(profile: Profile) -> bool:
    """Check if a profile belongs to a student (not admin or production leader)."""
    return (
        profile.admin_type == 'none' and 
        profile.special_role not in ['production_leader']
    )

def get_optimized_profiles_queryset():
    """Get optimized queryset for profiles with all related data prefetched."""
    return Profile.objects.select_related(
        'user',
        'osztaly',
        'osztaly__tanev',
        'stab',
        'radio_stab'
    ).all()

def get_student_profiles_queryset():
    """Get optimized queryset for student profiles only."""
    return Profile.objects.select_related(
        'user',
        'osztaly',
        'osztaly__tanev',
        'stab',
        'radio_stab'
    ).filter(
        admin_type='none'
    ).exclude(
        special_role='production_leader'
    )

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
    # Sync Endpoints
    # ============================================================================
    
    @router.get(
        "/full",
        response={200: FullSyncSchema, 401: ErrorSchema},
        summary="Full sync - all classes and all users",
        description="Retrieve all classes and all users in the system (including admins and production leaders)."
    )
    def full_sync(request, debug_performance: bool = False):
        """Full sync endpoint - returns all classes and all users."""
        perf = PerformanceMonitor(debug_performance)
        
        # Fetch classes
        perf.start_timer("fetch_classes")
        osztalyok = list(Osztaly.objects.select_related('tanev').all())
        perf.end_timer("fetch_classes")
        perf.record_count("class_count", len(osztalyok))
        
        # Fetch all users
        perf.start_timer("fetch_users")
        profiles = list(get_optimized_profiles_queryset())
        perf.end_timer("fetch_users")
        perf.record_count("user_count", len(profiles))
        
        # Serialize
        perf.start_timer("serialize")
        result = {
            'osztalyok': [serialize_osztaly(o) for o in osztalyok],
            'users': [serialize_profile_minimal(p) for p in profiles],
        }
        perf.end_timer("serialize")
        
        if debug_performance:
            result['performance'] = perf.get_results()
        
        return 200, result
    
    @router.get(
        "/base",
        response={200: BaseSyncSchema, 401: ErrorSchema},
        summary="Base sync - classes and student users only",
        description="Retrieve all classes and only student users (no admins or production leaders)."
    )
    def base_sync(request, debug_performance: bool = False):
        """Base sync endpoint - returns classes and only student users."""
        perf = PerformanceMonitor(debug_performance)
        
        # Fetch classes
        perf.start_timer("fetch_classes")
        osztalyok = list(Osztaly.objects.select_related('tanev').all())
        perf.end_timer("fetch_classes")
        perf.record_count("class_count", len(osztalyok))
        
        # Fetch student users only
        perf.start_timer("fetch_students")
        students = list(get_student_profiles_queryset())
        perf.end_timer("fetch_students")
        perf.record_count("student_count", len(students))
        
        # Serialize
        perf.start_timer("serialize")
        result = {
            'osztalyok': [serialize_osztaly(o) for o in osztalyok],
            'students': [serialize_profile_minimal(p) for p in students],
        }
        perf.end_timer("serialize")
        
        if debug_performance:
            result['performance'] = perf.get_results()
        
        return 200, result
    
    # ============================================================================
    # Osztály (Class) Endpoints
    # ============================================================================
    
    @router.get(
        "/osztalyok",
        response={200: List[OsztalySchema], 401: ErrorSchema},
        summary="Get all classes",
        description="Retrieve all classes in the system with their current names and school year information."
    )
    def get_osztalyok(request, debug_performance: bool = False):
        """Get all classes."""
        perf = PerformanceMonitor(debug_performance)
        
        perf.start_timer("fetch_classes")
        osztalyok = list(Osztaly.objects.select_related('tanev').all())
        perf.end_timer("fetch_classes")
        perf.record_count("class_count", len(osztalyok))
        
        perf.start_timer("serialize")
        result = [serialize_osztaly(o) for o in osztalyok]
        perf.end_timer("serialize")
        
        if debug_performance:
            return 200, {
                'data': result,
                'performance': perf.get_results()
            }
        
        return 200, result
    
    @router.get(
        "/osztaly/year/{start_year}",
        response={200: OsztalyUsersSchema, 404: ErrorSchema, 401: ErrorSchema},
        summary="Get all students for a class by start year",
        description="Retrieve all student users for a specific class by start year. Supports both YYYY (e.g., 2023) and YY (e.g., 23) formats."
    )
    def get_osztaly_by_year(request, start_year: str, debug_performance: bool = False):
        """Get all students for a class by start year (supports YYYY or YY format)."""
        perf = PerformanceMonitor(debug_performance)
        
        # Normalize start year to integer
        perf.start_timer("parse_year")
        try:
            year = int(start_year)
            # If 2-digit year, convert to 4-digit (assume 20xx)
            if year < 100:
                year = 2000 + year
        except ValueError:
            return 404, {"detail": f"Invalid year format: {start_year}"}
        perf.end_timer("parse_year")
        
        # Find osztaly by start year
        perf.start_timer("fetch_osztaly")
        osztalyok = list(Osztaly.objects.select_related('tanev').filter(startYear=year))
        perf.end_timer("fetch_osztaly")
        
        if not osztalyok:
            return 404, {"detail": f"No osztaly found with start year {year}"}
        
        # For now, take the first one (there might be multiple sections)
        # In the future, you might want to add szekcio parameter
        osztaly = osztalyok[0]
        perf.record_count("osztaly_count", len(osztalyok))
        
        # Fetch student users in this osztaly
        perf.start_timer("fetch_students")
        students = list(
            get_student_profiles_queryset().filter(osztaly=osztaly)
        )
        perf.end_timer("fetch_students")
        perf.record_count("student_count", len(students))
        
        # Serialize
        perf.start_timer("serialize")
        result = {
            'osztaly': serialize_osztaly(osztaly),
            'students': [serialize_profile_minimal(p) for p in students],
        }
        perf.end_timer("serialize")
        
        if debug_performance:
            result['performance'] = perf.get_results()
        
        return 200, result
    
    # ============================================================================
    # Hiányzás (Absence) Endpoints
    # ============================================================================
    
    @router.get(
        "/hianyzas/{absence_id}",
        response={200: AbsenceSchema, 404: ErrorSchema, 401: ErrorSchema},
        summary="Get absence details",
        description="Retrieve detailed information for a specific absence record by ID."
    )
    def get_hianyzas(request, absence_id: int, debug_performance: bool = False):
        """Get specific absence details."""
        perf = PerformanceMonitor(debug_performance)
        
        perf.start_timer("fetch_absence")
        absence = get_object_or_404(
            Absence.objects.select_related('diak', 'forgatas', 'forgatas__location'),
            id=absence_id
        )
        perf.end_timer("fetch_absence")
        
        perf.start_timer("serialize")
        result = serialize_absence(absence)
        perf.end_timer("serialize")
        
        if debug_performance:
            result['performance'] = perf.get_results()
        
        return 200, result
    
    @router.get(
        "/hianyzasok/user/{user_id}",
        response={200: List[AbsenceSchema], 404: ErrorSchema, 401: ErrorSchema},
        summary="Get all absences for a user",
        description="Retrieve all absence records for a specific user by user ID."
    )
    def get_hianyzasok_by_user(request, user_id: int, debug_performance: bool = False):
        """Get all absences for a user."""
        perf = PerformanceMonitor(debug_performance)
        
        # Verify user exists
        perf.start_timer("fetch_user")
        user = get_object_or_404(User, id=user_id)
        perf.end_timer("fetch_user")
        
        # Get all absences for this user
        perf.start_timer("fetch_absences")
        absences = list(
            Absence.objects.filter(
                diak=user
            ).select_related(
                'diak', 'forgatas', 'forgatas__location'
            ).order_by('-date', '-timeFrom')
        )
        perf.end_timer("fetch_absences")
        perf.record_count("absence_count", len(absences))
        
        perf.start_timer("serialize")
        result = [serialize_absence(a) for a in absences]
        perf.end_timer("serialize")
        
        if debug_performance:
            return 200, {
                'data': result,
                'performance': perf.get_results()
            }
        
        return 200, result
    
    # ============================================================================
    # Profile Endpoints
    # ============================================================================
    
    @router.get(
        "/profile/{email}",
        response={200: ProfileDetailedSchema, 404: ErrorSchema, 401: ErrorSchema},
        summary="Get user profile by email",
        description="Retrieve detailed user profile information using email address as the common key."
    )
    def get_profile_by_email(request, email: str, debug_performance: bool = False):
        """Get user profile by email address."""
        perf = PerformanceMonitor(debug_performance)
        
        # Find user by email
        perf.start_timer("fetch_user")
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return 404, {"detail": f"No user found with email: {email}"}
        perf.end_timer("fetch_user")
        
        # Get or create profile
        perf.start_timer("fetch_profile")
        profile, created = Profile.objects.select_related(
            'user', 'osztaly', 'osztaly__tanev', 'stab', 'radio_stab'
        ).get_or_create(user=user)
        perf.end_timer("fetch_profile")
        perf.record_count("profile_created", 1 if created else 0)
        
        perf.start_timer("serialize")
        result = serialize_profile_detailed(profile)
        perf.end_timer("serialize")
        
        if debug_performance:
            result['performance'] = perf.get_results()
        
        return 200, result
    
    @router.get(
        "/user/email/{email}",
        response={200: ProfileMinimalSchema, 404: ErrorSchema, 401: ErrorSchema},
        summary="Get user details by email",
        description="Retrieve user details using email address. Returns minimal profile information."
    )
    def get_user_by_email(request, email: str, debug_performance: bool = False):
        """Get user details by email address (minimal info)."""
        perf = PerformanceMonitor(debug_performance)
        
        # Find user by email
        perf.start_timer("fetch_user")
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return 404, {"detail": f"No user found with email: {email}"}
        perf.end_timer("fetch_user")
        
        # Get or create profile
        perf.start_timer("fetch_profile")
        profile, created = Profile.objects.select_related(
            'user', 'osztaly', 'osztaly__tanev', 'stab', 'radio_stab'
        ).get_or_create(user=user)
        perf.end_timer("fetch_profile")
        perf.record_count("profile_created", 1 if created else 0)
        
        perf.start_timer("serialize")
        result = serialize_profile_minimal(profile)
        perf.end_timer("serialize")
        
        if debug_performance:
            result['performance'] = perf.get_results()
        
        return 200, result
    
    # Register the router with the main API
    api.add_router("/sync", router)


# ============================================================================
# Module Export
# ============================================================================

__all__ = ['register_sync_endpoints']
