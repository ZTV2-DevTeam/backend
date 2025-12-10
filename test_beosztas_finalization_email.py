"""
Test script for Beosztás véglegesítve email notification.

This script tests the newly implemented email notification that is sent
when a Beosztás status changes from Piszkozat (kesz=False) to Kész (kesz=True).
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

# Try to load local settings if they exist
try:
    import local_settings
    os.environ['DJANGO_SETTINGS_MODULE'] = 'local_settings'
except ImportError:
    pass

django.setup()

from api.models import Beosztas, Forgatas, SzerepkorRelaciok, Szerepkor, User, Tanev
from datetime import date, time
from django.db import transaction


def test_beosztas_finalization_email():
    """Test Beosztás véglegesítve email notification."""
    
    print("🧪 Testing Beosztás Véglegesítve Email Notification")
    print("=" * 60)
    
    try:
        # Get test users with valid email addresses
        test_users = User.objects.filter(
            email__isnull=False,
            is_active=True
        ).exclude(email='')[:2]
        
        if len(test_users) < 1:
            print("❌ Error: Need at least 1 user with a valid email address")
            print("   Please ensure there are active users with email addresses in the database")
            return
        
        print(f"\n✅ Found {len(test_users)} test user(s) with valid emails:")
        for user in test_users:
            print(f"   - {user.get_full_name()} ({user.email})")
        
        # Get or create a test forgatas
        print("\n📋 Creating test forgatas...")
        
        active_tanev = Tanev.get_active()
        
        test_forgatas = Forgatas.objects.create(
            name="Test Forgatás - Véglegesítés Email Test",
            description="Ez egy teszt forgatás a véglegesítve email teszteléséhez",
            date=date.today(),
            timeFrom=time(14, 0),
            timeTo=time(16, 0),
            forgTipus="teszt",
            tanev=active_tanev
        )
        
        print(f"✅ Test forgatas created: {test_forgatas.name}")
        
        # Get or create test szerepkor
        print("\n👤 Getting test szerepkör...")
        
        test_szerepkor, created = Szerepkor.objects.get_or_create(
            name="Operatőr",
            defaults={'description': 'Kamera kezelő'}
        )
        
        print(f"✅ Using szerepkör: {test_szerepkor.name}")
        
        # Create szerepkor relációk for test users
        print("\n🔗 Creating szerepkör relációk...")
        
        szerepkor_relaciok = []
        for user in test_users:
            relacio, created = SzerepkorRelaciok.objects.get_or_create(
                user=user,
                szerepkor=test_szerepkor
            )
            szerepkor_relaciok.append(relacio)
            print(f"   - Created/found relacio for {user.get_full_name()}")
        
        # Create a Beosztás in PISZKOZAT state (kesz=False)
        print("\n📝 Creating Beosztás in PISZKOZAT state (kesz=False)...")
        
        with transaction.atomic():
            beosztas = Beosztas.objects.create(
                forgatas=test_forgatas,
                kesz=False,  # Start in Piszkozat state
                tanev=active_tanev
            )
            
            # Add the szerepkor relaciok to the beosztas
            beosztas.szerepkor_relaciok.add(*szerepkor_relaciok)
        
        print(f"✅ Beosztás created (ID: {beosztas.id}, kesz=False - PISZKOZAT)")
        print(f"   Assigned users: {len(szerepkor_relaciok)}")
        
        # Wait a moment for any signals to process
        import time as time_module
        time_module.sleep(1)
        
        # Now change status from PISZKOZAT to KÉSZ - this should trigger the email
        print("\n" + "=" * 60)
        print("🚀 CHANGING STATUS FROM PISZKOZAT TO KÉSZ")
        print("   This should trigger 'Beosztás véglegesítve' email...")
        print("=" * 60)
        
        with transaction.atomic():
            beosztas.kesz = True  # Change to Kész state
            beosztas.save()
        
        print(f"\n✅ Beosztás status changed to KÉSZ (ID: {beosztas.id})")
        print(f"   Email should be sent to {len(test_users)} user(s)")
        
        # Wait for email to be sent
        time_module.sleep(2)
        
        print("\n" + "=" * 60)
        print("🎉 Test Complete!")
        print("=" * 60)
        print("\n📧 Expected Results:")
        print("   • Email subject: 'FTV - Beosztás véglegesítve: Test Forgatás - Véglegesítés Email Test'")
        print("   • Recipients:")
        for user in test_users:
            print(f"     - {user.get_full_name()} ({user.email})")
        print("   • Email content: Detailed notification about assignment finalization")
        
        print("\n📝 Check the Django logs above for:")
        print("   • '[DEBUG] *** Beosztás status changed from Piszkozat to Kész'")
        print("   • '[SUCCESS] Beosztás véglegesítve email sent to X users'")
        
        print("\n🧹 Cleanup:")
        cleanup = input("Delete test data? (y/n): ").strip().lower()
        
        if cleanup == 'y':
            beosztas.delete()
            test_forgatas.delete()
            print("✅ Test data cleaned up")
        else:
            print(f"ℹ️  Test data kept - Beosztás ID: {beosztas.id}, Forgatas ID: {test_forgatas.id}")
        
    except Exception as e:
        print(f"\n❌ Error during test: {str(e)}")
        import traceback
        print(f"\n📋 Full traceback:")
        print(traceback.format_exc())


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Beosztás Véglegesítve Email Notification Test")
    print("=" * 60)
    print("\nThis test will:")
    print("1. Create a test Forgatas")
    print("2. Create a Beosztás in PISZKOZAT state (kesz=False)")
    print("3. Assign test users to the Beosztás")
    print("4. Change status to KÉSZ (kesz=True)")
    print("5. Verify that 'Beosztás véglegesítve' email is sent")
    print("\nPress Ctrl+C to cancel")
    
    try:
        input("\nPress Enter to start the test...\n")
        test_beosztas_finalization_email()
    except KeyboardInterrupt:
        print("\n\n❌ Test cancelled by user")
        sys.exit(0)
