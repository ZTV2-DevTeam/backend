"""
Configuration Wizard API Module

This module provides admin-only endpoints for the initial system setup wizard.
Handles XLSX file uploads, data parsing, validation, and bulk record creation.

Requires admin permissions for all endpoints.
"""

from ninja import Schema, File, UploadedFile
from ninja.files import UploadedFile
from typing import List, Optional, Dict, Any
import pandas as pd
import json
from datetime import datetime, date
from django.db import transaction
from django.contrib.auth.models import User
from api.models import (
    Osztaly, Stab, RadioStab, Profile, Tanev, 
    Partner, PartnerTipus, ContactPerson, Config
)
from .auth import JWTAuth, ErrorSchema

# ============================================================================
# Schemas
# ============================================================================

class ConfigWizardStatusSchema(Schema):
    """Configuration wizard status response."""
    total_records: int
    successful_uploads: int
    in_progress: int
    classes_completed: bool
    stabs_completed: bool
    radio_stabs_completed: bool
    teachers_completed: bool
    students_completed: bool
    wizard_completed: bool

class ParsedDataSchema(Schema):
    """Response schema for parsed XLSX data."""
    type: str
    total_records: int
    valid_records: int
    invalid_records: int
    data: List[Dict[str, Any]]
    errors: List[str]
    warnings: List[str]

class ConfirmationRequestSchema(Schema):
    """Request schema for confirming parsed data."""
    type: str
    data: List[Dict[str, Any]]

class BulkCreateResponseSchema(Schema):
    """Response schema for bulk record creation."""
    type: str
    created_records: int
    failed_records: int
    errors: List[str]
    warnings: List[str]

class TemplateDownloadSchema(Schema):
    """Template download response schema."""
    filename: str
    download_url: str
    description: str

# ============================================================================
# Utility Functions
# ============================================================================

def check_admin_permissions(user) -> tuple[bool, str]:
    """
    Check if user has admin permissions for configuration wizard.
    Only system admins and developer admins can access wizard.
    
    Args:
        user: Django User object
        
    Returns:
        Tuple of (has_permission, error_message)
    """
    try:
        profile = Profile.objects.get(user=user)
        if not profile.has_admin_permission('any'):
            return False, "Adminisztrátor jogosultság szükséges a konfigurációs varázslóhoz"
        if not (profile.is_system_admin or profile.is_developer_admin):
            return False, "Rendszeradminisztrátori vagy fejlesztői jogosultság szükséges"
        return True, ""
    except Profile.DoesNotExist:
        return False, "Felhasználói profil nem található"

def create_default_radio_stabs():
    """Create default radio stabs if they don't exist."""
    radio_teams = [
        ('A1', 'A1 rádió csapat'),
        ('A2', 'A2 rádió csapat'),
        ('B3', 'B3 rádió csapat'),
        ('B4', 'B4 rádió csapat'),
    ]
    
    created_count = 0
    for team_code, team_name in radio_teams:
        radio_stab, created = RadioStab.objects.get_or_create(
            team_code=team_code,
            defaults={
                'name': team_name,
                'description': f'{team_name} - Másodéves (9F) diákok rádiós csapata'
            }
        )
        if created:
            created_count += 1
    
    return created_count

def get_wizard_status() -> dict:
    """Get current configuration wizard status."""
    classes_count = Osztaly.objects.count()
    stabs_count = Stab.objects.count()
    radio_stabs_count = RadioStab.objects.count()
    teachers_count = Profile.objects.filter(
        admin_type__in=['teacher', 'system_admin']
    ).count()
    students_count = Profile.objects.filter(
        admin_type='none', 
        medias=True
    ).count()
    
    total_records = classes_count + stabs_count + radio_stabs_count + teachers_count + students_count
    
    return {
        'total_records': total_records,
        'successful_uploads': total_records,
        'in_progress': 0,
        'classes_completed': classes_count > 0,
        'stabs_completed': stabs_count > 0,
        'radio_stabs_completed': radio_stabs_count >= 4,  # Need all 4 radio teams
        'teachers_completed': teachers_count > 0,
        'students_completed': students_count > 0,
        'wizard_completed': all([
            classes_count > 0,
            stabs_count > 0,
            radio_stabs_count >= 4,
            teachers_count > 0,
            students_count > 0
        ])
    }

def parse_classes_xlsx(file_content: bytes) -> dict:
    """Parse classes XLSX file."""
    try:
        df = pd.read_excel(file_content)
        
        required_columns = ['start_year', 'section']
        optional_columns = ['school_year', 'class_teachers']
        
        # Validate columns
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return {
                'type': 'classes',
                'total_records': 0,
                'valid_records': 0,
                'invalid_records': 0,
                'data': [],
                'errors': [f"Hiányzó oszlopok: {', '.join(missing_columns)}"],
                'warnings': []
            }
        
        valid_records = []
        invalid_records = 0
        errors = []
        warnings = []
        
        for index, row in df.iterrows():
            try:
                start_year = int(row['start_year'])
                section = str(row['section']).strip().upper()
                
                if not section or len(section) != 1:
                    errors.append(f"Sor {index + 2}: Érvénytelen szekció '{section}'")
                    invalid_records += 1
                    continue
                
                if start_year < 2000 or start_year > datetime.now().year + 5:
                    errors.append(f"Sor {index + 2}: Érvénytelen indulási év '{start_year}'")
                    invalid_records += 1
                    continue
                
                record = {
                    'start_year': start_year,
                    'section': section,
                    'school_year': row.get('school_year', None),
                    'class_teachers': row.get('class_teachers', None)
                }
                
                # Check if class already exists
                existing = Osztaly.objects.filter(
                    startYear=start_year,
                    szekcio=section
                ).exists()
                
                if existing:
                    warnings.append(f"Osztály {start_year}{section} már létezik")
                
                valid_records.append(record)
                
            except Exception as e:
                errors.append(f"Sor {index + 2}: {str(e)}")
                invalid_records += 1
        
        return {
            'type': 'classes',
            'total_records': len(df),
            'valid_records': len(valid_records),
            'invalid_records': invalid_records,
            'data': valid_records,
            'errors': errors,
            'warnings': warnings
        }
        
    except Exception as e:
        return {
            'type': 'classes',
            'total_records': 0,
            'valid_records': 0,
            'invalid_records': 0,
            'data': [],
            'errors': [f"Fájl feldolgozási hiba: {str(e)}"],
            'warnings': []
        }

def parse_stabs_xlsx(file_content: bytes) -> dict:
    """Parse stabs XLSX file."""
    try:
        df = pd.read_excel(file_content)
        
        required_columns = ['name']
        optional_columns = ['description', 'type']
        
        # Validate columns
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return {
                'type': 'stabs',
                'total_records': 0,
                'valid_records': 0,
                'invalid_records': 0,
                'data': [],
                'errors': [f"Hiányzó oszlopok: {', '.join(missing_columns)}"],
                'warnings': []
            }
        
        valid_records = []
        invalid_records = 0
        errors = []
        warnings = []
        
        for index, row in df.iterrows():
            try:
                name = str(row['name']).strip()
                
                if not name:
                    errors.append(f"Sor {index + 2}: Stáb név nem lehet üres")
                    invalid_records += 1
                    continue
                
                record = {
                    'name': name,
                    'description': row.get('description', ''),
                    'type': row.get('type', 'media')
                }
                
                # Check if stab already exists
                existing = Stab.objects.filter(name=name).exists()
                if existing:
                    warnings.append(f"Stáb '{name}' már létezik")
                
                valid_records.append(record)
                
            except Exception as e:
                errors.append(f"Sor {index + 2}: {str(e)}")
                invalid_records += 1
        
        return {
            'type': 'stabs',
            'total_records': len(df),
            'valid_records': len(valid_records),
            'invalid_records': invalid_records,
            'data': valid_records,
            'errors': errors,
            'warnings': warnings
        }
        
    except Exception as e:
        return {
            'type': 'stabs',
            'total_records': 0,
            'valid_records': 0,
            'invalid_records': 0,
            'data': [],
            'errors': [f"Fájl feldolgozási hiba: {str(e)}"],
            'warnings': []
        }

def parse_teachers_xlsx(file_content: bytes) -> dict:
    """Parse teachers XLSX file."""
    try:
        df = pd.read_excel(file_content)
        
        required_columns = ['username', 'first_name', 'last_name', 'email']
        optional_columns = ['phone', 'admin_type', 'assigned_classes']
        
        # Validate columns
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return {
                'type': 'teachers',
                'total_records': 0,
                'valid_records': 0,
                'invalid_records': 0,
                'data': [],
                'errors': [f"Hiányzó oszlopok: {', '.join(missing_columns)}"],
                'warnings': []
            }
        
        valid_records = []
        invalid_records = 0
        errors = []
        warnings = []
        
        for index, row in df.iterrows():
            try:
                username = str(row['username']).strip()
                first_name = str(row['first_name']).strip()
                last_name = str(row['last_name']).strip()
                email = str(row['email']).strip()
                
                if not all([username, first_name, last_name, email]):
                    errors.append(f"Sor {index + 2}: Kötelező mezők hiányoznak")
                    invalid_records += 1
                    continue
                
                if '@' not in email:
                    errors.append(f"Sor {index + 2}: Érvénytelen email cím")
                    invalid_records += 1
                    continue
                
                admin_type = str(row.get('admin_type', 'teacher')).strip().lower()
                if admin_type not in ['teacher', 'system_admin', 'developer']:
                    admin_type = 'teacher'
                
                assigned_classes = str(row.get('assigned_classes', '')).strip()
                
                record = {
                    'username': username,
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': email,
                    'phone': str(row.get('phone', '')).strip(),
                    'admin_type': admin_type,
                    'assigned_classes': assigned_classes
                }
                
                # Check if user already exists
                existing = User.objects.filter(username=username).exists()
                if existing:
                    warnings.append(f"Felhasználó '{username}' már létezik")
                
                existing_email = User.objects.filter(email=email).exists()
                if existing_email:
                    warnings.append(f"Email cím '{email}' már használatban")
                
                valid_records.append(record)
                
            except Exception as e:
                errors.append(f"Sor {index + 2}: {str(e)}")
                invalid_records += 1
        
        return {
            'type': 'teachers',
            'total_records': len(df),
            'valid_records': len(valid_records),
            'invalid_records': invalid_records,
            'data': valid_records,
            'errors': errors,
            'warnings': warnings
        }
        
    except Exception as e:
        return {
            'type': 'teachers',
            'total_records': 0,
            'valid_records': 0,
            'invalid_records': 0,
            'data': [],
            'errors': [f"Fájl feldolgozási hiba: {str(e)}"],
            'warnings': []
        }

def parse_students_xlsx(file_content: bytes) -> dict:
    """Parse students XLSX file."""
    try:
        df = pd.read_excel(file_content)
        
        required_columns = ['username', 'first_name', 'last_name', 'email', 'class_start_year', 'class_section']
        optional_columns = ['phone', 'stab', 'radio_stab']
        
        # Validate columns
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return {
                'type': 'students',
                'total_records': 0,
                'valid_records': 0,
                'invalid_records': 0,
                'data': [],
                'errors': [f"Hiányzó oszlopok: {', '.join(missing_columns)}"],
                'warnings': []
            }
        
        valid_records = []
        invalid_records = 0
        errors = []
        warnings = []
        
        for index, row in df.iterrows():
            try:
                username = str(row['username']).strip()
                first_name = str(row['first_name']).strip()
                last_name = str(row['last_name']).strip()
                email = str(row['email']).strip()
                class_start_year = int(row['class_start_year'])
                class_section = str(row['class_section']).strip().upper()
                
                if not all([username, first_name, last_name, email, class_section]):
                    errors.append(f"Sor {index + 2}: Kötelező mezők hiányoznak")
                    invalid_records += 1
                    continue
                
                if '@' not in email:
                    errors.append(f"Sor {index + 2}: Érvénytelen email cím")
                    invalid_records += 1
                    continue
                
                if len(class_section) != 1:
                    errors.append(f"Sor {index + 2}: Érvénytelen osztály szekció")
                    invalid_records += 1
                    continue
                
                record = {
                    'username': username,
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': email,
                    'phone': str(row.get('phone', '')).strip(),
                    'class_start_year': class_start_year,
                    'class_section': class_section,
                    'stab': str(row.get('stab', '')).strip(),
                    'radio_stab': str(row.get('radio_stab', '')).strip()
                }
                
                # Check if user already exists
                existing = User.objects.filter(username=username).exists()
                if existing:
                    warnings.append(f"Felhasználó '{username}' már létezik")
                
                existing_email = User.objects.filter(email=email).exists()
                if existing_email:
                    warnings.append(f"Email cím '{email}' már használatban")
                
                # Check if class exists
                class_exists = Osztaly.objects.filter(
                    startYear=class_start_year,
                    szekcio=class_section
                ).exists()
                if not class_exists:
                    warnings.append(f"Osztály {class_start_year}{class_section} nem létezik")
                
                valid_records.append(record)
                
            except Exception as e:
                errors.append(f"Sor {index + 2}: {str(e)}")
                invalid_records += 1
        
        return {
            'type': 'students',
            'total_records': len(df),
            'valid_records': len(valid_records),
            'invalid_records': invalid_records,
            'data': valid_records,
            'errors': errors,
            'warnings': warnings
        }
        
    except Exception as e:
        return {
            'type': 'students',
            'total_records': 0,
            'valid_records': 0,
            'invalid_records': 0,
            'data': [],
            'errors': [f"Fájl feldolgozási hiba: {str(e)}"],
            'warnings': []
        }

def create_classes_from_data(data: list) -> dict:
    """Create class records from parsed data."""
    created_records = 0
    failed_records = 0
    errors = []
    warnings = []
    
    try:
        with transaction.atomic():
            current_tanev = Tanev.get_active()
            
            for record in data:
                try:
                    # Check if class already exists
                    existing = Osztaly.objects.filter(
                        startYear=record['start_year'],
                        szekcio=record['section']
                    ).first()
                    
                    if existing:
                        warnings.append(f"Osztály {record['start_year']}{record['section']} már létezik")
                        continue
                    
                    # Create new class
                    osztaly = Osztaly.objects.create(
                        startYear=record['start_year'],
                        szekcio=record['section'],
                        tanev=current_tanev
                    )
                    
                    # Add to current school year if it exists
                    if current_tanev:
                        current_tanev.add_osztaly(osztaly)
                    
                    created_records += 1
                    
                except Exception as e:
                    errors.append(f"Osztály {record.get('start_year', '?')}{record.get('section', '?')}: {str(e)}")
                    failed_records += 1
                    
    except Exception as e:
        errors.append(f"Általános hiba: {str(e)}")
        
    return {
        'type': 'classes',
        'created_records': created_records,
        'failed_records': failed_records,
        'errors': errors,
        'warnings': warnings
    }

def create_stabs_from_data(data: list) -> dict:
    """Create stab records from parsed data."""
    created_records = 0
    failed_records = 0
    errors = []
    warnings = []
    
    try:
        with transaction.atomic():
            # First, create default radio stabs
            radio_stabs_created = create_default_radio_stabs()
            if radio_stabs_created > 0:
                warnings.append(f"{radio_stabs_created} alapértelmezett rádiós stáb létrehozva")
            
            for record in data:
                try:
                    # Check if stab already exists
                    existing = Stab.objects.filter(name=record['name']).first()
                    
                    if existing:
                        warnings.append(f"Stáb '{record['name']}' már létezik")
                        continue
                    
                    # Create new stab
                    Stab.objects.create(name=record['name'])
                    created_records += 1
                    
                except Exception as e:
                    errors.append(f"Stáb '{record.get('name', '?')}': {str(e)}")
                    failed_records += 1
                    
    except Exception as e:
        errors.append(f"Általános hiba: {str(e)}")
        
    return {
        'type': 'stabs',
        'created_records': created_records,
        'failed_records': failed_records,
        'errors': errors,
        'warnings': warnings
    }

def create_teachers_from_data(data: list) -> dict:
    """Create teacher records from parsed data."""
    created_records = 0
    failed_records = 0
    errors = []
    warnings = []
    
    try:
        with transaction.atomic():
            for record in data:
                try:
                    # Check if user already exists
                    existing_user = User.objects.filter(username=record['username']).first()
                    
                    if existing_user:
                        warnings.append(f"Felhasználó '{record['username']}' már létezik")
                        continue
                    
                    # Create new user
                    user = User.objects.create_user(
                        username=record['username'],
                        first_name=record['first_name'],
                        last_name=record['last_name'],
                        email=record['email'],
                        password=User.objects.make_random_password()  # Temporary password
                    )
                    
                    # Create profile (teachers cannot be production leaders - that's for students only)
                    profile = Profile.objects.create(
                        user=user,
                        telefonszam=record.get('phone', ''),
                        admin_type=record.get('admin_type', 'teacher'),
                        special_role='none',  # Teachers cannot be production leaders
                        medias=True,  # All teachers in the system are media teachers
                        password_set=False  # User needs to set password
                    )
                    
                    # Handle class assignments if specified
                    assigned_classes = record.get('assigned_classes', '')
                    if assigned_classes:
                        # Parse class assignments (format: "2024F,2023A,2022B")
                        class_assignments = [cls.strip() for cls in assigned_classes.split(',') if cls.strip()]
                        
                        for class_name in class_assignments:
                            try:
                                # Parse class name (e.g., "2024F" -> start_year=2024, section="F")
                                if len(class_name) >= 5:  # e.g., "2024F"
                                    start_year = int(class_name[:-1])
                                    section = class_name[-1].upper()
                                    
                                    osztaly = Osztaly.objects.filter(
                                        startYear=start_year,
                                        szekcio=section
                                    ).first()
                                    
                                    if osztaly:
                                        osztaly.add_osztaly_fonok(user)
                                        warnings.append(f"'{record['username']}' hozzárendelve '{class_name}' osztályfőnökként")
                                    else:
                                        warnings.append(f"Osztály '{class_name}' nem található a '{record['username']}' tanárhoz")
                                        
                            except (ValueError, IndexError):
                                warnings.append(f"Érvénytelen osztály formátum: '{class_name}' a '{record['username']}' tanárnál")
                    
                    created_records += 1
                    
                except Exception as e:
                    errors.append(f"Tanár '{record.get('username', '?')}': {str(e)}")
                    failed_records += 1
                    
    except Exception as e:
        errors.append(f"Általános hiba: {str(e)}")
        
    return {
        'type': 'teachers',
        'created_records': created_records,
        'failed_records': failed_records,
        'errors': errors,
        'warnings': warnings
    }

def create_students_from_data(data: list) -> dict:
    """Create student records from parsed data."""
    created_records = 0
    failed_records = 0
    errors = []
    warnings = []
    
    try:
        with transaction.atomic():
            for record in data:
                try:
                    # Check if user already exists
                    existing_user = User.objects.filter(username=record['username']).first()
                    
                    if existing_user:
                        warnings.append(f"Felhasználó '{record['username']}' már létezik")
                        continue
                    
                    # Create new user
                    user = User.objects.create_user(
                        username=record['username'],
                        first_name=record['first_name'],
                        last_name=record['last_name'],
                        email=record['email'],
                        password=User.objects.make_random_password()  # Temporary password
                    )
                    
                    # Get class
                    osztaly = Osztaly.objects.filter(
                        startYear=record['class_start_year'],
                        szekcio=record['class_section']
                    ).first()
                    
                    # Get stab if specified
                    stab = None
                    if record.get('stab'):
                        stab = Stab.objects.filter(name=record['stab']).first()
                    
                    # Get radio stab if specified (only for 9F students)
                    radio_stab = None
                    if record.get('radio_stab') and record['class_section'].upper() == 'F':
                        # Check for valid radio stab team codes
                        radio_stab_name = record['radio_stab']
                        if radio_stab_name in ['A1', 'A2', 'B3', 'B4']:
                            radio_stab = RadioStab.objects.filter(team_code=radio_stab_name).first()
                            if not radio_stab:
                                warnings.append(f"Rádiós stáb '{radio_stab_name}' nem található - automatikusan létrehozva lesz")
                        else:
                            warnings.append(f"Érvénytelen rádiós stáb kód: '{radio_stab_name}' (csak A1, A2, B3, B4 engedélyezett)")
                    
                    # Create profile
                    Profile.objects.create(
                        user=user,
                        telefonszam=record.get('phone', ''),
                        admin_type='none',
                        stab=stab,
                        radio_stab=radio_stab,
                        osztaly=osztaly,
                        medias=True,
                        password_set=False  # User needs to set password
                    )
                    
                    created_records += 1
                    
                except Exception as e:
                    errors.append(f"Diák '{record.get('username', '?')}': {str(e)}")
                    failed_records += 1
                    
    except Exception as e:
        errors.append(f"Általános hiba: {str(e)}")
        
    return {
        'type': 'students',
        'created_records': created_records,
        'failed_records': failed_records,
        'errors': errors,
        'warnings': warnings
    }

def generate_xlsx_template(template_type: str) -> dict:
    """Generate XLSX template for specific data type."""
    templates = {
        'classes': {
            'filename': 'classes_template.xlsx',
            'columns': ['start_year', 'section', 'school_year', 'class_teachers'],
            'sample_data': [
                [2024, 'F', '2024/2025', 'Nagy János'],
                [2023, 'A', '2024/2025', 'Kis Petra'],
                [2022, 'B', '2024/2025', 'Szabó Mihály']
            ],
            'description': 'Osztályok feltöltése - indulási év és szekció kötelező'
        },
        'stabs': {
            'filename': 'stabs_template.xlsx',
            'columns': ['name', 'description', 'type'],
            'sample_data': [
                ['A stáb', 'Első műszak média stáb', 'media'],
                ['B stáb', 'Második műszak média stáb', 'media'],
                ['Karbantartó stáb', 'Eszközök karbantartása', 'maintenance']
            ],
            'description': 'Média stábok konfigurálása - név kötelező'
        },
        'teachers': {
            'filename': 'teachers_template.xlsx',
            'columns': ['username', 'first_name', 'last_name', 'email', 'phone', 'admin_type', 'assigned_classes'],
            'sample_data': [
                ['nagy.janos', 'János', 'Nagy', 'nagy.janos@iskola.hu', '+36301234567', 'teacher', '2024F,2023A'],
                ['kis.petra', 'Petra', 'Kis', 'kis.petra@iskola.hu', '+36309876543', 'teacher', '2023F'],
                ['szabo.mihaly', 'Mihály', 'Szabó', 'szabo.mihaly@iskola.hu', '', 'system_admin', ''],
                ['toth.anna', 'Anna', 'Tóth', 'toth.anna@iskola.hu', '+36305551234', 'teacher', '2022F,2022A']
            ],
            'description': 'Médiatanárok feltöltése - felhasználónév, név és email kötelező. Osztályok: 2024F,2023A formátumban. Tanárok nem lehetnek gyártásvezetők.'
        },
        'students': {
            'filename': 'students_template.xlsx',
            'columns': ['username', 'first_name', 'last_name', 'email', 'phone', 'class_start_year', 'class_section', 'stab', 'radio_stab'],
            'sample_data': [
                ['toth.anna', 'Anna', 'Tóth', 'toth.anna@student.hu', '', 2024, 'F', 'A stáb', 'A1'],
                ['varga.bela', 'Béla', 'Varga', 'varga.bela@student.hu', '+36305551234', 2023, 'A', 'B stáb', ''],
                ['horvath.cili', 'Cili', 'Horváth', 'horvath.cili@student.hu', '', 2024, 'F', '', 'B3']
            ],
            'description': 'Diákok adatai és osztályok hozzárendelése - felhasználónév, név, email és osztály kötelező. Rádiós stáb: A1, A2, B3, B4'
        }
    }
    
    return templates.get(template_type, {})

# ============================================================================
# API Endpoints
# ============================================================================

def register_configuration_wizard_endpoints(api):
    """Register all configuration wizard endpoints with the API router."""
    
    @api.get("/config-wizard/status", auth=JWTAuth(), response={200: ConfigWizardStatusSchema, 401: ErrorSchema})
    def get_wizard_status_endpoint(request):
        """
        Get configuration wizard status.
        
        Shows current completion status of each required setup step.
        
        Returns:
            200: Wizard status information
            401: Authentication or permission failed
        """
        try:
            # Check admin permissions
            has_permission, error_message = check_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            status = get_wizard_status()
            return 200, status
            
        except Exception as e:
            return 401, {"message": f"Hiba a varázsló státusz lekérdezésekor: {str(e)}"}

    @api.post("/config-wizard/parse-xlsx", auth=JWTAuth(), response={200: ParsedDataSchema, 400: ErrorSchema, 401: ErrorSchema})
    def parse_xlsx_file(request, file: UploadedFile = File(...), data_type: str = None):
        """
        Parse uploaded XLSX file and return parsed data for confirmation.
        
        Args:
            file: XLSX file to parse
            data_type: Type of data (classes, stabs, teachers, students)
            
        Returns:
            200: Parsed data for confirmation
            400: File parsing error
            401: Authentication or permission failed
        """
        try:
            # Check admin permissions
            has_permission, error_message = check_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            if not data_type:
                return 400, {"message": "Adattípus megadása kötelező"}
            
            if data_type not in ['classes', 'stabs', 'teachers', 'students']:
                return 400, {"message": "Érvénytelen adattípus"}
            
            # Read file content
            file_content = file.read()
            
            # Parse based on data type
            if data_type == 'classes':
                result = parse_classes_xlsx(file_content)
            elif data_type == 'stabs':
                result = parse_stabs_xlsx(file_content)
            elif data_type == 'teachers':
                result = parse_teachers_xlsx(file_content)
            elif data_type == 'students':
                result = parse_students_xlsx(file_content)
            else:
                return 400, {"message": "Nem támogatott adattípus"}
            
            return 200, result
            
        except Exception as e:
            return 400, {"message": f"Fájl feldolgozási hiba: {str(e)}"}

    @api.post("/config-wizard/confirm-data", auth=JWTAuth(), response={200: BulkCreateResponseSchema, 400: ErrorSchema, 401: ErrorSchema})
    def confirm_and_create_data(request, data: ConfirmationRequestSchema):
        """
        Confirm parsed data and create records in the database.
        
        Args:
            data: Confirmed data to create records from
            
        Returns:
            200: Bulk creation results
            400: Creation error
            401: Authentication or permission failed
        """
        try:
            # Check admin permissions
            has_permission, error_message = check_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            if data.type not in ['classes', 'stabs', 'teachers', 'students']:
                return 400, {"message": "Érvénytelen adattípus"}
            
            # Create records based on data type
            if data.type == 'classes':
                result = create_classes_from_data(data.data)
            elif data.type == 'stabs':
                result = create_stabs_from_data(data.data)
            elif data.type == 'teachers':
                result = create_teachers_from_data(data.data)
            elif data.type == 'students':
                result = create_students_from_data(data.data)
            else:
                return 400, {"message": "Nem támogatott adattípus"}
            
            return 200, result
            
        except Exception as e:
            return 400, {"message": f"Adatok létrehozási hiba: {str(e)}"}

    @api.get("/config-wizard/template/{template_type}", auth=JWTAuth(), response={200: TemplateDownloadSchema, 400: ErrorSchema, 401: ErrorSchema})
    def get_xlsx_template(request, template_type: str):
        """
        Get XLSX template information for download.
        
        Args:
            template_type: Type of template (classes, stabs, teachers, students)
            
        Returns:
            200: Template information
            400: Invalid template type
            401: Authentication or permission failed
        """
        try:
            # Check admin permissions
            has_permission, error_message = check_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            template_info = generate_xlsx_template(template_type)
            
            if not template_info:
                return 400, {"message": "Érvénytelen sablon típus"}
            
            return 200, {
                'filename': template_info['filename'],
                'download_url': f'/api/config-wizard/download-template/{template_type}',
                'description': template_info['description']
            }
            
        except Exception as e:
            return 400, {"message": f"Sablon információ lekérési hiba: {str(e)}"}

    @api.get("/config-wizard/download-template/{template_type}", auth=JWTAuth())
    def download_xlsx_template(request, template_type: str):
        """
        Download XLSX template file.
        
        Args:
            template_type: Type of template (classes, stabs, teachers, students)
            
        Returns:
            XLSX file for download
        """
        try:
            # Check admin permissions
            has_permission, error_message = check_admin_permissions(request.auth)
            if not has_permission:
                from django.http import HttpResponseForbidden
                return HttpResponseForbidden(error_message)
            
            template_info = generate_xlsx_template(template_type)
            
            if not template_info:
                from django.http import HttpResponseBadRequest
                return HttpResponseBadRequest("Érvénytelen sablon típus")
            
            # Create DataFrame and Excel file
            df = pd.DataFrame(template_info['sample_data'], columns=template_info['columns'])
            
            from django.http import HttpResponse
            from io import BytesIO
            
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Template')
            
            output.seek(0)
            
            response = HttpResponse(
                output.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="{template_info["filename"]}"'
            
            return response
            
        except Exception as e:
            from django.http import HttpResponseServerError
            return HttpResponseServerError(f"Sablon letöltési hiba: {str(e)}")

    @api.post("/config-wizard/complete", auth=JWTAuth(), response={200: dict, 400: ErrorSchema, 401: ErrorSchema})
    def complete_configuration_wizard(request):
        """
        Complete the configuration wizard and mark system as configured.
        
        Validates that all required data has been uploaded and creates initial system configuration.
        
        Returns:
            200: Wizard completion successful
            400: Wizard cannot be completed
            401: Authentication or permission failed
        """
        try:
            # Check admin permissions
            has_permission, error_message = check_admin_permissions(request.auth)
            if not has_permission:
                return 401, {"message": error_message}
            
            # Check wizard status
            status = get_wizard_status()
            
            if not status['wizard_completed']:
                missing_steps = []
                if not status['classes_completed']:
                    missing_steps.append('Osztályok')
                if not status['stabs_completed']:
                    missing_steps.append('Stábok')
                if not status['radio_stabs_completed']:
                    missing_steps.append('Rádiós stábok')
                if not status['teachers_completed']:
                    missing_steps.append('Tanárok')
                if not status['students_completed']:
                    missing_steps.append('Tanulók')
                
                return 400, {"message": f"Hiányzó lépések: {', '.join(missing_steps)}"}
            
            # Create or update system configuration
            config, created = Config.objects.get_or_create(
                defaults={
                    'active': True,
                    'allowEmails': True
                }
            )
            
            if not created:
                config.active = True
                config.save()
            
            return 200, {
                'message': 'Konfiguráció varázsló sikeresen befejezve',
                'system_active': True,
                'total_records': status['total_records'],
                'wizard_completed': True
            }
            
        except Exception as e:
            return 400, {"message": f"Hiba a varázsló befejezésekor: {str(e)}"}

    @api.post("/config-wizard/reset", auth=JWTAuth(), response={200: dict, 401: ErrorSchema})
    def reset_configuration_wizard(request):
        """
        Reset configuration wizard (DANGER: Deletes all data).
        
        Only for developer admins. Removes all wizard-created data.
        
        Returns:
            200: Reset successful
            401: Authentication or permission failed
        """
        try:
            # Check developer admin permissions
            try:
                profile = Profile.objects.get(user=request.auth)
                if not profile.is_developer_admin:
                    return 401, {"message": "Fejlesztői adminisztrátor jogosultság szükséges"}
            except Profile.DoesNotExist:
                return 401, {"message": "Felhasználói profil nem található"}
            
            with transaction.atomic():
                # Delete all non-admin users and their profiles
                users_to_delete = User.objects.exclude(
                    profile__admin_type__in=['developer', 'system_admin']
                ).exclude(is_superuser=True)
                
                deleted_users = users_to_delete.count()
                users_to_delete.delete()
                
                # Delete all classes
                deleted_classes = Osztaly.objects.count()
                Osztaly.objects.all().delete()
                
                # Delete all stabs
                deleted_stabs = Stab.objects.count()
                Stab.objects.all().delete()
                
                # Delete all radio stabs
                deleted_radio_stabs = RadioStab.objects.count()
                RadioStab.objects.all().delete()
                
                # Deactivate system configuration
                Config.objects.update(active=False)
            
            return 200, {
                'message': 'Konfiguráció varázsló visszaállítva',
                'deleted_users': deleted_users,
                'deleted_classes': deleted_classes,
                'deleted_stabs': deleted_stabs,
                'deleted_radio_stabs': deleted_radio_stabs
            }
            
        except Exception as e:
            return 401, {"message": f"Hiba a varázsló visszaállításakor: {str(e)}"}
