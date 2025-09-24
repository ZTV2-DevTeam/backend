#!/usr/bin/env python
"""
Test script to validate the enhanced absence creation functionality.
This script can be run in the Django shell to test the absence auto-creation.
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from api.models import *
from datetime import date, time

def test_absence_creation():
    """
    Test the enhanced absence creation functionality
    """
    print("=" * 60)
    print("TESTING ENHANCED ABSENCE CREATION FUNCTIONALITY")
    print("=" * 60)
    
    # Get or create test data
    print("\n1. Setting up test data...")
    
    # Get current tanev or create one
    current_tanev = Tanev.get_active()
    if not current_tanev:
        print("   Creating test tanev...")
        current_tanev = Tanev.objects.create(
            start_date=date(2025, 9, 1),
            end_date=date(2026, 6, 15)
        )
    print(f"   Using tanev: {current_tanev}")
    
    # Get or create a stab
    stab, _ = Stab.objects.get_or_create(name="Test Stáb")
    print(f"   Using stab: {stab}")
    
    # Get or create a partner for location
    partner_tipus, _ = PartnerTipus.objects.get_or_create(name="Teszt Intézmény")
    partner, _ = Partner.objects.get_or_create(
        name="Test Helyszín",
        defaults={'institution': partner_tipus}
    )
    print(f"   Using partner: {partner}")
    
    # Create test forgatas
    print("   Creating test forgatas...")
    forgatas = Forgatas.objects.create(
        name="Test Forgatás - Absence Creation",
        description="Test forgatás hiányzás létrehozás tesztelésére",
        date=date.today(),
        timeFrom=time(14, 0),
        timeTo=time(16, 0),
        location=partner,
        forgTipus='rendes',
        tanev=current_tanev
    )
    print(f"   Created forgatas: {forgatas}")
    
    # Get test users
    test_users = User.objects.filter(is_active=True)[:3]
    if len(test_users) < 2:
        print("   ERROR: Need at least 2 active users for testing")
        return
    
    user1, user2 = test_users[0], test_users[1]
    user3 = test_users[2] if len(test_users) > 2 else None
    
    print(f"   Using test users: {user1.get_full_name()}, {user2.get_full_name()}")
    if user3:
        print(f"   Additional user: {user3.get_full_name()}")
    
    # Create szerepkor and szerepkor relations
    print("   Creating test szerepkor...")
    szerepkor, _ = Szerepkor.objects.get_or_create(name="Test Szerepkör")
    
    relacio1 = SzerepkorRelaciok.objects.create(user=user1, szerepkor=szerepkor)
    relacio2 = SzerepkorRelaciok.objects.create(user=user2, szerepkor=szerepkor)
    
    print("\n2. Testing Beosztas creation with draft status...")
    
    # Create beosztas (draft by default)
    beosztas = Beosztas.objects.create(
        kesz=False,  # Start as draft
        forgatas=forgatas,
        stab=stab,
        tanev=current_tanev
    )
    print(f"   Created draft beosztas: {beosztas}")
    
    # Add szerepkor relations
    beosztas.szerepkor_relaciok.add(relacio1, relacio2)
    print(f"   Added {beosztas.szerepkor_relaciok.count()} szerepkor relations")
    
    # Check if absences were created
    absences = Absence.objects.filter(forgatas=forgatas, auto_generated=True)
    print(f"   Auto-generated absences created: {absences.count()}")
    
    for absence in absences:
        print(f"     - {absence.diak.get_full_name()}: {absence.date} {absence.timeFrom}-{absence.timeTo}")
    
    print("\n3. Testing beosztas finalization...")
    
    # Finalize beosztas
    beosztas.kesz = True
    beosztas.save()
    print("   Finalized beosztas")
    
    # Check absences again
    absences = Absence.objects.filter(forgatas=forgatas, auto_generated=True)
    print(f"   Auto-generated absences after finalization: {absences.count()}")
    
    print("\n4. Testing user addition...")
    
    if user3:
        # Add third user
        relacio3 = SzerepkorRelaciok.objects.create(user=user3, szerepkor=szerepkor)
        beosztas.szerepkor_relaciok.add(relacio3)
        print(f"   Added third user: {user3.get_full_name()}")
        
        # Check absences
        absences = Absence.objects.filter(forgatas=forgatas, auto_generated=True)
        print(f"   Auto-generated absences after adding user: {absences.count()}")
        
        for absence in absences:
            print(f"     - {absence.diak.get_full_name()}: {absence.date} {absence.timeFrom}-{absence.timeTo}")
    
    print("\n5. Testing forgatas timing change...")
    
    # Change forgatas timing
    forgatas.timeFrom = time(15, 0)
    forgatas.timeTo = time(17, 0)
    forgatas.save()
    print("   Changed forgatas timing to 15:00-17:00")
    
    # Check if absences were updated
    absences = Absence.objects.filter(forgatas=forgatas, auto_generated=True)
    print(f"   Auto-generated absences after timing change: {absences.count()}")
    
    for absence in absences:
        print(f"     - {absence.diak.get_full_name()}: {absence.date} {absence.timeFrom}-{absence.timeTo}")
    
    print("\n6. Testing user removal...")
    
    # Remove first user
    beosztas.szerepkor_relaciok.remove(relacio1)
    print(f"   Removed user: {user1.get_full_name()}")
    
    # Check absences
    absences = Absence.objects.filter(forgatas=forgatas, auto_generated=True)
    print(f"   Auto-generated absences after user removal: {absences.count()}")
    
    for absence in absences:
        print(f"     - {absence.diak.get_full_name()}: {absence.date} {absence.timeFrom}-{absence.timeTo}")
    
    # Check if removed user's absence was deleted
    user1_absences = Absence.objects.filter(forgatas=forgatas, diak=user1, auto_generated=True)
    print(f"   {user1.get_full_name()}'s auto absences remaining: {user1_absences.count()}")
    
    print("\n7. Testing sync_all_absence_records...")
    
    # Test bulk sync
    result = Beosztas.sync_all_absence_records()
    print(f"   Sync result: {result}")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)
    
    # Cleanup
    print("\nCleaning up test data...")
    beosztas.delete()
    forgatas.delete()
    relacio1.delete()
    relacio2.delete()
    if user3:
        relacio3.delete()
    
    print("Test cleanup completed.")

if __name__ == "__main__":
    test_absence_creation()