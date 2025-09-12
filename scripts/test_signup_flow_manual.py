"""
Manual test script for signup flow edge cases
Tests registration, persistence, validation, and error handling
"""
import asyncio
import httpx
import json
import time
from shared.isolated_environment import IsolatedEnvironment

BASE_URL = "http://localhost:8081"

async def test_signup_flow():
    """Test complete signup flow with edge cases"""
    
    async with httpx.AsyncClient() as client:
        print("\n=== TESTING SIGNUP FLOW WITH EDGE CASES ===\n")
        
        # Test 1: Valid registration
        print("1. Testing valid registration...")
        response = await client.post(
            f"{BASE_URL}/auth/register",
            json={
                "email": "validuser@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
                "full_name": "Valid User"
            }
        )
        if response.status_code == 201:
            print(" PASS:  Valid registration successful")
            result = response.json()
            print(f"   User ID: {result.get('user_id')}")
            print(f"   Email: {result.get('email')}")
        else:
            print(f" FAIL:  Registration failed: {response.status_code} - {response.text}")
        
        # Test 2: Duplicate email
        print("\n2. Testing duplicate email...")
        response = await client.post(
            f"{BASE_URL}/auth/register",
            json={
                "email": "validuser@example.com",
                "password": "AnotherPass123!",
                "confirm_password": "AnotherPass123!",
                "full_name": "Duplicate User"
            }
        )
        if response.status_code == 400:
            print(" PASS:  Duplicate email correctly rejected")
            print(f"   Error: {response.json().get('detail')}")
        else:
            print(f" FAIL:  Duplicate not handled: {response.status_code}")
        
        # Test 3: Invalid email format
        print("\n3. Testing invalid email format...")
        response = await client.post(
            f"{BASE_URL}/auth/register",
            json={
                "email": "not-an-email",
                "password": "ValidPass123!",
                "confirm_password": "ValidPass123!",
                "full_name": "Invalid Email"
            }
        )
        if response.status_code == 400:
            print(" PASS:  Invalid email correctly rejected")
            print(f"   Error: {response.json().get('detail')}")
        else:
            print(f" FAIL:  Invalid email not caught: {response.status_code}")
        
        # Test 4: Weak password
        print("\n4. Testing weak password...")
        response = await client.post(
            f"{BASE_URL}/auth/register",
            json={
                "email": "weakpass@example.com",
                "password": "weak",
                "confirm_password": "weak",
                "full_name": "Weak Password"
            }
        )
        if response.status_code == 400:
            print(" PASS:  Weak password correctly rejected")
            print(f"   Error: {response.json().get('detail')}")
        else:
            print(f" FAIL:  Weak password not caught: {response.status_code}")
        
        # Test 5: Password mismatch
        print("\n5. Testing password mismatch...")
        response = await client.post(
            f"{BASE_URL}/auth/register",
            json={
                "email": "mismatch@example.com",
                "password": "Password123!",
                "confirm_password": "Different123!",
                "full_name": "Password Mismatch"
            }
        )
        if response.status_code == 400:
            print(" PASS:  Password mismatch correctly rejected")
            print(f"   Error: {response.json().get('detail')}")
        else:
            print(f" FAIL:  Password mismatch not caught: {response.status_code}")
        
        # Test 6: Missing required fields
        print("\n6. Testing missing required fields...")
        response = await client.post(
            f"{BASE_URL}/auth/register",
            json={
                "email": "missing@example.com"
            }
        )
        if response.status_code == 400:
            print(" PASS:  Missing fields correctly rejected")
            print(f"   Error: {response.json().get('detail')}")
        else:
            print(f" FAIL:  Missing fields not caught: {response.status_code}")
        
        # Test 7: SQL injection attempt
        print("\n7. Testing SQL injection prevention...")
        response = await client.post(
            f"{BASE_URL}/auth/register",
            json={
                "email": "test'; DROP TABLE users; --",
                "password": "ValidPass123!",
                "confirm_password": "ValidPass123!",
                "full_name": "SQL Injection"
            }
        )
        if response.status_code == 400:
            print(" PASS:  SQL injection attempt blocked")
            print(f"   Error: {response.json().get('detail')}")
        else:
            print(f" FAIL:  SQL injection not blocked: {response.status_code}")
        
        # Test 8: Login with registered user
        print("\n8. Testing login with registered user...")
        response = await client.post(
            f"{BASE_URL}/auth/login",
            json={
                "email": "validuser@example.com",
                "password": "SecurePass123!"
            }
        )
        if response.status_code == 200:
            print(" PASS:  Login successful")
            result = response.json()
            print(f"   Access token: {result.get('access_token')[:50]}...")
            print(f"   User ID: {result.get('user', {}).get('id')}")
        else:
            print(f" FAIL:  Login failed: {response.status_code}")
        
        # Test 9: Login with wrong password
        print("\n9. Testing login with wrong password...")
        response = await client.post(
            f"{BASE_URL}/auth/login",
            json={
                "email": "validuser@example.com",
                "password": "WrongPassword123!"
            }
        )
        if response.status_code == 422:
            print(" PASS:  Wrong password correctly rejected")
        else:
            print(f" FAIL:  Wrong password not handled: {response.status_code}")
        
        print("\n=== SIGNUP FLOW TESTING COMPLETE ===\n")

if __name__ == "__main__":
    print("Starting signup flow tests...")
    print("Make sure the auth service is running on port 8081")
    asyncio.run(test_signup_flow())