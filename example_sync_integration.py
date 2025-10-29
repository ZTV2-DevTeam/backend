"""
Example integration script for Igazoláskezelő

This script demonstrates how to integrate the FTV Sync API into Igazoláskezelő.
Shows practical examples of common sync operations.

Author: FTV Development Team
Date: October 29, 2024
"""

import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# ============================================================================
# Configuration
# ============================================================================

class FTVSyncConfig:
    """Configuration for FTV Sync API."""
    
    # API Settings
    BASE_URL = "https://ftvapi.szlg.info/api/sync"  # Production
    # BASE_URL = "http://localhost:8000/api/sync"  # Development
    
    # Security
    ACCESS_TOKEN = "your-secure-token-here-change-in-production"  # Change this!
    
    # Timeouts and Retries
    REQUEST_TIMEOUT = 10  # seconds
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds

# ============================================================================
# FTV Sync Client
# ============================================================================

class FTVSyncClient:
    """Client for interacting with FTV Sync API."""
    
    def __init__(self, config: FTVSyncConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {config.ACCESS_TOKEN}',
            'Content-Type': 'application/json'
        })
    
    def _make_request(self, endpoint: str, method: str = 'GET') -> Optional[Dict]:
        """Make an API request with retry logic."""
        url = f"{self.config.BASE_URL}{endpoint}"
        
        for attempt in range(1, self.config.MAX_RETRIES + 1):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    timeout=self.config.REQUEST_TIMEOUT
                )
                
                # Handle different status codes
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401:
                    raise Exception("Invalid access token - check configuration")
                elif response.status_code == 404:
                    return None  # Resource not found
                else:
                    raise Exception(f"HTTP {response.status_code}: {response.text}")
                    
            except requests.exceptions.Timeout:
                if attempt < self.config.MAX_RETRIES:
                    print(f"⚠️  Timeout on attempt {attempt}/{self.config.MAX_RETRIES}, retrying...")
                    continue
                raise Exception("Request timeout after multiple attempts")
            
            except requests.exceptions.ConnectionError:
                if attempt < self.config.MAX_RETRIES:
                    print(f"⚠️  Connection error on attempt {attempt}/{self.config.MAX_RETRIES}, retrying...")
                    continue
                raise Exception("Connection error - FTV API may be down")
        
        raise Exception(f"Failed after {self.config.MAX_RETRIES} attempts")
    
    # ========================================================================
    # User Profile Methods
    # ========================================================================
    
    def get_profile_by_email(self, email: str) -> Optional[Dict]:
        """
        Get user profile by email address.
        
        Args:
            email: User's email address
            
        Returns:
            Profile dictionary or None if not found
        """
        return self._make_request(f"/profile/{email}")
    
    # ========================================================================
    # Absence Methods
    # ========================================================================
    
    def get_user_absences(self, user_id: int) -> List[Dict]:
        """
        Get all absences for a specific user.
        
        Args:
            user_id: FTV user ID
            
        Returns:
            List of absence dictionaries
        """
        result = self._make_request(f"/hianyzasok/user/{user_id}")
        return result if result else []
    
    def get_class_absences(self, osztaly_id: int) -> List[Dict]:
        """
        Get all absences for a class.
        
        Args:
            osztaly_id: FTV class ID
            
        Returns:
            List of absence dictionaries
        """
        result = self._make_request(f"/hianyzasok/osztaly/{osztaly_id}")
        return result if result else []
    
    def get_absence(self, absence_id: int) -> Optional[Dict]:
        """
        Get specific absence details.
        
        Args:
            absence_id: FTV absence record ID
            
        Returns:
            Absence dictionary or None if not found
        """
        return self._make_request(f"/hianyzas/{absence_id}")
    
    # ========================================================================
    # Class Methods
    # ========================================================================
    
    def get_all_classes(self) -> List[Dict]:
        """
        Get all classes in FTV system.
        
        Returns:
            List of class dictionaries
        """
        result = self._make_request("/osztalyok")
        return result if result else []
    
    def get_class(self, osztaly_id: int) -> Optional[Dict]:
        """
        Get specific class details.
        
        Args:
            osztaly_id: FTV class ID
            
        Returns:
            Class dictionary or None if not found
        """
        return self._make_request(f"/osztaly/{osztaly_id}")

# ============================================================================
# Example Integration Functions
# ============================================================================

def example_sync_single_user(client: FTVSyncClient, email: str):
    """
    Example: Sync a single user's absences.
    
    This demonstrates the most common use case - syncing one user on demand.
    """
    print(f"\n{'='*80}")
    print(f"Syncing user: {email}")
    print('='*80)
    
    # Step 1: Find user in FTV
    print("\n1️⃣  Looking up user profile...")
    profile = client.get_profile_by_email(email)
    
    if not profile:
        print(f"❌ User not found in FTV system: {email}")
        return
    
    print(f"✅ Found user: {profile['full_name']}")
    print(f"   - User ID: {profile['user_id']}")
    print(f"   - Class: {profile['osztaly_name']}")
    print(f"   - Stab: {profile['stab_name']}")
    
    # Step 2: Get user's absences
    print("\n2️⃣  Fetching absences...")
    absences = client.get_user_absences(profile['user_id'])
    
    print(f"✅ Found {len(absences)} absence records")
    
    # Step 3: Process absences
    print("\n3️⃣  Processing absences...")
    
    if len(absences) == 0:
        print("   No absences to sync")
        return
    
    for idx, absence in enumerate(absences, 1):
        print(f"\n   Absence #{idx}:")
        print(f"   - Date: {absence['date']}")
        print(f"   - Time: {absence['timeFrom']} - {absence['timeTo']}")
        print(f"   - Status: {'Igazolt' if absence['excused'] else 'Igazolatlan' if absence['unexcused'] else 'Feldolgozás alatt'}")
        print(f"   - Affected periods: {', '.join(map(str, absence['affected_classes']))}")
        
        if absence['forgatas_details']:
            print(f"   - Filming session: {absence['forgatas_details']['name']}")
        
        # Here you would save to your database
        # save_absence_to_database(email, absence)
    
    print(f"\n✅ Successfully synced {len(absences)} absences for {profile['full_name']}")

def example_sync_entire_class(client: FTVSyncClient, osztaly_id: int):
    """
    Example: Sync all students in a class.
    
    This demonstrates batch syncing for a whole class.
    """
    print(f"\n{'='*80}")
    print(f"Syncing class ID: {osztaly_id}")
    print('='*80)
    
    # Step 1: Get class details
    print("\n1️⃣  Getting class details...")
    osztaly = client.get_class(osztaly_id)
    
    if not osztaly:
        print(f"❌ Class not found: {osztaly_id}")
        return
    
    print(f"✅ Found class: {osztaly['current_name']}")
    
    # Step 2: Get all absences for this class
    print("\n2️⃣  Fetching absences for entire class...")
    absences = client.get_class_absences(osztaly_id)
    
    print(f"✅ Found {len(absences)} total absence records")
    
    # Step 3: Group by student
    print("\n3️⃣  Grouping absences by student...")
    
    students = {}
    for absence in absences:
        email = absence['diak_email']
        if email not in students:
            students[email] = {
                'name': absence['diak_full_name'],
                'absences': []
            }
        students[email]['absences'].append(absence)
    
    print(f"✅ Found {len(students)} students with absences")
    
    # Step 4: Process each student
    print("\n4️⃣  Processing students...")
    
    for email, data in students.items():
        print(f"\n   Student: {data['name']} ({email})")
        print(f"   Absences: {len(data['absences'])}")
        
        # Here you would save to your database
        # save_student_absences(email, data['absences'])
    
    print(f"\n✅ Successfully synced {len(students)} students from class {osztaly['current_name']}")

def example_get_recent_absences(client: FTVSyncClient, email: str, days: int = 30):
    """
    Example: Get absences from the last N days.
    
    This demonstrates filtering absences by date range.
    """
    print(f"\n{'='*80}")
    print(f"Getting recent absences for: {email} (last {days} days)")
    print('='*80)
    
    # Step 1: Get user profile
    profile = client.get_profile_by_email(email)
    if not profile:
        print(f"❌ User not found: {email}")
        return
    
    print(f"✅ Found user: {profile['full_name']}")
    
    # Step 2: Get all absences
    absences = client.get_user_absences(profile['user_id'])
    
    # Step 3: Filter by date
    from datetime import date, timedelta
    cutoff_date = date.today() - timedelta(days=days)
    
    recent_absences = [
        a for a in absences 
        if datetime.strptime(a['date'], '%Y-%m-%d').date() >= cutoff_date
    ]
    
    print(f"✅ Found {len(recent_absences)} absences in last {days} days")
    
    for absence in recent_absences:
        print(f"\n   Date: {absence['date']}")
        print(f"   Time: {absence['timeFrom']} - {absence['timeTo']}")
        if absence['forgatas_details']:
            print(f"   Reason: {absence['forgatas_details']['name']}")

def example_check_user_availability(client: FTVSyncClient, email: str, check_date: str):
    """
    Example: Check if a user has absences on a specific date.
    
    This demonstrates checking availability.
    """
    print(f"\n{'='*80}")
    print(f"Checking availability for {email} on {check_date}")
    print('='*80)
    
    # Get user profile
    profile = client.get_profile_by_email(email)
    if not profile:
        print(f"❌ User not found: {email}")
        return
    
    # Get absences
    absences = client.get_user_absences(profile['user_id'])
    
    # Filter by date
    absences_on_date = [
        a for a in absences 
        if a['date'] == check_date
    ]
    
    if len(absences_on_date) == 0:
        print(f"✅ User is available on {check_date}")
    else:
        print(f"❌ User has {len(absences_on_date)} absence(s) on {check_date}:")
        for absence in absences_on_date:
            print(f"   - {absence['timeFrom']} - {absence['timeTo']}")
            if absence['forgatas_details']:
                print(f"     Reason: {absence['forgatas_details']['name']}")

def example_list_all_classes(client: FTVSyncClient):
    """
    Example: List all classes in the system.
    
    This demonstrates getting the class structure.
    """
    print(f"\n{'='*80}")
    print("Listing all classes")
    print('='*80)
    
    classes = client.get_all_classes()
    
    print(f"\n✅ Found {len(classes)} classes:")
    
    for osztaly in classes:
        print(f"\n   ID: {osztaly['id']}")
        print(f"   Name: {osztaly['current_name']}")
        print(f"   Section: {osztaly['szekcio']}")
        print(f"   Start Year: {osztaly['startYear']}")
        if osztaly['tanev_name']:
            print(f"   School Year: {osztaly['tanev_name']}")

# ============================================================================
# Main Demo
# ============================================================================

def main():
    """Run example integrations."""
    print("\n" + "="*80)
    print(" FTV Sync API - Example Integration Demo")
    print("="*80)
    
    # Initialize client
    config = FTVSyncConfig()
    client = FTVSyncClient(config)
    
    print(f"\nConnecting to: {config.BASE_URL}")
    print(f"Using token: {config.ACCESS_TOKEN[:20]}...")
    
    try:
        # Example 1: Sync single user
        # Uncomment and replace with real email to test
        # example_sync_single_user(client, "kovacs.janos@szlg.info")
        
        # Example 2: Sync entire class
        # Uncomment and replace with real class ID to test
        # example_sync_entire_class(client, osztaly_id=1)
        
        # Example 3: Get recent absences
        # Uncomment and replace with real email to test
        # example_get_recent_absences(client, "kovacs.janos@szlg.info", days=30)
        
        # Example 4: Check availability
        # Uncomment and replace with real email and date to test
        # example_check_user_availability(client, "kovacs.janos@szlg.info", "2024-10-30")
        
        # Example 5: List all classes (safe to run without data)
        example_list_all_classes(client)
        
        print("\n" + "="*80)
        print(" Demo complete!")
        print("="*80)
        print("\n💡 Tip: Uncomment the example functions above to test with real data")
        print("   Make sure to replace email addresses and IDs with actual values from your FTV system")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
