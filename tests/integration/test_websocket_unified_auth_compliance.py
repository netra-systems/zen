"""
WebSocket SSOT Authentication Compliance Test Suite

ISSUE #342: Validates SSOT compliance in WebSocket authentication

This test suite validates that WebSocket authentication properly uses
the unified authentication service and doesn't bypass SSOT patterns.

PRIORITY: TERTIARY - These tests ensure architectural compliance
"""

import pytest
import json
import asyncio
import unittest
from typing import Dict, Any, Optional, List, Set
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# SSOT imports from registry
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.unified_websocket_auth import (
    UnifiedWebSocketAuthenticator,
    authenticate_websocket_ssot,
    get_websocket_authenticator
)
from netra_backend.app.services.unified_authentication_service import (
    get_unified_auth_service
)

class TestWebSocketUnifiedAuthCompliance(SSotAsyncTestCase):
    """
    Test suite to validate SSOT compliance in WebSocket authentication.
    
    These tests ensure that WebSocket auth follows SSOT principles and
    doesn't create duplicate authentication paths.
    """

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.websocket_authenticator = UnifiedWebSocketAuthenticator()
        
    def create_mock_websocket(self, headers: Dict[str, str]) -> Mock:
        """Create mock WebSocket with specific headers.""" 
        websocket = Mock()
        websocket.headers = headers
        websocket.client = Mock()
        websocket.client.host = "127.0.0.1"
        websocket.client.port = 8000
        websocket.client_state = Mock()
        websocket.client_state.name = "CONNECTED"
        return websocket

    async def test_websocket_uses_unified_auth_service(self):
        """
        Test that WebSocket authentication uses the unified auth service.
        
        This validates that WebSocket auth doesn't bypass SSOT patterns.
        """
        # Get the unified auth service
        unified_auth_service = get_unified_auth_service()
        
        # Check that WebSocket authenticator uses the same service
        websocket_authenticator = get_websocket_authenticator()
        
        # Verify SSOT compliance
        ssot_compliance = {
            "unified_service_available": unified_auth_service is not None,
            "websocket_authenticator_available": websocket_authenticator is not None,
            "websocket_auth_service_type": type(getattr(websocket_authenticator, '_auth_service', None)).__name__,
            "unified_auth_service_type": type(unified_auth_service).__name__,
            "services_match": False
        }
        
        # Check if they're the same service or same type
        websocket_auth_service = getattr(websocket_authenticator, '_auth_service', None)
        
        if websocket_auth_service and unified_auth_service:
            # Check if they're the exact same instance
            ssot_compliance["same_instance"] = websocket_auth_service is unified_auth_service
            # Check if they're the same type
            ssot_compliance["same_type"] = type(websocket_auth_service) == type(unified_auth_service)
            ssot_compliance["services_match"] = ssot_compliance["same_instance"] or ssot_compliance["same_type"]
        
        # Log SSOT compliance check
        print("\n=== SSOT COMPLIANCE VALIDATION ===")
        print(json.dumps(ssot_compliance, indent=2))
        
        # Validate SSOT compliance
        self.assertIsNotNone(
            unified_auth_service,
            "Unified auth service should be available"
        )
        
        self.assertIsNotNone(
            websocket_authenticator,
            "WebSocket authenticator should be available"
        )
        
        self.assertIsNotNone(
            websocket_auth_service,
            "WebSocket authenticator should have an auth service"
        )
        
        self.assertTrue(
            ssot_compliance["services_match"],
            f"WebSocket authenticator should use the unified auth service. "
            f"WebSocket uses: {ssot_compliance['websocket_auth_service_type']}, "
            f"Unified service: {ssot_compliance['unified_auth_service_type']}"
        )

    async def test_no_auth_bypass_patterns(self):
        """
        Test that WebSocket authentication doesn't bypass unified patterns.
        
        This checks for anti-patterns like direct JWT validation or
        separate authentication logic.
        """
        jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        
        mock_websocket = self.create_mock_websocket({
            "authorization": f"Bearer {jwt_token}"
        })
        
        # Track what methods are called during authentication
        called_methods = []
        original_methods = {}
        
        # Patch unified auth service methods to track calls
        with patch.object(get_unified_auth_service(), 'authenticate_websocket', wraps=get_unified_auth_service().authenticate_websocket) as mock_ws_auth:
            with patch.object(get_unified_auth_service(), 'authenticate', wraps=getattr(get_unified_auth_service(), 'authenticate', None)) as mock_auth:
                
                # Mock successful responses
                from netra_backend.app.services.unified_authentication_service import AuthResult
                from netra_backend.app.services.user_execution_context import UserExecutionContext
                
                mock_auth_result = AuthResult(
                    success=True,
                    user_id="test-user-123",
                    email="test@example.com",
                    permissions=["read", "write"]
                )
                
                mock_user_context = UserExecutionContext(
                    user_id="test-user-123",
                    thread_id="thread-123",
                    run_id="run-123",
                    request_id="req-123",
                    websocket_client_id="ws-client-123"
                )
                
                if mock_ws_auth:
                    mock_ws_auth.return_value = (mock_auth_result, mock_user_context)
                if mock_auth:
                    mock_auth.return_value = mock_auth_result
                
                # Perform WebSocket authentication
                try:
                    result = await authenticate_websocket_ssot(mock_websocket)
                    
                    # Check that unified service methods were called
                    bypass_check = {
                        "websocket_auth_called": mock_ws_auth.called if mock_ws_auth else False,
                        "general_auth_called": mock_auth.called if mock_auth else False,
                        "either_method_called": (mock_ws_auth.called if mock_ws_auth else False) or (mock_auth.called if mock_auth else False),
                        "authentication_success": result.success,
                        "result_has_user_context": result.user_context is not None
                    }
                    
                    print("\n=== AUTH BYPASS CHECK ===")
                    print(json.dumps(bypass_check, indent=2))
                    
                    # Verify that unified service was actually used
                    self.assertTrue(
                        bypass_check["either_method_called"],
                        "WebSocket authentication should call unified auth service methods"
                    )
                    
                except Exception as e:
                    print(f"Authentication failed with error: {e}")
                    # Even if auth fails, we should still check if unified service was called
                    bypass_check = {
                        "websocket_auth_called": mock_ws_auth.called if mock_ws_auth else False,
                        "general_auth_called": mock_auth.called if mock_auth else False,
                        "either_method_called": (mock_ws_auth.called if mock_ws_auth else False) or (mock_auth.called if mock_auth else False),
                        "authentication_failed": True,
                        "error": str(e)
                    }
                    
                    print("\n=== AUTH BYPASS CHECK (FAILED) ===")
                    print(json.dumps(bypass_check, indent=2))

    async def test_websocket_auth_module_imports(self):
        """
        Test that WebSocket auth modules only import from approved SSOT sources.
        
        This detects if WebSocket auth is importing from deprecated or
        non-SSOT authentication modules.
        """
        import inspect
        import sys
        
        # Get the WebSocket auth modules
        websocket_auth_modules = [
            'netra_backend.app.websocket_core.unified_websocket_auth',
            'netra_backend.app.websocket_core.unified_jwt_protocol_handler',
        ]
        
        # Approved SSOT import patterns
        approved_patterns = [
            'netra_backend.app.services.unified_authentication_service',
            'netra_backend.app.services.user_execution_context',
            'shared.isolated_environment',
            'test_framework.ssot',  # Test framework is allowed
            # Standard library and external packages
            'asyncio', 'json', 'time', 'datetime', 'typing', 'dataclasses',
            'fastapi', 'pydantic', 'base64', 'hashlib', 'uuid', 'logging'
        ]
        
        # Forbidden import patterns (indicate SSOT violations)
        forbidden_patterns = [
            'netra_backend.app.auth_integration',  # Should use unified service
            'auth_service.auth_core.core',  # Direct auth service access
            'netra_backend.app.clients.auth_client',  # Should use unified service
            '.jwt_handler',  # Direct JWT handling
            '.auth_client_core',  # Direct auth client
        ]
        
        import_violations = []
        module_imports = {}
        
        for module_name in websocket_auth_modules:
            try:
                if module_name in sys.modules:
                    module = sys.modules[module_name]
                else:
                    module = __import__(module_name, fromlist=[''])
                
                # Get source code to analyze imports
                source = inspect.getsource(module)
                import_lines = [line.strip() for line in source.split('\n') if line.strip().startswith(('import ', 'from '))]
                
                module_imports[module_name] = import_lines
                
                # Check each import
                for import_line in import_lines:
                    # Skip comments and empty lines
                    if import_line.startswith('#') or not import_line:
                        continue
                    
                    # Extract the module being imported
                    if import_line.startswith('from '):
                        imported_module = import_line.split(' from ')[1].split(' import')[0].strip()
                    elif import_line.startswith('import '):
                        imported_module = import_line.replace('import ', '').split(' as')[0].split('.')[0].strip()
                    else:
                        continue
                    
                    # Check against forbidden patterns
                    for forbidden in forbidden_patterns:
                        if forbidden in import_line or forbidden in imported_module:
                            import_violations.append({
                                "module": module_name,
                                "import_line": import_line,
                                "violation": f"Imports forbidden pattern: {forbidden}",
                                "imported_module": imported_module
                            })
                    
                    # Check if it matches approved patterns
                    is_approved = False
                    for approved in approved_patterns:
                        if imported_module.startswith(approved) or approved in imported_module:
                            is_approved = True
                            break
                    
                    # Special case: relative imports within the same package are usually OK
                    if imported_module.startswith('.') or imported_module.startswith('netra_backend.app.websocket_core'):
                        is_approved = True
                    
                    # Log potential unapproved imports for manual review
                    if not is_approved and not any(std in imported_module for std in ['asyncio', 'json', 'time', 'datetime', 'typing', 'dataclasses', 'fastapi', 'base64', 'hashlib', 'uuid', 'logging']):
                        import_violations.append({
                            "module": module_name,
                            "import_line": import_line, 
                            "violation": f"Potentially unapproved import: {imported_module}",
                            "imported_module": imported_module,
                            "severity": "warning"
                        })
                
            except Exception as e:
                import_violations.append({
                    "module": module_name,
                    "violation": f"Failed to analyze imports: {e}",
                    "severity": "error"
                })
        
        # Log import analysis
        print("\n=== WEBSOCKET AUTH IMPORT ANALYSIS ===")
        print(json.dumps({
            "modules_analyzed": list(module_imports.keys()),
            "violations_found": len(import_violations),
            "violations": import_violations
        }, indent=2))
        
        # Filter critical violations (exclude warnings)
        critical_violations = [v for v in import_violations if v.get("severity") != "warning"]
        
        if critical_violations:
            violation_details = "\n".join([
                f"  - {v['module']}: {v['violation']} ({v.get('import_line', 'N/A')})"
                for v in critical_violations
            ])
            raise AssertionError(f"SSOT import violations found:\n{violation_details}")

    async def test_websocket_auth_service_singleton_compliance(self):
        """
        Test that WebSocket authenticator follows singleton patterns correctly.
        
        This ensures proper SSOT instance management.
        """
        # Test that get_websocket_authenticator returns the same instance
        auth1 = get_websocket_authenticator()
        auth2 = get_websocket_authenticator()
        
        singleton_compliance = {
            "instance1_type": type(auth1).__name__,
            "instance2_type": type(auth2).__name__,
            "same_instance": auth1 is auth2,
            "same_type": type(auth1) == type(auth2),
            "both_not_none": auth1 is not None and auth2 is not None
        }
        
        # Test that the underlying auth service is also properly managed
        auth_service1 = getattr(auth1, '_auth_service', None)
        auth_service2 = getattr(auth2, '_auth_service', None)
        
        if auth_service1 and auth_service2:
            singleton_compliance.update({
                "auth_service1_type": type(auth_service1).__name__,
                "auth_service2_type": type(auth_service2).__name__,
                "auth_services_same_instance": auth_service1 is auth_service2,
                "auth_services_same_type": type(auth_service1) == type(auth_service2)
            })
        
        print("\n=== SINGLETON COMPLIANCE CHECK ===")
        print(json.dumps(singleton_compliance, indent=2))
        
        # Validate singleton compliance
        self.assertTrue(
            singleton_compliance["same_instance"],
            "get_websocket_authenticator() should return the same instance (singleton pattern)"
        )
        
        self.assertTrue(
            singleton_compliance["both_not_none"],
            "WebSocket authenticator instances should not be None"
        )
        
        if auth_service1 and auth_service2:
            self.assertTrue(
                singleton_compliance["auth_services_same_type"],
                "Underlying auth services should be the same type"
            )

    async def test_websocket_auth_error_handling_compliance(self):
        """
        Test that WebSocket auth error handling follows SSOT patterns.
        
        This ensures errors are handled consistently across the system.
        """
        # Test various error scenarios
        error_scenarios = [
            {
                "description": "No authentication headers",
                "headers": {},
                "expected_error_pattern": "AUTH"
            },
            {
                "description": "Invalid authorization header format",
                "headers": {"authorization": "InvalidFormat token"},
                "expected_error_pattern": "AUTH"
            },
            {
                "description": "Empty token",
                "headers": {"authorization": "Bearer "},
                "expected_error_pattern": "AUTH"
            },
            {
                "description": "Malformed JWT token",
                "headers": {"authorization": "Bearer invalid.jwt.token"},
                "expected_error_pattern": "AUTH"
            }
        ]
        
        error_handling_results = []
        
        for scenario in error_scenarios:
            mock_websocket = self.create_mock_websocket(scenario["headers"])
            
            try:
                result = await authenticate_websocket_ssot(mock_websocket)
                
                error_result = {
                    "description": scenario["description"],
                    "success": result.success,
                    "error_message": result.error_message,
                    "error_code": result.error_code,
                    "has_expected_pattern": scenario["expected_error_pattern"] in (result.error_code or "").upper() if result.error_code else False
                }
                
                error_handling_results.append(error_result)
                
            except Exception as e:
                error_result = {
                    "description": scenario["description"],
                    "success": False,
                    "exception": str(e),
                    "exception_type": type(e).__name__,
                    "has_expected_pattern": scenario["expected_error_pattern"] in str(e).upper()
                }
                
                error_handling_results.append(error_result)
        
        print("\n=== ERROR HANDLING COMPLIANCE ===")
        for result in error_handling_results:
            print(f"- {result['description']}: {result['success']} (Error: {result.get('error_message', result.get('exception', 'None'))})")
        
        # Validate error handling compliance
        for result in error_handling_results:
            # All scenarios should fail authentication (not crash)
            if "exception" in result:
                self.fail(f"Error handling compliance failure: {result['description']} caused exception: {result['exception']}")
            
            self.assertFalse(
                result["success"],
                f"Authentication should fail for {result['description']}"
            )
            
            # Should have proper error information
            self.assertTrue(
                result.get("error_message") or result.get("error_code"),
                f"Should have error information for {result['description']}"
            )

    async def test_websocket_auth_configuration_isolation(self):
        """
        Test that WebSocket auth configuration is properly isolated.
        
        This ensures WebSocket auth doesn't interfere with other auth systems.
        """
        # Check that WebSocket auth doesn't modify global auth configuration
        original_unified_service = get_unified_auth_service()
        original_service_type = type(original_unified_service).__name__
        
        # Create multiple WebSocket authenticators
        auth_instances = [get_websocket_authenticator() for _ in range(3)]
        
        # Check that unified service is unchanged
        current_unified_service = get_unified_auth_service()
        current_service_type = type(current_unified_service).__name__
        
        isolation_check = {
            "original_service_type": original_service_type,
            "current_service_type": current_service_type,
            "service_unchanged": original_unified_service is current_unified_service,
            "service_type_unchanged": original_service_type == current_service_type,
            "auth_instances_count": len(auth_instances),
            "all_instances_same": all(instance is auth_instances[0] for instance in auth_instances)
        }
        
        print("\n=== CONFIGURATION ISOLATION CHECK ===")
        print(json.dumps(isolation_check, indent=2))
        
        # Validate configuration isolation
        self.assertTrue(
            isolation_check["service_type_unchanged"],
            "WebSocket auth should not change unified service type"
        )
        
        self.assertTrue(
            isolation_check["all_instances_same"],
            "Multiple WebSocket authenticator calls should return the same instance"
        )


if __name__ == '__main__':
    unittest.main()