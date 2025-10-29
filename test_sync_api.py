"""
Test script for FTV Sync API endpoints

This script tests all sync API endpoints to ensure they work correctly.
Run this after implementing the sync API to verify functionality.

Usage:
    python test_sync_api.py
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000/api/sync"
TOKEN = "your-secure-token-here-change-in-production"  # Change this to match your local_settings.py

# Headers with authentication
headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)

def print_result(endpoint, status_code, success, data=None, error=None):
    """Print test result in a formatted way."""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"\n{status} | {endpoint}")
    print(f"Status Code: {status_code}")
    
    if error:
        print(f"Error: {error}")
    elif data:
        if isinstance(data, list):
            print(f"Returned {len(data)} items")
            if len(data) > 0:
                print(f"First item: {json.dumps(data[0], indent=2)}")
        else:
            print(f"Response: {json.dumps(data, indent=2)}")

def test_endpoint(method, endpoint, expected_status=200):
    """Test a single endpoint."""
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        else:
            return False, None, "Unsupported HTTP method"
        
        success = response.status_code == expected_status
        
        try:
            data = response.json()
        except:
            data = response.text
        
        return success, response.status_code, data
    
    except requests.exceptions.Timeout:
        return False, None, "Request timeout"
    except requests.exceptions.ConnectionError:
        return False, None, "Connection error - is the server running?"
    except Exception as e:
        return False, None, str(e)

def main():
    """Run all sync API tests."""
    print_section("FTV Sync API Test Suite")
    print(f"Testing against: {BASE_URL}")
    print(f"Using token: {TOKEN[:20]}...")
    
    all_passed = True
    
    # Test 1: Get all classes
    print_section("Test 1: GET /osztalyok - Get all classes")
    success, status, data = test_endpoint("GET", "/osztalyok")
    print_result("/osztalyok", status, success, data)
    all_passed = all_passed and success
    
    # Store first osztaly_id for later tests
    osztaly_id = None
    if success and isinstance(data, list) and len(data) > 0:
        osztaly_id = data[0]['id']
        print(f"\n📝 Using osztaly_id {osztaly_id} for subsequent tests")
    
    # Test 2: Get specific class (if we have an ID)
    if osztaly_id:
        print_section(f"Test 2: GET /osztaly/{osztaly_id} - Get specific class")
        success, status, data = test_endpoint("GET", f"/osztaly/{osztaly_id}")
        print_result(f"/osztaly/{osztaly_id}", status, success, data)
        all_passed = all_passed and success
    else:
        print_section("Test 2: SKIPPED - No osztaly_id available")
        print("⚠️  No classes found in system, create at least one class first")
    
    # Test 3: Get absences for class (if we have an ID)
    if osztaly_id:
        print_section(f"Test 3: GET /hianyzasok/osztaly/{osztaly_id} - Get absences for class")
        success, status, data = test_endpoint("GET", f"/hianyzasok/osztaly/{osztaly_id}")
        print_result(f"/hianyzasok/osztaly/{osztaly_id}", status, success, data)
        all_passed = all_passed and success
        
        # Store first absence_id and user_id for later tests
        absence_id = None
        user_id = None
        if success and isinstance(data, list) and len(data) > 0:
            absence_id = data[0]['id']
            user_id = data[0]['diak_id']
            print(f"\n📝 Using absence_id {absence_id} and user_id {user_id} for subsequent tests")
        
        # Test 4: Get specific absence (if we have an ID)
        if absence_id:
            print_section(f"Test 4: GET /hianyzas/{absence_id} - Get specific absence")
            success, status, data = test_endpoint("GET", f"/hianyzas/{absence_id}")
            print_result(f"/hianyzas/{absence_id}", status, success, data)
            all_passed = all_passed and success
        else:
            print_section("Test 4: SKIPPED - No absences found")
            print("ℹ️  No absences found for this class")
        
        # Test 5: Get absences for user (if we have a user_id)
        if user_id:
            print_section(f"Test 5: GET /hianyzasok/user/{user_id} - Get absences for user")
            success, status, data = test_endpoint("GET", f"/hianyzasok/user/{user_id}")
            print_result(f"/hianyzasok/user/{user_id}", status, success, data)
            all_passed = all_passed and success
        else:
            print_section("Test 5: SKIPPED - No user_id available")
            print("ℹ️  No absences found to get user_id from")
    else:
        print_section("Test 3-5: SKIPPED - No osztaly_id available")
    
    # Test 6: Get profile by email (we need to find an email first)
    print_section("Test 6: GET /profile/{email} - Get profile by email")
    
    # Try to find a user email from previous tests
    test_email = None
    if osztaly_id:
        # Try to get a user from class absences
        success_temp, status_temp, data_temp = test_endpoint("GET", f"/hianyzasok/osztaly/{osztaly_id}")
        if success_temp and isinstance(data_temp, list) and len(data_temp) > 0:
            test_email = data_temp[0]['diak_email']
    
    if test_email:
        success, status, data = test_endpoint("GET", f"/profile/{test_email}")
        print_result(f"/profile/{test_email}", status, success, data)
        all_passed = all_passed and success
    else:
        print("⚠️  No email address available for testing")
        print("ℹ️  Create a user with absence records to test this endpoint")
    
    # Test 7: Invalid token test
    print_section("Test 7: Authentication - Invalid token test")
    invalid_headers = {
        "Authorization": "Bearer invalid-token-should-fail",
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(f"{BASE_URL}/osztalyok", headers=invalid_headers, timeout=10)
        success = response.status_code == 401  # Should fail with 401
        print_result("/osztalyok (invalid token)", response.status_code, success, 
                    error="Expected 401 Unauthorized" if not success else None)
        if success:
            print("✅ Authentication properly rejects invalid tokens")
        all_passed = all_passed and success
    except Exception as e:
        print(f"❌ FAIL | Error testing invalid token: {e}")
        all_passed = False
    
    # Test 8: Test 404 handling
    print_section("Test 8: Error Handling - Non-existent resource")
    success, status, data = test_endpoint("GET", "/osztaly/99999", expected_status=404)
    print_result("/osztaly/99999 (non-existent)", status, success, data)
    if success:
        print("✅ Properly returns 404 for non-existent resources")
    all_passed = all_passed and success
    
    # Final summary
    print_section("Test Summary")
    if all_passed:
        print("🎉 All tests PASSED!")
        print("\n✅ Sync API is working correctly")
        print("✅ Authentication is working")
        print("✅ Error handling is correct")
        print("\nThe API is ready for Igazoláskezelő integration!")
    else:
        print("⚠️  Some tests FAILED")
        print("\n❌ Check the errors above and fix issues before integration")
        print("\nCommon issues:")
        print("  - Server not running (python manage.py runserver)")
        print("  - Token mismatch (check local_settings.py)")
        print("  - No data in database (create some test data first)")
        print("  - Database migrations not applied (python manage.py migrate)")
    
    return all_passed

if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
