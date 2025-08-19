"""
Shared utilities for user import functionality.

This module contains common functions used by both the API endpoints
and the Django management command for user import.
"""

from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from api.models import Profile, Osztaly, Stab, RadioStab, Tanev
from typing import Optional, List, Dict, Any
import re
import csv
import io


# ============================================================================
# Data Structure Classes
# ============================================================================

class UserImportData:
    """Data class for user import information."""
    def __init__(self, **kwargs):
        self.vezetekNev = kwargs.get('vezetekNev', '')
        self.keresztNev = kwargs.get('keresztNev', '')
        self.telefonszam = kwargs.get('telefonszam')
        self.email = kwargs.get('email', '')
        self.stab = kwargs.get('stab')
        self.kezdesEve = kwargs.get('kezdesEve')
        self.tagozat = kwargs.get('tagozat')
        self.radio = kwargs.get('radio')
        self.gyartasvezeto = kwargs.get('gyartasvezeto')
        self.mediatana = kwargs.get('mediatana')
        self.osztalyfonok = kwargs.get('osztalyfonok')
        self.osztalyai = kwargs.get('osztalyai')


# ============================================================================
# Utility Functions
# ============================================================================

def extract_username_from_email(email: str) -> str:
    """Extract username from email (part before @)."""
    return email.split('@')[0] if '@' in email else email


def normalize_yes_no(value: str) -> bool:
    """Normalize 'Igen'/'Nem' values to boolean."""
    if not value:
        return False
    return value.strip().lower() in ['igen', 'yes', 'true', '1']


def parse_class_name(class_string: str) -> tuple:
    """Parse class string like '2023F' into start_year and section."""
    if not class_string:
        return None, None
    
    # Extract year and section using regex
    match = re.match(r'(\d{4})([A-Z]+)', class_string.strip())
    if match:
        return int(match.group(1)), match.group(2)
    return None, None


def parse_radio_stab_name(start_year: str, radio_code: str) -> str:
    """Generate radio stab name from start year and radio code."""
    if not start_year or not radio_code:
        return None
    return f"{start_year} {radio_code}"


def get_current_tanev() -> Tanev:
    """Get or create current school year."""
    current_tanev = Tanev.get_active()
    if not current_tanev:
        # Create a default school year for current academic year
        from datetime import date
        current_year = date.today().year
        if date.today().month >= 9:  # After September, it's the new school year
            current_tanev = Tanev.create_for_year(current_year)
        else:
            current_tanev = Tanev.create_for_year(current_year - 1)
    return current_tanev


# ============================================================================
# Model Creation Functions
# ============================================================================

def get_or_create_stab(stab_name: str, dry_run: bool = False) -> tuple:
    """Get or create a stab by name. Returns (stab, created)."""
    if not stab_name:
        return None, False
    
    # Normalize stab name
    normalized_name = stab_name.strip()
    
    if dry_run:
        exists = Stab.objects.filter(name=normalized_name).exists()
        return normalized_name, not exists
    
    stab, created = Stab.objects.get_or_create(
        name=normalized_name,
        defaults={'name': normalized_name}
    )
    return stab, created


def get_or_create_radio_stab(radio_name: str, radio_code: str, dry_run: bool = False) -> tuple:
    """Get or create a radio stab by name and code. Returns (radio_stab, created)."""
    if not radio_name or not radio_code:
        return None, False
    
    if dry_run:
        exists = RadioStab.objects.filter(name=radio_name).exists()
        return radio_name, not exists
    
    # Check if radio stab exists
    radio_stab, created = RadioStab.objects.get_or_create(
        name=radio_name,
        defaults={
            'name': radio_name,
            'team_code': radio_code.upper(),
            'description': f'Automatikusan létrehozott rádiós stáb importálás során'
        }
    )
    return radio_stab, created


def get_or_create_class(start_year: int, section: str, tanev: Tanev = None, dry_run: bool = False) -> tuple:
    """Get or create a class by start year and section. Returns (osztaly, created)."""
    if not start_year or not section:
        return None, False
    
    if dry_run:
        exists = Osztaly.objects.filter(startYear=start_year, szekcio=section.upper()).exists()
        return f"{start_year}{section.upper()}", not exists
    
    # Get or create the class
    osztaly, created = Osztaly.objects.get_or_create(
        startYear=start_year,
        szekcio=section.upper(),
        defaults={
            'startYear': start_year,
            'szekcio': section.upper(),
            'tanev': tanev
        }
    )
    
    # If tanev is provided and the class didn't have one, assign it
    if tanev and not osztaly.tanev:
        osztaly.tanev = tanev
        osztaly.save()
        if tanev:
            tanev.add_osztaly(osztaly)
    
    return osztaly, created


# ============================================================================
# Excel Parsing Functions
# ============================================================================

def parse_csv_file(file_content: bytes) -> dict:
    """
    Parse CSV file content with proper UTF-8 support and return structured user data.
    
    Expected columns:
    - vezetekNev, keresztNev (required)
    - email (required)
    - telefonszam, stab, kezdesEve, tagozat, radio
    - gyartasvezeto, mediatana, osztalyfonok, osztalyai (optional)
    
    Returns:
        dict with success, parsed_users, errors, warnings, and detailed model preview
    """
    result = {
        'success': False,
        'total_rows': 0,
        'parsed_users': [],
        'errors': [],
        'warnings': [],
        'models_preview': {
            'users': [],
            'profiles': [],
            'classes': [],
            'stabs': [],
            'radio_stabs': []
        }
    }
    
    try:
        # Decode the file content with UTF-8
        text_content = file_content.decode('utf-8-sig')  # utf-8-sig handles BOM
        
        # Use CSV reader with proper dialect detection
        csv_file = io.StringIO(text_content)
        
        # Try to detect delimiter
        sample = text_content[:1024]
        delimiter = ','
        if ';' in sample and sample.count(';') > sample.count(','):
            delimiter = ';'
        elif '\t' in sample and sample.count('\t') > sample.count(','):
            delimiter = '\t'
        
        csv_file.seek(0)
        csv_reader = csv.DictReader(csv_file, delimiter=delimiter)
        
        # Get headers and check required columns
        headers = csv_reader.fieldnames
        if not headers:
            result['errors'].append("CSV fájl nem tartalmaz fejléceket")
            return result
        
        # Clean headers (remove BOM and whitespace)
        headers = [h.strip() for h in headers if h]
        
        # Define column mappings (English -> Hungarian alternatives)
        column_mappings = {
            'vezetekNev': ['vezetekNev', 'Vezetéknév', 'last_name'],
            'keresztNev': ['keresztNev', 'Keresztnév', 'first_name'], 
            'telefonszam': ['telefonszam', 'Telefonszám', 'phone', 'telefon'],
            'email': ['email', 'E-mail cím', 'Email', 'e_mail'],
            'stab': ['stab', 'Stáb'],
            'kezdesEve': ['kezdesEve', 'Kezdés éve', 'starting_year'],
            'tagozat': ['tagozat', 'Tagozat', 'department'],
            'radio': ['radio', 'Rádió', 'radio_stab'],
            'gyartasvezeto': ['gyartasvezeto', 'Gyártásvezető?', 'production_manager'],
            'mediatana': ['mediatana', 'Médiatanár', 'media_teacher'],
            'osztalyfonok': ['osztalyfonok', 'Osztályfőnök', 'class_teacher'],
            'osztalyai': ['osztalyai', 'Osztályai', 'classes']
        }
        
        # Create reverse mapping from CSV headers to internal names
        header_to_internal = {}
        for internal_name, alternatives in column_mappings.items():
            for header in headers:
                if header in alternatives:
                    header_to_internal[header] = internal_name
                    break
        
        # Check for required columns
        required_internal_columns = ['vezetekNev', 'keresztNev', 'email']
        found_required = []
        for req_col in required_internal_columns:
            found = False
            for header in headers:
                if header_to_internal.get(header) == req_col:
                    found_required.append(req_col)
                    found = True
                    break
            if not found:
                # Try to find by alternative names
                for alt_name in column_mappings[req_col]:
                    if alt_name in headers:
                        found_required.append(req_col)
                        header_to_internal[alt_name] = req_col
                        found = True
                        break
        
        missing_columns = [col for col in required_internal_columns if col not in found_required]
        if missing_columns:
            result['errors'].append(f"Hiányzó kötelező oszlopok: {', '.join(missing_columns)} (elfogadott nevek: {', '.join([', '.join(column_mappings[col]) for col in missing_columns])})")
            return result
        
        # Track models that would be created
        classes_to_create = set()
        stabs_to_create = set()
        radio_stabs_to_create = set()
        
        # Process data rows
        row_count = 0
        for row_idx, row in enumerate(csv_reader, start=2):
            try:
                # Extract values safely with UTF-8 handling using header mapping
                def get_cell_value(internal_column_name):
                    # Find the actual CSV header for this internal column name
                    for csv_header, internal_name in header_to_internal.items():
                        if internal_name == internal_column_name:
                            value = row.get(csv_header, '')
                            if value is None:
                                return ''
                            return str(value).strip()
                    
                    # Fallback: try direct column name (backward compatibility)
                    value = row.get(internal_column_name, '')
                    if value is None:
                        return ''
                    return str(value).strip()
                
                vezetekNev = get_cell_value('vezetekNev')
                keresztNev = get_cell_value('keresztNev')
                email = get_cell_value('email')
                
                # Skip empty rows
                if not any([vezetekNev, keresztNev, email]):
                    result['warnings'].append(f"Sor {row_idx} kihagyva: hiányzó kötelező adatok")
                    continue
                
                # Validate email format
                if not email or '@' not in email:
                    result['errors'].append(f"Sor {row_idx}: érvénytelen email cím '{email}'")
                    continue
                
                # Check for duplicates
                username = extract_username_from_email(email)
                if User.objects.filter(username=username).exists():
                    result['errors'].append(f"Sor {row_idx}: felhasználónév már létezik '{username}'")
                    continue
                
                if User.objects.filter(email=email).exists():
                    result['errors'].append(f"Sor {row_idx}: email cím már létezik '{email}'")
                    continue
                
                # Extract other fields
                telefonszam = get_cell_value('telefonszam') or None
                stab = get_cell_value('stab') or None
                kezdesEve = get_cell_value('kezdesEve') or None
                tagozat = get_cell_value('tagozat') or None
                radio = get_cell_value('radio') or None
                gyartasvezeto = get_cell_value('gyartasvezeto') or None
                mediatana = get_cell_value('mediatana') or None
                osztalyfonok = get_cell_value('osztalyfonok') or None
                osztalyai = get_cell_value('osztalyai') or None
                
                # Create user data object
                user_data = UserImportData(
                    vezetekNev=vezetekNev,
                    keresztNev=keresztNev,
                    telefonszam=telefonszam,
                    email=email,
                    stab=stab,
                    kezdesEve=kezdesEve,
                    tagozat=tagozat,
                    radio=radio,
                    gyartasvezeto=gyartasvezeto,
                    mediatana=mediatana,
                    osztalyfonok=osztalyfonok,
                    osztalyai=osztalyai
                )
                
                result['parsed_users'].append(user_data)
                
                # Determine what models would be created
                admin_type = 'teacher' if normalize_yes_no(mediatana) else 'none'
                special_role = 'production_leader' if normalize_yes_no(gyartasvezeto) else 'none'
                is_osztaly_fonok = normalize_yes_no(osztalyfonok)
                
                # User model preview
                user_preview = {
                    'row': row_idx,
                    'username': username,
                    'full_name': f"{vezetekNev} {keresztNev}",
                    'email': email,
                    'first_name': keresztNev,
                    'last_name': vezetekNev,
                    'is_active': True,
                    'will_be_created': True
                }
                result['models_preview']['users'].append(user_preview)
                
                # Profile model preview
                profile_preview = {
                    'row': row_idx,
                    'user_email': email,
                    'admin_type': admin_type,
                    'special_role': special_role,
                    'telefonszam': telefonszam,
                    'medias': True,
                    'osztaly_name': None,
                    'stab_name': stab,
                    'radio_stab_name': None,
                    'will_be_created': True
                }
                
                # Class handling
                if kezdesEve and tagozat:
                    try:
                        start_year = int(kezdesEve)
                        section = tagozat.upper()
                        class_name = f"{start_year}{section}"
                        
                        if class_name not in classes_to_create:
                            # Check if class already exists
                            class_exists = Osztaly.objects.filter(
                                startYear=start_year, 
                                szekcio=section
                            ).exists()
                            
                            class_preview = {
                                'name': class_name,
                                'start_year': start_year,
                                'section': section,
                                'will_be_created': not class_exists,
                                'already_exists': class_exists,
                                'students_to_add': []
                            }
                            result['models_preview']['classes'].append(class_preview)
                            classes_to_create.add(class_name)
                        
                        # Add student to class
                        for class_preview in result['models_preview']['classes']:
                            if class_preview['name'] == class_name:
                                class_preview['students_to_add'].append({
                                    'name': f"{vezetekNev} {keresztNev}",
                                    'email': email,
                                    'will_be_class_teacher': is_osztaly_fonok
                                })
                                break
                        
                        profile_preview['osztaly_name'] = class_name
                        
                    except ValueError:
                        result['warnings'].append(f"Sor {row_idx}: érvénytelen kezdés év '{kezdesEve}'")
                
                # Stab handling
                if stab:
                    if stab not in stabs_to_create:
                        stab_exists = Stab.objects.filter(name=stab).exists()
                        
                        stab_preview = {
                            'name': stab,
                            'will_be_created': not stab_exists,
                            'already_exists': stab_exists,
                            'members_to_add': []
                        }
                        result['models_preview']['stabs'].append(stab_preview)
                        stabs_to_create.add(stab)
                    
                    # Add member to stab
                    for stab_preview in result['models_preview']['stabs']:
                        if stab_preview['name'] == stab:
                            stab_preview['members_to_add'].append({
                                'name': f"{vezetekNev} {keresztNev}",
                                'email': email
                            })
                            break
                
                # Radio stab handling
                if radio and kezdesEve:
                    radio_name = f"{kezdesEve} {radio}"
                    if radio_name not in radio_stabs_to_create:
                        radio_stab_exists = RadioStab.objects.filter(name=radio_name).exists()
                        
                        radio_stab_preview = {
                            'name': radio_name,
                            'team_code': radio.upper(),
                            'will_be_created': not radio_stab_exists,
                            'already_exists': radio_stab_exists,
                            'members_to_add': []
                        }
                        result['models_preview']['radio_stabs'].append(radio_stab_preview)
                        radio_stabs_to_create.add(radio_name)
                    
                    # Add member to radio stab
                    for radio_stab_preview in result['models_preview']['radio_stabs']:
                        if radio_stab_preview['name'] == radio_name:
                            radio_stab_preview['members_to_add'].append({
                                'name': f"{vezetekNev} {keresztNev}",
                                'email': email
                            })
                            break
                    
                    profile_preview['radio_stab_name'] = radio_name
                
                # Handle class teacher assignments to other classes
                if is_osztaly_fonok and osztalyai:
                    for class_name in osztalyai.split(','):
                        class_name = class_name.strip()
                        start_year, section = parse_class_name(class_name)
                        if start_year and section:
                            full_class_name = f"{start_year}{section}"
                            
                            # Ensure the target class is in our preview
                            class_found = False
                            for class_preview in result['models_preview']['classes']:
                                if class_preview['name'] == full_class_name:
                                    # Add as class teacher
                                    class_preview['students_to_add'].append({
                                        'name': f"{vezetekNev} {keresztNev}",
                                        'email': email,
                                        'will_be_class_teacher': True,
                                        'assigned_to_manage_class': True
                                    })
                                    class_found = True
                                    break
                            
                            if not class_found:
                                # Create preview for this class too
                                class_exists = Osztaly.objects.filter(
                                    startYear=start_year, 
                                    szekcio=section
                                ).exists()
                                
                                class_preview = {
                                    'name': full_class_name,
                                    'start_year': start_year,
                                    'section': section,
                                    'will_be_created': not class_exists,
                                    'already_exists': class_exists,
                                    'students_to_add': [{
                                        'name': f"{vezetekNev} {keresztNev}",
                                        'email': email,
                                        'will_be_class_teacher': True,
                                        'assigned_to_manage_class': True
                                    }]
                                }
                                result['models_preview']['classes'].append(class_preview)
                
                result['models_preview']['profiles'].append(profile_preview)
                row_count += 1
                
            except Exception as row_error:
                result['errors'].append(f"Sor {row_idx} feldolgozási hiba: {str(row_error)}")
        
        result['total_rows'] = row_count
        
        if len(result['parsed_users']) > 0:
            result['success'] = True
            result['warnings'].append(f"Sikeresen feldolgozott sorok: {len(result['parsed_users'])}")
        else:
            result['errors'].append("Nem található feldolgozható felhasználói adat")
        
        # Add summary
        result['summary'] = {
            'users_to_create': len(result['models_preview']['users']),
            'profiles_to_create': len(result['models_preview']['profiles']),
            'classes_to_create': len([c for c in result['models_preview']['classes'] if c['will_be_created']]),
            'stabs_to_create': len([s for s in result['models_preview']['stabs'] if s['will_be_created']]),
            'radio_stabs_to_create': len([r for r in result['models_preview']['radio_stabs'] if r['will_be_created']]),
            'existing_classes': len([c for c in result['models_preview']['classes'] if c['already_exists']]),
            'existing_stabs': len([s for s in result['models_preview']['stabs'] if s['already_exists']]),
            'existing_radio_stabs': len([r for r in result['models_preview']['radio_stabs'] if r['already_exists']])
        }
        
        return result
        
    except UnicodeDecodeError:
        # Try with different encodings if UTF-8 fails
        try:
            text_content = file_content.decode('iso-8859-1')
            result['warnings'].append("Fájl ISO-8859-1 kódolással lett beolvasva")
            # Retry parsing with the new encoding
            # (same logic as above but with different encoding)
        except Exception as encoding_error:
            result['errors'].append(f"Fájl kódolási hiba: {str(encoding_error)}")
            return result
    except Exception as e:
        result['errors'].append(f"CSV fájl feldolgozási hiba: {str(e)}")
        return result
    """
    Parse Excel file content with proper UTF-8 support and return structured user data.
    
    Expected columns:
    - vezetekNev, keresztNev (required)
    - email (required)
    - telefonszam, stab, kezdesEve, tagozat, radio
    - gyartasvezeto, mediatana, osztalyfonok, osztalyai (optional)
    
    Returns:
        dict with success, parsed_users, errors, warnings, and detailed model preview
    """
    result = {
        'success': False,
        'total_rows': 0,
        'parsed_users': [],
        'errors': [],
        'warnings': [],
        'models_preview': {
            'users': [],
            'profiles': [],
            'classes': [],
            'stabs': [],
            'radio_stabs': []
        }
    }
    
    try:
        # Use openpyxl directly for better UTF-8 support
        workbook = load_workbook(io.BytesIO(file_content), read_only=True, data_only=True)
        worksheet = workbook.active
        
        # Get header row
        headers = []
        for cell in worksheet[1]:
            if cell.value:
                headers.append(str(cell.value).strip())
            else:
                headers.append('')
        
        # Check for required columns
        required_columns = ['vezetekNev', 'keresztNev', 'email']
        missing_columns = [col for col in required_columns if col not in headers]
        
        if missing_columns:
            result['errors'].append(f"Hiányzó kötelező oszlopok: {', '.join(missing_columns)}")
            return result
        
        # Create column mapping with Hungarian support
        column_map = {}
        
        # Define column mappings (English -> Hungarian alternatives)
        column_mappings = {
            'vezetekNev': ['vezetekNev', 'Vezetéknév', 'last_name'],
            'keresztNev': ['keresztNev', 'Keresztnév', 'first_name'], 
            'telefonszam': ['telefonszam', 'Telefonszám', 'phone', 'telefon'],
            'email': ['email', 'E-mail cím', 'Email', 'e_mail'],
            'stab': ['stab', 'Stáb'],
            'kezdesEve': ['kezdesEve', 'Kezdés éve', 'starting_year'],
            'tagozat': ['tagozat', 'Tagozat', 'department'],
            'radio': ['radio', 'Rádió', 'radio_stab'],
            'gyartasvezeto': ['gyartasvezeto', 'Gyártásvezető?', 'production_manager'],
            'mediatana': ['mediatana', 'Médiatanár', 'media_teacher'],
            'osztalyfonok': ['osztalyfonok', 'Osztályfőnök', 'class_teacher'],
            'osztalyai': ['osztalyai', 'Osztályai', 'classes']
        }
        
        # Map CSV headers to our internal column names
        for i, header in enumerate(headers):
            for internal_name, alternatives in column_mappings.items():
                if header in alternatives:
                    column_map[internal_name] = i
                    break
        
        # Track models that would be created
        classes_to_create = set()
        stabs_to_create = set()
        radio_stabs_to_create = set()
        
        # Process data rows
        row_count = 0
        for row_idx, row in enumerate(worksheet.iter_rows(min_row=2, values_only=True), start=2):
            try:
                # Extract values safely with UTF-8 handling
                def get_cell_value(column_name):
                    if column_name in column_map:
                        idx = column_map[column_name]
                        if idx < len(row) and row[idx] is not None:
                            return str(row[idx]).strip()
                    return ''
                
                vezetekNev = get_cell_value('vezetekNev')
                keresztNev = get_cell_value('keresztNev')
                email = get_cell_value('email')
                
                # Skip empty rows
                if not any([vezetekNev, keresztNev, email]):
                    result['warnings'].append(f"Sor {row_idx} kihagyva: hiányzó kötelező adatok")
                    continue
                
                # Validate email format
                if not email or '@' not in email:
                    result['errors'].append(f"Sor {row_idx}: érvénytelen email cím '{email}'")
                    continue
                
                # Check for duplicates
                username = extract_username_from_email(email)
                if User.objects.filter(username=username).exists():
                    result['errors'].append(f"Sor {row_idx}: felhasználónév már létezik '{username}'")
                    continue
                
                if User.objects.filter(email=email).exists():
                    result['errors'].append(f"Sor {row_idx}: email cím már létezik '{email}'")
                    continue
                
                # Extract other fields
                telefonszam = get_cell_value('telefonszam') or None
                stab = get_cell_value('stab') or None
                kezdesEve = get_cell_value('kezdesEve') or None
                tagozat = get_cell_value('tagozat') or None
                radio = get_cell_value('radio') or None
                gyartasvezeto = get_cell_value('gyartasvezeto') or None
                mediatana = get_cell_value('mediatana') or None
                osztalyfonok = get_cell_value('osztalyfonok') or None
                osztalyai = get_cell_value('osztalyai') or None
                
                # Create user data object
                user_data = UserImportData(
                    vezetekNev=vezetekNev,
                    keresztNev=keresztNev,
                    telefonszam=telefonszam,
                    email=email,
                    stab=stab,
                    kezdesEve=kezdesEve,
                    tagozat=tagozat,
                    radio=radio,
                    gyartasvezeto=gyartasvezeto,
                    mediatana=mediatana,
                    osztalyfonok=osztalyfonok,
                    osztalyai=osztalyai
                )
                
                result['parsed_users'].append(user_data)
                
                # Determine what models would be created
                admin_type = 'teacher' if normalize_yes_no(mediatana) else 'none'
                special_role = 'production_leader' if normalize_yes_no(gyartasvezeto) else 'none'
                is_osztaly_fonok = normalize_yes_no(osztalyfonok)
                
                # User model preview
                user_preview = {
                    'row': row_idx,
                    'username': username,
                    'full_name': f"{vezetekNev} {keresztNev}",
                    'email': email,
                    'first_name': keresztNev,
                    'last_name': vezetekNev,
                    'is_active': True,
                    'will_be_created': True
                }
                result['models_preview']['users'].append(user_preview)
                
                # Profile model preview
                profile_preview = {
                    'row': row_idx,
                    'user_email': email,
                    'admin_type': admin_type,
                    'special_role': special_role,
                    'telefonszam': telefonszam,
                    'medias': True,
                    'osztaly_name': None,
                    'stab_name': stab,
                    'radio_stab_name': None,
                    'will_be_created': True
                }
                
                # Class handling
                if kezdesEve and tagozat:
                    try:
                        start_year = int(kezdesEve)
                        section = tagozat.upper()
                        class_name = f"{start_year}{section}"
                        
                        if class_name not in classes_to_create:
                            # Check if class already exists
                            class_exists = Osztaly.objects.filter(
                                startYear=start_year, 
                                szekcio=section
                            ).exists()
                            
                            class_preview = {
                                'name': class_name,
                                'start_year': start_year,
                                'section': section,
                                'will_be_created': not class_exists,
                                'already_exists': class_exists,
                                'students_to_add': []
                            }
                            result['models_preview']['classes'].append(class_preview)
                            classes_to_create.add(class_name)
                        
                        # Add student to class
                        for class_preview in result['models_preview']['classes']:
                            if class_preview['name'] == class_name:
                                class_preview['students_to_add'].append({
                                    'name': f"{vezetekNev} {keresztNev}",
                                    'email': email,
                                    'will_be_class_teacher': is_osztaly_fonok
                                })
                                break
                        
                        profile_preview['osztaly_name'] = class_name
                        
                    except ValueError:
                        result['warnings'].append(f"Sor {row_idx}: érvénytelen kezdés év '{kezdesEve}'")
                
                # Stab handling
                if stab:
                    if stab not in stabs_to_create:
                        stab_exists = Stab.objects.filter(name=stab).exists()
                        
                        stab_preview = {
                            'name': stab,
                            'will_be_created': not stab_exists,
                            'already_exists': stab_exists,
                            'members_to_add': []
                        }
                        result['models_preview']['stabs'].append(stab_preview)
                        stabs_to_create.add(stab)
                    
                    # Add member to stab
                    for stab_preview in result['models_preview']['stabs']:
                        if stab_preview['name'] == stab:
                            stab_preview['members_to_add'].append({
                                'name': f"{vezetekNev} {keresztNev}",
                                'email': email
                            })
                            break
                
                # Radio stab handling
                if radio and kezdesEve:
                    radio_name = f"{kezdesEve} {radio}"
                    if radio_name not in radio_stabs_to_create:
                        radio_stab_exists = RadioStab.objects.filter(name=radio_name).exists()
                        
                        radio_stab_preview = {
                            'name': radio_name,
                            'team_code': radio.upper(),
                            'will_be_created': not radio_stab_exists,
                            'already_exists': radio_stab_exists,
                            'members_to_add': []
                        }
                        result['models_preview']['radio_stabs'].append(radio_stab_preview)
                        radio_stabs_to_create.add(radio_name)
                    
                    # Add member to radio stab
                    for radio_stab_preview in result['models_preview']['radio_stabs']:
                        if radio_stab_preview['name'] == radio_name:
                            radio_stab_preview['members_to_add'].append({
                                'name': f"{vezetekNev} {keresztNev}",
                                'email': email
                            })
                            break
                    
                    profile_preview['radio_stab_name'] = radio_name
                
                # Handle class teacher assignments to other classes
                if is_osztaly_fonok and osztalyai:
                    for class_name in osztalyai.split(','):
                        class_name = class_name.strip()
                        start_year, section = parse_class_name(class_name)
                        if start_year and section:
                            full_class_name = f"{start_year}{section}"
                            
                            # Ensure the target class is in our preview
                            class_found = False
                            for class_preview in result['models_preview']['classes']:
                                if class_preview['name'] == full_class_name:
                                    # Add as class teacher
                                    class_preview['students_to_add'].append({
                                        'name': f"{vezetekNev} {keresztNev}",
                                        'email': email,
                                        'will_be_class_teacher': True,
                                        'assigned_to_manage_class': True
                                    })
                                    class_found = True
                                    break
                            
                            if not class_found:
                                # Create preview for this class too
                                class_exists = Osztaly.objects.filter(
                                    startYear=start_year, 
                                    szekcio=section
                                ).exists()
                                
                                class_preview = {
                                    'name': full_class_name,
                                    'start_year': start_year,
                                    'section': section,
                                    'will_be_created': not class_exists,
                                    'already_exists': class_exists,
                                    'students_to_add': [{
                                        'name': f"{vezetekNev} {keresztNev}",
                                        'email': email,
                                        'will_be_class_teacher': True,
                                        'assigned_to_manage_class': True
                                    }]
                                }
                                result['models_preview']['classes'].append(class_preview)
                
                result['models_preview']['profiles'].append(profile_preview)
                row_count += 1
                
            except Exception as row_error:
                result['errors'].append(f"Sor {row_idx} feldolgozási hiba: {str(row_error)}")
        
        result['total_rows'] = row_count
        
        if len(result['parsed_users']) > 0:
            result['success'] = True
            result['warnings'].append(f"Sikeresen feldolgozott sorok: {len(result['parsed_users'])}")
        else:
            result['errors'].append("Nem található feldolgozható felhasználói adat")
        
        # Add summary
        result['summary'] = {
            'users_to_create': len(result['models_preview']['users']),
            'profiles_to_create': len(result['models_preview']['profiles']),
            'classes_to_create': len([c for c in result['models_preview']['classes'] if c['will_be_created']]),
            'stabs_to_create': len([s for s in result['models_preview']['stabs'] if s['will_be_created']]),
            'radio_stabs_to_create': len([r for r in result['models_preview']['radio_stabs'] if r['will_be_created']]),
            'existing_classes': len([c for c in result['models_preview']['classes'] if c['already_exists']]),
            'existing_stabs': len([s for s in result['models_preview']['stabs'] if s['already_exists']]),
            'existing_radio_stabs': len([r for r in result['models_preview']['radio_stabs'] if r['already_exists']])
        }
        
        workbook.close()
        return result
        
    except Exception as e:
        result['errors'].append(f"Excel fájl feldolgozási hiba: {str(e)}")
        return result


# ============================================================================
# Core Import Logic
# ============================================================================

def process_single_user_import(user_data: UserImportData, dry_run: bool = False) -> dict:
    """Process import for a single user."""
    result = {
        'success': False,
        'user': None,
        'profile': None,
        'osztaly': None,
        'stab': None,
        'radio_stab': None,
        'errors': [],
        'warnings': [],
        'created_models': {
            'user': None,
            'profile': None,
            'osztaly': None,
            'stab': None,
            'radio_stab': None
        }
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
        current_tanev = get_current_tanev() if not dry_run else None
        
        # Handle class creation if student
        osztaly = None
        if user_data.kezdesEve and user_data.tagozat:
            start_year = int(user_data.kezdesEve)
            section = user_data.tagozat.upper()
            osztaly, class_created = get_or_create_class(start_year, section, current_tanev, dry_run)
            result['osztaly'] = osztaly
            result['created_models']['osztaly'] = {
                'name': f"{start_year}{section}",
                'start_year': start_year,
                'section': section,
                'created': class_created
            }
        
        # Handle stab creation
        stab = None
        if user_data.stab:
            stab, stab_created = get_or_create_stab(user_data.stab, dry_run)
            result['stab'] = stab
            result['created_models']['stab'] = {
                'name': user_data.stab,
                'created': stab_created
            }
        
        # Handle radio stab creation
        radio_stab = None
        if user_data.radio and user_data.kezdesEve:
            radio_name = parse_radio_stab_name(user_data.kezdesEve, user_data.radio)
            if radio_name:
                radio_stab, radio_created = get_or_create_radio_stab(radio_name, user_data.radio, dry_run)
                result['radio_stab'] = radio_stab
                result['created_models']['radio_stab'] = {
                    'name': radio_name,
                    'team_code': user_data.radio.upper(),
                    'created': radio_created
                }
        
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
                            target_osztaly, _ = get_or_create_class(start_year, section, current_tanev)
                            if target_osztaly:
                                target_osztaly.add_osztaly_fonok(user)
                                result['warnings'].append(f"Felhasználó osztályfőnökként hozzáadva: {class_name}")
                
                # Also assign to their own class if they're a student
                if osztaly:
                    osztaly.add_osztaly_fonok(user)
            
            result['user'] = user
            result['profile'] = profile
            result['created_models']['user'] = {
                'id': user.id,
                'username': username,
                'full_name': f"{user_data.vezetekNev} {user_data.keresztNev}",
                'email': user_data.email,
                'admin_type': admin_type,
                'special_role': special_role
            }
            result['created_models']['profile'] = {
                'id': profile.id,
                'admin_type': admin_type,
                'special_role': special_role,
                'telefonszam': user_data.telefonszam
            }
        else:
            # For dry run, create mock objects
            result['created_models']['user'] = {
                'username': username,
                'full_name': f"{user_data.vezetekNev} {user_data.keresztNev}",
                'email': user_data.email,
                'admin_type': admin_type,
                'special_role': special_role,
                'would_be_created': True
            }
            result['created_models']['profile'] = {
                'admin_type': admin_type,
                'special_role': special_role,
                'telefonszam': user_data.telefonszam,
                'would_be_created': True
            }
        
        result['success'] = True
        return result
        
    except Exception as e:
        result['errors'].append(f"Hiba a felhasználó létrehozásakor: {str(e)}")
        return result


def process_bulk_user_import(users_data: List[UserImportData], dry_run: bool = False, send_emails: bool = True) -> dict:
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
        'user_details': [],
        'models_to_create': {
            'users': [],
            'profiles': [],
            'classes': [],
            'stabs': [],
            'radio_stabs': []
        }
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
                    if user_result['created_models']['stab'] and user_result['created_models']['stab']['created']:
                        stab_name = user_result['created_models']['stab']['name']
                        if stab_name not in created_stabs:
                            created_stabs.add(stab_name)
                            results['created_stabs'] += 1
                            results['models_to_create']['stabs'].append(user_result['created_models']['stab'])
                    
                    if user_result['created_models']['radio_stab'] and user_result['created_models']['radio_stab']['created']:
                        radio_name = user_result['created_models']['radio_stab']['name']
                        if radio_name not in created_radio_stabs:
                            created_radio_stabs.add(radio_name)
                            results['created_radio_stabs'] += 1
                            results['models_to_create']['radio_stabs'].append(user_result['created_models']['radio_stab'])
                    
                    if user_result['created_models']['osztaly'] and user_result['created_models']['osztaly']['created']:
                        class_key = f"{user_result['created_models']['osztaly']['start_year']}{user_result['created_models']['osztaly']['section']}"
                        if class_key not in created_classes:
                            created_classes.add(class_key)
                            results['created_classes'] += 1
                            results['models_to_create']['classes'].append(user_result['created_models']['osztaly'])
                    
                    # Store user and profile details
                    results['models_to_create']['users'].append(user_result['created_models']['user'])
                    results['models_to_create']['profiles'].append(user_result['created_models']['profile'])
                    
                    # Store user details for backward compatibility
                    user_detail = {
                        'index': i + 1,
                        'username': extract_username_from_email(user_data.email),
                        'full_name': f"{user_data.vezetekNev} {user_data.keresztNev}",
                        'email': user_data.email,
                        'admin_type': 'teacher' if normalize_yes_no(user_data.mediatana) else 'none',
                        'special_role': 'production_leader' if normalize_yes_no(user_data.gyartasvezeto) else 'none',
                        'osztaly': str(user_result['osztaly']) if user_result['osztaly'] else None,
                        'stab': user_result['stab'].name if hasattr(user_result['stab'], 'name') else user_result['stab'],
                        'radio_stab': user_result['radio_stab'].name if hasattr(user_result['radio_stab'], 'name') else user_result['radio_stab'],
                        'success': True
                    }
                    results['user_details'].append(user_detail)
                    
                    # Add any warnings
                    results['warnings'].extend(user_result['warnings'])
                    
                    # Send first-login email if requested and not dry run
                    if send_emails and not dry_run and user_result['user']:
                        try:
                            # This import should be handled by the calling code
                            pass
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
# Sample Data
# ============================================================================

def get_sample_users_data() -> List[UserImportData]:
    """Get sample user data for testing and demonstration."""
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
    
    return [UserImportData(**user_data) for user_data in sample_data]
