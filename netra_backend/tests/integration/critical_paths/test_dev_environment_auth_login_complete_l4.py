#!/usr/bin/env python3
"""
L4 Integration Test: Dev Environment Complete Authentication and Login Flow

Tests the complete authentication and login process:
1. User registration with validation
2. Email verification flow
3. Login with credentials
4. JWT token generation and validation
5. Token refresh mechanism
6. Session management
7. Multi-factor authentication (if enabled)
8. Cross-service authentication propagation

BVJ:
- Segment: Free, Early, Mid, Enterprise
- Business Goal: Conversion
- Value Impact: Secure and seamless authentication for all users
- Strategic Impact: Foundation for user trust and platform access
"""

# Test framework import - using pytest fixtures instead

import asyncio
import hashlib
import json
import os
import secrets
import sys
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
import jwt
import pytest

# Service URLs
AUTH_SERVICE_URL = "http://localhost:8081"
BACKEND_URL = "http://localhost:8000"
WEBSOCKET_URL = "ws://localhost:8000/websocket"

# Test user configurations
TEST_USERS = [
    {
        "email": "test_user_1@example.com",
        "password": "SecurePass123!",
        "name": "Test User One",
        "role": "user",
        "tier": "free"
    },
    {
        "email": "test_user_2@example.com",
        "password": "SecurePass456!",
        "name": "Test User Two",
        "role": "user",
        "tier": "early"
    },
    {
        "email": "test_admin@example.com",
        "password": "AdminPass789!",
        "name": "Test Admin",
        "role": "admin",
        "tier": "enterprise"
    }
]

class AuthenticationFlowTester:
    """Test complete authentication and login flows."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.user_tokens: Dict[str, Dict[str, Any]] = {}
        self.user_sessions: Dict[str, Dict[str, Any]] = {}
        self.auth_logs: List[str] = []
        self.test_results: Dict[str, Any] = {}
        
    async def __aenter__(self):
        """Setup test environment."""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup test environment."""
        if self.session:
            await self.session.close()
    
    def log_auth_event(self, user: str, event: str, details: str = ""):
        """Log authentication events for analysis."""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] [{user}] {event}"
        if details:
            log_entry += f" - {details}"
        self.auth_logs.append(log_entry)
        print(log_entry)
    
    @pytest.mark.asyncio
    async def test_user_registration(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test user registration with validation."""
        result = {
            "registered": False,
            "user_id": None,
            "validation_errors": [],
            "registration_time": 0
        }
        
        start_time = time.time()
        email = user_data["email"]
        
        self.log_auth_event(email, "REGISTRATION_START", f"Registering {user_data['role']} user")
        
        try:
            # Validate input
            if not self._validate_email(email):
                result["validation_errors"].append("Invalid email format")
                
            if not self._validate_password(user_data["password"]):
                result["validation_errors"].append("Password does not meet requirements")
                
            if result["validation_errors"]:
                self.log_auth_event(email, "VALIDATION_FAILED", str(result["validation_errors"]))
                return result
            
            # Register user
            register_payload = {
                "email": email,
                "password": user_data["password"],
                "name": user_data["name"],
                "role": user_data.get("role", "user"),
                "tier": user_data.get("tier", "free")
            }
            
            async with self.session.post(
                f"{AUTH_SERVICE_URL}/auth/register",
                json=register_payload
            ) as response:
                if response.status in [200, 201]:
                    data = await response.json()
                    result["registered"] = True
                    result["user_id"] = data.get("user_id")
                    self.log_auth_event(email, "REGISTRATION_SUCCESS", f"User ID: {result['user_id']}")
                    
                elif response.status == 409:
                    self.log_auth_event(email, "USER_EXISTS", "User already registered")
                    result["registered"] = True  # Consider this success for testing
                    
                else:
                    error_text = await response.text()
                    self.log_auth_event(email, "REGISTRATION_FAILED", f"Status: {response.status}, Error: {error_text}")
                    result["validation_errors"].append(error_text)
                    
        except Exception as e:
            self.log_auth_event(email, "REGISTRATION_ERROR", str(e))
            result["validation_errors"].append(str(e))
            
        result["registration_time"] = time.time() - start_time
        return result
    
    @pytest.mark.asyncio
    async def test_email_verification(self, email: str) -> Dict[str, Any]:
        """Test email verification flow."""
        result = {
            "verification_sent": False,
            "verification_token": None,
            "verified": False
        }
        
        self.log_auth_event(email, "VERIFICATION_START", "Starting email verification")
        
        try:
            # Request verification email
            async with self.session.post(
                f"{AUTH_SERVICE_URL}/auth/request-verification",
                json={"email": email}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    result["verification_sent"] = True
                    # In test mode, we might get the token directly
                    result["verification_token"] = data.get("test_token")
                    self.log_auth_event(email, "VERIFICATION_SENT", "Verification email sent")
                    
            # Simulate verification
            if result["verification_token"]:
                async with self.session.post(
                    f"{AUTH_SERVICE_URL}/auth/verify-email",
                    json={
                        "email": email,
                        "token": result["verification_token"]
                    }
                ) as response:
                    if response.status == 200:
                        result["verified"] = True
                        self.log_auth_event(email, "VERIFICATION_SUCCESS", "Email verified")
                        
        except Exception as e:
            self.log_auth_event(email, "VERIFICATION_ERROR", str(e))
            
        return result
    
    @pytest.mark.asyncio
    async def test_user_login(self, email: str, password: str) -> Dict[str, Any]:
        """Test user login and token generation."""
        result = {
            "login_success": False,
            "access_token": None,
            "refresh_token": None,
            "token_expiry": None,
            "user_data": {},
            "login_time": 0
        }
        
        start_time = time.time()
        
        self.log_auth_event(email, "LOGIN_ATTEMPT", "Attempting login")
        
        try:
            login_payload = {
                "email": email,
                "password": password
            }
            
            async with self.session.post(
                f"{AUTH_SERVICE_URL}/auth/login",
                json=login_payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    result["login_success"] = True
                    result["access_token"] = data.get("access_token")
                    result["refresh_token"] = data.get("refresh_token")
                    result["token_expiry"] = data.get("expires_in")
                    result["user_data"] = data.get("user", {})
                    
                    # Store tokens for later use
                    self.user_tokens[email] = {
                        "access_token": result["access_token"],
                        "refresh_token": result["refresh_token"],
                        "expiry": datetime.now() + timedelta(seconds=result["token_expiry"] or 3600)
                    }
                    
                    self.log_auth_event(email, "LOGIN_SUCCESS", f"Token expires in {result['token_expiry']}s")
                    
                else:
                    error_text = await response.text()
                    self.log_auth_event(email, "LOGIN_FAILED", f"Status: {response.status}, Error: {error_text}")
                    
        except Exception as e:
            self.log_auth_event(email, "LOGIN_ERROR", str(e))
            
        result["login_time"] = time.time() - start_time
        return result
    
    @pytest.mark.asyncio
    async def test_token_validation(self, email: str) -> Dict[str, Any]:
        """Test JWT token validation."""
        result = {
            "token_valid": False,
            "token_claims": {},
            "validation_errors": []
        }
        
        tokens = self.user_tokens.get(email)
        if not tokens:
            result["validation_errors"].append("No tokens found for user")
            return result
            
        self.log_auth_event(email, "TOKEN_VALIDATION", "Validating access token")
        
        try:
            # Validate token with auth service
            headers = {"Authorization": f"Bearer {tokens['access_token']}"}
            
            async with self.session.get(
                f"{AUTH_SERVICE_URL}/auth/validate",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    result["token_valid"] = True
                    result["token_claims"] = data.get("claims", {})
                    self.log_auth_event(email, "TOKEN_VALID", f"Claims: {result['token_claims']}")
                    
                else:
                    error_text = await response.text()
                    result["validation_errors"].append(error_text)
                    self.log_auth_event(email, "TOKEN_INVALID", error_text)
                    
        except Exception as e:
            result["validation_errors"].append(str(e))
            self.log_auth_event(email, "TOKEN_VALIDATION_ERROR", str(e))
            
        return result
    
    @pytest.mark.asyncio
    async def test_token_refresh(self, email: str) -> Dict[str, Any]:
        """Test token refresh mechanism."""
        result = {
            "refresh_success": False,
            "new_access_token": None,
            "new_refresh_token": None,
            "refresh_time": 0
        }
        
        tokens = self.user_tokens.get(email)
        if not tokens or not tokens.get("refresh_token"):
            self.log_auth_event(email, "REFRESH_SKIP", "No refresh token available")
            return result
            
        start_time = time.time()
        self.log_auth_event(email, "TOKEN_REFRESH", "Refreshing access token")
        
        try:
            refresh_payload = {
                "refresh_token": tokens["refresh_token"]
            }
            
            async with self.session.post(
                f"{AUTH_SERVICE_URL}/auth/refresh",
                json=refresh_payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    result["refresh_success"] = True
                    result["new_access_token"] = data.get("access_token")
                    result["new_refresh_token"] = data.get("refresh_token")
                    
                    # Update stored tokens
                    self.user_tokens[email] = {
                        "access_token": result["new_access_token"],
                        "refresh_token": result["new_refresh_token"] or tokens["refresh_token"],
                        "expiry": datetime.now() + timedelta(seconds=data.get("expires_in", 3600))
                    }
                    
                    self.log_auth_event(email, "REFRESH_SUCCESS", "Tokens refreshed")
                    
                else:
                    error_text = await response.text()
                    self.log_auth_event(email, "REFRESH_FAILED", error_text)
                    
        except Exception as e:
            self.log_auth_event(email, "REFRESH_ERROR", str(e))
            
        result["refresh_time"] = time.time() - start_time
        return result
    
    @pytest.mark.asyncio
    async def test_cross_service_auth(self, email: str) -> Dict[str, Any]:
        """Test authentication propagation across services."""
        result = {
            "backend_auth": False,
            "websocket_auth": False,
            "service_responses": {}
        }
        
        tokens = self.user_tokens.get(email)
        if not tokens:
            self.log_auth_event(email, "CROSS_SERVICE_SKIP", "No tokens available")
            return result
            
        self.log_auth_event(email, "CROSS_SERVICE_TEST", "Testing cross-service authentication")
        
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        
        # Test backend authentication
        try:
            async with self.session.get(
                f"{BACKEND_URL}/api/user/profile",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    result["backend_auth"] = True
                    result["service_responses"]["backend"] = data
                    self.log_auth_event(email, "BACKEND_AUTH_SUCCESS", "Backend authenticated")
                else:
                    self.log_auth_event(email, "BACKEND_AUTH_FAILED", f"Status: {response.status}")
                    
        except Exception as e:
            self.log_auth_event(email, "BACKEND_AUTH_ERROR", str(e))
            
        # Test WebSocket authentication
        try:
            import websockets
            
            ws_headers = {"Authorization": f"Bearer {tokens['access_token']}"}
            async with websockets.connect(WEBSOCKET_URL, extra_headers=ws_headers) as ws:
                # Send auth message
                auth_msg = {
                    "type": "auth",
                    "token": tokens["access_token"]
                }
                await ws.send(json.dumps(auth_msg))
                
                # Wait for response
                response = await asyncio.wait_for(ws.recv(), timeout=5)
                data = json.loads(response)
                
                if data.get("type") == "auth_success":
                    result["websocket_auth"] = True
                    result["service_responses"]["websocket"] = data
                    self.log_auth_event(email, "WEBSOCKET_AUTH_SUCCESS", "WebSocket authenticated")
                else:
                    self.log_auth_event(email, "WEBSOCKET_AUTH_FAILED", str(data))
                    
        except Exception as e:
            self.log_auth_event(email, "WEBSOCKET_AUTH_ERROR", str(e))
            
        return result
    
    @pytest.mark.asyncio
    async def test_session_management(self, email: str) -> Dict[str, Any]:
        """Test session creation and management."""
        result = {
            "session_created": False,
            "session_id": None,
            "session_data": {},
            "session_ttl": 0
        }
        
        tokens = self.user_tokens.get(email)
        if not tokens:
            return result
            
        self.log_auth_event(email, "SESSION_CREATE", "Creating user session")
        
        try:
            headers = {"Authorization": f"Bearer {tokens['access_token']}"}
            
            # Create session
            session_payload = {
                "user_agent": "Test Client",
                "ip_address": "127.0.0.1"
            }
            
            async with self.session.post(
                f"{AUTH_SERVICE_URL}/auth/session",
                json=session_payload,
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    result["session_created"] = True
                    result["session_id"] = data.get("session_id")
                    result["session_data"] = data.get("session", {})
                    result["session_ttl"] = data.get("ttl", 0)
                    
                    # Store session info
                    self.user_sessions[email] = {
                        "session_id": result["session_id"],
                        "created_at": datetime.now(),
                        "ttl": result["session_ttl"]
                    }
                    
                    self.log_auth_event(email, "SESSION_CREATED", f"Session ID: {result['session_id']}")
                    
        except Exception as e:
            self.log_auth_event(email, "SESSION_ERROR", str(e))
            
        return result
    
    @pytest.mark.asyncio
    async def test_logout_flow(self, email: str) -> Dict[str, Any]:
        """Test logout and token revocation."""
        result = {
            "logout_success": False,
            "token_revoked": False,
            "session_terminated": False
        }
        
        tokens = self.user_tokens.get(email)
        if not tokens:
            return result
            
        self.log_auth_event(email, "LOGOUT_START", "Initiating logout")
        
        try:
            headers = {"Authorization": f"Bearer {tokens['access_token']}"}
            
            async with self.session.post(
                f"{AUTH_SERVICE_URL}/auth/logout",
                headers=headers
            ) as response:
                if response.status == 200:
                    result["logout_success"] = True
                    
                    # Clear stored tokens
                    if email in self.user_tokens:
                        del self.user_tokens[email]
                    if email in self.user_sessions:
                        del self.user_sessions[email]
                        
                    self.log_auth_event(email, "LOGOUT_SUCCESS", "User logged out")
                    
                    # Verify token is revoked
                    async with self.session.get(
                        f"{AUTH_SERVICE_URL}/auth/validate",
                        headers=headers
                    ) as validate_response:
                        if validate_response.status == 401:
                            result["token_revoked"] = True
                            result["session_terminated"] = True
                            
        except Exception as e:
            self.log_auth_event(email, "LOGOUT_ERROR", str(e))
            
        return result
    
    def _validate_email(self, email: str) -> bool:
        """Validate email format."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def _validate_password(self, password: str) -> bool:
        """Validate password requirements."""
        # At least 8 chars, one upper, one lower, one digit, one special
        if len(password) < 8:
            return False
        if not any(c.isupper() for c in password):
            return False
        if not any(c.islower() for c in password):
            return False
        if not any(c.isdigit() for c in password):
            return False
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            return False
        return True
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all authentication flow tests."""
        all_results = {
            "test_timestamp": datetime.now().isoformat(),
            "users_tested": len(TEST_USERS),
            "user_results": {},
            "auth_logs": [],
            "summary": {}
        }
        
        for user_data in TEST_USERS:
            email = user_data["email"]
            print(f"\n{'='*60}")
            print(f"Testing user: {email}")
            print('='*60)
            
            user_results = {}
            
            # Test registration
            user_results["registration"] = await self.test_user_registration(user_data)
            
            # Test email verification
            user_results["email_verification"] = await self.test_email_verification(email)
            
            # Test login
            user_results["login"] = await self.test_user_login(
                email, 
                user_data["password"]
            )
            
            # Test token validation
            user_results["token_validation"] = await self.test_token_validation(email)
            
            # Test token refresh
            user_results["token_refresh"] = await self.test_token_refresh(email)
            
            # Test cross-service auth
            user_results["cross_service_auth"] = await self.test_cross_service_auth(email)
            
            # Test session management
            user_results["session_management"] = await self.test_session_management(email)
            
            # Test logout
            user_results["logout"] = await self.test_logout_flow(email)
            
            all_results["user_results"][email] = user_results
            
        # Add logs
        all_results["auth_logs"] = self.auth_logs
        
        # Generate summary
        total_tests = 0
        passed_tests = 0
        
        for email, results in all_results["user_results"].items():
            if results["registration"]["registered"]:
                passed_tests += 1
            total_tests += 1
            
            if results["login"]["login_success"]:
                passed_tests += 1
            total_tests += 1
            
            if results["token_validation"]["token_valid"]:
                passed_tests += 1
            total_tests += 1
            
            if results["cross_service_auth"]["backend_auth"]:
                passed_tests += 1
            total_tests += 1
            
        all_results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            "users_authenticated": len(self.user_tokens),
            "active_sessions": len(self.user_sessions)
        }
        
        return all_results

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.level_4
@pytest.mark.asyncio
async def test_dev_environment_auth_login_complete():
    """Test complete authentication and login flow."""
    async with AuthenticationFlowTester() as tester:
        results = await tester.run_all_tests()
        
        # Print detailed results
        print("\n" + "="*60)
        print("AUTHENTICATION AND LOGIN TEST RESULTS")
        print("="*60)
        
        for email, user_results in results["user_results"].items():
            print(f"\nUser: {email}")
            print("-" * 40)
            
            # Registration
            reg = user_results["registration"]
            print(f"  Registration: {'✓' if reg['registered'] else '✗'} ({reg['registration_time']:.2f}s)")
            
            # Login
            login = user_results["login"]
            print(f"  Login: {'✓' if login['login_success'] else '✗'} ({login['login_time']:.2f}s)")
            
            # Token validation
            token = user_results["token_validation"]
            print(f"  Token Valid: {'✓' if token['token_valid'] else '✗'}")
            
            # Cross-service auth
            cross = user_results["cross_service_auth"]
            print(f"  Backend Auth: {'✓' if cross['backend_auth'] else '✗'}")
            print(f"  WebSocket Auth: {'✓' if cross['websocket_auth'] else '✗'}")
            
            # Logout
            logout = user_results["logout"]
            print(f"  Logout: {'✓' if logout['logout_success'] else '✗'}")
            
        # Summary
        summary = results["summary"]
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed Tests: {summary['passed_tests']}")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
        print(f"Users Authenticated: {summary['users_authenticated']}")
        print(f"Active Sessions: {summary['active_sessions']}")
        
        # Assert critical conditions
        assert summary["success_rate"] >= 75, f"Success rate too low: {summary['success_rate']:.1f}%"
        assert summary["users_authenticated"] >= 2, "Not enough users authenticated"
        
        print("\n[SUCCESS] Authentication and login flow tests completed!")

async def main():
    """Run the test standalone."""
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    print("="*60)
    print("DEV ENVIRONMENT AUTH AND LOGIN TEST (L4)")
    print("="*60)
    print(f"Started at: {datetime.now().isoformat()}")
    print("="*60)
    
    async with AuthenticationFlowTester() as tester:
        results = await tester.run_all_tests()
        
        # Save results
        results_file = project_root / "test_results" / "auth_login_results.json"
        results_file.parent.mkdir(exist_ok=True)
        
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2, default=str)
            
        print(f"\nResults saved to: {results_file}")
        
        # Return exit code
        if results["summary"]["success_rate"] >= 75:
            return 0
        else:
            return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)