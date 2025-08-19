"""
FTV User Import API Module

This module handles bulk user import functionality from CSV files or direct data,
creating users, profiles, radio stabs, and classes based on the import data.

Public API Overview:
==================

Base URL: /api/user-import/

Endpoints:
- POST /import-users - Import users from structured data
- POST /validate-import - Validate import data without creating users

Features:
- Bulk user creation with profiles
- Automatic radio stab generation (format: "YYYY XX" where XX is stab callsign)
- Class creation based on start year and section
- Username generation from email addresses
- Profile permission assignment
- Class teacher assignment

Import Data Structure:
=====================

Expected data format for each user:
{
    "vezetekNev": "Nagy",
    "keresztNev": "Imre", 
    "telefonszam": "+36301234567",
    "email": "nagy.imre.25f@szlgbp.hu",
    "stab": "B stáb",
    "kezdesEve": "2025",
    "tagozat": "F",
    "radio": "B3",
    "gyartasvezeto": "Igen",
    "mediatanar": "Igen", 
    "osztalyfonok": "Igen",
    "osztalyai": "2023F"
}

Role Mapping:
============

Admin Types:
- "Igen" in mediatanar -> 'teacher'
- Default -> 'none'

Special Roles:
- "Igen" in gyartasvezeto -> 'production_leader'
- Default -> 'none'

Class Teacher Assignment:
- Users with osztalyfonok = "Igen" are assigned as class teachers
- Classes specified in osztalyai column are managed
"""

from ninja import Schema, File, UploadedFile
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from api.models import Profile, Osztaly, Stab, RadioStab, Tanev
from .auth import JWTAuth, ErrorSchema
from .user_management import check_system_admin_permissions, generate_random_password
from .user_import_utils import (
    UserImportData, extract_username_from_email, normalize_yes_no,
    parse_class_name, parse_radio_stab_name, get_current_tanev,
    get_or_create_stab, get_or_create_radio_stab, get_or_create_class,
    parse_csv_file, process_single_user_import, process_bulk_user_import,
    get_sample_users_data
)
from typing import Optional, List
import re

# ============================================================================
# Schemas
# ============================================================================

class UserImportSchema(Schema):
    """Schema for single user import data."""
    vezetekNev: str
    keresztNev: str
    telefonszam: Optional[str] = None
    email: str
    stab: Optional[str] = None
    kezdesEve: Optional[str] = None
    tagozat: Optional[str] = None
    radio: Optional[str] = None
    gyartasvezeto: Optional[str] = None
    mediatana: Optional[str] = None
    osztalyfonok: Optional[str] = None
    osztalyai: Optional[str] = None
    
    @classmethod
    def from_import_data(cls, import_data: UserImportData):
        """Create schema from UserImportData."""
        return cls(
            vezetekNev=import_data.vezetekNev,
            keresztNev=import_data.keresztNev,
            telefonszam=import_data.telefonszam,
            email=import_data.email,
            stab=import_data.stab,
            kezdesEve=import_data.kezdesEve,
            tagozat=import_data.tagozat,
            radio=import_data.radio,
            gyartasvezeto=import_data.gyartasvezeto,
            mediatana=import_data.mediatana,
            osztalyfonok=import_data.osztalyfonok,
            osztalyai=import_data.osztalyai
        )
    
    def to_import_data(self) -> UserImportData:
        """Convert schema to UserImportData."""
        return UserImportData(
            vezetekNev=self.vezetekNev,
            keresztNev=self.keresztNev,
            telefonszam=self.telefonszam,
            email=self.email,
            stab=self.stab,
            kezdesEve=self.kezdesEve,
            tagozat=self.tagozat,
            radio=self.radio,
            gyartasvezeto=self.gyartasvezeto,
            mediatana=self.mediatana,
            osztalyfonok=self.osztalyfonok,
            osztalyai=self.osztalyai
        )

class BulkUserImportSchema(Schema):
    """Schema for bulk user import."""
    users: List[UserImportSchema]
    dry_run: bool = False
    send_emails: bool = True

class ImportResultSchema(Schema):
    """Schema for import operation results."""
    success: bool
    total_users: int
    created_users: int
    created_classes: int
    created_stabs: int
    created_radio_stabs: int
    errors: List[str]
    warnings: List[str]
    user_details: List[dict]

class CsvPreviewSchema(Schema):
    """Schema for CSV file preview results with detailed model information."""
    success: bool
    total_rows: int
    parsed_users: List[UserImportSchema]
    errors: List[str]
    warnings: List[str]
    models_preview: dict  # Detailed preview of all models that will be created
    summary: dict  # Summary statistics

class ModelToCreateSchema(Schema):
    """Schema for models that will be created during import."""
    model_type: str  # 'user', 'profile', 'class', 'stab', 'radio_stab'
    action: str      # 'create', 'update', 'assign'
    data: dict       # The actual model data
    exists: bool     # Whether the model already exists
    conflicts: List[str]  # Any conflicts or issues

class ValidationResultSchema(Schema):
    """Schema for detailed validation results with model preview."""
    success: bool
    total_users: int
    models_to_create: List[ModelToCreateSchema]
    summary: dict    # Summary counts by model type
    errors: List[str]
    warnings: List[str]
    user_details: List[dict]

class SystemOverviewSchema(Schema):
    """Schema for system overview statistics."""
    total_users: int
    total_classes: int
    total_stabs: int
    total_radio_stabs: int
    active_users: int
    inactive_users: int
    admin_users: int
    teacher_users: int
    student_users: int
    classes_with_teachers: int
    classes_without_teachers: int
    last_updated: str

class UserStatusSchema(Schema):
    """Schema for detailed user status."""
    id: int
    username: str
    full_name: str
    email: str
    is_active: bool
    admin_type: str
    special_role: str
    osztaly: Optional[str]
    stab: Optional[str]
    radio_stab: Optional[str]
    is_osztaly_fonok: bool
    date_joined: str
    last_login: Optional[str]

class ClassStatusSchema(Schema):
    """Schema for detailed class status."""
    id: int
    name: str
    start_year: int
    section: str
    tanev: Optional[str]
    student_count: int
    teacher_count: int
    class_teachers: List[str]
    has_class_teacher: bool
    created_at: str

class StabStatusSchema(Schema):
    """Schema for detailed stab status."""
    id: int
    name: str
    member_count: int
    radio_stab_count: int
    members: List[str]
    radio_stabs: List[str]

# ============================================================================
# Import Logic (now using shared utilities)
# ============================================================================

def get_system_statistics():
    """Get comprehensive system overview statistics."""
    from django.utils import timezone
    
    # User statistics
    all_users = User.objects.all()
    total_users = all_users.count()
    active_users = all_users.filter(is_active=True).count()
    inactive_users = total_users - active_users
    
    # Profile-based statistics
    all_profiles = Profile.objects.select_related('user', 'osztaly', 'stab', 'radio_stab').all()
    admin_users = all_profiles.filter(admin_type__in=['system_admin', 'teacher']).count()
    teacher_users = all_profiles.filter(admin_type='teacher').count()
    student_users = all_profiles.filter(admin_type='none', osztaly__isnull=False).count()
    
    # Class statistics
    all_classes = Osztaly.objects.all()
    total_classes = all_classes.count()
    classes_with_teachers = all_classes.filter(osztaly_fonokei__isnull=False).distinct().count()
    classes_without_teachers = total_classes - classes_with_teachers
    
    # Stab statistics
    total_stabs = Stab.objects.count()
    total_radio_stabs = RadioStab.objects.count()
    
    return {
        'total_users': total_users,
        'total_classes': total_classes,
        'total_stabs': total_stabs,
        'total_radio_stabs': total_radio_stabs,
        'active_users': active_users,
        'inactive_users': inactive_users,
        'admin_users': admin_users,
        'teacher_users': teacher_users,
        'student_users': student_users,
        'classes_with_teachers': classes_with_teachers,
        'classes_without_teachers': classes_without_teachers,
        'last_updated': timezone.now().isoformat()
    }

def get_detailed_user_status() -> List[dict]:
    """Get detailed status for all users."""
    users_data = []
    
    for profile in Profile.objects.select_related('user', 'osztaly', 'stab', 'radio_stab').all():
        user = profile.user
        
        # Check if user is class teacher
        is_osztaly_fonok = user.osztaly_fonok_set.exists()
        
        user_data = {
            'id': user.id,
            'username': user.username,
            'full_name': f"{user.last_name} {user.first_name}",
            'email': user.email,
            'is_active': user.is_active,
            'admin_type': profile.admin_type,
            'special_role': profile.special_role,
            'osztaly': str(profile.osztaly) if profile.osztaly else None,
            'stab': profile.stab.name if profile.stab else None,
            'radio_stab': profile.radio_stab.name if profile.radio_stab else None,
            'is_osztaly_fonok': is_osztaly_fonok,
            'date_joined': user.date_joined.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None
        }
        users_data.append(user_data)
    
    return users_data

def get_detailed_class_status() -> List[dict]:
    """Get detailed status for all classes."""
    classes_data = []
    
    for osztaly in Osztaly.objects.prefetch_related('profile_set', 'osztaly_fonokei').all():
        # Count students in this class
        student_count = osztaly.profile_set.filter(admin_type='none').count()
        
        # Count teachers assigned to this class (not necessarily class teachers)
        teacher_count = osztaly.profile_set.filter(admin_type='teacher').count()
        
        # Get class teachers
        class_teachers = [f"{teacher.last_name} {teacher.first_name}" 
                         for teacher in osztaly.osztaly_fonokei.all()]
        
        class_data = {
            'id': osztaly.id,
            'name': str(osztaly),
            'start_year': osztaly.startYear,
            'section': osztaly.szekcio,
            'tanev': str(osztaly.tanev) if osztaly.tanev else None,
            'student_count': student_count,
            'teacher_count': teacher_count,
            'class_teachers': class_teachers,
            'has_class_teacher': len(class_teachers) > 0,
            'created_at': osztaly.id  # Using ID as proxy for creation time since no created_at field
        }
        classes_data.append(class_data)
    
    return classes_data

def get_detailed_stab_status() -> List[dict]:
    """Get detailed status for all stabs."""
    stabs_data = []
    
    for stab in Stab.objects.prefetch_related('profile_set', 'radiostab_set').all():
        # Get stab members
        members = [f"{profile.user.last_name} {profile.user.first_name}" 
                  for profile in stab.profile_set.all()]
        
        # Get radio stabs associated with this stab
        radio_stabs = [radio_stab.name for radio_stab in stab.radiostab_set.all()]
        
        stab_data = {
            'id': stab.id,
            'name': stab.name,
            'member_count': len(members),
            'radio_stab_count': len(radio_stabs),
            'members': members,
            'radio_stabs': radio_stabs
        }
        stabs_data.append(stab_data)
    
    return stabs_data

def process_detailed_validation(users_data: List[UserImportSchema]) -> dict:
    """
    Process validation and return detailed information about all models that would be created.
    
    This function analyzes the import data and returns comprehensive information about:
    - All users that would be created
    - All profiles that would be created
    - All classes that would be created
    - All stabs that would be created
    - All radio stabs that would be created
    - Any conflicts or issues
    """
    result = {
        'success': True,
        'total_users': len(users_data),
        'models_to_create': [],
        'summary': {
            'users': 0,
            'profiles': 0,
            'classes': 0,
            'stabs': 0,
            'radio_stabs': 0,
            'class_assignments': 0
        },
        'errors': [],
        'warnings': [],
        'user_details': []
    }
    
    # Track what we've already processed to avoid duplicates
    processed_classes = set()
    processed_stabs = set()
    processed_radio_stabs = set()
    
    try:
        current_tanev = get_current_tanev()
        
        for i, user_data in enumerate(users_data):
            user_errors = []
            user_warnings = []
            
            try:
                # Generate username from email
                username = extract_username_from_email(user_data.email)
                
                # Check for conflicts
                user_exists = User.objects.filter(username=username).exists()
                email_exists = User.objects.filter(email=user_data.email).exists()
                
                if user_exists:
                    user_errors.append(f"Felhasználónév már létezik: {username}")
                if email_exists:
                    user_errors.append(f"Email cím már létezik: {user_data.email}")
                
                # Process class creation
                if user_data.kezdesEve and user_data.tagozat:
                    start_year = int(user_data.kezdesEve)
                    section = user_data.tagozat.upper()
                    class_key = f"{start_year}_{section}"
                    
                    if class_key not in processed_classes:
                        class_exists = Osztaly.objects.filter(startYear=start_year, szekcio=section).exists()
                        
                        result['models_to_create'].append({
                            'model_type': 'class',
                            'action': 'get_or_create',
                            'data': {
                                'startYear': start_year,
                                'szekcio': section,
                                'tanev': str(current_tanev) if current_tanev else None,
                                'display_name': f"{start_year}{section}"
                            },
                            'exists': class_exists,
                            'conflicts': []
                        })
                        
                        if not class_exists:
                            result['summary']['classes'] += 1
                        processed_classes.add(class_key)
                
                # Process stab creation
                if user_data.stab:
                    stab_name = user_data.stab.strip()
                    if stab_name not in processed_stabs:
                        stab_exists = Stab.objects.filter(name=stab_name).exists()
                        
                        result['models_to_create'].append({
                            'model_type': 'stab',
                            'action': 'get_or_create',
                            'data': {
                                'name': stab_name
                            },
                            'exists': stab_exists,
                            'conflicts': []
                        })
                        
                        if not stab_exists:
                            result['summary']['stabs'] += 1
                        processed_stabs.add(stab_name)
                
                # Process radio stab creation
                if user_data.radio and user_data.kezdesEve:
                    radio_name = parse_radio_stab_name(user_data.kezdesEve, user_data.radio)
                    if radio_name and radio_name not in processed_radio_stabs:
                        radio_exists = RadioStab.objects.filter(name=radio_name).exists()
                        
                        result['models_to_create'].append({
                            'model_type': 'radio_stab',
                            'action': 'get_or_create',
                            'data': {
                                'name': radio_name,
                                'team_code': user_data.radio.upper(),
                                'description': f'Automatikusan létrehozott rádiós stáb importálás során'
                            },
                            'exists': radio_exists,
                            'conflicts': []
                        })
                        
                        if not radio_exists:
                            result['summary']['radio_stabs'] += 1
                        processed_radio_stabs.add(radio_name)
                
                # Process user creation
                if not user_exists and not email_exists:
                    admin_type = 'teacher' if normalize_yes_no(user_data.mediatana) else 'none'
                    special_role = 'production_leader' if normalize_yes_no(user_data.gyartasvezeto) else 'none'
                    
                    result['models_to_create'].append({
                        'model_type': 'user',
                        'action': 'create',
                        'data': {
                            'username': username,
                            'email': user_data.email,
                            'first_name': user_data.keresztNev,
                            'last_name': user_data.vezetekNev,
                            'is_active': True
                        },
                        'exists': False,
                        'conflicts': []
                    })
                    
                    result['models_to_create'].append({
                        'model_type': 'profile',
                        'action': 'create',
                        'data': {
                            'user_username': username,
                            'admin_type': admin_type,
                            'special_role': special_role,
                            'telefonszam': user_data.telefonszam,
                            'osztaly': f"{user_data.kezdesEve}{user_data.tagozat}" if user_data.kezdesEve and user_data.tagozat else None,
                            'stab': user_data.stab,
                            'radio_stab': parse_radio_stab_name(user_data.kezdesEve, user_data.radio) if user_data.radio and user_data.kezdesEve else None,
                            'medias': True
                        },
                        'exists': False,
                        'conflicts': []
                    })
                    
                    result['summary']['users'] += 1
                    result['summary']['profiles'] += 1
                    
                    # Process class teacher assignments
                    if normalize_yes_no(user_data.osztalyfonok) and user_data.osztalyai:
                        for class_name in user_data.osztalyai.split(','):
                            class_name = class_name.strip()
                            start_year, section = parse_class_name(class_name)
                            if start_year and section:
                                result['models_to_create'].append({
                                    'model_type': 'class_assignment',
                                    'action': 'assign',
                                    'data': {
                                        'user_username': username,
                                        'class_name': f"{start_year}{section}",
                                        'assignment_type': 'osztaly_fonok'
                                    },
                                    'exists': False,
                                    'conflicts': []
                                })
                                result['summary']['class_assignments'] += 1
                
                # Store user details
                user_detail = {
                    'index': i + 1,
                    'username': username,
                    'full_name': f"{user_data.vezetekNev} {user_data.keresztNev}",
                    'email': user_data.email,
                    'admin_type': 'teacher' if normalize_yes_no(user_data.mediatana) else 'none',
                    'special_role': 'production_leader' if normalize_yes_no(user_data.gyartasvezeto) else 'none',
                    'osztaly': f"{user_data.kezdesEve}{user_data.tagozat}" if user_data.kezdesEve and user_data.tagozat else None,
                    'stab': user_data.stab,
                    'radio_stab': parse_radio_stab_name(user_data.kezdesEve, user_data.radio) if user_data.radio and user_data.kezdesEve else None,
                    'is_osztaly_fonok': normalize_yes_no(user_data.osztalyfonok),
                    'success': len(user_errors) == 0,
                    'errors': user_errors,
                    'warnings': user_warnings
                }
                result['user_details'].append(user_detail)
                
                if user_errors:
                    result['errors'].extend(user_errors)
                    result['success'] = False
                if user_warnings:
                    result['warnings'].extend(user_warnings)
                
            except Exception as row_error:
                error_msg = f"Sor {i+1} feldolgozási hiba: {str(row_error)}"
                result['errors'].append(error_msg)
                result['success'] = False
                
                user_detail = {
                    'index': i + 1,
                    'username': extract_username_from_email(user_data.email) if user_data.email else 'ismeretlen',
                    'full_name': f"{user_data.vezetekNev} {user_data.keresztNev}" if user_data.vezetekNev and user_data.keresztNev else 'ismeretlen',
                    'email': user_data.email or 'ismeretlen',
                    'success': False,
                    'errors': [error_msg],
                    'warnings': []
                }
                result['user_details'].append(user_detail)
        
        return result
        
    except Exception as e:
        result['errors'].append(f"Validáció hiba: {str(e)}")
        result['success'] = False
        return result

# ============================================================================
# Import Logic
# ============================================================================

def process_single_user_import(user_data: UserImportSchema, dry_run: bool = False) -> dict:
    """Process import for a single user."""
    result = {
        'success': False,
        'user': None,
        'profile': None,
        'osztaly': None,
        'stab': None,
        'radio_stab': None,
        'errors': [],
        'warnings': []
    }
    
    try:
        # Generate username from email
        username = extract_username_from_email(user_data.email)
        
        # Check for duplicate username or email
        if User.objects.filter(username=username).exists():
            result['errors'].append(f"Felhasználónév már létezik: {username}")
            return result
        
        if User.objects.filter(email=user_data.email).exists():
            result['errors'].append(f"Email cím már létezik: {user_data.email}")
            return result
        
        # Determine admin type and special role
        admin_type = 'teacher' if normalize_yes_no(user_data.mediatana) else 'none'
        special_role = 'production_leader' if normalize_yes_no(user_data.gyartasvezeto) else 'none'
        
        # Get current school year
        current_tanev = get_current_tanev()
        
        # Handle class creation if student
        osztaly = None
        if user_data.kezdesEve and user_data.tagozat:
            start_year = int(user_data.kezdesEve)
            section = user_data.tagozat.upper()
            osztaly = get_or_create_class(start_year, section, current_tanev)
            result['osztaly'] = osztaly
        
        # Handle stab creation
        stab = None
        if user_data.stab:
            stab = get_or_create_stab(user_data.stab)
            result['stab'] = stab
        
        # Handle radio stab creation
        radio_stab = None
        if user_data.radio and user_data.kezdesEve:
            radio_name = parse_radio_stab_name(user_data.kezdesEve, user_data.radio)
            if radio_name:
                radio_stab = get_or_create_radio_stab(radio_name, user_data.radio)
                result['radio_stab'] = radio_stab
        
        if not dry_run:
            # Create user
            user = User.objects.create_user(
                username=username,
                email=user_data.email,
                first_name=user_data.keresztNev,
                last_name=user_data.vezetekNev,
                is_active=True
            )
            
            # Create profile
            profile = Profile.objects.create(
                user=user,
                admin_type=admin_type,
                special_role=special_role,
                telefonszam=user_data.telefonszam,
                osztaly=osztaly,
                stab=stab,
                radio_stab=radio_stab,
                medias=True  # Default to true for media students
            )
            
            # Handle class teacher assignment
            if normalize_yes_no(user_data.osztalyfonok):
                # Parse and assign to classes mentioned in osztalyai
                if user_data.osztalyai:
                    for class_name in user_data.osztalyai.split(','):
                        class_name = class_name.strip()
                        start_year, section = parse_class_name(class_name)
                        if start_year and section:
                            target_osztaly = get_or_create_class(start_year, section, current_tanev)
                            if target_osztaly:
                                target_osztaly.add_osztaly_fonok(user)
                                result['warnings'].append(f"Felhasználó osztályfőnökként hozzáadva: {class_name}")
                
                # Also assign to their own class if they're a student
                if osztaly:
                    osztaly.add_osztaly_fonok(user)
            
            result['user'] = user
            result['profile'] = profile
        
        result['success'] = True
        return result
        
    except Exception as e:
        result['errors'].append(f"Hiba a felhasználó létrehozásakor: {str(e)}")
        return result

def process_bulk_user_import(users_data: List[UserImportSchema], dry_run: bool = False, send_emails: bool = True) -> dict:
    """Process bulk user import."""
    results = {
        'success': True,
        'total_users': len(users_data),
        'created_users': 0,
        'created_classes': 0,
        'created_stabs': 0,
        'created_radio_stabs': 0,
        'errors': [],
        'warnings': [],
        'user_details': []
    }
    
    # Track created objects to avoid duplicates
    created_stabs = set()
    created_radio_stabs = set()
    created_classes = set()
    
    with transaction.atomic() if not dry_run else transaction.atomic():
        for i, user_data in enumerate(users_data):
            try:
                user_result = process_single_user_import(user_data, dry_run)
                
                if user_result['success']:
                    results['created_users'] += 1
                    
                    # Track created objects
                    if user_result['stab'] and user_result['stab'].name not in created_stabs:
                        created_stabs.add(user_result['stab'].name)
                        results['created_stabs'] += 1
                    
                    if user_result['radio_stab'] and user_result['radio_stab'].name not in created_radio_stabs:
                        created_radio_stabs.add(user_result['radio_stab'].name)
                        results['created_radio_stabs'] += 1
                    
                    if user_result['osztaly']:
                        class_key = f"{user_result['osztaly'].startYear}{user_result['osztaly'].szekcio}"
                        if class_key not in created_classes:
                            created_classes.add(class_key)
                            results['created_classes'] += 1
                    
                    # Store user details
                    user_detail = {
                        'index': i + 1,
                        'username': extract_username_from_email(user_data.email),
                        'full_name': f"{user_data.vezetekNev} {user_data.keresztNev}",
                        'email': user_data.email,
                        'admin_type': 'teacher' if normalize_yes_no(user_data.mediatana) else 'none',
                        'special_role': 'production_leader' if normalize_yes_no(user_data.gyartasvezeto) else 'none',
                        'osztaly': str(user_result['osztaly']) if user_result['osztaly'] else None,
                        'stab': user_result['stab'].name if user_result['stab'] else None,
                        'radio_stab': user_result['radio_stab'].name if user_result['radio_stab'] else None,
                        'success': True
                    }
                    results['user_details'].append(user_detail)
                    
                    # Add any warnings
                    results['warnings'].extend(user_result['warnings'])
                    
                    # Send first-login email if requested and not dry run
                    if send_emails and not dry_run and user_result['user']:
                        try:
                            from .authentication import generate_first_login_token, send_first_login_email
                            token = generate_first_login_token(user_result['user'].id)
                            user_result['profile'].first_login_token = token
                            user_result['profile'].first_login_sent_at = timezone.now()
                            user_result['profile'].save()
                            
                            email_sent = send_first_login_email(user_result['user'], token)
                            if email_sent:
                                results['warnings'].append(f"Első bejelentkezési email elküldve: {user_data.email}")
                            else:
                                results['warnings'].append(f"Email küldés sikertelen: {user_data.email}")
                        except Exception as email_error:
                            results['warnings'].append(f"Email küldési hiba {user_data.email}: {str(email_error)}")
                    
                else:
                    # Add failed user details
                    user_detail = {
                        'index': i + 1,
                        'username': extract_username_from_email(user_data.email),
                        'full_name': f"{user_data.vezetekNev} {user_data.keresztNev}",
                        'email': user_data.email,
                        'success': False,
                        'errors': user_result['errors']
                    }
                    results['user_details'].append(user_detail)
                    results['errors'].extend(user_result['errors'])
                    results['success'] = False
                
            except Exception as e:
                error_msg = f"Sor {i+1} feldolgozási hiba: {str(e)}"
                results['errors'].append(error_msg)
                results['success'] = False
                
                # Add failed user details
                user_detail = {
                    'index': i + 1,
                    'username': extract_username_from_email(user_data.email) if user_data.email else 'ismeretlen',
                    'full_name': f"{user_data.vezetekNev} {user_data.keresztNev}" if user_data.vezetekNev and user_data.keresztNev else 'ismeretlen',
                    'email': user_data.email or 'ismeretlen',
                    'success': False,
                    'errors': [error_msg]
                }
                results['user_details'].append(user_detail)
        
        # If dry run mode, rollback transaction
        if dry_run:
            transaction.set_rollback(True)
    
    return results

# ============================================================================
# API Endpoints
# ============================================================================

def register_user_import_endpoints(api):
    """Register all user import endpoints with the API router."""
    
    @api.post("/import-csv-preview", auth=JWTAuth(), response={200: CsvPreviewSchema, 400: ErrorSchema, 401: ErrorSchema})
    def import_csv_preview(request, file: UploadedFile = File(...)):
        """
        Upload and preview CSV file content for user import.
        
        Parses a CSV file and returns the structured data for frontend validation
        without creating any users or models. This allows the frontend to display
        what would be imported and validate the data before actual import.
        
        Expected CSV columns:
        - vezetekNev, keresztNev, email (required)
        - telefonszam, stab, kezdesEve, tagozat, radio (optional)
        - gyartasvezeto, mediatana, osztalyfonok, osztalyai (optional)
        
        Supports multiple delimiters: comma, semicolon, tab
        Supports UTF-8 encoding with BOM
        
        Args:
            file: CSV (.csv) file to parse
            
        Returns:
            200: Parsed data with detailed model preview
            400: Invalid file or parsing error
            401: Authentication or permission failed
        """
        try:
            # Check permissions
            has_permission, error_message = check_system_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            # Validate file type
            if not file.name.lower().endswith('.csv'):
                return 400, {"message": "Csak CSV (.csv) fájlok támogatottak"}
            
            # Read file content
            file_content = file.read()
            if not file_content:
                return 400, {"message": "Üres fájl"}
            
            # Parse CSV file
            parse_result = parse_csv_file(file_content)
            
            # Convert UserImportData objects to UserImportSchema for API response
            if parse_result['success']:
                parse_result['parsed_users'] = [
                    UserImportSchema.from_import_data(user_data) 
                    for user_data in parse_result['parsed_users']
                ]
            
            # Return parsed data with detailed model preview
            return 200, parse_result
            
        except Exception as e:
            return 400, {"message": f"Fájl feldolgozási hiba: {str(e)}"}
    
    @api.post("/import-validated-data", auth=JWTAuth(), response={200: ImportResultSchema, 400: ErrorSchema, 401: ErrorSchema})
    def import_validated_data(request, data: BulkUserImportSchema):
        """
        Import validated user data and create models.
        
        This endpoint accepts the validated data from the frontend (usually after
        the user has reviewed the preview from import-csv-preview) and actually
        creates the users, profiles, classes, stabs, and radio stabs.
        
        The import process handles dependencies correctly:
        1. Creates classes first
        2. Creates users and profiles
        3. Assigns class teachers (ofő) to existing classes
        4. Returns details of actually created models
        
        Args:
            data: Validated user import data
            
        Returns:
            200: Import completed with created model details
            400: Invalid data or creation error
            401: Authentication or permission failed
        """
        try:
            # Check permissions
            has_permission, error_message = check_system_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            # Convert schemas to UserImportData objects
            users_import_data = [user.to_import_data() for user in data.users]
            
            # Process import with model creation
            results = process_bulk_user_import(
                users_import_data, 
                dry_run=False, 
                send_emails=data.send_emails
            )
            
            return 200, results
            
        except Exception as e:
            return 400, {"message": f"Import hiba: {str(e)}"}
    
    @api.post("/import-users", auth=JWTAuth(), response={200: ImportResultSchema, 400: ErrorSchema, 401: ErrorSchema})
    def import_users(request, data: BulkUserImportSchema):
        """
        Import users from structured data.
        
        Creates users, profiles, classes, stabs, and radio stabs based on import data.
        Supports dry-run mode for validation.
        
        Args:
            data: Bulk import data with list of users
            
        Returns:
            200: Import completed (check success field for actual result)
            400: Invalid data
            401: Authentication or permission failed
        """
        try:
            # Check permissions
            has_permission, error_message = check_system_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            # Convert schemas to UserImportData objects
            users_import_data = [user.to_import_data() for user in data.users]
            
            # Process import
            results = process_bulk_user_import(
                users_import_data, 
                dry_run=data.dry_run, 
                send_emails=data.send_emails
            )
            
            return 200, results
            
        except Exception as e:
            return 400, {"message": f"Import hiba: {str(e)}"}
    
    @api.post("/validate-import", auth=JWTAuth(), response={200: ValidationResultSchema, 400: ErrorSchema, 401: ErrorSchema})
    def validate_import(request, data: BulkUserImportSchema):
        """
        Validate import data and return detailed information about all models that would be created.
        
        This endpoint performs comprehensive validation and returns detailed information about:
        - All users that would be created
        - All profiles that would be created  
        - All classes that would be created
        - All stabs that would be created
        - All radio stabs that would be created
        - Any class teacher assignments
        - Conflicts and validation errors
        
        Args:
            data: Import data to validate
            
        Returns:
            200: Detailed validation results with model preview
            400: Invalid data
            401: Authentication or permission failed
        """
        try:
            # Check permissions
            has_permission, error_message = check_system_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            # Process detailed validation
            validation_results = process_detailed_validation(data.users)
            
            return 200, validation_results
            
        except Exception as e:
            return 400, {"message": f"Validáció hiba: {str(e)}"}
    
    @api.get("/import-template", auth=JWTAuth(), response={200: dict, 400: ErrorSchema, 401: ErrorSchema})
    def get_import_template(request):
        """
        Get template structure for user import.
        
        Returns example data structure for import.
        """
        try:
            # Check permissions
            has_permission, error_message = check_system_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            template = {
                "description": "FTV felhasználó import sablon",
                "required_fields": [
                    "vezetekNev", "keresztNev", "email"
                ],
                "optional_fields": [
                    "telefonszam", "stab", "kezdesEve", "tagozat", "radio", 
                    "gyartasvezeto", "mediatana", "osztalyfonok", "osztalyai"
                ],
                "supported_column_names": {
                    "vezetekNev": ["vezetekNev", "Vezetéknév", "last_name"],
                    "keresztNev": ["keresztNev", "Keresztnév", "first_name"],
                    "email": ["email", "E-mail cím", "Email", "e_mail"],
                    "telefonszam": ["telefonszam", "Telefonszám", "phone", "telefon"],
                    "stab": ["stab", "Stáb"],
                    "kezdesEve": ["kezdesEve", "Kezdés éve", "starting_year"],
                    "tagozat": ["tagozat", "Tagozat", "department"],
                    "radio": ["radio", "Rádió", "radio_stab"],
                    "gyartasvezeto": ["gyartasvezeto", "Gyártásvezető?", "production_manager"],
                    "mediatana": ["mediatana", "Médiatanár", "media_teacher"],
                    "osztalyfonok": ["osztalyfonok", "Osztályfőnök", "class_teacher"],
                    "osztalyai": ["osztalyai", "Osztályai", "classes"]
                },
                "field_descriptions": {
                    "vezetekNev": "Vezetéknév (kötelező)",
                    "keresztNev": "Keresztnév (kötelező)", 
                    "telefonszam": "Telefonszám (+36301234567 formátum)",
                    "email": "Email cím (kötelező, ebből generálódik a felhasználónév)",
                    "stab": "Stáb neve (pl. 'A stáb', 'B stáb')",
                    "kezdesEve": "Tanulmányok kezdésének éve (pl. '2025')",
                    "tagozat": "Tagozat (pl. 'F', 'A', 'B')",
                    "radio": "Rádiós csapat kód (pl. 'A1', 'B3')",
                    "gyartasvezeto": "'Igen' ha gyártásvezető jogot kap",
                    "mediatana": "'Igen' ha médiatanár jogot kap",
                    "osztalyfonok": "'Igen' ha osztályfőnök jogot kap",
                    "osztalyai": "Osztályok amiket vezet (pl. '2023F,2024F')"
                },
                "example_csv_hungarian": "Vezetéknév,Keresztnév,Telefonszám,E-mail cím,Stáb,Kezdés éve,Tagozat,Rádió,Gyártásvezető?,Médiatanár,Osztályfőnök,Osztályai\nNagy,Imre,+36301234567,nagy.imre.25f@szlgbp.hu,B stáb,2025,F,,,,,\nKis,Péter,+36301234568,kis.peter.25f@szlgbp.hu,A stáb,2025,F,,,,,\nHorváth,Bence,+36301234575,horvath.bence@szlgbp.hu,,,,,Igen,Igen,2025F",
                "example_data": [
                    {
                        "vezetekNev": "Nagy",
                        "keresztNev": "Imre",
                        "telefonszam": "+36301234567",
                        "email": "nagy.imre.25f@szlgbp.hu",
                        "stab": "B stáb",
                        "kezdesEve": "2025",
                        "tagozat": "F",
                        "radio": "",
                        "gyartasvezeto": "",
                        "mediatana": "",
                        "osztalyfonok": "",
                        "osztalyai": ""
                    },
                    {
                        "vezetekNev": "Szabó",
                        "keresztNév": "Attila",
                        "telefonszam": "+36301234567",
                        "email": "szabo.attila.22f@szlgbp.hu",
                        "stab": "A stáb",
                        "kezdesEve": "2022",
                        "tagozat": "F",
                        "radio": "A1",
                        "gyartasvezeto": "",
                        "mediatana": "",
                        "osztalyfonok": "",
                        "osztalyai": ""
                    },
                    {
                        "vezetekNev": "Horváth",
                        "keresztNev": "Bence",
                        "telefonszam": "+36301234567",
                        "email": "horvath.bence@szlgbp.hu",
                        "stab": "",
                        "kezdesEve": "",
                        "tagozat": "",
                        "radio": "",
                        "gyartasvezeto": "Igen",
                        "mediatana": "Igen",
                        "osztalyfonok": "Igen",
                        "osztalyai": "2022F"
                    }
                ]
            }
            
            return 200, template
            
        except Exception as e:
            return 400, {"message": f"Sablon lekérési hiba: {str(e)}"}
    
    @api.post("/import-sample-data", auth=JWTAuth(), response={200: ImportResultSchema, 400: ErrorSchema, 401: ErrorSchema})
    def import_sample_data(request, dry_run: bool = False, send_emails: bool = False):
        """
        Import the sample data from the attachment.
        
        Imports all users from the provided sample data with their profiles, 
        classes, stabs, and radio stabs.
        
        Args:
            dry_run: If true, validate only without creating users
            send_emails: If true, send first-login emails to created users
            
        Returns:
            200: Import completed (check success field for actual result)
            400: Invalid data
            401: Authentication or permission failed
        """
        try:
            # Check permissions
            has_permission, error_message = check_system_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            # Sample data from the attachment
            sample_data = [
                {
                    "vezetekNev": "Nagy",
                    "keresztNev": "Imre",
                    "telefonszam": "+36301234567",
                    "email": "nagy.imre.25f@szlgbp.hu",
                    "stab": "B stáb",
                    "kezdesEve": "2025",
                    "tagozat": "F",
                    "radio": "",
                    "gyartasvezeto": "",
                    "mediatana": "",
                    "osztalyfonok": "",
                    "osztalyai": ""
                },
                {
                    "vezetekNev": "Kis",
                    "keresztNev": "Imre",
                    "telefonszam": "+36301234567",
                    "email": "kis.imre.25f@szlgbp.hu",
                    "stab": "A stáb",
                    "kezdesEve": "2025",
                    "tagozat": "F",
                    "radio": "",
                    "gyartasvezeto": "",
                    "mediatana": "",
                    "osztalyfonok": "",
                    "osztalyai": ""
                },
                {
                    "vezetekNev": "Varga",
                    "keresztNev": "Ivó",
                    "telefonszam": "+36301234567",
                    "email": "varga.ivo.24f@szlgbp.hu",
                    "stab": "B stáb",
                    "kezdesEve": "2024",
                    "tagozat": "F",
                    "radio": "",
                    "gyartasvezeto": "",
                    "mediatana": "",
                    "osztalyfonok": "",
                    "osztalyai": ""
                },
                {
                    "vezetekNev": "Halmi",
                    "keresztNev": "Emese",
                    "telefonszam": "+36301234567",
                    "email": "halmi.emese.24f@szlgbp.hu",
                    "stab": "A stáb",
                    "kezdesEve": "2024",
                    "tagozat": "F",
                    "radio": "",
                    "gyartasvezeto": "",
                    "mediatana": "",
                    "osztalyfonok": "",
                    "osztalyai": ""
                },
                {
                    "vezetekNev": "Minta",
                    "keresztNev": "Katalin",
                    "telefonszam": "+36301234567",
                    "email": "minta.katalin.23f@szlgbp.hu",
                    "stab": "B stáb",
                    "kezdesEve": "2023",
                    "tagozat": "F",
                    "radio": "",
                    "gyartasvezeto": "Igen",
                    "mediatana": "",
                    "osztalyfonok": "",
                    "osztalyai": ""
                },
                {
                    "vezetekNev": "Riport",
                    "keresztNev": "Erik",
                    "telefonszam": "+36301234567",
                    "email": "riport.erik.23f@szlgbp.hu",
                    "stab": "A stáb",
                    "kezdesEve": "2023",
                    "tagozat": "F",
                    "radio": "",
                    "gyartasvezeto": "Igen",
                    "mediatana": "",
                    "osztalyfonok": "",
                    "osztalyai": ""
                },
                {
                    "vezetekNev": "Minta",
                    "keresztNev": "László",
                    "telefonszam": "+36301234567",
                    "email": "minta.laszlo.23f@szlgbp.hu",
                    "stab": "A stáb",
                    "kezdesEve": "2023",
                    "tagozat": "F",
                    "radio": "",
                    "gyartasvezeto": "",
                    "mediatana": "",
                    "osztalyfonok": "",
                    "osztalyai": ""
                },
                {
                    "vezetekNev": "Kovács",
                    "keresztNev": "Anna",
                    "telefonszam": "+36301234567",
                    "email": "kovacs.anna.23f@szlgbp.hu",
                    "stab": "A stáb",
                    "kezdesEve": "2023",
                    "tagozat": "F",
                    "radio": "",
                    "gyartasvezeto": "",
                    "mediatana": "",
                    "osztalyfonok": "",
                    "osztalyai": ""
                },
                {
                    "vezetekNev": "Mártír",
                    "keresztNev": "Jenő",
                    "telefonszam": "+36301234567",
                    "email": "martir.jeno.22f@szlgbp.hu",
                    "stab": "B stáb",
                    "kezdesEve": "2022",
                    "tagozat": "F",
                    "radio": "B3",
                    "gyartasvezeto": "",
                    "mediatana": "",
                    "osztalyfonok": "",
                    "osztalyai": ""
                },
                {
                    "vezetekNev": "Szakáll",
                    "keresztNev": "Enikő",
                    "telefonszam": "+36301234567",
                    "email": "szakall.eniko.22f@szlgbp.hu",
                    "stab": "B stáb",
                    "kezdesEve": "2022",
                    "tagozat": "F",
                    "radio": "B4",
                    "gyartasvezeto": "",
                    "mediatana": "",
                    "osztalyfonok": "",
                    "osztalyai": ""
                },
                {
                    "vezetekNev": "Szabó",
                    "keresztNev": "Attila",
                    "telefonszam": "+36301234567",
                    "email": "szabo.attila.22f@szlgbp.hu",
                    "stab": "A stáb",
                    "kezdesEve": "2022",
                    "tagozat": "F",
                    "radio": "A1",
                    "gyartasvezeto": "",
                    "mediatana": "",
                    "osztalyfonok": "",
                    "osztalyai": ""
                },
                {
                    "vezetekNev": "Kis",
                    "keresztNev": "Gergő",
                    "telefonszam": "+36301234567",
                    "email": "kis.gergo.21f@szlgbp.hu",
                    "stab": "A stáb",
                    "kezdesEve": "2021",
                    "tagozat": "F",
                    "radio": "",
                    "gyartasvezeto": "",
                    "mediatana": "",
                    "osztalyfonok": "",
                    "osztalyai": ""
                },
                {
                    "vezetekNev": "Nagy",
                    "keresztNev": "Ernő",
                    "telefonszam": "+36301234567",
                    "email": "nagy.erno.21f@szlgbp.hu",
                    "stab": "B stáb",
                    "kezdesEve": "2021",
                    "tagozat": "F",
                    "radio": "",
                    "gyartasvezeto": "Igen",
                    "mediatana": "",
                    "osztalyfonok": "",
                    "osztalyai": ""
                },
                {
                    "vezetekNev": "Csanádi",
                    "keresztNev": "Ágnes",
                    "telefonszam": "",
                    "email": "csanadi.agnes@szlgbp.hu",
                    "stab": "",
                    "kezdesEve": "",
                    "tagozat": "",
                    "radio": "",
                    "gyartasvezeto": "",
                    "mediatana": "Igen",
                    "osztalyfonok": "",
                    "osztalyai": "2023F"
                },
                {
                    "vezetekNev": "Horváth",
                    "keresztNev": "Bence",
                    "telefonszam": "+36301234567",
                    "email": "horvath.bence@szlgbp.hu",
                    "stab": "",
                    "kezdesEve": "",
                    "tagozat": "",
                    "radio": "",
                    "gyartasvezeto": "",
                    "mediatana": "Igen",
                    "osztalyfonok": "Igen",
                    "osztalyai": "2022F"
                },
                {
                    "vezetekNev": "Tóth",
                    "keresztNev": "Dóra",
                    "telefonszam": "",
                    "email": "toth.dora@szlgbp.hu",
                    "stab": "",
                    "kezdesEve": "",
                    "tagozat": "",
                    "radio": "",
                    "gyartasvezeto": "",
                    "mediatana": "Igen",
                    "osztalyfonok": "",
                    "osztalyai": "2022F"
                },
                {
                    "vezetekNev": "Sibak",
                    "keresztNev": "Zsuzsanna",
                    "telefonszam": "+36301234567",
                    "email": "sibak.zsuzsanna@szlgbp.hu",
                    "stab": "",
                    "kezdesEve": "",
                    "tagozat": "",
                    "radio": "",
                    "gyartasvezeto": "",
                    "mediatana": "Igen",
                    "osztalyfonok": "",
                    "osztalyai": ""
                }
            ]
            
            # Convert to UserImportSchema objects
            users_to_import = [UserImportSchema(**user_data) for user_data in sample_data]
            
            # Process import
            results = process_bulk_user_import(
                users_to_import, 
                dry_run=dry_run, 
                send_emails=send_emails
            )
            
            return 200, results
            
        except Exception as e:
            return 400, {"message": f"Sample import hiba: {str(e)}"}
    
    # ============================================================================
    # Admin Status and Overview Endpoints
    # ============================================================================
    
    @api.get("/admin/system-overview", auth=JWTAuth(), response={200: SystemOverviewSchema, 401: ErrorSchema, 403: ErrorSchema})
    def get_system_overview_endpoint(request):
        """
        Get comprehensive system overview statistics.
        
        Provides high-level statistics about users, classes, stabs, and radio stabs.
        Only accessible to system administrators.
        
        Returns:
            200: System overview data
            401: Authentication failed
            403: Insufficient permissions
        """
        try:
            # Check for system admin permissions
            has_permission, error_message = check_system_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            # Get overview data
            overview_data = get_system_statistics()
            
            return 200, overview_data
            
        except Exception as e:
            return 403, {"message": f"Rendszer áttekintés hiba: {str(e)}"}
    
    @api.get("/admin/users-status", auth=JWTAuth(), response={200: List[UserStatusSchema], 401: ErrorSchema, 403: ErrorSchema})
    def get_users_status_endpoint(request):
        """
        Get detailed status for all users.
        
        Provides comprehensive information about all users including their roles,
        class assignments, stab memberships, and activity status.
        Only accessible to system administrators.
        
        Returns:
            200: List of user status details
            401: Authentication failed
            403: Insufficient permissions
        """
        try:
            # Check for system admin permissions
            has_permission, error_message = check_system_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            # Get detailed user status
            users_status = get_detailed_user_status()
            
            return 200, users_status
            
        except Exception as e:
            return 403, {"message": f"Felhasználói státusz lekérés hiba: {str(e)}"}
    
    @api.get("/admin/classes-status", auth=JWTAuth(), response={200: List[ClassStatusSchema], 401: ErrorSchema, 403: ErrorSchema})
    def get_classes_status_endpoint(request):
        """
        Get detailed status for all classes.
        
        Provides comprehensive information about all classes including student counts,
        assigned teachers, class teachers, and school year assignments.
        Only accessible to system administrators.
        
        Returns:
            200: List of class status details
            401: Authentication failed
            403: Insufficient permissions
        """
        try:
            # Check for system admin permissions
            has_permission, error_message = check_system_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            # Get detailed class status
            classes_status = get_detailed_class_status()
            
            return 200, classes_status
            
        except Exception as e:
            return 403, {"message": f"Osztály státusz lekérés hiba: {str(e)}"}
    
    @api.get("/admin/stabs-status", auth=JWTAuth(), response={200: List[StabStatusSchema], 401: ErrorSchema, 403: ErrorSchema})
    def get_stabs_status_endpoint(request):
        """
        Get detailed status for all stabs.
        
        Provides comprehensive information about all stabs including member counts,
        member lists, and associated radio stabs.
        Only accessible to system administrators.
        
        Returns:
            200: List of stab status details
            401: Authentication failed
            403: Insufficient permissions
        """
        try:
            # Check for system admin permissions
            has_permission, error_message = check_system_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            # Get detailed stab status
            stabs_status = get_detailed_stab_status()
            
            return 200, stabs_status
            
        except Exception as e:
            return 403, {"message": f"Stáb státusz lekérés hiba: {str(e)}"}
    
    @api.get("/admin/full-status", auth=JWTAuth(), response={200: dict, 401: ErrorSchema, 403: ErrorSchema})
    def get_full_system_status(request):
        """
        Get complete system status including overview and detailed information.
        
        Provides a comprehensive view of the entire system including:
        - System overview statistics
        - Detailed user information
        - Detailed class information  
        - Detailed stab information
        
        Only accessible to system administrators.
        
        Returns:
            200: Complete system status
            401: Authentication failed
            403: Insufficient permissions
        """
        try:
            # Check for system admin permissions
            has_permission, error_message = check_system_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            # Get all status data
            full_status = {
                'overview': get_system_overview(),
                'users': get_detailed_user_status(),
                'classes': get_detailed_class_status(),
                'stabs': get_detailed_stab_status()
            }
            
            return 200, full_status
            
        except Exception as e:
            return 403, {"message": f"Teljes rendszer státusz hiba: {str(e)}"}
