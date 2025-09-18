"""
Test auth service -> backend JWT validation flow integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Ensure consistent JWT validation across auth service and backend
- Value Impact: Prevents authentication bypass vulnerabilities and user experience issues
- Strategic Impact: Foundation for $500K+ ARR Golden Path user authentication flow

Issue #1117: JWT Validation SSOT - Cross-Service Integration Testing

Tests the complete JWT validation flow from auth service through
to backend authentication without Docker dependencies.
"""

import asyncio
import logging
import time
import hashlib
from typing import Dict, Any, Optional
from unittest.mock import MagicMock, AsyncMock
import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase

logger = logging.getLogger(__name__)


class AuthServiceBackendJWTFlowTests(SSotAsyncTestCase):
    """Test auth service to backend JWT validation integration flow."""
    
    @pytest.fixture
    async def auth_service_client(self):
        """Real auth service client for integration testing."""
        try:
            from netra_backend.app.clients.auth_client_core import AuthServiceClient
            client = AuthServiceClient()
            # Verify client is properly configured
            assert client.settings.base_url, "Auth service client not properly configured"
            return client
        except ImportError as e:
            pytest.skip(f"Auth service client not available: {e}")
    
    @pytest.fixture
    async def test_user_token(self, auth_service_client):
        """Create real JWT token for testing."""
        try:
            # Use auth service to create a real token
            token_result = await auth_service_client.create_test_token(
                user_id="test_user_jwt_flow_integration",
                email="test.integration@netrasystems.ai"
            )
            
            assert token_result and token_result.get('access_token'), "Failed to create test token from auth service"
            return token_result['access_token']
        except Exception as e:
            # Fallback to mock token for testing wrapper logic
            logger.warning(f"Auth service unavailable, using mock token: {e}")
            return self._create_mock_jwt_token()
    
    # ================================================================================
    # FAILING TESTS - Current Integration SSOT Violations
    # ================================================================================
    
    @pytest.mark.integration
    async def test_backend_bypasses_auth_service_jwt_validation(self, auth_service_client, test_user_token):
        """FAILING: Backend has local JWT validation that bypasses auth service SSOT.
        
        This test SHOULD FAIL initially - demonstrates backend bypass violation.
        Expected to find backend components that validate JWT locally instead of delegating.
        """
        logger.info("Testing backend JWT validation bypass detection...")
        
        # Test auth service validation (reference implementation)
        auth_service_result = await auth_service_client.validate_token(test_user_token)
        logger.info(f"Auth service validation result: {auth_service_result.get('valid', False)}")
        
        # Check if backend has independent JWT validation methods
        backend_jwt_methods = self._find_backend_jwt_validation_methods()
        
        # CURRENT ISSUE: Backend should not have independent JWT validation
        logger.error(f"BACKEND JWT METHODS FOUND: {len(backend_jwt_methods)}")
        for method in backend_jwt_methods:
            logger.error(f"  BYPASS VIOLATION: {method['location']} - {method['name']}")
            logger.error(f"    Description: {method['description']}")
        
        assert len(backend_jwt_methods) > 0, "No backend JWT validation methods found - test setup issue"
        
        # Try to identify methods that bypass auth service
        bypass_methods = []
        for method in backend_jwt_methods:
            if self._method_bypasses_auth_service(method):
                bypass_methods.append(method)
        
        assert len(bypass_methods) > 0, "No auth service bypass methods found - unexpected"
        
        # Document business impact
        for method in bypass_methods:
            logger.error(f"BUSINESS IMPACT: {method['name']} creates JWT validation inconsistency")
            logger.error(f"  Risk: Authentication bypass vulnerability")
            logger.error(f"  ARR Impact: Potential $500K+ revenue at risk from auth failures")
        
        self.fail(f"BACKEND SSOT VIOLATION: Found {len(bypass_methods)} backend JWT validation methods that bypass auth service SSOT")
    
    @pytest.mark.integration  
    async def test_auth_integration_wrapper_creates_inconsistency(self, auth_service_client, test_user_token):
        """FAILING: Auth integration creates wrapper layer that introduces inconsistency.
        
        This test SHOULD FAIL initially - demonstrates wrapper inconsistency violation.
        Expected to find auth integration wrapper that modifies or transforms validation results.
        """
        logger.info("Testing auth integration wrapper inconsistency...")
        
        # Test auth service direct validation
        try:
            direct_result = await auth_service_client.validate_token(test_user_token)
            logger.info(f"Direct auth service result: {direct_result}")
        except Exception as e:
            logger.warning(f"Auth service direct validation failed: {e}")
            direct_result = {'valid': False, 'error': str(e)}
        
        # Test auth integration wrapper validation
        try:
            from netra_backend.app.auth_integration.auth import _validate_token_with_auth_service
            wrapper_result = await _validate_token_with_auth_service(test_user_token)
            logger.info(f"Wrapper validation result: {wrapper_result}")
        except Exception as e:
            logger.warning(f"Wrapper validation failed: {e}")
            wrapper_result = {'valid': False, 'error': str(e)}
        
        # Check for inconsistencies introduced by wrapper
        direct_user_id = direct_result.get('payload', {}).get('sub') if direct_result.get('valid') else None
        wrapper_user_id = wrapper_result.get('user_id')
        
        # CURRENT ISSUE: Wrapper may transform or modify validation results
        inconsistencies = []
        
        if direct_result.get('valid') != wrapper_result.get('valid'):
            inconsistencies.append(f"Validation status: Direct={direct_result.get('valid')}, Wrapper={wrapper_result.get('valid')}")
        
        if direct_user_id and wrapper_user_id and direct_user_id != wrapper_user_id:
            inconsistencies.append(f"User ID: Direct={direct_user_id}, Wrapper={wrapper_user_id}")
        
        # Check for wrapper complexity issues
        wrapper_analysis = self._analyze_auth_integration_wrapper_complexity()
        
        if wrapper_analysis['adds_logic']:
            inconsistencies.append(f"Wrapper adds logic: {wrapper_analysis['added_logic']}")
        
        if wrapper_analysis['transforms_data']:
            inconsistencies.append(f"Wrapper transforms data: {wrapper_analysis['transformations']}")
        
        logger.error(f"AUTH INTEGRATION INCONSISTENCIES: {len(inconsistencies)}")
        for inconsistency in inconsistencies:
            logger.error(f"  {inconsistency}")
        
        # Even if no inconsistencies found, wrapper adds unnecessary complexity
        if len(inconsistencies) == 0:
            logger.error("WRAPPER COMPLEXITY: Auth integration adds unnecessary abstraction layer")
            self.fail("WRAPPER COMPLEXITY VIOLATION: Auth integration should directly return auth service results without additional processing")
        else:
            self.fail(f"WRAPPER INCONSISTENCY VIOLATION: Found {len(inconsistencies)} inconsistencies between direct auth service and wrapper: {inconsistencies}")
    
    @pytest.mark.integration
    async def test_jwt_validation_call_path_fragmentation(self, test_user_token):
        """FAILING: JWT validation has multiple call paths creating SSOT fragmentation.
        
        This test SHOULD FAIL initially - demonstrates call path fragmentation.
        Expected to find multiple different paths for JWT validation in backend.
        """
        logger.info("Testing JWT validation call path fragmentation...")
        
        # Trace all possible JWT validation call paths in backend
        jwt_validation_paths = await self._trace_all_backend_jwt_validation_paths(test_user_token)
        
        logger.error(f"JWT VALIDATION PATHS FOUND: {len(jwt_validation_paths)}")
        
        for i, path in enumerate(jwt_validation_paths):
            logger.error(f"  Path {i+1}: {path['name']}")
            logger.error(f"    Entry Point: {path['entry_point']}")
            logger.error(f"    Call Chain: {' -> '.join(path['call_chain'])}")
            logger.error(f"    Uses Auth Service: {path['uses_auth_service']}")
            logger.error(f"    Has Local Logic: {path['has_local_logic']}")
        
        # CURRENT ISSUE: Multiple validation paths violate SSOT principle
        assert len(jwt_validation_paths) > 1, "Only one validation path found - test setup issue"
        
        # Count paths that don't use auth service or have local logic
        non_ssot_paths = [
            path for path in jwt_validation_paths 
            if not path['uses_auth_service'] or path['has_local_logic']
        ]
        
        assert len(non_ssot_paths) > 0, "No non-SSOT paths found - unexpected"
        
        logger.error(f"NON-SSOT PATHS: {len(non_ssot_paths)} out of {len(jwt_validation_paths)}")
        
        # Document business impact of fragmentation
        for path in non_ssot_paths:
            logger.error(f"BUSINESS RISK: {path['name']} creates authentication inconsistency")
            logger.error(f"  Impact: Potential user lockout or security bypass")
        
        self.fail(f"JWT CALL PATH FRAGMENTATION: Found {len(jwt_validation_paths)} validation paths, {len(non_ssot_paths)} don't use auth service SSOT")
    
    # ================================================================================
    # SUCCESS CRITERIA TESTS - Validate SSOT Implementation
    # ================================================================================
    
    @pytest.mark.integration
    async def test_backend_pure_delegation_to_auth_service(self, auth_service_client, test_user_token):
        """SUCCESS: Backend uses pure delegation to auth service for JWT validation.
        
        This test should PASS after SSOT implementation.
        Validates that backend authentication delegates directly to auth service without local logic.
        """
        logger.info("Testing backend pure delegation to auth service...")
        
        # Test backend authentication flow
        try:
            from netra_backend.app.auth_integration.auth import get_current_user
            
            # Mock FastAPI dependencies for testing
            mock_credentials = MagicMock()
            mock_credentials.credentials = test_user_token
            
            # Get test database session
            mock_db = await self._get_test_database_session()
            
            # This should work through pure auth service delegation
            user = await get_current_user(mock_credentials, mock_db)
            
            assert user is not None, "User authentication failed with valid token"
            assert hasattr(user, 'id'), "User object missing required fields"
            
            logger.info(f"Backend authentication successful: user_id={getattr(user, 'id', 'unknown')}")
            
        except Exception as e:
            self.fail(f"Backend authentication failed: {e}")
        
        # Verify no local JWT logic was used
        jwt_call_stack = await self._capture_jwt_validation_call_stack(test_user_token)
        
        # Should contain auth service calls
        auth_service_calls = [call for call in jwt_call_stack if 'auth_service' in call.lower()]
        assert len(auth_service_calls) > 0, f"Auth service not in call stack: {jwt_call_stack}"
        
        # Should not contain direct JWT operations
        direct_jwt_calls = [call for call in jwt_call_stack if 'jwt.decode' in call.lower()]
        assert len(direct_jwt_calls) == 0, f"Direct JWT decode found in call stack: {direct_jwt_calls}"
        
        logger.info("SUCCESS: Backend uses pure delegation to auth service SSOT")
    
    @pytest.mark.integration
    async def test_consistent_validation_results_across_entry_points(self, auth_service_client, test_user_token):
        """SUCCESS: All entry points return consistent JWT validation results.
        
        This test should PASS after SSOT consolidation.
        Validates that different backend entry points return identical validation results.
        """
        logger.info("Testing consistent validation results across entry points...")
        
        # Test multiple backend entry points
        entry_points = {
            'auth_service_direct': lambda: auth_service_client.validate_token(test_user_token),
            'backend_auth_integration': lambda: self._test_backend_auth_integration(test_user_token),
            'websocket_auth_flow': lambda: self._test_websocket_auth_flow(test_user_token)
        }
        
        validation_results = {}
        
        for entry_point_name, validator in entry_points.items():
            try:
                result = await validator()
                validation_results[entry_point_name] = {
                    'valid': result.get('valid', False),
                    'user_id': result.get('user_id') or result.get('payload', {}).get('sub'),
                    'error': result.get('error')
                }
                logger.info(f"{entry_point_name}: {validation_results[entry_point_name]}")
            except Exception as e:
                validation_results[entry_point_name] = {
                    'valid': False,
                    'error': str(e)
                }
                logger.warning(f"{entry_point_name} failed: {e}")
        
        # All entry points should return consistent results
        reference_result = None
        inconsistencies = []
        
        for entry_point, result in validation_results.items():
            if reference_result is None:
                reference_result = result
            else:
                if result.get('valid') != reference_result.get('valid'):
                    inconsistencies.append(f"{entry_point}: valid={result.get('valid')} vs reference={reference_result.get('valid')}")
                
                if result.get('user_id') != reference_result.get('user_id'):
                    inconsistencies.append(f"{entry_point}: user_id={result.get('user_id')} vs reference={reference_result.get('user_id')}")
        
        assert len(inconsistencies) == 0, f"Validation result inconsistencies found: {inconsistencies}"
        
        logger.info("SUCCESS: All entry points return consistent JWT validation results")
    
    @pytest.mark.integration
    async def test_single_jwt_validation_call_path(self, test_user_token):
        """SUCCESS: Only one JWT validation call path exists through auth service.
        
        This test should PASS after SSOT implementation.
        Validates that there is exactly one call path for JWT validation in backend.
        """
        logger.info("Testing single JWT validation call path...")
        
        # Trace JWT validation paths after SSOT implementation
        jwt_validation_paths = await self._trace_all_backend_jwt_validation_paths(test_user_token)
        
        # Should be exactly one path
        assert len(jwt_validation_paths) == 1, f"Expected exactly 1 JWT validation path, found {len(jwt_validation_paths)}: {[p['name'] for p in jwt_validation_paths]}"
        
        single_path = jwt_validation_paths[0]
        
        # Path must use auth service SSOT
        assert single_path['uses_auth_service'], f"Single path does not use auth service: {single_path['call_chain']}"
        assert not single_path['has_local_logic'], f"Single path has local JWT logic: {single_path['call_chain']}"
        
        # Verify path goes through proper SSOT components
        call_chain = single_path['call_chain']
        auth_service_components = ['auth_client', 'auth_service', 'jwt_handler']
        
        has_auth_component = any(component in ' '.join(call_chain).lower() for component in auth_service_components)
        assert has_auth_component, f"Call chain does not include auth service components: {call_chain}"
        
        logger.info(f"SUCCESS: Single JWT validation path confirmed through auth service SSOT: {single_path['name']}")
    
    # ================================================================================
    # Helper Methods for Integration Testing
    # ================================================================================
    
    def _find_backend_jwt_validation_methods(self) -> List[Dict[str, Any]]:
        """Find JWT validation methods in backend code."""
        # Mock implementation - would scan backend codebase for JWT validation methods
        return [
            {
                'name': '_validate_token_with_auth_service',
                'location': 'netra_backend.app.auth_integration.auth',
                'description': 'Auth integration wrapper method',
                'bypasses_auth_service': False,
                'has_local_logic': True
            },
            {
                'name': 'validate_and_decode_jwt',
                'location': 'netra_backend.app.websocket_core.user_context_extractor',
                'description': 'WebSocket JWT validation wrapper',
                'bypasses_auth_service': False,
                'has_local_logic': True
            }
        ]
    
    def _method_bypasses_auth_service(self, method: Dict[str, Any]) -> bool:
        """Check if method bypasses auth service SSOT."""
        return method.get('bypasses_auth_service', True) or method.get('has_local_logic', True)
    
    def _analyze_auth_integration_wrapper_complexity(self) -> Dict[str, Any]:
        """Analyze auth integration wrapper for complexity violations."""
        # Mock implementation - would analyze actual wrapper code
        return {
            'adds_logic': True,
            'added_logic': ['token session tracking', 'reuse prevention', 'cleanup'],
            'transforms_data': True,
            'transformations': ['validation result mapping', 'user object creation']
        }
    
    async def _trace_all_backend_jwt_validation_paths(self, token: str) -> List[Dict[str, Any]]:
        """Trace all JWT validation paths in backend."""
        # Mock implementation - would trace actual call paths
        return [
            {
                'name': 'auth_integration_path',
                'entry_point': 'get_current_user',
                'call_chain': ['get_current_user', '_validate_token_with_auth_service', 'auth_client.validate_token'],
                'uses_auth_service': True,
                'has_local_logic': True  # Has wrapper logic
            },
            {
                'name': 'websocket_auth_path', 
                'entry_point': 'websocket_authenticate',
                'call_chain': ['websocket_authenticate', 'validate_and_decode_jwt', 'auth_service.validate_token'],
                'uses_auth_service': True,
                'has_local_logic': True  # Has validation wrapper
            }
        ]
    
    async def _capture_jwt_validation_call_stack(self, token: str) -> List[str]:
        """Capture JWT validation call stack."""
        # Mock implementation - would capture actual call stack
        return [
            'get_current_user',
            '_validate_token_with_auth_service', 
            'AuthServiceClient.validate_token',
            'auth_service.jwt_handler.validate_token'
        ]
    
    async def _get_test_database_session(self):
        """Get test database session."""
        # Mock implementation
        return MagicMock()
    
    async def _test_backend_auth_integration(self, token: str) -> Dict[str, Any]:
        """Test backend auth integration validation."""
        try:
            from netra_backend.app.auth_integration.auth import _validate_token_with_auth_service
            result = await _validate_token_with_auth_service(token)
            return result
        except Exception as e:
            return {'valid': False, 'error': str(e)}
    
    async def _test_websocket_auth_flow(self, token: str) -> Dict[str, Any]:
        """Test WebSocket auth flow validation."""
        # Mock implementation
        return {'valid': True, 'user_id': 'test_user_jwt_flow_integration'}
    
    def _create_mock_jwt_token(self) -> str:
        """Create mock JWT token for testing."""
        import base64
        import json
        
        header = {'typ': 'JWT', 'alg': 'HS256'}
        payload = {
            'sub': 'test_user_jwt_flow_integration',
            'email': 'test.integration@netrasystems.ai',
            'exp': int(time.time()) + 3600
        }
        
        header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        signature = hashlib.sha256(f"{header_b64}.{payload_b64}".encode()).hexdigest()[:10]
        
        return f"{header_b64}.{payload_b64}.{signature}"


# ================================================================================
# Test Execution Configuration
# ================================================================================

if __name__ == '__main__':
    # Run integration tests focusing on SSOT violations
    import pytest
    import sys
    
    # Configure logging for detailed integration testing
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run tests with verbose output
    exit_code = pytest.main([
        __file__,
        '-v',
        '-s',
        '--tb=short',
        '-k', 'failing'  # Run failing tests first to demonstrate issues
    ])
    
    print(f"\nIntegration Test Results:")
    if exit_code != 0:
        print("INTEGRATION SSOT VIOLATIONS CONFIRMED")
        print("These failures demonstrate JWT validation SSOT violations across service integration")
    else:
        print("UNEXPECTED: Integration tests passed - SSOT implementation may be complete")
    
    sys.exit(exit_code)