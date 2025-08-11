import random
from datetime import datetime, timedelta, time, date
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from api.models import (
    Profile, Osztaly, Stab, RadioStab, Partner, PartnerTipus, Config, 
    Forgatas, EquipmentTipus, Equipment, ContactPerson, Announcement,
    Tavollet, RadioSession, Beosztas, SzerepkorRelaciok, Szerepkor, Tanev
)


class Command(BaseCommand):
    help = 'Load demo data for FTV application'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before loading demo data',
        )
        parser.add_argument(
            '--users',
            type=int,
            default=50,
            help='Number of users to create (default: 50)',
        )
        parser.add_argument(
            '--shoots',
            type=int,
            default=100,
            help='Number of shoots (forgatások) to create (default: 100)',
        )
        parser.add_argument(
            '--partners',
            type=int,
            default=30,
            help='Number of partners to create (default: 30)',
        )
        parser.add_argument(
            '--announcements',
            type=int,
            default=20,
            help='Number of announcements to create (default: 20)',
        )
        parser.add_argument(
            '--radio-sessions',
            type=int,
            default=50,
            help='Number of radio sessions to create (default: 50)',
        )
        parser.add_argument(
            '--absences',
            type=int,
            default=30,
            help='Number of absences to create (default: 30)',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing existing data...'))
            self.clear_data()

        self.stdout.write(self.style.SUCCESS('Loading demo data...'))
        
        # Load basic configuration data
        self.create_config()
        
        # Create school years first (needed for other models)
        self.create_school_years()
        
        # Load lookup data
        self.create_stabs()
        self.create_radio_stabs()
        self.create_classes()
        self.create_partner_types()
        self.create_equipment_types()
        self.create_roles()
        
        # Load main entities
        self.create_partners(options['partners'])
        self.create_contact_persons()
        self.create_equipment()
        self.create_users_and_profiles(options['users'])
        self.create_shoots(options['shoots'])
        self.create_announcements(options['announcements'])
        self.create_absences(options['absences'])
        self.create_radio_sessions(options['radio_sessions'])
        self.create_assignments()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Demo data loaded successfully!\n'
                f'- {options["users"]} users created\n'
                f'- {options["partners"]} partners created\n'
                f'- {options["shoots"]} shoots created\n'
                f'- {options["announcements"]} announcements created\n'
                f'- {options["absences"]} absences created\n'
                f'- {options["radio_sessions"]} radio sessions created'
            )
        )

    def clear_data(self):
        """Clear existing data"""
        models_to_clear = [
            Beosztas, SzerepkorRelaciok, Szerepkor, RadioSession, Tavollet, 
            Announcement, Forgatas, Profile, User, Equipment, ContactPerson, 
            Partner, PartnerTipus, EquipmentTipus, RadioStab, Stab, Osztaly, 
            Config, Tanev
        ]
        
        for model in models_to_clear:
            count = model.objects.count()
            model.objects.all().delete()
            self.stdout.write(f'Deleted {count} {model._meta.verbose_name_plural}')

    def create_config(self):
        """Create configuration"""
        config, created = Config.objects.get_or_create(
            defaults={'active': True, 'allowEmails': True}
        )
        if created:
            self.stdout.write('Created configuration')
        else:
            self.stdout.write('Configuration already exists')

    def create_school_years(self):
        """Create school years (tanévek)"""
        current_year = datetime.now().year
        created_count = 0
        
        # Create school years from 3 years ago to 2 years in the future
        for year_offset in range(-3, 3):
            start_year = current_year + year_offset
            tanev, created = Tanev.objects.get_or_create(
                start_date=date(start_year, 9, 1),
                defaults={
                    'end_date': date(start_year + 1, 6, 15)
                }
            )
            if created:
                created_count += 1
        
        self.stdout.write(f'Created {created_count} school years (tanévek)')

    def create_stabs(self):
        """Create staff groups (stábok)"""
        stab_names = [
            'A stáb', 'B stáb', 'Vágó stáb', 'Hang stáb', 'Színpad stáb'
        ]
        
        created_count = 0
        for name in stab_names:
            stab, created = Stab.objects.get_or_create(name=name)
            if created:
                created_count += 1
        
        self.stdout.write(f'Created {created_count} stabs (skipped {len(stab_names) - created_count} existing)')

    def create_radio_stabs(self):
        """Create radio stabs for second year students"""
        radio_stabs = [
            ('A1 rádió csapat', 'A1'),
            ('A2 rádió csapat', 'A2'),
            ('B3 rádió csapat', 'B3'),
            ('B4 rádió csapat', 'B4')
        ]
        
        created_count = 0
        for name, team_code in radio_stabs:
            radio_stab, created = RadioStab.objects.get_or_create(
                team_code=team_code,
                defaults={
                    'name': name,
                    'description': f'Rádiós stáb a {team_code} csapat számára'
                }
            )
            if created:
                created_count += 1
        
        self.stdout.write(f'Created {created_count} radio stabs (skipped {len(radio_stabs) - created_count} existing)')

    def create_roles(self):
        """Create roles (szerepkörök)"""
        current_year = datetime.now().year
        roles = [
            ('Operatőr', current_year),
            ('Rendező', current_year),
            ('Hangmérnök', current_year),
            ('Vágó', current_year),
            ('Világosító', current_year),
            ('Háttértáncos', current_year),
            ('Moderátor', current_year),
            ('Műsorvezető', current_year),
            ('Kameramozgató', current_year),
            ('Szerkesztő', current_year),
            ('Gyártásvezető', current_year),
            ('Produkciós asszisztens', current_year)
        ]
        
        created_count = 0
        for name, ev in roles:
            szerepkor, created = Szerepkor.objects.get_or_create(
                name=name,
                defaults={'ev': ev}
            )
            if created:
                created_count += 1
        
        self.stdout.write(f'Created {created_count} roles (szerepkörök)')
    

    def create_classes(self):
        """Create classes (osztályok)"""
        current_year = datetime.now().year
        sections = ["F"]  # We mainly work with F section
        tanevek = list(Tanev.objects.all())

        created_count = 0
        for year_offset in range(5):
            start_year = current_year - year_offset
            for section in sections:
                osztaly, created = Osztaly.objects.get_or_create(
                    startYear=start_year,
                    szekcio=section,
                    defaults={
                        'tanev': random.choice(tanevek) if tanevek else None
                    }
                )
                if created:
                    created_count += 1

        self.stdout.write(f'Created {created_count} F classes (skipped {5 * len(sections) - created_count} existing)')

        # Assign classes to school years
        if tanevek:
            for tanev in tanevek:
                classes_for_year = list(Osztaly.objects.all())
                # Add some classes to each school year
                classes_to_add = random.sample(classes_for_year, min(3, len(classes_for_year)))
                tanev.osztalyok.set(classes_to_add)
            
            self.stdout.write('Assigned classes to school years')

    def create_partner_types(self):
        """Create partner types"""
        partner_types = [
            'Iskola', 'Kutatóintézet', 'Közösségi Ház', 'Kulturális Központ',
            'Múzeum', 'Könyvtár', 'Egyesület', 'Vállalat', 'Önkormányzat', 'Egyéb'
        ]
        
        created_count = 0
        for ptype in partner_types:
            partner_type, created = PartnerTipus.objects.get_or_create(name=ptype)
            if created:
                created_count += 1
        
        self.stdout.write(f'Created {created_count} partner types (skipped {len(partner_types) - created_count} existing)')

    def create_equipment_types(self):
        """Create equipment types"""
        equipment_types = [
            ('Kamera', '📹'), ('Objektív', '🔍'), ('Mikrofon', '🎤'),
            ('Lámpa', '💡'), ('Statív', '🎬'), ('Akkumulátor', '🔋'),
            ('Memóriakártya', '💾'), ('Kábel', '🔌'), ('Táska', '🎒'),
            ('Szűrő', '🌈'), ('Monitor', '📺'), ('Fülhallgató', '🎧')
        ]
        
        created_count = 0
        for name, emoji in equipment_types:
            equipment_type, created = EquipmentTipus.objects.get_or_create(
                name=name, 
                defaults={'emoji': emoji}
            )
            if created:
                created_count += 1
        
        self.stdout.write(f'Created {created_count} equipment types (skipped {len(equipment_types) - created_count} existing)')

    def create_partners(self, count):
        """Create partner organizations"""
        partner_types = list(PartnerTipus.objects.all())
        
        partner_names = [
            'Budapesti Műszaki Egyetem', 'ELTE Informatikai Kar', 'Corvinus Egyetem',
            'Szent István Gimnázium', 'Vörösmarty Gimnázium', 'Fazekas Gimnázium',
            'MTA Kutatóintézet', 'BME Kutatóközpont', 'Nemzeti Múzeum',
            'Szépművészeti Múzeum', 'Magyar Nemzeti Galéria', 'Természettudományi Múzeum',
            'Károlyi Palota', 'Buda Kulturális Központ', 'Pest Megyei Könyvtár',
            'Fővárosi Könyvtár', 'Microsoft Hungary', 'Google Budapest',
            'Nokia Budapest', 'IBM Hungary', 'Telekom Hungary',
            'Budapest Főváros Önkormányzata', 'V. kerületi Önkormányzat',
            'Budapesti Ifjúsági Egyesület', 'Magyar Filmkészítők Egyesülete',
            'Zöld Föld Alapítvány', 'Jövő Generációi Egyesület',
            'Tech Startup Hub', 'Innovation Center', 'Creative Commons Hungary'
        ]
        
        addresses = [
            'Budapest, Váci út 45.', 'Budapest, Fő utca 12.', 'Budapest, Andrássy út 78.',
            'Budapest, Kossuth Lajos tér 5.', 'Budapest, Rákóczi út 23.',
            'Budapest, Petőfi Sándor utca 34.', 'Budapest, Bajcsy-Zsilinszky út 56.',
            'Budapest, Dózsa György út 89.', 'Budapest, Széchenyi István tér 15.',
            'Budapest, Deák Ferenc tér 7.'
        ]
        
        for i in range(count):
            # Use unique names to avoid duplicates
            if i < len(partner_names):
                name = partner_names[i]
            else:
                name = f"{random.choice(partner_names)} - {i+1}"
            
            partner, created = Partner.objects.get_or_create(
                name=name,
                defaults={
                    'address': random.choice(addresses),
                    'institution': random.choice(partner_types)
                }
            )
            if not created:
                # Update existing partner with new data
                partner.address = random.choice(addresses)
                partner.institution = random.choice(partner_types)
                partner.save()
        
        self.stdout.write(f'Created {count} partners')

    def create_contact_persons(self):
        """Create contact persons"""
        first_names = [
            'János', 'Péter', 'László', 'Zoltán', 'András', 'Gábor', 'István',
            'Anna', 'Mária', 'Katalin', 'Eszter', 'Judit', 'Éva', 'Krisztina'
        ]
        
        last_names = [
            'Nagy', 'Kovács', 'Tóth', 'Szabó', 'Horváth', 'Varga', 'Kiss',
            'Molnár', 'Németh', 'Farkas', 'Balogh', 'Papp', 'Takács', 'Juhász'
        ]
        
        domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'freemail.hu']
        
        for i in range(40):
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            email = f"{first_name.lower()}.{last_name.lower()}@{random.choice(domains)}"
            phone = f"+36-{random.randint(20, 99)}-{random.randint(100, 999)}-{random.randint(1000, 9999)}"
            
            ContactPerson.objects.create(
                name=f"{last_name} {first_name}",
                email=email,
                phone=phone
            )
        
        self.stdout.write('Created 40 contact persons')

    def create_equipment(self):
        """Create equipment"""
        equipment_data = [
            # (Hungarian Nickname, Brand, Model, Equipment Type)
            ('Béla', 'Canon', 'EOS R5', 'Kamera'),
            ('János', 'Sony', 'A7 III', 'Kamera'),
            ('Gábor', 'Blackmagic', 'URSA Mini Pro', 'Kamera'),
            ('László', 'RED', 'Komodo 6K', 'Kamera'),

            ('Fanni', 'Canon', 'RF 24-70mm f/2.8L', 'Objektív'),
            ('Kata', 'Sony', 'FE 85mm f/1.4 GM', 'Objektív'),
            ('Eszter', 'Sigma', '35mm f/1.4 DG DN Art', 'Objektív'),

            ('Ádám', 'Rode', 'VideoMic Pro Plus', 'Mikrofon'),
            ('Péter', 'Sennheiser', 'MKE 600', 'Mikrofon'),
            ('Zsófi', 'Audio-Technica', 'AT875R', 'Mikrofon'),

            ('Misi', 'Aputure', 'Light Storm COB 300d', 'Lámpa'),
            ('Réka', 'Godox', 'SL-60W', 'Lámpa'),
            ('Tamás', 'Neewer', '660 LED Panel', 'Lámpa'),

            ('András', 'Manfrotto', 'MVK502AM', 'Állvány'),
            ('Bence', 'Benro', 'S8 Head', 'Állvány'),
            ('Dóra', 'Gitzo', 'GT3543XLS', 'Állvány'),

            ('Gergő', 'Sony', 'NP-FZ100', 'Akkumulátor'),
            ('Márta', 'Canon', 'LP-E6NH', 'Akkumulátor'),
            ('Zoltán', 'RedPro', 'RP-150V', 'Akkumulátor'),
        ]

        equipment_types = {et.name: et for et in EquipmentTipus.objects.all()}

        for i, (nickname, brand, model, eq_type) in enumerate(equipment_data):
            serial_number = f"ZTV{2025}{i+1:03d}"

            equipment, created = Equipment.objects.get_or_create(
                nickname=nickname,
                defaults={
                    'brand': brand,
                    'model': model,
                    'serialNumber': serial_number,
                    'equipmentType': equipment_types.get(eq_type),
                    'functional': random.choice([True, True, True, False]),  # 75% functional
                    'notes': random.choice([
                        '', '', '',  # Most have no notes
                        'Kis sérülés a házán', 'Akkumulátor élettartama csökkent',
                        'Tisztítás szükséges', 'Kalibráció szükséges'
                    ])
                }
            )
            if not created and equipment.serialNumber != serial_number:
                # Update serial number if different
                equipment.serialNumber = serial_number
                equipment.save()

        self.stdout.write(f'Created {len(equipment_data)} equipment items')

    def create_users_and_profiles(self, count):
        """Create users with profiles"""
        first_names = [
            'Alex', 'Béla', 'Csaba', 'Dániel', 'Erik', 'Ferenc', 'Gergő', 'Henrik',
            'Anna', 'Barbara', 'Csilla', 'Diána', 'Emília', 'Fanni', 'Greta', 'Hanna',
            'István', 'János', 'Károly', 'László', 'Máté', 'Norbert', 'Olivér', 'Péter',
            'Réka', 'Szilvia', 'Tamás', 'Viktor', 'Zoltán', 'Zsófia'
        ]
        
        last_names = [
            'Nagy', 'Kovács', 'Tóth', 'Szabó', 'Horváth', 'Varga', 'Kiss', 'Molnár',
            'Németh', 'Farkas', 'Balogh', 'Papp', 'Takács', 'Juhász', 'Mészáros', 'Oláh',
            'Simon', 'Rácz', 'Fekete', 'Szűcs', 'Kocsis', 'Lakatos', 'Török', 'Somogyi'
        ]
        
        stabs = list(Stab.objects.all())
        radio_stabs = list(RadioStab.objects.all())
        classes = list(Osztaly.objects.all())
        
        admin_types = ['none', 'developer', 'teacher', 'system_admin']
        special_roles = ['none', 'production_leader']
        
        created_count = 0
        
        # Create some admin users first
        admin_users = [
            ('admin', 'Admin', 'User', 'developer'),
            ('teacher1', 'Média', 'Tanár', 'teacher'),
            ('sysadmin', 'System', 'Admin', 'system_admin'),
            ('producer', 'Gyártás', 'Vezető', 'none')
        ]
        
        for username, first_name, last_name, admin_type in admin_users:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@szlgbp.hu',
                    'first_name': first_name,
                    'last_name': last_name,
                    'is_staff': True,
                    'is_superuser': admin_type == 'developer'
                }
            )
            
            if created:
                user.set_password('admin123')
                user.save()
                created_count += 1
            
            # Create profile
            profile, profile_created = Profile.objects.get_or_create(
                user=user,
                defaults={
                    'telefonszam': f"+36-{random.randint(20, 99)} {random.randint(100, 999)} {random.randint(1000, 9999)}",
                    'medias': True,
                    'admin_type': admin_type,
                    'special_role': 'production_leader' if username == 'producer' else 'none',
                    'password_set': True
                }
            )
        
        # Create regular students
        for i in range(count - len(admin_users)):
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            username = f"{first_name.lower()}.{last_name.lower()}.{i+1}"
            email = f"{username}@szlgbp.hu"
            
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name,
                }
            )
            
            if created:
                user.set_password('demo123')  # Simple password for demo
                user.save()
                created_count += 1
            
            # Create or get profile
            selected_class = random.choice(classes) if random.random() > 0.2 else None
            selected_stab = random.choice(stabs) if random.random() > 0.3 else None
            
            # Second year students (9F) might get radio stab
            selected_radio_stab = None
            if selected_class and selected_class.szekcio == 'F':
                # Check if this would be a second year (9F) student
                current_year = datetime.now().year
                elso_felev = datetime.now().month >= 9
                year_diff = current_year - selected_class.startYear 
                year_diff += 8 if elso_felev else 7
                
                if year_diff == 9 and random.random() > 0.5:  # 50% chance for 9F students
                    selected_radio_stab = random.choice(radio_stabs)
            
            profile, profile_created = Profile.objects.get_or_create(
                user=user,
                defaults={
                    'telefonszam': f"+36-{random.randint(20, 99)} {random.randint(100, 999)} {random.randint(1000, 9999)}",
                    'medias': random.choice([True, False]),
                    'stab': selected_stab,
                    'radio_stab': selected_radio_stab,
                    'osztaly': selected_class,
                    'admin_type': 'none',
                    'special_role': 'none',
                    'password_set': random.choice([True, False])
                }
            )
        
        self.stdout.write(f'Created {created_count} users with profiles (skipped {count - created_count} existing)')

    def create_shoots(self, count):
        """Create shoots (forgatások)"""
        shoot_names = [
            'Kampányfilm egyetemeknek', 'Interjú rektorral', 'Campus bemutató',
            'Hallgatói élet dokumentum', 'Tudományos konferencia', 'Diplomaosztó ünnepség',
            'Sportrendezvény közvetítés', 'Kulturális program', 'Gólyabál felvétel',
            'Szakmai előadás rögzítés', 'Alumni találkozó', 'Nyílt nap dokumentáció',
            'Kutatólabor bemutató', 'Professzorinterjú sorozat', 'Évzáró gála',
            'Diákönkormányzat ülés', 'Startup pitch verseny', 'Művészeti kiállítás',
            'Koncert felvétel', 'Színházi előadás dokumentum'
        ]
        
        descriptions = [
            'Promóciós anyag készítése új jelentkezők számára',
            'Szakmai tartalmat bemutató dokumentumfilm',
            'Egyetemi élet mindennapjainak bemutatása',
            'Oktatási célú videó anyag készítése',
            'Esemény dokumentációja és közvetítése',
            'Archívum célú felvétel készítése',
            'Közösségi média tartalmat szolgáló videó'
        ]
        
        partners = list(Partner.objects.all())
        contact_persons = list(ContactPerson.objects.all())
        equipments = list(Equipment.objects.filter(functional=True))
        
        shoot_types = ['kacsa', 'rendes', 'rendezveny', 'egyeb']
        
        for i in range(count):
            # Random date in the next 6 months
            start_date = date.today() + timedelta(days=random.randint(-180, 180))
            
            # Random time
            start_hour = random.randint(8, 20)
            start_minute = random.choice([0, 15, 30, 45])
            duration_hours = random.randint(1, 8)
            
            time_from = time(start_hour, start_minute)
            time_to = time(
                min(23, start_hour + duration_hours), 
                start_minute
            )
            
            shoot_type = random.choice(shoot_types)
            
            forgatas = Forgatas.objects.create(
                name=f"{random.choice(shoot_names)} - {i+1}",
                description=random.choice(descriptions),
                date=start_date,
                timeFrom=time_from,
                timeTo=time_to,
                location=random.choice(partners) if random.random() > 0.1 else None,
                contactPerson=random.choice(contact_persons) if random.random() > 0.2 else None,
                forgTipus=shoot_type,
                notes=random.choice([
                    '', '', '',  # Most have no notes
                    'Parkolási engedély szükséges',
                    'Csendes környezet biztosítása',
                    'Elektromos csatlakozó szükséges',
                    'Biztonsági előírások betartása'
                ])
            )
            
            # Assign random equipment (1-5 items)
            num_equipments = random.randint(1, min(5, len(equipments)))
            selected_equipments = random.sample(equipments, num_equipments)
            forgatas.equipments.set(selected_equipments)
        
        # Create some KaCsa relationships
        kacsa_shoots = list(Forgatas.objects.filter(forgTipus='kacsa'))
        regular_shoots = list(Forgatas.objects.filter(forgTipus='rendes'))
        
        for regular_shoot in regular_shoots[:len(kacsa_shoots)//2]:
            if kacsa_shoots:
                regular_shoot.relatedKaCsa = random.choice(kacsa_shoots)
                regular_shoot.save()
        
        self.stdout.write(f'Created {count} shoots')

    def create_announcements(self, count):
        """Create announcements (közlemények)"""
        users = list(User.objects.all())
        if not users:
            self.stdout.write(self.style.WARNING('No users found for creating announcements'))
            return
            
        announcement_titles = [
            'Fontos változás a forgatási menetrendben',
            'Új eszközök érkeztek a stúdióba',
            'Hétvégi forgatás lemondva',
            'Rendkívüli stábgyűlés',
            'Műszaki ellenőrzés a következő héten',
            'Új biztonsági előírások',
            'Gyakorlati vizsga időpontjai',
            'Őszi szünet programja',
            'Téli forgatási időszak',
            'Tavasz végi értékelés',
            'Nyári gyakorlat lehetőségei',
            'Vendég előadó a következő héten',
            'Dokumentumfilm verseny',
            'Technikai workshop',
            'Kreatív pályázat kiírása',
            'Alumni találkozó',
            'Nyílt nap előkészületei',
            'Gala est szervezése',
            'Nemzetközi együttműködés',
            'Diploma projektekről'
        ]
        
        announcement_bodies = [
            'Tisztelt Kollégák!\n\nTájékoztatjuk Önöket, hogy a következő változások léptek életbe...',
            'Kedves Diákok!\n\nÖrömmel jelentjük be, hogy új technikai eszközök érkeztek...',
            'Sajnos az időjárási körülmények miatt kénytelenek vagyunk lemondani...',
            'Fontos kérdések megvitatására kerül sor a holnapi napon...',
            'A műszaki ellenőrzés célja az eszközök biztonságos működésének ellenőrzése...',
            'Az új biztonsági előírások betartása mindenkinek kötelessége...',
            'A gyakorlati vizsgák időpontjai a következők szerint alakulnak...',
            'Az őszi szünetben is lesznek lehetőségek kreatív munkára...',
            'A téli időszakban speciális körülményekre kell felkészülni...',
            'A félévet értékeléssel zárjuk, ahol minden résztvevő...',
            'Nyári gyakorlati lehetőségek várják az érdeklődőket...',
            'Neves szakember tart előadást a következő héten...',
            'Dokumentumfilm verseny kiírása, jelentkezési határidő...',
            'Technikai workshop új eszközök használatáról...',
            'Kreatív pályázat kiírása fiatal filmkészítők számára...',
            'Alumni találkozó szervezése, egykori diákok tapasztalatai...',
            'Nyílt nap előkészületei, minden diák részvétele szükséges...',
            'Gala est szervezése az év végi ünnepségre...',
            'Nemzetközi együttműködési lehetőségek...',
            'Diploma projektek szabályairól és értékeléséről...'
        ]
        
        created_count = 0
        for i in range(count):
            title = random.choice(announcement_titles)
            body = random.choice(announcement_bodies)
            author = random.choice(users)
            
            # Create announcement
            announcement = Announcement.objects.create(
                title=f"{title} - {i+1}" if i > 0 else title,
                body=body,
                author=author
            )
            
            # Assign random recipients (20-80% of users)
            num_recipients = random.randint(len(users)//5, 4*len(users)//5)
            recipients = random.sample(users, num_recipients)
            announcement.cimzettek.set(recipients)
            
            created_count += 1
        
        self.stdout.write(f'Created {created_count} announcements')

    def create_absences(self, count):
        """Create absences (távollétek)"""
        users = list(User.objects.filter(profile__isnull=False))
        if not users:
            self.stdout.write(self.style.WARNING('No users with profiles found for creating absences'))
            return
            
        absence_reasons = [
            'Betegség',
            'Orvosi vizsgálat',
            'Családi esemény',
            'Más tantárgy ZH',
            'Személyes ügyek',
            'Utazás',
            'Munkavállalás',
            'Egyéb elfoglaltság',
            'Karantén',
            'Szabadság'
        ]
        
        created_count = 0
        for i in range(count):
            user = random.choice(users)
            
            # Random date range (past 2 months to future 2 months)
            start_offset = random.randint(-60, 60)
            duration = random.randint(1, 5)  # 1-5 days
            
            start_date = date.today() + timedelta(days=start_offset)
            end_date = start_date + timedelta(days=duration)
            
            reason = random.choice(absence_reasons)
            denied = random.choice([False, False, False, True])  # 25% denied
            
            Tavollet.objects.create(
                user=user,
                start_date=start_date,
                end_date=end_date,
                reason=reason,
                denied=denied
            )
            
            created_count += 1
        
        self.stdout.write(f'Created {created_count} absences')

    def create_radio_sessions(self, count):
        """Create radio sessions (rádiós összejátszások)"""
        radio_stabs = list(RadioStab.objects.all())
        if not radio_stabs:
            self.stdout.write(self.style.WARNING('No radio stabs found for creating radio sessions'))
            return
            
        # Get 9F students for radio sessions
        f_students = list(User.objects.filter(
            profile__osztaly__szekcio='F',
            profile__radio_stab__isnull=False
        ))
        
        descriptions = [
            'Heti gyakorlati összejátszás',
            'Technikai próba új műsorral',
            'Élő adás gyakorlása',
            'Interjú készítés tréning',
            'Hírolvasás gyakorlás',
            'Zenei műsor összeállítása',
            'Vendég interjú felvétel',
            'Reggeli műsor próbája',
            'Délutáni magazin gyakorlat',
            'Esti műsor előkészítése'
        ]
        
        tanevek = list(Tanev.objects.all())
        
        created_count = 0
        for i in range(count):
            radio_stab = random.choice(radio_stabs)
            
            # Random date (past 3 months to future 3 months)
            session_date = date.today() + timedelta(days=random.randint(-90, 90))
            
            # Random time (usually afternoon/evening)
            start_hour = random.randint(14, 20)
            duration_hours = random.randint(1, 3)
            
            time_from = time(start_hour, random.choice([0, 15, 30, 45]))
            time_to = time(
                min(23, start_hour + duration_hours),
                time_from.minute
            )
            
            radio_session = RadioSession.objects.create(
                radio_stab=radio_stab,
                date=session_date,
                time_from=time_from,
                time_to=time_to,
                description=random.choice(descriptions),
                tanev=random.choice(tanevek) if tanevek else None
            )
            
            # Assign participants from the radio stab
            stab_members = list(User.objects.filter(profile__radio_stab=radio_stab))
            if stab_members:
                # Usually 2-4 participants per session
                num_participants = random.randint(2, min(4, len(stab_members)))
                participants = random.sample(stab_members, num_participants)
                radio_session.participants.set(participants)
            
            created_count += 1
        
        self.stdout.write(f'Created {created_count} radio sessions')

    def create_assignments(self):
        """Create assignments (beosztások) and role relations"""
        users = list(User.objects.all())
        roles = list(Szerepkor.objects.all())
        tanevek = list(Tanev.objects.all())
        
        if not users or not roles:
            self.stdout.write(self.style.WARNING('Need users and roles to create assignments'))
            return
            
        # Create 3-5 assignments
        assignment_count = 0
        for i in range(random.randint(3, 5)):
            beosztas = Beosztas.objects.create(
                kesz=random.choice([True, False, False]),  # 33% ready
                author=random.choice(users),
                tanev=random.choice(tanevek) if tanevek else None
            )
            
            # Create role relations for this assignment
            num_relations = random.randint(5, 15)
            relations_created = 0
            
            for j in range(num_relations):
                user = random.choice(users)
                role = random.choice(roles)
                
                # Create role relation
                relation, created = SzerepkorRelaciok.objects.get_or_create(
                    user=user,
                    szerepkor=role
                )
                
                if created:
                    relations_created += 1
                
                # Add to assignment
                beosztas.szerepkor_relaciok.add(relation)
            
            assignment_count += 1
        
        self.stdout.write(f'Created {assignment_count} assignments (beosztások)')
