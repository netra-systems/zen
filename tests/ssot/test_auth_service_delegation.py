"""
Auth Service Delegation Validation Tests

PURPOSE: These tests FAIL when backend bypasses auth service for JWT operations
instead of properly delegating. Tests will PASS after SSOT refactor.

MISSION CRITICAL: Protects $500K+ ARR Golden Path by ensuring all auth operations
go through the centralized auth service (SSOT pattern).

BUSINESS VALUE: Enterprise/Platform - Security Architecture & Audit Compliance
- Ensures single point of JWT validation for audit trails
- Prevents auth logic duplication and inconsistencies  
- Maintains proper service boundaries and separation of concerns
- Enables centralized security policy enforcement

EXPECTED STATUS: FAIL (before SSOT refactor) → PASS (after SSOT refactor)

These tests validate proper auth service delegation by:
1. Verifying auth_client is used for all JWT operations
2. Ensuring no local JWT fallback mechanisms exist
3. Checking proper error handling when auth service unavailable
4. Validating auth service communication patterns
"""

import ast
import httpx
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from unittest.mock import patch, AsyncMock, MagicMock
import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.integration_auth_manager import IntegrationAuthManager

logger = logging.getLogger(__name__)

class TestAuthServiceDelegation(SSotAsyncTestCase):
    """
    SSOT Auth Service Delegation Tests
    
    These tests FAIL when backend bypasses auth service delegation.
    After SSOT refactor, all tests should PASS.
    """

    def setup_method(self, method):
        super().setup_method(method)
        self.backend_path = Path("/Users/anthony/Desktop/netra-apex/netra_backend")
        self.auth_manager = IntegrationAuthManager()
        
    @pytest.mark.asyncio
    async def test_auth_integration_only_uses_auth_client(self):
        """
        SSOT Delegation Test: Auth integration module only uses auth_client.
        
        EXPECTED: FAIL - Backend currently has local JWT fallback logic
        AFTER SSOT: PASS - All JWT operations go through auth_client
        
        This test verifies auth integration delegates everything to auth service.
        """
        auth_integration_path = self.backend_path / "app" / "auth_integration" / "auth.py"
        delegation_violations = []
        
        if auth_integration_path.exists():
            try:
                with open(auth_integration_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check for SSOT violations - local JWT operations
                violation_patterns = [
                    # Direct JWT operations (should be delegated)
                    ('jwt.decode', 'Direct JWT decode instead of auth_client delegation'),
                    ('jwt.verify', 'Direct JWT verify instead of auth_client delegation'), 
                    ('jwt.encode', 'Direct JWT encode instead of auth_client delegation'),
                    
                    # Local validation methods (should be delegated)
                    ('_decode_test_jwt', 'Local test JWT decode instead of auth service'),
                    ('_decode_token', 'Local token decode instead of auth service'),
                    ('_validate_token_locally', 'Local token validation bypassing auth service'),
                    
                    # Fallback mechanisms (should not exist in SSOT)
                    ('fallback.*validation', 'JWT fallback validation bypassing auth service'),
                    ('circuit.*breaker.*open', 'Circuit breaker bypass instead of proper error handling'),
                    ('when.*auth.*service.*down', 'Local auth when service down violates SSOT')
                ]
                
                for pattern, description in violation_patterns:
                    if pattern.lower() in content.lower():
                        delegation_violations.append(f"{description}: pattern '{pattern}' found")
                        
            except Exception as e:
                logger.warning(f"Could not scan auth integration file: {e}")
        
        if delegation_violations:
            violation_summary = "\n".join([f"  - {v}" for v in delegation_violations])
            logger.error(f"SSOT DELEGATION VIOLATION: Auth integration bypasses auth service:")
            logger.error(violation_summary)
        
        # This test SHOULD FAIL before SSOT refactor
        assert not delegation_violations, (
            f"SSOT DELEGATION VIOLATION: Auth integration contains {len(delegation_violations)} "
            f"patterns that bypass auth service. All JWT operations must be delegated. "
            f"Violations:\n{violation_summary}"
        )

    @pytest.mark.asyncio
    async def test_websocket_auth_delegates_to_auth_service(self):
        """
        SSOT Delegation Test: WebSocket auth delegates to auth service only.
        
        EXPECTED: FAIL - WebSocket currently has local JWT validation fallback
        AFTER SSOT: PASS - WebSocket delegates all auth to auth service
        
        This test checks WebSocket authentication delegation compliance.
        """
        websocket_auth_path = self.backend_path / "app" / "websocket_core" / "auth.py"
        websocket_violations = []
        
        if websocket_auth_path.exists():
            try:
                with open(websocket_auth_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check for SSOT delegation violations in WebSocket auth
                violation_patterns = [
                    # Local JWT validation (should delegate to auth service)
                    ('authenticate.*local', 'WebSocket local authentication bypassing auth service'),
                    ('jwt.*local.*validation', 'WebSocket local JWT validation bypassing auth service'),
                    ('fallback.*jwt', 'WebSocket JWT fallback bypassing auth service'),
                    
                    # Circuit breaker misuse (should fail properly, not fallback)
                    ('circuit.*breaker.*open.*validate', 'Circuit breaker local validation bypassing auth service'),
                    ('when.*auth.*service.*unavailable', 'Local auth when service unavailable violates SSOT'),
                    
                    # Direct JWT operations (should delegate)  
                    ('jwt.decode.*websocket', 'WebSocket direct JWT decode instead of delegation'),
                    ('_validate_jwt_locally', 'WebSocket local JWT validation method')
                ]
                
                for pattern, description in violation_patterns:
                    if pattern.lower() in content.lower():
                        websocket_violations.append(f"{description}: pattern '{pattern}' found")
                        
            except Exception as e:
                logger.warning(f"Could not scan WebSocket auth file: {e}")
        
        if websocket_violations:
            violation_summary = "\n".join([f"  - {v}" for v in websocket_violations])
            logger.error(f"SSOT DELEGATION VIOLATION: WebSocket auth bypasses auth service:")
            logger.error(violation_summary)
        
        # This test SHOULD FAIL before SSOT refactor
        assert not websocket_violations, (
            f"SSOT DELEGATION VIOLATION: WebSocket auth contains {len(websocket_violations)} "
            f"patterns that bypass auth service delegation. Violations:\n{violation_summary}"
        )

    @pytest.mark.asyncio
    async def test_auth_client_is_single_jwt_interface(self):
        """
        SSOT Interface Test: AuthClient is the single interface to auth service.
        
        EXPECTED: FAIL - Multiple JWT interfaces exist in backend
        AFTER SSOT: PASS - Only AuthClient interface exists
        
        This test verifies AuthClient is the single JWT interface.
        """
        jwt_interface_violations = []
        
        # Scan for multiple JWT interface patterns
        for file_path in (self.backend_path / "app").rglob("*.py"):
            if "__pycache__" in str(file_path) or "test" in str(file_path).lower():
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check for multiple JWT interface patterns (SSOT violation)
                interface_patterns = [
                    # Alternative JWT clients (should only be AuthClient)
                    ('class.*JWT.*Client', f'Alternative JWT client in {file_path.relative_to(self.backend_path)}'),
                    ('class.*Token.*Client', f'Alternative token client in {file_path.relative_to(self.backend_path)}'),
                    ('class.*Auth.*Handler', f'Alternative auth handler in {file_path.relative_to(self.backend_path)}'),
                    
                    # Direct JWT service calls (should go through AuthClient)
                    ('requests.*auth/validate', f'Direct auth service call in {file_path.relative_to(self.backend_path)}'),
                    ('httpx.*auth/validate', f'Direct auth service HTTP call in {file_path.relative_to(self.backend_path)}'),
                    ('post.*auth/token', f'Direct token endpoint call in {file_path.relative_to(self.backend_path)}'),
                ]
                
                for pattern, description in interface_patterns:
                    if pattern.lower() in content.lower():
                        jwt_interface_violations.append(description)
                        
            except Exception as e:
                logger.warning(f"Could not scan {file_path}: {e}")
        
        if jwt_interface_violations:
            violation_summary = "\n".join([f"  - {v}" for v in jwt_interface_violations])
            logger.error(f"SSOT INTERFACE VIOLATION: Multiple JWT interfaces found:")
            logger.error(violation_summary)
        
        # This test SHOULD FAIL before SSOT refactor
        assert not jwt_interface_violations, (
            f"SSOT INTERFACE VIOLATION: Found {len(jwt_interface_violations)} alternative JWT interfaces. "
            f"Only AuthClient should interface with auth service. Violations:\n{violation_summary}"
        )

    @pytest.mark.asyncio 
    async def test_no_jwt_fallback_mechanisms_exist(self):
        """
        SSOT Reliability Test: No JWT fallback mechanisms should exist.
        
        EXPECTED: FAIL - Backend currently has JWT fallback validation
        AFTER SSOT: PASS - Proper error handling without JWT fallbacks
        
        This test checks that auth service failures are handled properly
        without local JWT fallback mechanisms.
        """
        fallback_violations = []
        
        # Scan for JWT fallback patterns (SSOT violations)
        for file_path in (self.backend_path / "app").rglob("*.py"):
            if "__pycache__" in str(file_path) or "test" in str(file_path).lower():
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check for fallback patterns (should not exist in SSOT)
                fallback_patterns = [
                    # JWT fallback mechanisms (violate SSOT)
                    ('fallback.*jwt.*validation', f'JWT fallback validation in {file_path.relative_to(self.backend_path)}'),
                    ('local.*jwt.*when.*service.*down', f'Local JWT when service down in {file_path.relative_to(self.backend_path)}'),
                    ('backup.*jwt.*decode', f'Backup JWT decode in {file_path.relative_to(self.backend_path)}'),
                    ('emergency.*auth.*validation', f'Emergency auth validation in {file_path.relative_to(self.backend_path)}'),
                    
                    # Circuit breaker misuse (should fail fast, not fallback)
                    ('circuit.*breaker.*open.*and.*validate', f'Circuit breaker JWT fallback in {file_path.relative_to(self.backend_path)}'),
                    ('if.*auth.*service.*unavailable.*then.*jwt', f'Auth service unavailable JWT fallback in {file_path.relative_to(self.backend_path)}'),
                ]
                
                for pattern, description in fallback_patterns:
                    if pattern.lower() in content.lower():
                        fallback_violations.append(description)
                        
            except Exception as e:
                logger.warning(f"Could not scan {file_path}: {e}")
        
        if fallback_violations:
            violation_summary = "\n".join([f"  - {v}" for v in fallback_violations])
            logger.error(f"SSOT RELIABILITY VIOLATION: JWT fallback mechanisms found:")
            logger.error(violation_summary)
        
        # This test SHOULD FAIL before SSOT refactor
        assert not fallback_violations, (
            f"SSOT RELIABILITY VIOLATION: Found {len(fallback_violations)} JWT fallback mechanisms. "
            f"Auth service failures should fail fast, not fallback to local JWT. Violations:\n{violation_summary}"
        )

    @pytest.mark.asyncio
    async def test_auth_service_communication_patterns(self):
        """
        SSOT Communication Test: Proper auth service communication patterns.
        
        EXPECTED: FAIL - Improper auth service communication patterns exist  
        AFTER SSOT: PASS - Clean auth service communication via AuthClient
        
        This test validates proper auth service communication patterns.
        """
        communication_violations = []
        auth_client_path = self.backend_path / "app" / "clients" / "auth_client_core.py"
        
        if auth_client_path.exists():
            try:
                with open(auth_client_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check for communication anti-patterns
                antipattern_checks = [
                    # Proper delegation patterns (these should exist)
                    ('validate_token.*auth.*service', 'Missing proper token validation delegation'),
                    ('POST.*auth/validate', 'Missing proper auth service validation endpoint'),
                    
                    # Anti-patterns that violate SSOT  
                    ('_decode_test_jwt', 'Local test JWT decode instead of auth service delegation'),
                    ('_decode_token.*fallback', 'Token decode with fallback instead of clean delegation'),
                    ('jwt.decode.*when.*', 'Conditional JWT decode instead of clean delegation'),
                ]
                
                # Check for missing proper patterns (indicate SSOT violations)
                required_patterns = [
                    'validate_token.*auth.*service',
                    'POST.*auth/validate'
                ]
                
                for pattern in required_patterns:
                    if pattern.lower() not in content.lower():
                        communication_violations.append(f"Missing required auth delegation pattern: {pattern}")
                
                # Check for anti-patterns
                violation_patterns = [
                    '_decode_test_jwt',
                    '_decode_token',
                    'jwt.decode.*when'
                ]
                
                for pattern in violation_patterns:
                    if pattern.lower() in content.lower():
                        communication_violations.append(f"SSOT violation pattern found: {pattern}")
                        
            except Exception as e:
                logger.warning(f"Could not scan auth client file: {e}")
        
        if communication_violations:
            violation_summary = "\n".join([f"  - {v}" for v in communication_violations])
            logger.error(f"SSOT COMMUNICATION VIOLATION: Improper auth service communication:")
            logger.error(violation_summary)
        
        # This test SHOULD FAIL before SSOT refactor
        assert not communication_violations, (
            f"SSOT COMMUNICATION VIOLATION: Found {len(communication_violations)} communication issues. "
            f"Auth service communication must be clean delegation only. Violations:\n{violation_summary}"
        )

    def teardown_method(self, method):
        """Clean up after test."""
        super().teardown_method(method)
        logger.info(f"Auth service delegation test completed: {method.__name__}")