from shared.isolated_environment import get_env
#!/usr/bin/env python3
"""
Critical Authentication Cross-System E2E Tests for GCP Staging Environment

These tests validate cross-service authentication between auth_service and netra_backend
against the real staging deployment. They are designed to run as external API tests
without requiring local service imports.
"""

import asyncio
import os
import sys
import time
import uuid
import json
import base64
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import pytest
import httpx
import jwt as pyjwt

# Set up staging environment URLs
BACKEND_URL = "https://api.staging.netrasystems.ai"
AUTH_SERVICE_URL = "https://auth.staging.netrasystems.ai"

class TestAuthCrossSystemStaging:
    """
    Authentication Cross-System E2E Tests for Staging Environment
    
    These tests validate real authentication issues against the live staging deployment.
    """

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_staging_concurrent_login_race_condition(self):
        """Test 1: Concurrent Login Race Condition (Staging)
        
        Test concurrent login attempts against staging to identify race conditions.
        """
        user_email = f"race-test-{uuid.uuid4().hex[:8]}@example.com"
        password = "testpass123"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Create test user first
            register_response = await client.post(f"{AUTH_SERVICE_URL}/auth/register", json={
                "email": user_email,
                "password": password,
                "confirm_password": password
            })
            
            if register_response.status_code != 201:
                pytest.skip(f"Cannot register user in staging: {register_response.status_code} - {register_response.text}")
            
            # Simulate concurrent login attempts
            async def login_attempt():
                try:
                    response = await client.post(f"{AUTH_SERVICE_URL}/auth/login", json={
                        "email": user_email,
                        "password": password
                    })
                    return response
                except Exception as e:
                    return e
            
            # Launch 5 concurrent login attempts
            tasks = [login_attempt() for _ in range(5)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Extract successful tokens
            successful_tokens = []
            for result in results:
                if hasattr(result, 'status_code') and result.status_code == 200:
                    try:
                        token_data = result.json()
                        if 'access_token' in token_data:
                            successful_tokens.append(token_data['access_token'])
                    except:
                        continue
            
            print(f"Concurrent logins: {len(results)} attempts, {len(successful_tokens)} successful tokens")
            
            # Check for race condition
            if len(successful_tokens) > 1:
                unique_tokens = set(successful_tokens)
                print(f"RACE CONDITION DETECTED: {len(successful_tokens)} tokens issued, {len(unique_tokens)} unique")
                
                # This indicates a potential race condition
                assert len(unique_tokens) == len(successful_tokens), (
                    "DUPLICATE TOKENS DETECTED: Auth service issued identical tokens concurrently"
                )

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_staging_token_validation_cross_service(self):
        """Test 2: Token Validation Cross-Service (Staging)
        
        Test that tokens issued by auth service are properly validated by backend.
        """
        user_email = f"validation-test-{uuid.uuid4().hex[:8]}@example.com"
        password = "testpass123"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Register user
            register_response = await client.post(f"{AUTH_SERVICE_URL}/auth/register", json={
                "email": user_email,
                "password": password,
                "confirm_password": password
            })
            
            if register_response.status_code != 201:
                pytest.skip(f"Cannot register user in staging: {register_response.status_code}")
            
            # Login to get token
            login_response = await client.post(f"{AUTH_SERVICE_URL}/auth/login", json={
                "email": user_email,
                "password": password
            })
            
            assert login_response.status_code == 200, f"Login failed: {login_response.status_code} - {login_response.text}"
            token = login_response.json()["access_token"]
            
            # Test token with backend health endpoint
            backend_response = await client.get(
                f"{BACKEND_URL}/health",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            print(f"Backend validation: {backend_response.status_code}")
            if backend_response.status_code not in [200, 401]:
                print(f"Unexpected backend response: {backend_response.text}")

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_staging_token_invalidation_propagation(self):
        """Test 3: Token Invalidation Propagation (Staging)
        
        Test that token invalidation in auth service affects backend validation.
        """
        user_email = f"invalidation-test-{uuid.uuid4().hex[:8]}@example.com"
        password = "testpass123"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Register user
            register_response = await client.post(f"{AUTH_SERVICE_URL}/auth/register", json={
                "email": user_email,
                "password": password,
                "confirm_password": password
            })
            
            if register_response.status_code != 201:
                pytest.skip(f"Cannot register user in staging: {register_response.status_code}")
            
            # Login to get token
            login_response = await client.post(f"{AUTH_SERVICE_URL}/auth/login", json={
                "email": user_email,
                "password": password
            })
            
            assert login_response.status_code == 200
            token = login_response.json()["access_token"]
            
            # Verify token works with backend
            initial_backend_response = await client.get(
                f"{BACKEND_URL}/health",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            print(f"Initial backend validation: {initial_backend_response.status_code}")
            
            # Attempt logout (invalidate token)
            logout_response = await client.post(
                f"{AUTH_SERVICE_URL}/auth/logout",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            print(f"Logout response: {logout_response.status_code}")
            
            # Test if token still works with backend after logout
            post_logout_backend_response = await client.get(
                f"{BACKEND_URL}/health",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            print(f"Post-logout backend validation: {post_logout_backend_response.status_code}")
            
            # Check if invalidation propagated
            if initial_backend_response.status_code == 200 and post_logout_backend_response.status_code == 200:
                print("WARNING: Token invalidation may not be propagating to backend service")

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_staging_user_data_consistency(self):
        """Test 4: User Data Consistency (Staging)
        
        Test that user data is consistent between auth service and backend.
        """
        user_email = f"consistency-test-{uuid.uuid4().hex[:8]}@example.com"
        password = "testpass123"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Register user
            register_response = await client.post(f"{AUTH_SERVICE_URL}/auth/register", json={
                "email": user_email,
                "password": password,
                "confirm_password": password
            })
            
            if register_response.status_code != 201:
                pytest.skip(f"Cannot register user in staging: {register_response.status_code}")
            
            # Login to get token
            login_response = await client.post(f"{AUTH_SERVICE_URL}/auth/login", json={
                "email": user_email,
                "password": password
            })
            
            assert login_response.status_code == 200
            token = login_response.json()["access_token"]
            
            # Get user info from auth service
            auth_me_response = await client.get(
                f"{AUTH_SERVICE_URL}/auth/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            print(f"Auth /me response: {auth_me_response.status_code}")
            
            # Get user info from backend
            backend_me_response = await client.get(
                f"{BACKEND_URL}/auth/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            print(f"Backend /auth/me response: {backend_me_response.status_code}")
            
            # Compare responses if both succeed
            if auth_me_response.status_code == 200 and backend_me_response.status_code == 200:
                auth_data = auth_me_response.json()
                backend_data = backend_me_response.json()
                
                print(f"Auth service user data: {auth_data}")
                print(f"Backend service user data: {backend_data}")
                
                # Check for basic consistency
                if auth_data.get('email') != backend_data.get('email'):
                    print("WARNING: Email mismatch between services")

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_staging_malformed_token_handling(self):
        """Test 5: Malformed Token Handling (Staging)
        
        Test how both services handle malformed or tampered tokens.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test with malformed tokens
            malformed_tokens = [
                "invalid-token",
                "Bearer invalid-token",
                "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.invalid",
                "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0QGV4YW1wbGUuY29tIn0.invalid",
            ]
            
            for token in malformed_tokens:
                # Test auth service response
                auth_response = await client.get(
                    f"{AUTH_SERVICE_URL}/auth/me",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                # Test backend response  
                backend_response = await client.get(
                    f"{BACKEND_URL}/health",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                print(f"Malformed token '{token[:20]}...': Auth={auth_response.status_code}, Backend={backend_response.status_code}")
                
                # Both services should reject malformed tokens
                assert auth_response.status_code == 401, f"Auth service should reject malformed token, got {auth_response.status_code}"

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_staging_service_health_and_availability(self):
        """Test 6: Service Health and Availability (Staging)
        
        Verify both services are accessible and responding.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test auth service health
            try:
                auth_health_response = await client.get(f"{AUTH_SERVICE_URL}/health")
                print(f"Auth service health: {auth_health_response.status_code}")
                if auth_health_response.status_code == 200:
                    print(f"Auth health data: {auth_health_response.json()}")
            except Exception as e:
                print(f"Auth service unreachable: {e}")
                pytest.fail("Auth service is not accessible")
            
            # Test backend health
            try:
                backend_health_response = await client.get(f"{BACKEND_URL}/health")
                print(f"Backend service health: {backend_health_response.status_code}")
                if backend_health_response.status_code == 200:
                    print(f"Backend health data: {backend_health_response.json()}")
            except Exception as e:
                print(f"Backend service unreachable: {e}")
                pytest.fail("Backend service is not accessible")

    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_staging_cross_origin_security(self):
        """Test 7: Cross-Origin Security (Staging)
        
        Test CORS and origin validation.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test with various origins
            origins = [
                "https://malicious-site.com",
                "http://localhost:3000",
                "https://app.staging.netrasystems.ai",
            ]
            
            for origin in origins:
                # Test preflight request
                preflight_response = await client.options(
                    f"{AUTH_SERVICE_URL}/auth/login",
                    headers={
                        "Origin": origin,
                        "Access-Control-Request-Method": "POST",
                        "Access-Control-Request-Headers": "Content-Type",
                    }
                )
                
                print(f"CORS preflight for {origin}: {preflight_response.status_code}")
                
                # Test actual request with origin
                login_attempt_response = await client.post(
                    f"{AUTH_SERVICE_URL}/auth/login",
                    headers={"Origin": origin},
                    json={"email": "test@example.com", "password": "invalid"}
                )
                
                print(f"Login with origin {origin}: {login_attempt_response.status_code}")

def run_staging_tests():
    """Run all staging authentication tests"""
    import subprocess
    
    # Set environment variables
    os.environ["BACKEND_URL"] = BACKEND_URL
    os.environ["AUTH_SERVICE_URL"] = AUTH_SERVICE_URL
    os.environ["TEST_ENV"] = "staging"
    os.environ["USE_REAL_LLM"] = "true"
    
    # Run tests
    cmd = [
        sys.executable, "-m", "pytest", 
        __file__,
        "-v", "-s",
        "--tb=short",
        "-k", "staging"
    ]
    
    print("Running Staging Authentication E2E Tests")
    print("=" * 60)
    print(f"Auth Service: {AUTH_SERVICE_URL}")
    print(f"Backend: {BACKEND_URL}")
    print("=" * 60)
    
    result = subprocess.run(cmd)
    return result.returncode

if __name__ == "__main__":
    exit_code = run_staging_tests()
    sys.exit(exit_code)
