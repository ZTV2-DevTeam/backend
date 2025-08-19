#!/usr/bin/env python
"""
Test script for CSV processing with Hungarian characters
"""

import os
import sys
import django

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from backend.api_modules.user_import_utils import parse_csv_file

def test_csv_processing():
    """Test CSV processing with Hungarian characters"""
    
    # Test CSV content with Hungarian characters and UTF-8 BOM
    test_csv_content = """vezetekNev,keresztNev,email,telefonszam,stab,kezdesEve,tagozat,radio,gyartasvezeto,mediatana,osztalyfonok,osztalyai
Kovács,János,kovacs.janos@example.com,06301234567,hangstab,2020,informatika,igen,nem,nem,nem,9.A
Nagy,Éva,nagy.eva@example.com,06309876543,grafikus,2019,media,nem,igen,nem,igen,10.B;11.C
Szabó,Péter,szabo.peter@example.com,,radio,2021,,igen,nem,igen,nem,
Tóth,Zsuzsanna,toth.zsuzsanna@example.com,06701234567,,,,,,,,"12.A;12.B"
""".strip()
    
    # Encode with UTF-8 BOM to simulate real file upload
    test_bytes = '\ufeff'.encode('utf-8') + test_csv_content.encode('utf-8')
    
    print("Testing CSV processing...")
    print("=" * 50)
    
    try:
        result = parse_csv_file(test_bytes)
        
        if result['success']:
            print(f"✅ Successfully parsed {len(result['parsed_users'])} users")
            print(f"📊 Summary: {result['summary']}")
            
            print("\n📋 Detailed model preview:")
            for category, items in result['model_preview'].items():
                if items:
                    print(f"\n{category.upper()}:")
                    for item in items:
                        print(f"  - {item}")
            
            print("\n👥 User details:")
            for i, user in enumerate(result['parsed_users'], 1):
                print(f"\n{i}. {user.vezetek_nev} {user.kereszt_nev}")
                print(f"   Email: {user.email}")
                print(f"   Telefon: {user.telefonszam or 'Nincs megadva'}")
                print(f"   Stab: {user.stab or 'Nincs megadva'}")
                print(f"   Osztályok: {', '.join(user.osztalyai) if user.osztalyai else 'Nincs megadva'}")
                
        else:
            print("❌ Parsing failed:")
            for error in result['errors']:
                print(f"  - {error}")
                
    except Exception as e:
        print(f"❌ Exception occurred: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_csv_processing()
