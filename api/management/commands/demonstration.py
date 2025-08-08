import random
from datetime import datetime, timedelta, time, date
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from api.models import (
    Profile, Osztaly, Stab, Partner, PartnerTipus, Config, 
    Forgatas, EquipmentTipus, Equipment, ContactPerson
)


class Command(BaseCommand):
    help = 'Load demo data for ZTV2 application'

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

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing existing data...'))
            self.clear_data()

        self.stdout.write(self.style.SUCCESS('Loading demo data...'))
        
        # Load basic configuration data
        self.create_config()
        
        # Load lookup data
        self.create_stabs()
        self.create_classes()
        self.create_partner_types()
        self.create_equipment_types()
        
        # Load main entities
        self.create_partners(options['partners'])
        self.create_contact_persons()
        self.create_equipment()
        self.create_users_and_profiles(options['users'])
        self.create_shoots(options['shoots'])
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Demo data loaded successfully!\n'
                f'- {options["users"]} users created\n'
                f'- {options["partners"]} partners created\n'
                f'- {options["shoots"]} shoots created'
            )
        )

    def clear_data(self):
        """Clear existing data"""
        models_to_clear = [
            Forgatas, Profile, User, Equipment, ContactPerson, 
            Partner, PartnerTipus, EquipmentTipus, Stab, Osztaly, Config
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

    def create_stabs(self):
        """Create staff groups (stábok)"""
        stab_names = [
            'A stáb', 'B stáb',
        ]
        
        created_count = 0
        for name in stab_names:
            stab, created = Stab.objects.get_or_create(name=name)
            if created:
                created_count += 1
        
        self.stdout.write(f'Created {created_count} stabs (skipped {len(stab_names) - created_count} existing)')

    def create_classes(self):

        """Create classes (osztályok)"""
        current_year = datetime.now().year
        sections = ["F"]

        created_count = 0
        for year_offset in range(5):
            start_year = current_year - year_offset
            for section in sections:
                osztaly, created = Osztaly.objects.get_or_create(
                    startYear=start_year,
                    szekcio=section
                )
                if created:
                    created_count += 1

        self.stdout.write(f'Created {created_count} F classes (skipped {5 * len(sections) - created_count} existing)')

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
            'Anna', 'Barbara', 'Csilla', 'Diána', 'Emília', 'Fanni', 'Greta', 'Hanna'
        ]
        
        last_names = [
            'Nagy', 'Kovács', 'Tóth', 'Szabó', 'Horváth', 'Varga', 'Kiss', 'Molnár',
            'Németh', 'Farkas', 'Balogh', 'Papp', 'Takács', 'Juhász', 'Mészáros', 'Oláh'
        ]
        
        stabs = list(Stab.objects.all())
        classes = list(Osztaly.objects.all())
        
        created_count = 0
        for i in range(count):
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
            profile, profile_created = Profile.objects.get_or_create(
                user=user,
                defaults={
                    'telefonszam': f"+36-{random.randint(20, 99)} {random.randint(100, 999)} {random.randint(1000, 9999)}",
                    'medias': random.choice([True, False]),
                    'stab': random.choice(stabs) if random.random() > 0.3 else None,  # 70% have stab
                    'osztaly': random.choice(classes) if random.random() > 0.2 else None  # 80% have class
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
