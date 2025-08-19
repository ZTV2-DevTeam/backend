#!/usr/bin/env python3
"""
FTV User Import Script

This script processes the Excel/CSV data attached and imports all users into the FTV system.
It handles:
- User creation with usernames generated from email addresses
- Profile assignment with correct admin types and special roles
- Radio stab creation (format: YYYY XX)
- Class creation based on start year and section
- Class teacher assignments

Usage:
    python import_users.py

Make sure Django is properly configured and the server is running.
"""

import os
import sys
import django
import json
from datetime import datetime

# Add the backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

# Now we can import Django models
from django.contrib.auth.models import User
from api.models import Profile, Osztaly, Stab, RadioStab, Tanev

# Sample data from the attachment (manually parsed)
SAMPLE_USERS = [
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
        "gyartasvezeto": "Igen",
        "mediatana": "Igen",
        "osztalyfonok": "",
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

def create_current_tanev():
    """Create or get current school year."""
    current_tanev = Tanev.get_active()
    if not current_tanev:
        # Create a default school year for current academic year
        current_year = datetime.now().year
        if datetime.now().month >= 9:  # After September, it's the new school year
            current_tanev = Tanev.create_for_year(current_year)
        else:
            current_tanev = Tanev.create_for_year(current_year - 1)
    return current_tanev

def extract_username_from_email(email: str) -> str:
    """Extract username from email (part before @)."""
    return email.split('@')[0] if '@' in email else email

def normalize_yes_no(value: str) -> bool:
    """Normalize 'Igen'/'Nem' values to boolean."""
    if not value:
        return False
    return value.strip().lower() in ['igen', 'yes', 'true', '1']

def get_or_create_stab(stab_name: str) -> Stab:
    """Get or create a stab by name."""
    if not stab_name:
        return None
    
    # Normalize stab name
    normalized_name = stab_name.strip()
    stab, created = Stab.objects.get_or_create(
        name=normalized_name,
        defaults={'name': normalized_name}
    )
    if created:
        print(f"  ✓ Created stab: {normalized_name}")
    return stab

def get_or_create_radio_stab(radio_name: str, radio_code: str) -> RadioStab:
    """Get or create a radio stab by name and code."""
    if not radio_name or not radio_code:
        return None
    
    # Check if radio stab exists
    radio_stab, created = RadioStab.objects.get_or_create(
        name=radio_name,
        defaults={
            'name': radio_name,
            'team_code': radio_code.upper(),
            'description': f'Automatikusan létrehozott rádiós stáb importálás során'
        }
    )
    if created:
        print(f"  ✓ Created radio stab: {radio_name} ({radio_code})")
    return radio_stab

def get_or_create_class(start_year: int, section: str, tanev: Tanev = None) -> Osztaly:
    """Get or create a class by start year and section."""
    if not start_year or not section:
        return None
    
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
    
    if created:
        print(f"  ✓ Created class: {start_year}{section.upper()}")
    
    return osztaly

def parse_radio_stab_name(start_year: str, radio_code: str) -> str:
    """Generate radio stab name from start year and radio code."""
    if not start_year or not radio_code:
        return None
    return f"{start_year} {radio_code}"

def import_users():
    """Import all users from the sample data."""
    print("🎬 Starting FTV User Import...")
    print(f"📊 Total users to import: {len(SAMPLE_USERS)}")
    print("=" * 60)
    
    # Create current school year
    current_tanev = create_current_tanev()
    print(f"📅 Using school year: {current_tanev}")
    
    # Statistics
    stats = {
        'created_users': 0,
        'created_classes': 0,
        'created_stabs': 0,
        'created_radio_stabs': 0,
        'errors': [],
        'warnings': []
    }
    
    # Track created objects to avoid duplicates
    created_stabs = set()
    created_radio_stabs = set()
    created_classes = set()
    
    for i, user_data in enumerate(SAMPLE_USERS, 1):
        print(f"\n{i:2d}. Processing: {user_data['vezetekNev']} {user_data['keresztNev']}")
        
        try:
            # Generate username from email
            username = extract_username_from_email(user_data['email'])
            
            # Check for duplicate username or email
            if User.objects.filter(username=username).exists():
                error = f"Felhasználónév már létezik: {username}"
                stats['errors'].append(error)
                print(f"   ❌ {error}")
                continue
            
            if User.objects.filter(email=user_data['email']).exists():
                error = f"Email cím már létezik: {user_data['email']}"
                stats['errors'].append(error)
                print(f"   ❌ {error}")
                continue
            
            # Determine admin type and special role
            admin_type = 'teacher' if normalize_yes_no(user_data['mediatana']) else 'none'
            special_role = 'production_leader' if normalize_yes_no(user_data['gyartasvezeto']) else 'none'
            
            print(f"   👤 Username: {username}")
            print(f"   🎭 Admin Type: {admin_type}, Special Role: {special_role}")
            
            # Handle class creation if student
            osztaly = None
            if user_data['kezdesEve'] and user_data['tagozat']:
                start_year = int(user_data['kezdesEve'])
                section = user_data['tagozat'].upper()
                osztaly = get_or_create_class(start_year, section, current_tanev)
                
                class_key = f"{start_year}{section}"
                if class_key not in created_classes:
                    created_classes.add(class_key)
                    stats['created_classes'] += 1
            
            # Handle stab creation
            stab = None
            if user_data['stab']:
                stab = get_or_create_stab(user_data['stab'])
                if stab and stab.name not in created_stabs:
                    created_stabs.add(stab.name)
                    stats['created_stabs'] += 1
            
            # Handle radio stab creation
            radio_stab = None
            if user_data['radio'] and user_data['kezdesEve']:
                radio_name = parse_radio_stab_name(user_data['kezdesEve'], user_data['radio'])
                if radio_name:
                    radio_stab = get_or_create_radio_stab(radio_name, user_data['radio'])
                    if radio_stab and radio_name not in created_radio_stabs:
                        created_radio_stabs.add(radio_name)
                        stats['created_radio_stabs'] += 1
            
            # Create user
            user = User.objects.create_user(
                username=username,
                email=user_data['email'],
                first_name=user_data['keresztNev'],
                last_name=user_data['vezetekNev'],
                is_active=True
            )
            
            # Create profile
            profile = Profile.objects.create(
                user=user,
                admin_type=admin_type,
                special_role=special_role,
                telefonszam=user_data['telefonszam'] if user_data['telefonszam'] else None,
                osztaly=osztaly,
                stab=stab,
                radio_stab=radio_stab,
                medias=True  # Default to true for media students
            )
            
            # Handle class teacher assignment
            if normalize_yes_no(user_data['osztalyfonok']):
                # Parse and assign to classes mentioned in osztalyai
                if user_data['osztalyai']:
                    for class_name in user_data['osztalyai'].split(','):
                        class_name = class_name.strip()
                        # Parse class string like '2023F' into start_year and section
                        import re
                        match = re.match(r'(\d{4})([A-Z]+)', class_name)
                        if match:
                            target_start_year = int(match.group(1))
                            target_section = match.group(2)
                            target_osztaly = get_or_create_class(target_start_year, target_section, current_tanev)
                            if target_osztaly:
                                target_osztaly.add_osztaly_fonok(user)
                                print(f"   👨‍🏫 Added as class teacher: {class_name}")
                
                # Also assign to their own class if they're a student
                if osztaly:
                    osztaly.add_osztaly_fonok(user)
                    print(f"   👨‍🏫 Added as class teacher to own class")
            
            stats['created_users'] += 1
            print(f"   ✅ User created successfully")
            
        except Exception as e:
            error = f"Hiba a felhasználó létrehozásakor ({user_data['email']}): {str(e)}"
            stats['errors'].append(error)
            print(f"   ❌ {error}")
    
    # Print final statistics
    print("\n" + "=" * 60)
    print("📊 IMPORT SUMMARY")
    print("=" * 60)
    print(f"✅ Users created: {stats['created_users']}/{len(SAMPLE_USERS)}")
    print(f"🏫 Classes created: {stats['created_classes']}")
    print(f"👥 Stabs created: {stats['created_stabs']}")
    print(f"📻 Radio stabs created: {stats['created_radio_stabs']}")
    
    if stats['warnings']:
        print(f"\n⚠️  Warnings ({len(stats['warnings'])}):")
        for warning in stats['warnings']:
            print(f"   • {warning}")
    
    if stats['errors']:
        print(f"\n❌ Errors ({len(stats['errors'])}):")
        for error in stats['errors']:
            print(f"   • {error}")
    else:
        print("\n🎉 Import completed successfully with no errors!")
    
    return stats

if __name__ == "__main__":
    try:
        stats = import_users()
        
        if stats['errors']:
            sys.exit(1)  # Exit with error code if there were errors
        else:
            print("\n✨ All users imported successfully!")
            sys.exit(0)  # Exit with success code
            
    except Exception as e:
        print(f"\n💥 Critical error during import: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
