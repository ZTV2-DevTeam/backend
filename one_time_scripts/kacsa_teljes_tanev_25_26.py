#!/usr/bin/env python
"""
KaCsa Teljes Tanév 2025-26 Parser Script

This script parses the KaCsa schedule for the 2025-26 school year and creates
Forgatás and Beosztás records in the Django database.

Usage:
    python manage.py shell
    exec(open('one_time_scripts/kacsa_teljes_tanev_25_26.py').read())

OR run directly from the script directory:
    python kacsa_teljes_tanev_25_26.py
"""

import os
import sys
import django
from datetime import datetime, date, time

# Django setup for standalone script execution
if __name__ == "__main__":
    # Add the parent directory to Python path to import Django settings
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    sys.path.append(parent_dir)
    
    # Setup Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
    django.setup()

# Import Django models after setup
from django.contrib.auth.models import User
from api.models import (
    Forgatas, Beosztas, Szerepkor, SzerepkorRelaciok, 
    Tanev, Stab, Partner, PartnerTipus
)

# ============================================================================
# NAME REGISTRY - MAP LITERAL NAMES TO USERNAMES
# ============================================================================

# TODO: Update this registry with actual usernames from your system
# Format: "Literal Name From Excel": "username_in_system"
NAME_REGISTRY = {
    # Szerkesztők és műsvezetők
    "Bercea Dóri": "bercea.dora.23f",
    "Aszódi Laura": "aszodi.laura.23f",
    "Bertalan Réka": "bertalan.reka.23f",
    "Boldizsár Lilla": "boldizsar.lilla.23f",
    "Bozsóki Áron": "bozsoki.aron.23f",
    "Csomós Dávid": "csomos.david.23f",
    "Földesi Amira": "foldesi.amira.23f",
    "Hargitai Kata": "hargitai.kata.23f",
    "Geibinger Félix": "geibinger.felix.23f",
    "Kalotai Fanni": "kalotai.fanni.23f",
    "Kocsis Ferenc": "kocsis.ferenc.23f",
    "Kassai Adél": "kassai.adel.23f",
    "Molnár Lili": "molnar.lili.23f",
    "Kátai Kornél": "katai.kornel.23f",
    "Ruby Luca": "ruby.luca.23f",
    "Richtseidt Alina": "richtseidt.alina.23f",
    "Sándor Zita": "sandor.zita.23f",
    "Horváth Renáta": "horvath.renata.23f",

    # Rendezők és stáb
    "Pásztor Lilien": "pasztor.lilien.22f",
    "Németh Lola": "nemeth.lola.22f",
    "Marton Ádám": "marton.adam.22f",
    "Botos Csenge": "botos.csenge.22f",
    "Konok Flóra": "konok.flora.22f",
    "Faludy Flóra": "faludy.flora.22f",
    "Hancz Johanna": "hancz.johanna.22f",
    "Bartha Dóri": "bartha.dora.22f",
    "Kapta Zétény": "kapta.zeteny.22f",

    # Bejátszók és technikusok
    "Diósi Attila": "diosi.attila.24f",
    "Homa-Bálint Kornélia": "homa-balint.kornelia.24f",
    "Gajzágó Anna": "gajzago.anna.24f",
    "Aczél Gergő": "aczel.gergo.24f",
    "Deutsch Levente": "deutsch.levente.24f",
    "Kristóf Eszter": "kristof.eszter.24f",
    "Váradi Szilárd": "varadi.szilard.24f",
    "Magyar Marcell": "magyar.marcell.24f",
    "Szabó-Kovács Kolos Gyula": "szabo-kovacs.kolos.24f",
    "Farkas Olivér": "farkas.oliver.24f",
    "Hricsovszky Milán": "hricsovszky.milan.24f",
    "Káldi Nóra": "kaldi.nora.24f",
    "Piatsek Zsófia": "piatsek.zsofia.24f",
    "Szokola Lina": "szokola.lina.24f",
    "Kruspier Kristóf": "kruspier.kristof.24f",
    "Vincze Ferenc": "vincze.ferenc.24f",
    "Barti Mira": "barti.mira.24f",
    "Mantz Lilla": "mantz.lilla.24f",

    # Asszisztensek
    "Csontos Kata": "csontos.kata.25f",
    "Fejes Gréta": "fejes.greta.25f",
    "Gábor Levente": "gabor.levente.25f",
    "Gelencsér Martin Bence": "gelencser.bence.25f",
    "Démi Zoltán István": "demi.zoltan.25f",
    "Gajdos Zétény Zalán": "gajdos.zeteny.25f",
    "Kis Kornélia Gabriella": "kis.kornelia.25f",
    "Szalma-Baksi Ábel": "szalma-baksi.abel.25f",
    "Faludy Blanka": "faludy.blanka.25f",
    "Szabó-Aross Misa": "szabo-aross.misa.25f",
    "Kovács Donát Ádám": "kovacs.donat.25f",
    "Takács Alexandra": "takacs.alexandra.25f",
    "Fülöp Ádám Tamás": "fulop.adam.25f",
    "Rózsa Krisztina": "rozsa.krisztina.25f",
    "Rábai Fruzsina": "rabai.fruzsina.25f",
    "Varga Dóra Eszter": "varga.dora.25f",
}

# ============================================================================
# KACSA SCHEDULE DATA
# ============================================================================

# Dates for each KaCsa session (A1, B1, A2, B2, etc.)
KACSA_DATES = [
    ("A1", date(2025, 9, 25)),
    ("B1", date(2025, 10, 9)),
    ("A2", date(2025, 10, 22)),
    ("B2", date(2025, 11, 13)),
    ("A3", date(2025, 11, 27)),
    ("B3", date(2025, 12, 11)),
    ("A4", date(2026, 1, 8)),
    ("B4", date(2026, 1, 22)),
    ("A5", date(2026, 2, 5)),
    ("B5", date(2026, 2, 19)),
    ("A6", date(2026, 3, 5)),
    ("B6", date(2026, 3, 19)),
    ("A7", date(2026, 4, 1)),
    ("B7", date(2026, 4, 23)),
    ("A8", date(2026, 5, 7)),
    ("B8", date(2026, 5, 21)),
    ("A9", date(2026, 6, 4)),
    ("B9", date(2026, 6, 11)),
]

# Role assignments for each session
# Format: List of (role_name, [people_per_session])
KACSA_ASSIGNMENTS = [
    ("Szerkesztő", [
        "Bercea Dóri", "Aszódi Laura", "Bertalan Réka", "Boldizsár Lilla", 
        "Bozsóki Áron", "Csomós Dávid", "Földesi Amira", "Hargitai Kata", 
        "Geibinger Félix", "Kalotai Fanni", "Kocsis Ferenc", "Kassai Adél", 
        "Molnár Lili", "Kátai Kornél", "Ruby Luca", "Richtseidt Alina", 
        "Sándor Zita", "Horváth Renáta"
    ]),
    ("Műsorvezető", [
        "Sándor Zita", "Richtseidt Alina", "Kocsis Ferenc", "Aszódi Laura", 
        "Bertalan Réka", "Kátai Kornél", "Bozsóki Áron", "Csomós Dávid", 
        "Földesi Amira", "Hargitai Kata", "Geibinger Félix", "Kalotai Fanni", 
        "Kocsis Ferenc", "Kassai Adél", "Molnár Lili", "Boldizsár Lilla", 
        "Ruby Luca", "Richtseidt Alina"
    ]),
    ("Műsorvezető", [
        "Pásztor Lilien", "Németh Lola", "Marton Ádám", "Botos Csenge", 
        "Konok Flóra", "Faludy Flóra", "Molnár Lili", "Kassai Adél", 
        "Bercea Dóri", "Boldizsár Lilla", "Bertalan Réka", "Kátai Kornél", 
        "Geibinger Félix", "Aszódi Laura", "Bozsóki Áron", "Hargitai Kata", 
        "Sándor Zita", "Csomós Dávid"
    ]),
    ("Látványtervező", [
        "Ruby Luca", "Richtseidt Alina", "Sándor Zita", "Kalotai Fanni", 
        "Bercea Dóri", "Aszódi Laura", "Bertalan Réka", "Boldizsár Lilla", 
        "Bozsóki Áron", "Csomós Dávid", "Földesi Amira", "Hargitai Kata", 
        "Geibinger Félix", "Horváth Renáta", "Kocsis Ferenc", "Kassai Adél", 
        "Molnár Lili", "Kátai Kornél"
    ]),
    ("Rendezőasszisztens", [
        "Aszódi Laura", "Földesi Amira", "Horváth Renáta", "Geibinger Félix", 
        "Boldizsár Lilla", "Molnár Lili", "Hargitai Kata", "Ruby Luca", 
        "Kalotai Fanni", "Sándor Zita", "Kassai Adél", "Bercea Dóri", 
        "Kátai Kornél", "Bertalan Réka", "Richtseidt Alina", "Bozsóki Áron", 
        "Csomós Dávid", "Kocsis Ferenc"
    ]),
    ("Rendező", [
        "Botos Csenge", "Hancz Johanna", "Pásztor Lilien", "Konok Flóra", 
        "Bartha Dóri", "Marton Ádám", "Boldizsár Lilla", "Molnár Lili", 
        "Hargitai Kata", "Ruby Luca", "Kalotai Fanni", "Sándor Zita", 
        "Kassai Adél", "Bercea Dóri", "Kátai Kornél", "Bertalan Réka", 
        "Richtseidt Alina", "Bozsóki Áron"
    ]),
    ("Vezető operatőr", [
        "Hancz Johanna", "Bartha Dóri", "Faludy Flóra", "Németh Lola", 
        "Kapta Zétény", "Pásztor Lilien", "Richtseidt Alina", "Bozsóki Áron", 
        "Boldizsár Lilla", "Molnár Lili", "Hargitai Kata", "Ruby Luca", 
        "Kalotai Fanni", "Sándor Zita", "Kassai Adél", "Bercea Dóri", 
        "Kátai Kornél", "Bertalan Réka"
    ]),
    ("Képvágó", [
        "Kátai Kornél", "Bertalan Réka", "Aszódi Laura", "Bozsóki Áron", 
        "Csomós Dávid", "Földesi Amira", "Horváth Renáta", "Geibinger Félix", 
        "Richtseidt Alina", "Kocsis Ferenc", "Boldizsár Lilla", "Molnár Lili", 
        "Hargitai Kata", "Ruby Luca", "Kalotai Fanni", "Sándor Zita", 
        "Kassai Adél", "Bercea Dóri"
    ]),
    ("Hangmérnök", [
        "Kassai Adél", "Bercea Dóri", "Kátai Kornél", "Bertalan Réka", 
        "Aszódi Laura", "Bozsóki Áron", "Csomós Dávid", "Földesi Amira", 
        "Horváth Renáta", "Geibinger Félix", "Richtseidt Alina", "Kocsis Ferenc", 
        "Boldizsár Lilla", "Molnár Lili", "Hargitai Kata", "Ruby Luca", 
        "Kalotai Fanni", "Sándor Zita"
    ]),
    ("Bejátszó-mentor", [
        "Kalotai Fanni", "Bozsóki Áron", "Kassai Adél", "Bercea Dóri", 
        "Kátai Kornél", "Bertalan Réka", "Aszódi Laura", "Sándor Zita", 
        "Csomós Dávid", "Földesi Amira", "Horváth Renáta", "Geibinger Félix", 
        "Richtseidt Alina", "Kocsis Ferenc", "Boldizsár Lilla", "Molnár Lili", 
        "Hargitai Kata", "Ruby Luca"
    ]),
    ("Feliratozó-mentor", [
        "Hargitai Kata", "Ruby Luca", "Kalotai Fanni", "Sándor Zita", 
        "Kassai Adél", "Bercea Dóri", "Kátai Kornél", "Bertalan Réka", 
        "Aszódi Laura", "Bozsóki Áron", "Csomós Dávid", "Földesi Amira", 
        "Horváth Renáta", "Geibinger Félix", "Richtseidt Alina", "Kocsis Ferenc", 
        "Boldizsár Lilla", "Molnár Lili"
    ]),
    ("Technikus", [
        "Boldizsár Lilla", "Molnár Lili", "Richtseidt Alina", "Ruby Luca", 
        "Kalotai Fanni", "Sándor Zita", "Kassai Adél", "Bercea Dóri", 
        "Kátai Kornél", "Bertalan Réka", "Aszódi Laura", "Bozsóki Áron", 
        "Csomós Dávid", "Földesi Amira", "Horváth Renáta", "Geibinger Félix", 
        "Hargitai Kata", "Kocsis Ferenc"
    ]),
    ("Technikus", [
        "Richtseidt Alina", "Sándor Zita", "Boldizsár Lilla", "Molnár Lili", 
        "Hargitai Kata", "Ruby Luca", "Kalotai Fanni", "Kocsis Ferenc", 
        "Kassai Adél", "Bercea Dóri", "Kátai Kornél", "Bertalan Réka", 
        "Aszódi Laura", "Bozsóki Áron", "Csomós Dávid", "Földesi Amira", 
        "Horváth Renáta", "Geibinger Félix"
    ]),
    ("Bejátszó", [
        "Diósi Attila", "Homa-Bálint Kornélia", "Gajzágó Anna", "Aczél Gergő", 
        "Deutsch Levente", "Kristóf Eszter", "Váradi Szilárd", "Magyar Marcell", 
        "Szabó-Kovács Kolos Gyula", "Farkas Olivér", "Hricsovszky Milán", "Káldi Nóra", 
        "Piatsek Zsófia", "Szokola Lina", "Kruspier Kristóf", "Vincze Ferenc", 
        "Barti Mira", "Mantz Lilla"
    ]),
    ("Feliratozó", [
        "Farkas Olivér", "Hricsovszky Milán", "Káldi Nóra", "Barti Mira", 
        "Szokola Lina", "Kruspier Kristóf", "Vincze Ferenc", "Piatsek Zsófia", 
        "Mantz Lilla", "Gajzágó Anna", "Homa-Bálint Kornélia", "Aczél Gergő", 
        "Diósi Attila", "Deutsch Levente", "Kristóf Eszter", "Váradi Szilárd", 
        "Magyar Marcell", "Szabó-Kovács Kolos Gyula"
    ]),
    ("Operatőr", [
        "Aczél Gergő", "Káldi Nóra", "Homa-Bálint Kornélia", "Kristóf Eszter", 
        "Mantz Lilla", "Szokola Lina", "Aczél Gergő", "Káldi Nóra", 
        "Homa-Bálint Kornélia", "Kristóf Eszter", "Mantz Lilla", "Szokola Lina", 
        "Aczél Gergő", "Káldi Nóra", "Homa-Bálint Kornélia", "Kristóf Eszter", 
        "Mantz Lilla", "Szokola Lina"
    ]),
    ("Operatőr", [
        "Barti Mira", "Farkas Olivér", "Hricsovszky Milán", "Kruspier Kristóf", 
        "Piatsek Zsófia", "Váradi Szilárd", "Barti Mira", "Farkas Olivér", 
        "Hricsovszky Milán", "Kruspier Kristóf", "Piatsek Zsófia", "Váradi Szilárd", 
        "Barti Mira", "Farkas Olivér", "Hricsovszky Milán", "Kruspier Kristóf", 
        "Piatsek Zsófia", "Váradi Szilárd"
    ]),
    ("Operatőr", [
        "Deutsch Levente", "Gajzágó Anna", "Diósi Attila", "Magyar Marcell", 
        "Szabó-Kovács Kolos Gyula", "Vincze Ferenc", "Deutsch Levente", "Gajzágó Anna", 
        "Diósi Attila", "Magyar Marcell", "Szabó-Kovács Kolos Gyula", "Vincze Ferenc", 
        "Deutsch Levente", "Gajzágó Anna", "Diósi Attila", "Magyar Marcell", 
        "Szabó-Kovács Kolos Gyula", "Vincze Ferenc"
    ]),
    ("Asszisztens", [
        "Csontos Kata", "Fejes Gréta", "Gábor Levente", "Gelencsér Martin Bence", 
        "Csontos Kata", "Fejes Gréta", "Gábor Levente", "Gelencsér Martin Bence", 
        "Csontos Kata", "Fejes Gréta", "Gábor Levente", "Gelencsér Martin Bence", 
        "Csontos Kata", "Fejes Gréta", "Gábor Levente", "Gelencsér Martin Bence", 
        "Fejes Gréta", "Csontos Kata"
    ]),
    ("Asszisztens", [
        "Démi Zoltán István", "Gajdos Zétény Zalán", "Kis Kornélia Gabriella", "Szalma-Baksi Ábel", 
        "Démi Zoltán István", "Gajdos Zétény Zalán", "Kis Kornélia Gabriella", "Szalma-Baksi Ábel", 
        "Démi Zoltán István", "Gajdos Zétény Zalán", "Kis Kornélia Gabriella", "Szalma-Baksi Ábel", 
        "Démi Zoltán István", "Gajdos Zétény Zalán", "Kis Kornélia Gabriella", "Szalma-Baksi Ábel", 
        "Gajdos Zétény Zalán", "Démi Zoltán István"
    ]),
    ("Asszisztens", [
        "Faludy Blanka", "Szabó-Aross Misa", "Kovács Donát Ádám", "Takács Alexandra", 
        "Faludy Blanka", "Szabó-Aross Misa", "Kovács Donát Ádám", "Takács Alexandra", 
        "Faludy Blanka", "Szabó-Aross Misa", "Kovács Donát Ádám", "Takács Alexandra", 
        "Faludy Blanka", "Szabó-Aross Misa", "Kovács Donát Ádám", "Takács Alexandra", 
        "Szabó-Aross Misa", "Faludy Blanka"
    ]),
    ("Asszisztens", [
        "Fülöp Ádám Tamás", "Rózsa Krisztina", "Rábai Fruzsina", "Varga Dóra Eszter", 
        "Fülöp Ádám Tamás", "Rózsa Krisztina", "Rábai Fruzsina", "Varga Dóra Eszter", 
        "Fülöp Ádám Tamás", "Rózsa Krisztina", "Rábai Fruzsina", "Varga Dóra Eszter", 
        "Fülöp Ádám Tamás", "Rózsa Krisztina", "Rábai Fruzsina", "Varga Dóra Eszter", 
        "Rózsa Krisztina", "Fülöp Ádám Tamás"
    ]),
]

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_user_by_name(literal_name):
    """
    Get Django User object by literal name using the name registry.
    Returns None if name not found in registry or user doesn't exist.
    """
    username = NAME_REGISTRY.get(literal_name)
    if not username:
        print(f"⚠️  WARNING: No username mapping found for '{literal_name}'")
        return None
    
    try:
        user = User.objects.get(username=username)
        return user
    except User.DoesNotExist:
        print(f"⚠️  WARNING: User '{username}' not found in database (mapped from '{literal_name}')")
        return None

def get_or_create_szerepkor(role_name):
    """
    Get or create a Szerepkor (role) object.
    """
    szerepkor, created = Szerepkor.objects.get_or_create(
        name=role_name,
        defaults={'ev': None}  # No specific year for KaCsa roles
    )
    if created:
        print(f"✅ Created new role: {role_name}")
    return szerepkor

def get_current_tanev():
    """
    Get the current school year (tanév) for 2025-26.
    Creates it if it doesn't exist.
    """
    try:
        # Try to find existing school year for 2025-2026
        tanev = Tanev.objects.get(start_date__year=2025, end_date__year=2026)
        return tanev
    except Tanev.DoesNotExist:
        # Create new school year for 2025-2026
        tanev = Tanev.objects.create(
            start_date=date(2025, 9, 1),
            end_date=date(2026, 6, 15)
        )
        print(f"✅ Created new school year: {tanev}")
        return tanev

def get_default_stab():
    """
    Get or create a default stab for KaCsa assignments.
    """
    stab, created = Stab.objects.get_or_create(
        name="KaCsa Stáb",
        defaults={}
    )
    if created:
        print(f"✅ Created new stab: {stab.name}")
    return stab

def get_kacsa_studio_location():
    """
    Get or create the KaCsa studio location as a Partner.
    """
    partner, created = Partner.objects.get_or_create(
        name="SZLG - Műterem",
        defaults={
            'address': "1102 Budapest, Kőrösi Csoma Sándor út 28-34.",
            'institution': PartnerTipus.objects.get_or_create(name='Házon belül')[0],
            'imgUrl': None
        }
    )
    if created:
        print(f"✅ Created new partner location: {partner.name}")
    return partner

# ============================================================================
# MAIN PROCESSING FUNCTIONS
# ============================================================================

def create_kacsa_forgatas(session_name, session_date):
    """
    Create a KaCsa Forgatás record for a specific session.
    """
    # Default KaCsa timing (can be adjusted as needed)
    default_start_time = time(15, 15)  # 3:15 PM
    default_end_time = time(18, 0)    # 6:00 PM
    
    tanev = get_current_tanev()
    location = get_kacsa_studio_location()
    
    # Check if this forgatás already exists
    existing_forgatas = Forgatas.objects.filter(
        name__icontains=session_name,
        start_time__date=session_date,
        forgTipus='kacsa'
    ).first()
    
    if existing_forgatas:
        print(f"⚠️  Forgatás already exists: {existing_forgatas.name} on {session_date}")
        return existing_forgatas
    
    # Create new KaCsa forgatás
    forgatas = Forgatas.objects.create(
        name=f"KaCsa {session_name}",
        description=f"KaCsa {session_name} - Kamasz Csatorna című műsor összejátszása a Padláson. Körősi szárny, Padlás (4. emelet) - Műterem",
        start_time=datetime.combine(session_date, default_start_time),
        end_time=datetime.combine(session_date, default_end_time),
        location=location,
        forgTipus='kacsa',
        tanev=tanev,
        szerkeszto=None,  # Will be set based on assignment
        contactPerson=None,
        notes=f"Automatikusan generálva a 2025-26 tanévi KaCsa ütemtervből",
        relatedKaCsa=None
    )
    
    print(f"✅ Created KaCsa forgatás: {forgatas.name} on {session_date}")
    return forgatas

def create_beosztas_for_session(forgatas, session_index):
    """
    Create a Beosztás (assignment) record for a KaCsa session.
    """
    tanev = get_current_tanev()
    stab = get_default_stab()
    
    # Check if beosztás already exists for this forgatás
    existing_beosztas = Beosztas.objects.filter(forgatas=forgatas).first()
    if existing_beosztas:
        print(f"⚠️  Beosztás already exists for: {forgatas.name}")
        return existing_beosztas
    
    # Create new beosztás
    beosztas = Beosztas.objects.create(
        kesz=False,  # Not finalized yet - you can review before marking as complete
        author=None,  # Will be set when finalized
        tanev=tanev,
        forgatas=forgatas,
        stab=stab
    )
    
    print(f"✅ Created beosztás for: {forgatas.name}")
    
    # Create role assignments for this session
    create_role_assignments(beosztas, session_index)
    
    return beosztas

def create_role_assignments(beosztas, session_index):
    """
    Create SzerepkorRelaciok records for a specific session.
    """
    created_assignments = 0
    failed_assignments = 0
    
    for role_name, assigned_people in KACSA_ASSIGNMENTS:
        if session_index >= len(assigned_people):
            print(f"⚠️  WARNING: No assignment for {role_name} in session {session_index}")
            continue
        
        literal_name = assigned_people[session_index]
        user = get_user_by_name(literal_name)
        
        if not user:
            print(f"❌ Failed to assign {literal_name} to {role_name} (user not found)")
            failed_assignments += 1
            continue
        
        # Get or create the role
        szerepkor = get_or_create_szerepkor(role_name)
        
        # Check if this assignment already exists
        existing_assignment = SzerepkorRelaciok.objects.filter(
            user=user,
            szerepkor=szerepkor
        ).first()
        
        if existing_assignment:
            # Check if it's already connected to this beosztás
            if existing_assignment.beosztasok.filter(id=beosztas.id).exists():
                print(f"⚠️  Assignment already exists: {user.get_full_name()} -> {role_name}")
                continue
            else:
                # Use existing assignment relation
                beosztas.szerepkor_relaciok.add(existing_assignment)
                print(f"🔗 Linked existing assignment: {user.get_full_name()} -> {role_name}")
                created_assignments += 1
        else:
            # Create new role relation
            szerepkor_relacio = SzerepkorRelaciok.objects.create(
                user=user,
                szerepkor=szerepkor
            )
            
            # Add to beosztás
            beosztas.szerepkor_relaciok.add(szerepkor_relacio)
            print(f"✅ Created assignment: {user.get_full_name()} -> {role_name}")
            created_assignments += 1
    
    print(f"📊 Session assignments summary: {created_assignments} created, {failed_assignments} failed")
    return created_assignments, failed_assignments

def finalize_beosztas(beosztas, editor_user=None):
    """
    Finalize a beosztás by marking it as complete and setting the author.
    """
    if beosztas.kesz:
        print(f"⚠️  Beosztás already finalized: {beosztas.forgatas.name}")
        return beosztas
    
    beosztas.kesz = True
    beosztas.author = editor_user
    beosztas.save()
    
    print(f"🎯 Finalized beosztás: {beosztas.forgatas.name}")
    return beosztas

# ============================================================================
# MAIN EXECUTION FUNCTION
# ============================================================================

def process_kacsa_schedule(dry_run=True, auto_finalize=False, skip_confirmation=False):
    """
    Main function to process the entire KaCsa schedule for 2025-26.
    
    Args:
        dry_run (bool): If True, only show what would be created without making changes
        auto_finalize (bool): If True, automatically mark all beosztások as complete
        skip_confirmation (bool): If True, skip user confirmation step (for automated use)
    """
    # STEP 1: Always validate all data first
    print("🔍 STEP 1: VALIDATING ALL DATA")
    print("=" * 60)
    
    total_sessions = len(KACSA_DATES)
    total_assignments = 0
    total_failed = 0
    validation_results = []
    
    print(f"🎬 Validating {total_sessions} KaCsa sessions for 2025-26 school year")
    print("=" * 60)
    
    # Validate each session and collect results
    for i, (session_name, session_date) in enumerate(KACSA_DATES):
        print(f"\n📅 Validating session {i+1}/{total_sessions}: {session_name} ({session_date})")
        print("-" * 40)
        
        session_assignment_count = 0
        session_failed = 0
        session_details = {
            'name': session_name,
            'date': session_date,
            'assignments': [],
            'failed_assignments': []
        }
        
        for role_name, assigned_people in KACSA_ASSIGNMENTS:
            if i < len(assigned_people):
                literal_name = assigned_people[i]
                user = get_user_by_name(literal_name)
                if user:
                    session_assignment_count += 1
                    session_details['assignments'].append({
                        'role': role_name,
                        'person': literal_name,
                        'username': user.username,
                        'full_name': user.get_full_name()
                    })
                    print(f"✅ {role_name}: {literal_name} -> {user.username}")
                else:
                    session_failed += 1
                    session_details['failed_assignments'].append({
                        'role': role_name,
                        'person': literal_name
                    })
                    print(f"❌ {role_name}: {literal_name} -> USER NOT FOUND")
            else:
                session_failed += 1
                session_details['failed_assignments'].append({
                    'role': role_name,
                    'person': 'NO ASSIGNMENT'
                })
                print(f"❌ {role_name}: NO ASSIGNMENT FOR SESSION {i}")
        
        total_assignments += session_assignment_count
        total_failed += session_failed
        validation_results.append(session_details)
        
        print(f"📊 Session validation: {session_assignment_count} valid, {session_failed} failed")
    
    # STEP 2: Show validation summary
    print("\n" + "=" * 60)
    print("📈 VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Total sessions: {total_sessions}")
    print(f"Total valid assignments: {total_assignments}")
    print(f"Total failed assignments: {total_failed}")
    
    if total_failed > 0:
        print(f"\n❌ VALIDATION FAILED: {total_failed} assignments have issues")
        print("Please fix the following issues before proceeding:")
        for session in validation_results:
            if session['failed_assignments']:
                print(f"\n📅 {session['name']} ({session['date']}):")
                for failed in session['failed_assignments']:
                    print(f"   ❌ {failed['role']}: {failed['person']}")
        print(f"\n⛔ Cannot proceed with data creation until all issues are resolved.")
        return False
    
    print(f"\n✅ VALIDATION PASSED: All {total_assignments} assignments are valid!")
    
    # STEP 3: User confirmation (unless skipped or dry run)
    if dry_run:
        print("\n🔍 DRY RUN MODE - This was a validation preview only")
        print("To actually create the data, run: process_kacsa_schedule(dry_run=False)")
        return True
    
    if not skip_confirmation:
        print("\n" + "=" * 60)
        print("⚠️  CONFIRMATION REQUIRED")
        print("=" * 60)
        print("You are about to create the following records in the database:")
        print(f"  - {total_sessions} KaCsa Forgatás records")
        print(f"  - {total_sessions} Beosztás records")
        print(f"  - {total_assignments} role assignments")
        print(f"  - Time period: {KACSA_DATES[0][1]} to {KACSA_DATES[-1][1]}")
        
        if auto_finalize:
            print(f"  - All beosztások will be automatically FINALIZED")
        else:
            print(f"  - Beosztások will be created as DRAFT (not finalized)")
        
        print("\nThis action cannot be easily undone!")
        print("\nTo proceed, type exactly: CREATE_KACSA_SCHEDULE_2025_26")
        print("To cancel, type anything else or press Ctrl+C")
        
        try:
            user_input = input("\nYour confirmation: ").strip()
            if user_input != "CREATE_KACSA_SCHEDULE_2025_26":
                print("❌ Confirmation failed. Operation cancelled.")
                return False
            print("✅ Confirmation received. Proceeding with data creation...")
        except KeyboardInterrupt:
            print("\n❌ Operation cancelled by user.")
            return False
        except EOFError:
            print("\n❌ No input received. Operation cancelled.")
            return False
    
    # STEP 4: Actually create the data
    print("\n" + "=" * 60)
    print("� CREATING DATABASE RECORDS")
    print("=" * 60)
    
    created_sessions = 0
    created_assignments = 0
    
    for i, (session_name, session_date) in enumerate(KACSA_DATES):
        print(f"\n📅 Creating session {i+1}/{total_sessions}: {session_name} ({session_date})")
        print("-" * 40)
        
        try:
            # Create Forgatás
            forgatas = create_kacsa_forgatas(session_name, session_date)
            
            # Create Beosztás with assignments
            beosztas = create_beosztas_for_session(forgatas, i)
            
            # Count assignments for this session
            session_assignments = beosztas.szerepkor_relaciok.count()
            created_assignments += session_assignments
            created_sessions += 1
            
            # Auto-finalize if requested
            if auto_finalize:
                finalize_beosztas(beosztas)
            
            print(f"✅ Completed session {session_name}: {session_assignments} assignments created")
            
        except Exception as e:
            print(f"❌ Error creating session {session_name}: {str(e)}")
            print(f"⚠️  Continuing with remaining sessions...")
    
    # STEP 5: Final summary
    print("\n" + "=" * 60)
    print("🎯 CREATION COMPLETE")
    print("=" * 60)
    print(f"Successfully created:")
    print(f"  - {created_sessions}/{total_sessions} KaCsa sessions")
    print(f"  - {created_assignments} role assignments")
    
    if auto_finalize:
        print(f"  - All beosztások have been FINALIZED")
    else:
        print(f"  - Beosztások created as DRAFT (review and finalize in Django admin)")
    
    print(f"\n✅ KaCsa schedule for 2025-26 has been successfully created!")
    return True

def validate_name_registry():
    """
    Validate the name registry by checking if all mapped users exist in the database.
    """
    print("🔍 Validating name registry...")
    print("=" * 50)
    
    missing_users = []
    existing_users = []
    
    for literal_name, username in NAME_REGISTRY.items():
        try:
            user = User.objects.get(username=username)
            existing_users.append((literal_name, username, user.get_full_name()))
        except User.DoesNotExist:
            missing_users.append((literal_name, username))
    
    print(f"✅ Found {len(existing_users)} existing users")
    if missing_users:
        print(f"❌ Missing {len(missing_users)} users:")
        for literal_name, username in missing_users:
            print(f"   - {literal_name} -> {username}")
    
    print("\n📊 Validation Summary:")
    print(f"   Total mapped names: {len(NAME_REGISTRY)}")
    print(f"   Existing users: {len(existing_users)}")
    print(f"   Missing users: {len(missing_users)}")
    
    if missing_users:
        print(f"\n⚠️  Please create missing users or update the NAME_REGISTRY mapping")
        return False
    else:
        print(f"\n✅ All users in registry exist in database!")
        return True

# ============================================================================
# SCRIPT EXECUTION
# ============================================================================

if __name__ == "__main__":
    print("🎯 KaCsa Teljes Tanév 2025-26 Parser")
    print("=" * 50)
    
    # First validate the name registry
    validation_passed = validate_name_registry()
    
    if validation_passed:
        print(f"\n🚀 Ready to process KaCsa schedule!")
        print("Run one of these commands:")
        print("  process_kacsa_schedule(dry_run=True)   # Validate and preview only")
        print("  process_kacsa_schedule(dry_run=False)  # Validate, confirm, then create data")
        print("  process_kacsa_schedule(dry_run=False, auto_finalize=True)  # Create and auto-finalize")
        print("  process_kacsa_schedule(dry_run=False, skip_confirmation=True)  # Skip confirmation prompt")
    else:
        print(f"\n⛔ Please fix the name registry before proceeding")

# Example usage when run through Django shell:
# exec(open('one_time_scripts/kacsa_teljes_tanev_25_26.py').read())
# validate_name_registry()
# process_kacsa_schedule(dry_run=True)   # First: validate and preview
# process_kacsa_schedule(dry_run=False)  # Then: create with confirmation