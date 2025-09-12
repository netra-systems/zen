"""
Unit Tests for WebSocket Authentication Competing Implementations Detection

These tests are designed to FAIL initially and expose the architectural conflicts
in the WebSocket authentication layer that are causing golden path issues.

Business Impact:
- $500K+ ARR at risk from broken WebSocket authentication
- Chat functionality (90% of platform value) depends on reliable auth
- Multiple auth paths create race conditions and conflicts

Test Strategy:
- Each test validates SSOT (Single Source of Truth) principles
- Tests should FAIL initially to prove they detect the issues
- Focus on detecting competing implementations, not success cases
- Validate there is only ONE auth path, not multiple competing ones
"""

import asyncio
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, Any, Optional
from fastapi import WebSocket

# SSOT base test case - all tests must inherit from this
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Import the competing auth implementations we need to test
from netra_backend.app.websocket_core.unified_websocket_auth import (
    UnifiedWebSocketAuthenticator,
    authenticate_websocket_ssot,
    authenticate_websocket_connection,
    validate_websocket_token_business_logic
)
from netra_backend.app.websocket_core.auth_remediation import (
    WebSocketAuthIntegration,
    authenticate_websocket_with_remediation
)
from netra_backend.app.websocket_core.user_context_extractor import UserContextExtractor


class TestCompetingAuthImplementations(SSotAsyncTestCase):
    """
    Unit tests to detect and expose competing auth implementations in WebSocket layer.
    
    These tests validate SSOT principles and should FAIL initially to prove
    they can detect the architectural issues causing golden path problems.
    
    Business Context:
    - WebSocket auth failures block $500K+ ARR chat functionality
    - Multiple auth paths create race conditions and inconsistent behavior
    - SSOT violations lead to maintenance complexity and security risks
    """

    def setUp(self):
        """Set up test fixtures and mock WebSocket connections."""
        super().setUp()
        
        # Create mock WebSocket connection
        self.mock_websocket = Mock(spec=WebSocket)
        self.mock_websocket.headers = {
            'authorization': 'Bearer test_token_123',
            'x-api-key': 'test_key'
        }
        self.mock_websocket.state = MagicMock()
        
        # Test tokens and user data
        self.valid_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiMTIzIiwiZXhwIjo5OTk5OTk5OTk5fQ.token"
        self.invalid_token = "invalid_token"
        
        # User context data
        self.test_user_data = {
            'user_id': '123',
            'email': 'test@example.com',
            'exp': 9999999999
        }

    async def test_multiple_auth_paths_create_conflicts(self):
        """
        Test that detects multiple authentication paths causing conflicts.
        
        This test should FAIL initially because there ARE multiple auth paths:
        1. UnifiedWebSocketAuthenticator.authenticate_websocket_connection()
        2. authenticate_websocket_ssot() function
        3. authenticate_websocket_connection() function  
        4. authenticate_websocket_with_remediation() function
        5. UserContextExtractor.validate_and_decode_jwt()
        
        Business Impact: Multiple paths cause race conditions and inconsistent auth results
        Expected Initial Result: FAIL - Multiple auth paths detected
        """
        
        # Count the different authentication entry points
        auth_methods = []
        
        # Method 1: UnifiedWebSocketAuthenticator class method
        authenticator = UnifiedWebSocketAuthenticator()
        if hasattr(authenticator, 'authenticate_websocket_connection'):
            auth_methods.append('UnifiedWebSocketAuthenticator.authenticate_websocket_connection')
        
        # Method 2: Module-level SSOT function
        if callable(authenticate_websocket_ssot):
            auth_methods.append('authenticate_websocket_ssot')
        
        # Method 3: Module-level connection function  
        if callable(authenticate_websocket_connection):
            auth_methods.append('authenticate_websocket_connection')
        
        # Method 4: Remediation function
        if callable(authenticate_websocket_with_remediation):
            auth_methods.append('authenticate_websocket_with_remediation')
            
        # Method 5: Token validation function
        if callable(validate_websocket_token_business_logic):
            auth_methods.append('validate_websocket_token_business_logic')
            
        # Method 6: User context extractor
        extractor = UserContextExtractor()
        if hasattr(extractor, 'validate_and_decode_jwt'):
            auth_methods.append('UserContextExtractor.validate_and_decode_jwt')
        
        # SSOT Principle: There should be EXACTLY ONE authentication path
        self.assertEqual(
            len(auth_methods), 1,
            f"SSOT VIOLATION: Multiple auth paths detected: {auth_methods}. "
            f"Expected exactly 1 authentication method, found {len(auth_methods)}. "
            f"This causes race conditions and conflicts in WebSocket authentication."
        )
        
        # Verify the single auth path is the expected SSOT method
        expected_ssot_method = 'authenticate_websocket_ssot'
        self.assertIn(
            expected_ssot_method, auth_methods,
            f"Expected SSOT method '{expected_ssot_method}' not found in auth methods: {auth_methods}"
        )

    async def test_auth_handler_precedence_violations(self):
        """
        Test that validates SSOT auth service precedence is maintained.
        
        This test should FAIL initially because WebSocket layer has its own
        auth logic instead of delegating to the SSOT auth service.
        
        Business Impact: Bypassing SSOT auth service creates security vulnerabilities
        Expected Initial Result: FAIL - Local auth logic detected, SSOT bypass found
        """
        
        # Check if WebSocket modules import auth service properly
        auth_service_violations = []
        
        # Test 1: UnifiedWebSocketAuthenticator should delegate to SSOT auth service
        authenticator = UnifiedWebSocketAuthenticator()
        
        # Mock the SSOT auth service
        with patch('netra_backend.app.services.unified_authentication_service.get_unified_auth_service') as mock_auth_service:
            mock_auth_service.return_value.validate_token.return_value = {'user_id': '123', 'valid': True}
            
            # If this method does its own JWT validation instead of using auth service, it's a violation
            try:
                # This should fail if there's local JWT validation logic
                with patch('jwt.decode') as mock_jwt:
                    mock_jwt.return_value = self.test_user_data
                    
                    # If this succeeds, it means there's local JWT logic (SSOT violation)
                    result = await authenticate_websocket_ssot(self.mock_websocket, self.valid_token)
                    if result and hasattr(result, 'success') and result.success:
                        auth_service_violations.append('Local JWT decode logic found in authenticate_websocket_ssot')
                        
            except Exception:
                pass  # Good, should fail without auth service
        
        # Test 2: Check for direct JWT imports (SSOT violation)
        try:
            import inspect
            import netra_backend.app.websocket_core.unified_websocket_auth as auth_module
            
            source = inspect.getsource(auth_module)
            if 'import jwt' in source or 'from jwt import' in source:
                auth_service_violations.append('Direct JWT import found in unified_websocket_auth module')
                
        except Exception:
            pass
        
        # Test 3: UserContextExtractor should not have local JWT logic
        extractor = UserContextExtractor()
        with patch('jwt.decode') as mock_jwt:
            mock_jwt.return_value = self.test_user_data
            
            try:
                result = await extractor.validate_and_decode_jwt(self.valid_token)
                if result:
                    auth_service_violations.append('UserContextExtractor has local JWT validation logic')
            except Exception:
                pass  # Good, should fail without auth service
        
        # SSOT Principle: All auth must go through SSOT auth service
        self.assertEqual(
            len(auth_service_violations), 0,
            f"SSOT AUTH SERVICE VIOLATIONS detected: {auth_service_violations}. "
            f"All authentication must delegate to the SSOT auth service, not implement local logic."
        )

    async def test_competing_token_validation_logic(self):
        """
        Test that detects duplicate token validation implementations.
        
        This test should FAIL initially because there are multiple places
        implementing JWT token validation logic instead of using SSOT.
        
        Business Impact: Duplicate validation logic leads to inconsistent results
        Expected Initial Result: FAIL - Multiple token validation implementations found
        """
        
        validation_methods = []
        
        # Method 1: validate_websocket_token_business_logic function
        if callable(validate_websocket_token_business_logic):
            validation_methods.append('validate_websocket_token_business_logic')
        
        # Method 2: UserContextExtractor.validate_and_decode_jwt
        extractor = UserContextExtractor()
        if hasattr(extractor, 'validate_and_decode_jwt'):
            validation_methods.append('UserContextExtractor.validate_and_decode_jwt')
        
        # Method 3: UnifiedWebSocketAuthenticator internal validation
        authenticator = UnifiedWebSocketAuthenticator()
        if hasattr(authenticator, '_validate_token') or hasattr(authenticator, 'validate_token'):
            validation_methods.append('UnifiedWebSocketAuthenticator token validation')
        
        # Method 4: Check for JWT validation in auth_remediation
        auth_integration = WebSocketAuthIntegration()
        if hasattr(auth_integration, 'validate_token') or hasattr(auth_integration, '_decode_token'):
            validation_methods.append('WebSocketAuthIntegration token validation')
        
        # Test for direct JWT operations (SSOT violations)
        jwt_violations = []
        
        # Check modules for direct JWT usage
        modules_to_check = [
            'netra_backend.app.websocket_core.unified_websocket_auth',
            'netra_backend.app.websocket_core.user_context_extractor',
            'netra_backend.app.websocket_core.auth_remediation'
        ]
        
        for module_name in modules_to_check:
            try:
                import importlib
                import inspect
                module = importlib.import_module(module_name)
                source = inspect.getsource(module)
                
                if 'jwt.decode' in source or 'jwt.encode' in source:
                    jwt_violations.append(f'{module_name} contains direct JWT operations')
                    
            except Exception:
                continue
        
        # SSOT Principle: Token validation should be in ONE place only
        total_validation_methods = len(validation_methods) + len(jwt_violations)
        
        self.assertEqual(
            total_validation_methods, 1,
            f"DUPLICATE TOKEN VALIDATION DETECTED: "
            f"Validation methods: {validation_methods}, "
            f"JWT violations: {jwt_violations}. "
            f"Expected exactly 1 token validation implementation, found {total_validation_methods}. "
            f"This creates inconsistent validation behavior and maintenance complexity."
        )

    async def test_auth_method_resolution_order(self):
        """
        Test that validates single method resolution chain for authentication.
        
        This test should FAIL initially because there are multiple auth classes
        and functions that can be called, creating ambiguity about which one
        takes precedence.
        
        Business Impact: Ambiguous method resolution leads to unpredictable auth results
        Expected Initial Result: FAIL - Multiple auth entry points without clear precedence
        """
        
        # Test different ways authentication can be invoked
        auth_entry_points = []
        
        # Entry point 1: Direct class instantiation
        try:
            authenticator = UnifiedWebSocketAuthenticator()
            if hasattr(authenticator, 'authenticate_websocket_connection'):
                auth_entry_points.append({
                    'type': 'class_method',
                    'name': 'UnifiedWebSocketAuthenticator.authenticate_websocket_connection',
                    'instance': authenticator
                })
        except Exception:
            pass
        
        # Entry point 2: Module-level functions
        for func_name, func in [
            ('authenticate_websocket_ssot', authenticate_websocket_ssot),
            ('authenticate_websocket_connection', authenticate_websocket_connection),
            ('authenticate_websocket_with_remediation', authenticate_websocket_with_remediation)
        ]:
            if callable(func):
                auth_entry_points.append({
                    'type': 'function',
                    'name': func_name,
                    'callable': func
                })
        
        # Entry point 3: Integration class
        try:
            integration = WebSocketAuthIntegration()
            if hasattr(integration, 'authenticate_websocket_connection'):
                auth_entry_points.append({
                    'type': 'integration_method',
                    'name': 'WebSocketAuthIntegration.authenticate_websocket_connection',
                    'instance': integration
                })
        except Exception:
            pass
        
        # Test method resolution ambiguity
        if len(auth_entry_points) > 1:
            # Try calling each entry point to see if they give different results
            results = []
            
            for entry_point in auth_entry_points[:3]:  # Limit to first 3 to avoid long test
                try:
                    if entry_point['type'] == 'class_method':
                        # Mock the method to return a predictable result
                        with patch.object(entry_point['instance'], 'authenticate_websocket_connection') as mock_method:
                            mock_method.return_value = AsyncMock(success=True, user_id='123')
                            result = await mock_method(self.mock_websocket, self.valid_token)
                            results.append((entry_point['name'], 'class_method_success'))
                    
                    elif entry_point['type'] == 'function':
                        with patch(f"netra_backend.app.websocket_core.unified_websocket_auth.{entry_point['name']}") as mock_func:
                            mock_func.return_value = AsyncMock(success=True, user_id='123')
                            result = await mock_func(self.mock_websocket, self.valid_token)
                            results.append((entry_point['name'], 'function_success'))
                    
                    elif entry_point['type'] == 'integration_method':
                        with patch.object(entry_point['instance'], 'authenticate_websocket_connection') as mock_method:
                            mock_method.return_value = (True, Mock(), None)
                            result = await mock_method(self.valid_token, 'conn_123')
                            results.append((entry_point['name'], 'integration_success'))
                            
                except Exception as e:
                    results.append((entry_point['name'], f'error_{type(e).__name__}'))
        
        # SSOT Principle: There should be ONE clear authentication entry point
        self.assertEqual(
            len(auth_entry_points), 1,
            f"METHOD RESOLUTION AMBIGUITY DETECTED: "
            f"Found {len(auth_entry_points)} auth entry points: "
            f"{[ep['name'] for ep in auth_entry_points]}. "
            f"Expected exactly 1 clear authentication entry point. "
            f"Multiple entry points create ambiguity and unpredictable behavior."
        )
        
        # If we have exactly one entry point, it should be the SSOT method
        if len(auth_entry_points) == 1:
            expected_ssot_entry_point = 'authenticate_websocket_ssot'
            actual_entry_point = auth_entry_points[0]['name']
            
            self.assertEqual(
                actual_entry_point, expected_ssot_entry_point,
                f"Expected SSOT entry point '{expected_ssot_entry_point}', "
                f"but found '{actual_entry_point}'. "
                f"The single entry point should be the designated SSOT method."
            )

    async def test_auth_configuration_consistency(self):
        """
        Test that validates authentication configuration is consistent across implementations.
        
        This test should FAIL initially because different auth implementations
        may have different configuration sources and defaults.
        
        Business Impact: Inconsistent configuration leads to unpredictable auth behavior
        Expected Initial Result: FAIL - Configuration inconsistencies detected
        """
        
        config_sources = []
        
        # Test 1: UnifiedWebSocketAuthenticator configuration
        try:
            authenticator = UnifiedWebSocketAuthenticator()
            if hasattr(authenticator, 'config') or hasattr(authenticator, '_config'):
                config_sources.append('UnifiedWebSocketAuthenticator has its own config')
        except Exception:
            pass
        
        # Test 2: WebSocketAuthIntegration configuration
        try:
            integration = WebSocketAuthIntegration()
            if hasattr(integration, 'config'):
                config_sources.append('WebSocketAuthIntegration has its own config')
        except Exception:
            pass
        
        # Test 3: UserContextExtractor configuration
        try:
            extractor = UserContextExtractor()
            if hasattr(extractor, 'config') or hasattr(extractor, '_config'):
                config_sources.append('UserContextExtractor has its own config')
        except Exception:
            pass
        
        # Test 4: Check for hardcoded configuration values
        hardcoded_configs = []
        
        modules_to_check = [
            'netra_backend.app.websocket_core.unified_websocket_auth',
            'netra_backend.app.websocket_core.user_context_extractor', 
            'netra_backend.app.websocket_core.auth_remediation'
        ]
        
        for module_name in modules_to_check:
            try:
                import importlib
                import inspect
                module = importlib.import_module(module_name)
                source = inspect.getsource(module)
                
                # Look for hardcoded timeouts, retry counts, etc.
                hardcoded_patterns = [
                    'timeout=15', 'timeout = 15',
                    'retries=3', 'retries = 3',  
                    'max_attempts=', 'max_retries='
                ]
                
                for pattern in hardcoded_patterns:
                    if pattern in source:
                        hardcoded_configs.append(f'{module_name} contains hardcoded config: {pattern}')
                        
            except Exception:
                continue
        
        total_config_issues = len(config_sources) + len(hardcoded_configs)
        
        # SSOT Principle: Configuration should come from ONE centralized source
        self.assertEqual(
            total_config_issues, 0,
            f"AUTH CONFIGURATION INCONSISTENCIES DETECTED: "
            f"Multiple config sources: {config_sources}, "
            f"Hardcoded configs: {hardcoded_configs}. "
            f"All auth configuration should come from a single, centralized source."
        )

    async def test_auth_state_management_conflicts(self):
        """
        Test that detects conflicting authentication state management.
        
        This test should FAIL initially because different auth implementations
        may maintain their own state, leading to inconsistencies.
        
        Business Impact: State conflicts cause auth failures and security issues
        Expected Initial Result: FAIL - Multiple auth state management systems detected
        """
        
        state_managers = []
        
        # Test 1: Check for authentication state in different classes
        try:
            authenticator = UnifiedWebSocketAuthenticator()
            state_attrs = ['_auth_cache', '_token_cache', '_user_cache', '_session_cache',
                          'auth_state', 'token_state', 'session_state', '_connections']
            
            for attr in state_attrs:
                if hasattr(authenticator, attr):
                    state_managers.append(f'UnifiedWebSocketAuthenticator.{attr}')
        except Exception:
            pass
        
        # Test 2: Check WebSocketAuthIntegration state
        try:
            integration = WebSocketAuthIntegration()
            state_attrs = ['_connections', '_sessions', '_auth_cache', 'connection_state']
            
            for attr in state_attrs:
                if hasattr(integration, attr):
                    state_managers.append(f'WebSocketAuthIntegration.{attr}')
        except Exception:
            pass
        
        # Test 3: Check for module-level state
        try:
            import netra_backend.app.websocket_core.unified_websocket_auth as auth_module
            
            module_attrs = ['_global_auth_cache', '_connection_registry', '_session_store',
                           'ACTIVE_CONNECTIONS', 'AUTH_CACHE', 'TOKEN_CACHE']
            
            for attr in module_attrs:
                if hasattr(auth_module, attr):
                    state_managers.append(f'unified_websocket_auth.{attr}')
        except Exception:
            pass
        
        # SSOT Principle: Authentication state should be managed in ONE place
        self.assertEqual(
            len(state_managers), 0,
            f"AUTHENTICATION STATE CONFLICTS DETECTED: "
            f"Multiple state management systems found: {state_managers}. "
            f"Authentication state should be managed by a single, centralized system. "
            f"Multiple state managers cause synchronization issues and security vulnerabilities."
        )


if __name__ == '__main__':
    # Run the tests to see them fail and expose the issues
    pytest.main([__file__, '-v', '--tb=short'])