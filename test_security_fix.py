#!/usr/bin/env python3
"""
Security Test: SL-1 Fix Verification
=====================================
Tests that doctor role registration requires valid invite code.
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def print_test(name, passed):
    """Print test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {name}")

def test_doctor_registration_without_invite_code():
    """Test 1: Doctor registration should FAIL without invite code."""
    print("\n--- Test 1: Doctor registration WITHOUT invite code ---")
    
    response = requests.post(f"{BASE_URL}/auth/register", json={
        "email": f"attacker_{datetime.now().timestamp()}@evil.com",
        "password": "password123",
        "full_name": "Attacker",
        "role": "doctor",
        "specialization": "None"
    })
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    passed = response.status_code == 403
    print_test("Blocked unauthorized doctor registration", passed)
    return passed

def test_doctor_registration_with_invalid_code():
    """Test 2: Doctor registration should FAIL with invalid invite code."""
    print("\n--- Test 2: Doctor registration WITH INVALID invite code ---")
    
    response = requests.post(f"{BASE_URL}/auth/register", json={
        "email": f"attacker_{datetime.now().timestamp()}@evil.com",
        "password": "password123",
        "full_name": "Attacker",
        "role": "doctor",
        "invite_code": "invalid_fake_code_123",
        "specialization": "None"
    })
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    passed = response.status_code == 403
    print_test("Blocked registration with invalid invite code", passed)
    return passed

def test_generate_and_use_invite_code():
    """Test 3: Valid invite code should ALLOW registration."""
    print("\n--- Test 3: Generate invite code and register ---")
    
    # Step 1: Generate invite code
    print("Generating invite code...")
    gen_response = requests.post(f"{BASE_URL}/admin/invite-codes/generate", json={
        "role": "doctor",
        "count": 1,
        "expires_days": 1
    })
    
    if gen_response.status_code != 200:
        print(f"Failed to generate invite code: {gen_response.status_code}")
        return False
    
    codes = gen_response.json()["codes"]
    invite_code = codes[0]
    print(f"Generated invite code: {invite_code[:16]}...")
    
    # Step 2: Register with valid code
    print("Registering with valid invite code...")
    reg_response = requests.post(f"{BASE_URL}/auth/register", json={
        "email": f"legitimate_doctor_{datetime.now().timestamp()}@hospital.com",
        "password": "SecurePass123",
        "full_name": "Dr. Jane Smith",
        "role": "doctor",
        "invite_code": invite_code,
        "specialization": "Obstetrics",
        "license_number": "MD12345"
    })
    
    print(f"Status: {reg_response.status_code}")
    if reg_response.status_code == 201:
        print(f"✅ Registration successful!")
        print(f"User ID: {reg_response.json().get('user_id')}")
    else:
        print(f"Response: {reg_response.json()}")
    
    passed = reg_response.status_code == 201
    print_test("Allowed registration with valid invite code", passed)
    
    # Step 3: Try to reuse same code
    print("\nAttempting to reuse invite code...")
    reuse_response = requests.post(f"{BASE_URL}/auth/register", json={
        "email": f"attacker_reuse_{datetime.now().timestamp()}@evil.com",
        "password": "password123",
        "full_name": "Attacker Reuse",
        "role": "doctor",
        "invite_code": invite_code  # Same code
    })
    
    print(f"Status: {reuse_response.status_code}")
    print(f"Response: {reuse_response.json()}")
    
    reuse_blocked = reuse_response.status_code == 403
    print_test("Blocked reuse of same invite code", reuse_blocked)
    
    return passed and reuse_blocked

def test_asha_registration_no_code_needed():
    """Test 4: ASHA registration should work WITHOUT invite code."""
    print("\n--- Test 4: ASHA registration (no invite code needed) ---")
    
    response = requests.post(f"{BASE_URL}/auth/register", json={
        "email": f"asha_worker_{datetime.now().timestamp()}@field.org",
        "password": "SecurePass123",
        "full_name": "Sarah Worker",
        "role": "asha",
        "age": 28,
        "gestational_weeks": 24
    })
    
    print(f"Status: {response.status_code}")
    if response.status_code == 201:
        print(f"✅ ASHA registration successful (no invite code required)")
    else:
        print(f"Response: {response.json()}")
    
    passed = response.status_code == 201
    print_test("ASHA registration works without invite code", passed)
    return passed

def main():
    """Run all security tests."""
    print("="*70)
    print("Security Test Suite: SL-1 Fix Verification")
    print("="*70)
    
    results = []
    
    try:
        # Test unauthorized attempts
        results.append(test_doctor_registration_without_invite_code())
        results.append(test_doctor_registration_with_invalid_code())
        
        # Test authorized flow
        results.append(test_generate_and_use_invite_code())
        
        # Test ASHA still works
        results.append(test_asha_registration_no_code_needed())
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to backend. Is the server running?")
        print("Start with: docker-compose up -d")
        return
    
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        return
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ ALL TESTS PASSED - Security fix verified!")
        print("Doctor role registration is now properly protected.")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed")

if __name__ == "__main__":
    main()
