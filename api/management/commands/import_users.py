"""
Django management command to import users from provided data
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from api.models import Profile, Osztaly, Stab, RadioStab, Tanev
from datetime import datetime
import re

class Command(BaseCommand):
    help = 'Import users from provided Excel data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Perform a dry run without actually creating users',
        )
        parser.add_argument(
            '--chunk-size',
            type=int,
            default=3,
            help='Number of users to process in each chunk (default: 3)',
        )

    def handle(self, *args, **options):
        # Sample data from the attachment
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

        dry_run = options['dry_run']
        chunk_size = options['chunk_size']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No data will be actually created'))
        
        self.stdout.write(f"🎬 Starting FTV User Import...")
        self.stdout.write(f"📊 Total users to import: {len(SAMPLE_USERS)}")
        self.stdout.write(f"🔄 Processing in chunks of {chunk_size} users")
        
        # Create current school year
        current_tanev = self.get_or_create_current_tanev(dry_run)
        self.stdout.write(f"📅 Using school year: {current_tanev}")
        
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
        
        # Process users in chunks
        total_users = len(SAMPLE_USERS)
        for chunk_start in range(0, total_users, chunk_size):
            chunk_end = min(chunk_start + chunk_size, total_users)
            chunk_users = SAMPLE_USERS[chunk_start:chunk_end]
            
            self.stdout.write(f"\n{'='*20} CHUNK {chunk_start//chunk_size + 1} {'='*20}")
            self.stdout.write(f"📦 Processing users {chunk_start + 1}-{chunk_end} of {total_users}")
            
            # Force garbage collection before processing chunk
            if not dry_run:
                import gc
                gc.collect()
            
            # Process each user in the current chunk
            for i, user_data in enumerate(chunk_users, chunk_start + 1):
            self.stdout.write(f"\n{i:2d}. Processing: {user_data['vezetekNev']} {user_data['keresztNev']}")
            
            try:
                result = self.process_user(user_data, current_tanev, dry_run)
                
                if result['success']:
                    stats['created_users'] += 1
                    
                    # Track created objects
                    if result.get('stab_created'):
                        if result['stab_name'] not in created_stabs:
                            created_stabs.add(result['stab_name'])
                            stats['created_stabs'] += 1
                    
                    if result.get('radio_stab_created'):
                        if result['radio_stab_name'] not in created_radio_stabs:
                            created_radio_stabs.add(result['radio_stab_name'])
                            stats['created_radio_stabs'] += 1
                    
                    if result.get('class_created'):
                        class_key = f"{result['class_start_year']}{result['class_section']}"
                        if class_key not in created_classes:
                            created_classes.add(class_key)
                            stats['created_classes'] += 1
                    
                    self.stdout.write(f"   ✅ User {'would be ' if dry_run else ''}created successfully")
                    if result.get('warnings'):
                        for warning in result['warnings']:
                            self.stdout.write(f"   ⚠️  {warning}")
                            stats['warnings'].append(warning)
                else:
                    for error in result['errors']:
                        self.stdout.write(f"   ❌ {error}")
                        stats['errors'].append(error)
                
            except Exception as e:
                error = f"Hiba a felhasználó {'létrehozásakor' if not dry_run else 'feldolgozásakor'} ({user_data['email']}): {str(e)}"
                stats['errors'].append(error)
                self.stdout.write(f"   ❌ {error}")
            
            # Force database connection cleanup and garbage collection after each chunk
            if not dry_run:
                from django.db import connection
                connection.close()
                import gc
                gc.collect()
            
            self.stdout.write(f"📊 Chunk completed. Users {'would be ' if dry_run else ''}created so far: {stats['created_users']}")
            self.stdout.write(f"💾 Memory cleanup performed. Ready for next chunk...")
            
            # Optional: Add a small delay between chunks to allow memory cleanup
            if chunk_end < total_users and not dry_run:
                import time
                time.sleep(1)  # 1 second pause between chunks
        
        # Print final statistics
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("📊 IMPORT SUMMARY"))
        self.stdout.write("=" * 60)
        self.stdout.write(f"✅ Users {'would be ' if dry_run else ''}created: {stats['created_users']}/{len(SAMPLE_USERS)}")
        self.stdout.write(f"🏫 Classes {'would be ' if dry_run else ''}created: {stats['created_classes']}")
        self.stdout.write(f"👥 Stabs {'would be ' if dry_run else ''}created: {stats['created_stabs']}")
        self.stdout.write(f"📻 Radio stabs {'would be ' if dry_run else ''}created: {stats['created_radio_stabs']}")
        
        if stats['warnings']:
            self.stdout.write(f"\n⚠️  Warnings ({len(stats['warnings'])}):")
            for warning in stats['warnings']:
                self.stdout.write(f"   • {warning}")
        
        if stats['errors']:
            self.stdout.write(f"\n❌ Errors ({len(stats['errors'])}):")
            for error in stats['errors']:
                self.stdout.write(f"   • {error}")
        else:
            message = "🎉 Import validation completed successfully with no errors!" if dry_run else "🎉 Import completed successfully with no errors!"
            self.stdout.write(self.style.SUCCESS(f"\n{message}"))

    def get_or_create_current_tanev(self, dry_run=False):
        """Create or get current school year."""
        current_tanev = Tanev.get_active()
        if not current_tanev and not dry_run:
            # Create a default school year for current academic year
            current_year = datetime.now().year
            if datetime.now().month >= 9:  # After September, it's the new school year
                current_tanev = Tanev.create_for_year(current_year)
            else:
                current_tanev = Tanev.create_for_year(current_year - 1)
        elif not current_tanev and dry_run:
            # For dry run, just create a dummy object
            return f"New Tanév (would be created)"
        return current_tanev

    def extract_username_from_email(self, email: str) -> str:
        """Extract username from email (part before @)."""
        return email.split('@')[0] if '@' in email else email

    def normalize_yes_no(self, value: str) -> bool:
        """Normalize 'Igen'/'Nem' values to boolean."""
        if not value:
            return False
        return value.strip().lower() in ['igen', 'yes', 'true', '1']

    def process_user(self, user_data, current_tanev, dry_run=False):
        """Process a single user import."""
        result = {
            'success': False,
            'errors': [],
            'warnings': [],
            'stab_created': False,
            'radio_stab_created': False,
            'class_created': False
        }
        
        # Generate username from email
        username = self.extract_username_from_email(user_data['email'])
        
        # Check for duplicate username or email
        if User.objects.filter(username=username).exists():
            result['errors'].append(f"Felhasználónév már létezik: {username}")
            return result
        
        if User.objects.filter(email=user_data['email']).exists():
            result['errors'].append(f"Email cím már létezik: {user_data['email']}")
            return result
        
        # Determine admin type and special role
        admin_type = 'teacher' if self.normalize_yes_no(user_data['mediatana']) else 'none'
        special_role = 'production_leader' if self.normalize_yes_no(user_data['gyartasvezeto']) else 'none'
        
        self.stdout.write(f"   👤 Username: {username}")
        self.stdout.write(f"   🎭 Admin Type: {admin_type}, Special Role: {special_role}")
        
        # Handle class creation if student
        osztaly = None
        if user_data['kezdesEve'] and user_data['tagozat']:
            start_year = int(user_data['kezdesEve'])
            section = user_data['tagozat'].upper()
            
            if not dry_run:
                osztaly, created = Osztaly.objects.get_or_create(
                    startYear=start_year,
                    szekcio=section,
                    defaults={
                        'startYear': start_year,
                        'szekcio': section,
                        'tanev': current_tanev
                    }
                )
                result['class_created'] = created
            else:
                # For dry run, check if it would be created
                osztaly_exists = Osztaly.objects.filter(startYear=start_year, szekcio=section).exists()
                result['class_created'] = not osztaly_exists
            
            result['class_start_year'] = start_year
            result['class_section'] = section
            
            if result['class_created']:
                self.stdout.write(f"   ✓ {'Would create' if dry_run else 'Created'} class: {start_year}{section}")
        
        # Handle stab creation
        stab = None
        if user_data['stab']:
            normalized_name = user_data['stab'].strip()
            
            if not dry_run:
                stab, created = Stab.objects.get_or_create(
                    name=normalized_name,
                    defaults={'name': normalized_name}
                )
                result['stab_created'] = created
            else:
                stab_exists = Stab.objects.filter(name=normalized_name).exists()
                result['stab_created'] = not stab_exists
            
            result['stab_name'] = normalized_name
            
            if result['stab_created']:
                self.stdout.write(f"   ✓ {'Would create' if dry_run else 'Created'} stab: {normalized_name}")
        
        # Handle radio stab creation
        radio_stab = None
        if user_data['radio'] and user_data['kezdesEve']:
            radio_name = f"{user_data['kezdesEve']} {user_data['radio']}"
            radio_code = user_data['radio'].upper()
            
            if not dry_run:
                radio_stab, created = RadioStab.objects.get_or_create(
                    name=radio_name,
                    defaults={
                        'name': radio_name,
                        'team_code': radio_code,
                        'description': f'Automatikusan létrehozott rádiós stáb importálás során'
                    }
                )
                result['radio_stab_created'] = created
            else:
                radio_stab_exists = RadioStab.objects.filter(name=radio_name).exists()
                result['radio_stab_created'] = not radio_stab_exists
            
            result['radio_stab_name'] = radio_name
            
            if result['radio_stab_created']:
                self.stdout.write(f"   ✓ {'Would create' if dry_run else 'Created'} radio stab: {radio_name} ({radio_code})")
        
        if not dry_run:
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
            if self.normalize_yes_no(user_data['osztalyfonok']):
                # Parse and assign to classes mentioned in osztalyai
                if user_data['osztalyai']:
                    for class_name in user_data['osztalyai'].split(','):
                        class_name = class_name.strip()
                        # Parse class string like '2023F' into start_year and section
                        match = re.match(r'(\d{4})([A-Z]+)', class_name)
                        if match:
                            target_start_year = int(match.group(1))
                            target_section = match.group(2)
                            target_osztaly, _ = Osztaly.objects.get_or_create(
                                startYear=target_start_year,
                                szekcio=target_section,
                                defaults={
                                    'startYear': target_start_year,
                                    'szekcio': target_section,
                                    'tanev': current_tanev
                                }
                            )
                            target_osztaly.add_osztaly_fonok(user)
                            result['warnings'].append(f"Added as class teacher: {class_name}")
                
                # Also assign to their own class if they're a student
                if osztaly:
                    osztaly.add_osztaly_fonok(user)
                    result['warnings'].append(f"Added as class teacher to own class")
        
        result['success'] = True
        return result
