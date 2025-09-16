"""
Student Management API Module for Forgatás Creation

This module provides endpoints for student listing and reporter selection,
specifically designed to support forgatás creation forms.

Public API Overview:
==================

The Student API provides filtered access to student data for various
organizational needs, particularly focused on reporter selection and
media student identification.

Base URL: /api/students/

Protected Endpoints (JWT Token Required):

Student Listing:
- GET  /students                - List students with filters
- GET  /students/reporters      - List students eligible as reporters
- GET  /students/media          - List media students (F section)
- GET  /students/by-grade/{grade} - List students by grade level

Reporter Management:
- GET  /students/reporters/available - Available reporters for date/time
- GET  /students/reporters/experienced - Experienced reporters

Student Selection Features:
==========================

The student endpoints provide comprehensive filtering for various use cases:

1. **Reporter Selection**: Only current 10F students eligible to be assigned as reporters
2. **Media Students**: Students in media specialization (F section classes)
3. **Grade Filtering**: Students by specific grade levels (9F, 10F, 11F, 12F)
4. **Availability**: Students available for specific dates/times
5. **Experience Tracking**: Reporter experience levels

Data Structure:
==============

Student Response:
- id: Unique student identifier
- username: Student login username
- first_name: Student first name
- last_name: Student last name
- full_name: Computed full name
- email: Student email address
- osztaly: Class information with grade/section
- can_be_reporter: Reporter eligibility flag
- is_media_student: Media specialization flag
- telefonszam: Phone number (optional)
- reporter_experience: Previous reporter assignments

Class Information:
- id: Class unique identifier
- display_name: Human-readable class name (e.g., "10F")
- section: Class section letter (A, B, F, etc.)
- start_year: Year the class started
- current_grade: Current grade level

Reporter Specific Data:
- reporter_sessions_count: Number of previous reporter assignments
- last_reporter_date: Date of last reporter assignment
- is_experienced: Has 3+ reporter sessions
- availability_status: Current availability for assignments

Business Logic:
==============

Reporter Eligibility Rules:
- Must be an active student (is_active=True)
- Must have a profile with medias=True
- Must be in current 10F class only
- No current filming session conflicts

Media Student Identification:
- Students in classes with section='F'
- Includes 9F, 10F, 11F, 12F students
- Special handling for radio students (9F)

Grade Level Calculation:
- Based on class start_year and current academic year
- Automatic adjustment for academic year boundaries
- Consistent with Osztaly model logic

Example Usage:
=============

Get all available reporters:
curl -H "Authorization: Bearer {token}" /api/students/reporters

Get 10F students specifically:
curl -H "Authorization: Bearer {token}" /api/students?section=F&grade=10

Get experienced reporters:
curl -H "Authorization: Bearer {token}" /api/students/reporters/experienced
"""

from ninja import Schema
from django.contrib.auth.models import User
from api.models import Profile, Osztaly, Tanev, Forgatas
from .auth import JWTAuth, ErrorSchema
from datetime import datetime, date
from typing import Optional
from django.db.models import Q, Count

# ============================================================================
# Schemas
# ============================================================================

class OsztalyInfoSchema(Schema):
    """Class information schema for student responses."""
    id: int
    display_name: str
    section: str
    start_year: int
    current_grade: Optional[int] = None

class StudentSchema(Schema):
    """Comprehensive student information schema."""
    id: int
    username: str
    first_name: str
    last_name: str
    full_name: str
    email: str
    osztaly: Optional[OsztalyInfoSchema] = None
    can_be_reporter: bool
    is_media_student: bool
    telefonszam: Optional[str] = None

class ReporterSchema(Schema):
    """Reporter-specific student information schema."""
    id: int
    username: str
    full_name: str
    osztaly_display: str
    grade_level: Optional[int] = None
    is_experienced: bool
    reporter_sessions_count: int = 0
    last_reporter_date: Optional[str] = None
    reason: str

class MediaStudentSchema(Schema):
    """Media student information schema."""
    id: int
    username: str
    full_name: str
    osztaly_display: str
    section: str
    grade_level: Optional[int] = None
    is_radio_student: bool = False

# ============================================================================
# Utility Functions
# ============================================================================

def create_osztaly_info_response(osztaly: Osztaly) -> dict:
    """
    Create class information response.
    
    Args:
        osztaly: Osztaly model instance
        
    Returns:
        Dictionary with class information
    """
    if not osztaly:
        return None
    
    # Calculate current grade level
    current_grade = None
    if osztaly.szekcio.upper() == 'F':
        current_tanev = Tanev.get_active()
        if current_tanev:
            current_grade = current_tanev.start_year - osztaly.startYear + 8
    
    return {
        "id": osztaly.id,
        "display_name": str(osztaly),
        "section": osztaly.szekcio.upper(),
        "start_year": osztaly.startYear,
        "current_grade": current_grade
    }

def create_student_response(user: User, include_reporter_stats: bool = False) -> dict:
    """
    Create student information response.
    
    Args:
        user: Django User object
        include_reporter_stats: Whether to include reporter statistics
        
    Returns:
        Dictionary with student information
    """
    try:
        profile = user.profile
    except Profile.DoesNotExist:
        profile = None
    
    # Determine if student can be reporter (only current 10F students)
    can_be_reporter = False
    if user.is_active and profile and profile.medias and profile.osztaly:
        # Check if this is a current 10F student
        current_tanev = Tanev.get_active()
        if current_tanev and profile.osztaly.szekcio.upper() == 'F':
            # Calculate current grade level
            grade_level = current_tanev.start_year - profile.osztaly.startYear + 8
            can_be_reporter = (grade_level == 10)
    
    # Determine if student is media student (F section)
    is_media_student = (
        profile and 
        profile.osztaly and 
        profile.osztaly.szekcio.upper() == 'F'
    )
    
    # Get reporter statistics if requested
    reporter_stats = {}
    if include_reporter_stats:
        reporter_sessions = Forgatas.objects.filter(szerkeszto=user)
        reporter_stats = {
            "reporter_sessions_count": reporter_sessions.count(),
            "last_reporter_date": reporter_sessions.order_by('-date').first().date.isoformat() if reporter_sessions.exists() else None,
            "is_experienced": reporter_sessions.count() >= 3
        }
    
    return {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": user.get_full_name(),
        "email": user.email,
        "osztaly": create_osztaly_info_response(profile.osztaly if profile else None),
        "can_be_reporter": can_be_reporter,
        "is_media_student": is_media_student,
        "telefonszam": profile.telefonszam if profile else None,
        **reporter_stats
    }

def get_students_base_queryset():
    """
    Get base queryset for students with optimized joins.
    
    Returns:
        QuerySet of User objects with related data
    """
    return User.objects.select_related(
        'profile', 
        'profile__osztaly'
    ).filter(
        is_active=True,
        profile__isnull=False
    ).order_by('last_name', 'first_name')

# ============================================================================
# API Endpoints
# ============================================================================

def register_student_endpoints(api):
    """Register all student-related endpoints with the API router."""
    
    @api.get("/students", auth=JWTAuth(), response={200: list[StudentSchema], 401: ErrorSchema})
    def list_students(request, 
                     section: str = None, 
                     grade: int = None, 
                     can_be_reporter: bool = None,
                     search: str = None):
        """
        List students with comprehensive filtering options.
        
        Provides filtered access to student data for various organizational needs.
        
        Args:
            section: Filter by class section (A, B, F, etc.)
            grade: Filter by grade level (9, 10, 11, 12)
            can_be_reporter: Filter students eligible as reporters
            search: Search by name or username
            
        Returns:
            200: List of students with filtering applied
            401: Authentication failed
        """
        queryset = get_students_base_queryset()
        
        # Apply filters
        if section:
            queryset = queryset.filter(profile__osztaly__szekcio__iexact=section)
        
        if grade:
            # For F section, calculate based on start year
            if section and section.upper() == 'F':
                current_tanev = Tanev.get_active()
                if current_tanev:
                    target_start_year = current_tanev.start_year - grade + 8
                    queryset = queryset.filter(profile__osztaly__startYear=target_start_year)
            else:
                # For other sections, use different logic if needed
                pass
        
        if can_be_reporter is not None:
            if can_be_reporter:
                # Only current 10F students can be reporters
                current_tanev = Tanev.get_active()
                if current_tanev:
                    target_start_year_10f = current_tanev.start_year - 2
                    queryset = queryset.filter(
                        profile__medias=True,
                        profile__osztaly__isnull=False,
                        profile__osztaly__szekcio__iexact='F',
                        profile__osztaly__startYear=target_start_year_10f
                    )
                else:
                    # No active school year, no one can be reporter
                    queryset = queryset.none()
            else:
                # Exclude current 10F students
                current_tanev = Tanev.get_active()
                if current_tanev:
                    target_start_year_10f = current_tanev.start_year - 2
                    queryset = queryset.exclude(
                        profile__medias=True,
                        profile__osztaly__isnull=False,
                        profile__osztaly__szekcio__iexact='F',
                        profile__osztaly__startYear=target_start_year_10f
                    )
        
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(username__icontains=search)
            )
        
        students = [create_student_response(user) for user in queryset]
        return 200, students
    
    @api.get("/students/reporters", auth=JWTAuth(), response={200: list[ReporterSchema], 401: ErrorSchema, 400: ErrorSchema})
    def list_reporters(request):
        """
        List students eligible to be reporters.
        
        Returns three groups:
        1. 10F students (reason: "Harmadév")
        2. Production leaders (reason: "GYV") 
        3. Users with editor permission (reason: "Lehetséges Szerkesztő")
        
        Returns:
            200: List of eligible reporters from all three groups
            401: Authentication failed
            400: No active school year found
        """
        # Calculate the start year for current 10F students
        current_tanev = Tanev.get_active()
        if not current_tanev:
            return 400, {"message": "No active school year found."}
        
        reporters = []
        
        # Group 1: 10F students (Harmadév)
        # 10F students started when current_tanev.start_year - 10 + 8 = current_tanev.start_year - 2
        target_start_year_10f = current_tanev.start_year - 2
        
        tenf_queryset = get_students_base_queryset().filter(
            profile__medias=True,
            profile__osztaly__isnull=False,
            profile__osztaly__szekcio__iexact='F',
            profile__osztaly__startYear=target_start_year_10f
        ).annotate(
            reporter_count=Count('forgatas')
        )
        
        for user in tenf_queryset:
            profile = user.profile
            osztaly_display = str(profile.osztaly) if profile.osztaly else "Nincs osztály"
            
            # Calculate grade level for F section students
            grade_level = None
            if profile.osztaly and profile.osztaly.szekcio.upper() == 'F':
                if current_tanev:
                    grade_level = current_tanev.start_year - profile.osztaly.startYear + 8
            
            # Get reporter statistics
            last_session = Forgatas.objects.filter(szerkeszto=user).order_by('-date').first()
            
            reporters.append({
                "id": user.id,
                "username": user.username,
                "full_name": user.get_full_name(),
                "osztaly_display": osztaly_display,
                "grade_level": grade_level,
                "is_experienced": user.reporter_count >= 3,
                "reporter_sessions_count": user.reporter_count,
                "last_reporter_date": last_session.date.isoformat() if last_session else None,
                "reason": "Harmadév"
            })
        
        # Group 2: Production leaders (GYV)
        production_leaders_queryset = get_students_base_queryset().filter(
            profile__special_role='production_leader'
        ).annotate(
            reporter_count=Count('forgatas')
        )
        
        for user in production_leaders_queryset:
            profile = user.profile
            osztaly_display = str(profile.osztaly) if profile.osztaly else "Nincs osztály"
            
            # Calculate grade level if they have a class
            grade_level = None
            if profile.osztaly and profile.osztaly.szekcio.upper() == 'F':
                if current_tanev:
                    grade_level = current_tanev.start_year - profile.osztaly.startYear + 8
            
            # Get reporter statistics
            last_session = Forgatas.objects.filter(szerkeszto=user).order_by('-date').first()
            
            reporters.append({
                "id": user.id,
                "username": user.username,
                "full_name": user.get_full_name(),
                "osztaly_display": osztaly_display,
                "grade_level": grade_level,
                "is_experienced": user.reporter_count >= 3,
                "reporter_sessions_count": user.reporter_count,
                "last_reporter_date": last_session.date.isoformat() if last_session else None,
                "reason": "GYV"
            })
        
        # Group 3: Users with editor permission (Lehetséges Szerkesztő)
        editor_permission_queryset = get_students_base_queryset().filter(
            profile__szerkeszto=True
        ).annotate(
            reporter_count=Count('forgatas')
        )
        
        for user in editor_permission_queryset:
            profile = user.profile
            osztaly_display = str(profile.osztaly) if profile.osztaly else "Nincs osztály"
            
            # Calculate grade level if they have a class
            grade_level = None
            if profile.osztaly and profile.osztaly.szekcio.upper() == 'F':
                if current_tanev:
                    grade_level = current_tanev.start_year - profile.osztaly.startYear + 8
            
            # Get reporter statistics
            last_session = Forgatas.objects.filter(szerkeszto=user).order_by('-date').first()
            
            reporters.append({
                "id": user.id,
                "username": user.username,
                "full_name": user.get_full_name(),
                "osztaly_display": osztaly_display,
                "grade_level": grade_level,
                "is_experienced": user.reporter_count >= 3,
                "reporter_sessions_count": user.reporter_count,
                "last_reporter_date": last_session.date.isoformat() if last_session else None,
                "reason": "Lehetséges Szerkesztő"
            })
        
        # Remove duplicates based on user ID (if someone appears in multiple groups)
        seen_ids = set()
        unique_reporters = []
        for reporter in reporters:
            if reporter["id"] not in seen_ids:
                unique_reporters.append(reporter)
                seen_ids.add(reporter["id"])
        
        return 200, unique_reporters
    
    @api.get("/students/media", auth=JWTAuth(), response={200: list[MediaStudentSchema], 401: ErrorSchema})
    def list_media_students(request):
        """
        List media students (F section students).
        
        Returns students in media specialization classes with media-specific information.
        
        Returns:
            200: List of media students
            401: Authentication failed
        """
        queryset = get_students_base_queryset().filter(
            profile__osztaly__szekcio__iexact='F'
        )
        
        media_students = []
        for user in queryset:
            profile = user.profile
            osztaly_display = str(profile.osztaly) if profile.osztaly else "Nincs osztály"
            
            # Calculate grade level
            grade_level = None
            if profile.osztaly:
                current_tanev = Tanev.get_active()
                if current_tanev:
                    grade_level = current_tanev.start_year - profile.osztaly.startYear + 8
            
            # Check if radio student (9F)
            is_radio_student = grade_level == 9 if grade_level else False
            
            media_students.append({
                "id": user.id,
                "username": user.username,
                "full_name": user.get_full_name(),
                "osztaly_display": osztaly_display,
                "section": profile.osztaly.szekcio.upper() if profile.osztaly else "",
                "grade_level": grade_level,
                "is_radio_student": is_radio_student
            })
        
        return 200, media_students
    
    @api.get("/students/by-grade/{grade}", auth=JWTAuth(), response={200: list[StudentSchema], 401: ErrorSchema})
    def list_students_by_grade(request, grade: int):
        """
        List students by specific grade level.
        
        Returns students in the specified grade level, primarily for F section students.
        
        Args:
            grade: Grade level (9, 10, 11, 12)
            
        Returns:
            200: List of students in the specified grade
            401: Authentication failed
            400: Invalid grade level
        """
        if grade not in [9, 10, 11, 12]:
            return 400, {"message": "Invalid grade level. Must be 9, 10, 11, or 12."}
        
        # Calculate target start year for F section
        current_tanev = Tanev.get_active()
        if not current_tanev:
            return 400, {"message": "No active school year found."}
        
        target_start_year = current_tanev.start_year - grade + 8
        
        queryset = get_students_base_queryset().filter(
            profile__osztaly__szekcio__iexact='F',
            profile__osztaly__startYear=target_start_year
        )
        
        students = [create_student_response(user) for user in queryset]
        return 200, students
    
    @api.get("/students/reporters/experienced", auth=JWTAuth(), response={200: list[ReporterSchema], 401: ErrorSchema, 400: ErrorSchema})
    def list_experienced_reporters(request):
        """
        List experienced reporters (3+ filming sessions).
        
        Returns only current 10F students with significant reporter experience for priority assignment.
        
        Returns:
            200: List of experienced reporters (only 10F students)
            401: Authentication failed
            400: No active school year found
        """
        # Calculate the start year for current 10F students
        current_tanev = Tanev.get_active()
        if not current_tanev:
            return 401, {"message": "No active school year found."}
        
        # 10F students started when current_tanev.start_year - 10 + 8 = current_tanev.start_year - 2
        target_start_year_10f = current_tanev.start_year - 2
        
        queryset = get_students_base_queryset().filter(
            profile__medias=True,
            profile__osztaly__isnull=False,
            profile__osztaly__szekcio__iexact='F',
            profile__osztaly__startYear=target_start_year_10f
        ).annotate(
            reporter_count=Count('forgatas')
        ).filter(
            reporter_count__gte=3
        )
        
        experienced_reporters = []
        for user in queryset:
            profile = user.profile
            osztaly_display = str(profile.osztaly) if profile.osztaly else "Nincs osztály"
            
            # Calculate grade level
            grade_level = None
            if profile.osztaly and profile.osztaly.szekcio.upper() == 'F':
                current_tanev = Tanev.get_active()
                if current_tanev:
                    grade_level = current_tanev.start_year - profile.osztaly.startYear + 8
            
            # Get reporter statistics
            last_session = Forgatas.objects.filter(szerkeszto=user).order_by('-date').first()
            
            experienced_reporters.append({
                "id": user.id,
                "username": user.username,
                "full_name": user.get_full_name(),
                "osztaly_display": osztaly_display,
                "grade_level": grade_level,
                "is_experienced": True,
                "reporter_sessions_count": user.reporter_count,
                "last_reporter_date": last_session.date.isoformat() if last_session else None
            })
        
        return 200, experienced_reporters
    
    @api.get("/students/reporters/available", auth=JWTAuth(), response={200: list[ReporterSchema], 401: ErrorSchema, 400: ErrorSchema})
    def list_available_reporters(request, date: str = None, time_from: str = None, time_to: str = None):
        """
        List reporters available for specific date/time.
        
        Returns only current 10F students who don't have conflicting filming sessions.
        
        Args:
            date: Date to check availability (YYYY-MM-DD)
            time_from: Start time to check (HH:MM)
            time_to: End time to check (HH:MM)
            
        Returns:
            200: List of available reporters (only 10F students)
            401: Authentication failed
            400: Invalid date/time parameters or no active school year
        """
        # Calculate the start year for current 10F students
        current_tanev = Tanev.get_active()
        if not current_tanev:
            return 401, {"message": "No active school year found."}
        
        # 10F students started when current_tanev.start_year - 10 + 8 = current_tanev.start_year - 2
        target_start_year_10f = current_tanev.start_year - 2
        
        queryset = get_students_base_queryset().filter(
            profile__medias=True,
            profile__osztaly__isnull=False,
            profile__osztaly__szekcio__iexact='F',
            profile__osztaly__startYear=target_start_year_10f
        )
        
        # If date/time specified, filter out conflicting reporters
        if date and time_from and time_to:
            try:
                check_date = datetime.strptime(date, '%Y-%m-%d').date()
                check_time_from = datetime.strptime(time_from, '%H:%M').time()
                check_time_to = datetime.strptime(time_to, '%H:%M').time()
                
                # Find reporters with conflicting sessions
                conflicting_reporters = Forgatas.objects.filter(
                    date=check_date,
                    szerkeszto__isnull=False
                ).filter(
                    Q(timeFrom__lt=check_time_to) & Q(timeTo__gt=check_time_from)
                ).values_list('szerkeszto_id', flat=True)
                
                # Exclude conflicting reporters
                queryset = queryset.exclude(id__in=conflicting_reporters)
                
            except ValueError:
                return 400, {"message": "Invalid date or time format. Use YYYY-MM-DD for date and HH:MM for time."}
        
        reporters = []
        for user in queryset:
            profile = user.profile
            osztaly_display = str(profile.osztaly) if profile.osztaly else "Nincs osztály"
            
            # Calculate grade level
            grade_level = None
            if profile.osztaly and profile.osztaly.szekcio.upper() == 'F':
                current_tanev = Tanev.get_active()
                if current_tanev:
                    grade_level = current_tanev.start_year - profile.osztaly.startYear + 8
            
            # Get reporter statistics
            reporter_count = Forgatas.objects.filter(szerkeszto=user).count()
            last_session = Forgatas.objects.filter(szerkeszto=user).order_by('-date').first()
            
            reporters.append({
                "id": user.id,
                "username": user.username,
                "full_name": user.get_full_name(),
                "osztaly_display": osztaly_display,
                "grade_level": grade_level,
                "is_experienced": reporter_count >= 3,
                "reporter_sessions_count": reporter_count,
                "last_reporter_date": last_session.date.isoformat() if last_session else None
            })
        
        return 200, reporters
