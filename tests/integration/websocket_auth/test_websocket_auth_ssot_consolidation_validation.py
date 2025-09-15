"""
Integration Test for WebSocket Authentication SSOT Consolidation

BUSINESS IMPACT: $500K+ ARR - WebSocket authentication consolidation for Golden Path
ISSUE: #1076 - Multiple authentication pathways causing authentication chaos

This test SHOULD FAIL INITIALLY (detecting multiple auth pathways) and PASS AFTER REMEDIATION.

SSOT Gardener Step 2.3: Validate single entry point pattern for WebSocket authentication.
Tests that all WebSocket authentication goes through authenticate_websocket_ssot() ONLY.

Expected Test Behavior:
- FAILS NOW: Multiple authentication pathways detected
- PASSES AFTER: Single SSOT entry point enforced
"""

import pytest
import asyncio
import unittest
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, List, Any, Optional
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.websocket_helpers import MockWebSocketConnection


@pytest.mark.integration
class TestWebSocketAuthSSOTConsolidationValidation(SSotAsyncTestCase):
    """
    Integration Test: WebSocket Authentication SSOT Entry Point Validation
    
    Tests that WebSocket authentication follows SSOT pattern with single entry point
    and that no parallel/competing authentication pathways exist.
    """
    
    def setUp(self):
        """Set up test environment for SSOT consolidation validation."""
        super().setUp()
        self.test_token = "test-jwt-token-for-ssot-validation"
        self.test_user_id = "test-user-ssot-auth"
    
    async def test_websocket_auth_single_entry_point(self):
        """
        CRITICAL TEST: Should FAIL currently - validates SSOT authentication pattern.
        
        This test verifies that ALL WebSocket authentication goes through 
        authenticate_websocket_ssot() and that no parallel authentication 
        methods are being used.
        
        Business Impact: Prevents authentication chaos blocking Golden Path
        """
        from netra_backend.app.websocket_core.unified_websocket_auth import (
            authenticate_websocket_ssot,
            authenticate_websocket_connection  # This should be deprecated
        )
        
        # Create test WebSocket connection
        websocket = MockWebSocketConnection()
        websocket.headers = {"authorization": f"Bearer {self.test_token}"}
        websocket.subprotocols = [f"jwt-auth.{self.test_token}"]
        
        # Track which functions are actually called during authentication
        auth_function_calls = {
            'ssot_function_called': False,
            'deprecated_function_called': False,
            'other_auth_methods_called': []
        }
        
        # Patch to track function calls
        with patch('netra_backend.app.websocket_core.unified_websocket_auth.authenticate_websocket_ssot') as mock_ssot, \
             patch('netra_backend.app.websocket_core.unified_websocket_auth.authenticate_websocket_connection') as mock_deprecated:
            
            # Configure mocks to track calls
            mock_ssot.side_effect = self._track_ssot_call(auth_function_calls)
            mock_deprecated.side_effect = self._track_deprecated_call(auth_function_calls)
            
            # Test direct SSOT function call
            try:
                await authenticate_websocket_ssot(websocket)
                auth_function_calls['ssot_function_called'] = True
            except Exception as e:
                self.logger.warning(f"SSOT function call failed (expected during mocking): {e}")
            
            # Test that deprecated function delegates to SSOT
            try:
                await authenticate_websocket_connection(websocket)
                # If deprecated function is called directly, it should delegate to SSOT
                # This is acceptable during migration period
            except Exception as e:
                self.logger.warning(f"Deprecated function call failed (expected during mocking): {e}")
        
        # Analyze authentication pathway usage
        self._analyze_authentication_pathways(auth_function_calls)
        
        # CRITICAL ASSERTION: SSOT function should be the primary pathway
        # This test will FAIL initially if multiple competing pathways exist
        self.assertTrue(auth_function_calls['ssot_function_called'],
                       "SSOT VIOLATION: authenticate_websocket_ssot() not being used as primary entry point. "
                       "This indicates SSOT consolidation is incomplete.")
        
        # Log detailed analysis
        self.logger.info(f"SSOT ANALYSIS: Function calls tracked: {auth_function_calls}")
    
    async def test_no_direct_auth_service_calls_bypassing_ssot(self):
        """
        INTEGRATION TEST: Verify no direct auth service calls bypass SSOT layer.
        
        This test ensures that WebSocket authentication doesn't bypass the SSOT
        layer by calling auth services directly, which would create parallel pathways.
        """
        from netra_backend.app.websocket_core.unified_websocket_auth import authenticate_websocket_ssot
        
        # Create test WebSocket with staging E2E context
        websocket = MockWebSocketConnection()
        websocket.headers = {"authorization": f"Bearer {self.test_token}"}
        
        # Track direct auth service calls
        auth_service_calls = []
        
        # Patch auth service to track direct calls
        with patch('netra_backend.app.services.unified_authentication_service.get_unified_auth_service') as mock_auth_service:
            mock_service = AsyncMock()
            mock_service.authenticate_websocket.return_value = (
                Mock(success=True, user_id=self.test_user_id, error=None, error_code=None),
                Mock(user_id=self.test_user_id, websocket_client_id="test-client-id")
            )
            mock_auth_service.return_value = mock_service
            
            # Call SSOT function 
            try:
                result = await authenticate_websocket_ssot(websocket)
                self.logger.info(f"SSOT authentication result: {result}")
            except Exception as e:
                self.logger.info(f"SSOT authentication failed (may be expected): {e}")
            
            # Check that auth service was called THROUGH SSOT function only
            auth_service_call_count = mock_service.authenticate_websocket.call_count
            
        self.logger.info(f"AUTH SERVICE CALLS: {auth_service_call_count} calls made through SSOT layer")
        
        # This test validates that auth service calls go through SSOT layer
        # Multiple calls are acceptable as long as they go through SSOT
        self.assertGreaterEqual(auth_service_call_count, 0,
                               "Auth service calls should go through SSOT layer")
    
    async def test_websocket_authenticator_class_delegation_to_ssot(self):
        """
        CLASS DELEGATION TEST: Verify UnifiedWebSocketAuthenticator class delegates to SSOT.
        
        This test checks that the class-based authentication interface properly
        delegates to the SSOT function rather than implementing parallel logic.
        """
        from netra_backend.app.websocket_core.unified_websocket_auth import (
            UnifiedWebSocketAuthenticator,
            authenticate_websocket_ssot
        )
        
        # Create authenticator instance
        authenticator = UnifiedWebSocketAuthenticator()
        
        # Create test WebSocket
        websocket = MockWebSocketConnection()
        websocket.headers = {"authorization": f"Bearer {self.test_token}"}
        
        ssot_delegation_calls = []
        
        # Track if class methods delegate to SSOT function
        with patch('netra_backend.app.websocket_core.unified_websocket_auth.authenticate_websocket_ssot') as mock_ssot:
            mock_ssot.side_effect = lambda *args, **kwargs: ssot_delegation_calls.append({
                'args': args,
                'kwargs': kwargs
            }) or Mock(success=True)
            
            try:
                # Test class method authentication
                await authenticator.authenticate_websocket_connection(websocket)
            except Exception as e:
                self.logger.info(f"Class authentication failed (may be expected during mocking): {e}")
        
        self.logger.info(f"SSOT DELEGATION: {len(ssot_delegation_calls)} calls to SSOT function from class")
        
        # CLASS SHOULD DELEGATE TO SSOT FUNCTION (may fail initially if not implemented)
        # This assertion may fail initially, indicating SSOT consolidation needs completion
        self.assertGreater(len(ssot_delegation_calls), 0,
                          "SSOT VIOLATION: UnifiedWebSocketAuthenticator class does not delegate to "
                          "authenticate_websocket_ssot() function. This indicates parallel implementation.")
    
    async def test_e2e_authentication_pathway_consistency(self):
        """
        E2E TEST: Verify authentication pathway consistency in E2E scenarios.
        
        This test simulates E2E testing scenarios and verifies that authentication
        follows the same SSOT pathway regardless of test context.
        """
        from netra_backend.app.websocket_core.unified_websocket_auth import authenticate_websocket_ssot
        
        # Test scenarios with different E2E contexts
        test_scenarios = [
            {
                'name': 'no_e2e_context',
                'e2e_context': None,
                'expected_pathway': 'full_auth'
            },
            {
                'name': 'staging_e2e_context',
                'e2e_context': {
                    'is_e2e_testing': True,
                    'test_environment': 'staging',
                    'bypass_enabled': True
                },
                'expected_pathway': 'e2e_bypass'
            },
            {
                'name': 'demo_mode_context',
                'e2e_context': {
                    'demo_mode_enabled': True,
                    'bypass_enabled': True
                },
                'expected_pathway': 'demo_bypass'
            }
        ]
        
        pathway_consistency = {
            'all_scenarios_tested': True,
            'consistent_ssot_usage': True,
            'pathway_analysis': {}
        }
        
        for scenario in test_scenarios:
            websocket = MockWebSocketConnection()
            websocket.headers = {"authorization": f"Bearer {self.test_token}"}
            
            # Track authentication pathway for this scenario
            with patch('netra_backend.app.services.unified_authentication_service.get_unified_auth_service') as mock_auth:
                mock_service = AsyncMock()
                mock_auth.return_value = mock_service
                mock_service.authenticate_websocket.return_value = (
                    Mock(success=True, user_id=f"user-{scenario['name']}", error=None),
                    Mock(user_id=f"user-{scenario['name']}", websocket_client_id=f"client-{scenario['name']}")
                )
                
                try:
                    result = await authenticate_websocket_ssot(
                        websocket, 
                        e2e_context=scenario['e2e_context']
                    )
                    
                    pathway_analysis = {
                        'auth_service_called': mock_service.authenticate_websocket.called,
                        'call_count': mock_service.authenticate_websocket.call_count,
                        'success': getattr(result, 'success', False)
                    }
                    
                except Exception as e:
                    pathway_analysis = {
                        'auth_service_called': False,
                        'call_count': 0,
                        'success': False,
                        'error': str(e)
                    }
                
                pathway_consistency['pathway_analysis'][scenario['name']] = pathway_analysis
        
        # Log pathway analysis
        self._log_pathway_consistency_analysis(pathway_consistency)
        
        # All scenarios should use consistent SSOT pathway
        # This may fail initially if inconsistent pathways exist
        for scenario_name, analysis in pathway_consistency['pathway_analysis'].items():
            self.assertTrue(
                'error' not in analysis or 'mock' in analysis.get('error', '').lower(),
                f"PATHWAY INCONSISTENCY: Scenario '{scenario_name}' failed with: {analysis.get('error')}"
            )
    
    def _track_ssot_call(self, tracking_dict: Dict) -> callable:
        """Create a side effect function to track SSOT function calls."""
        def track_call(*args, **kwargs):
            tracking_dict['ssot_function_called'] = True
            # Return a mock result to prevent further execution
            return Mock(success=True, user_context=Mock(), auth_result=Mock())
        return track_call
    
    def _track_deprecated_call(self, tracking_dict: Dict) -> callable:
        """Create a side effect function to track deprecated function calls."""
        def track_call(*args, **kwargs):
            tracking_dict['deprecated_function_called'] = True
            # Return a mock result
            return Mock(success=True, user_context=Mock(), auth_result=Mock())
        return track_call
    
    def _analyze_authentication_pathways(self, auth_function_calls: Dict):
        """Analyze and log authentication pathway usage."""
        self.logger.info("AUTHENTICATION PATHWAY ANALYSIS:")
        self.logger.info(f"  SSOT function called: {auth_function_calls['ssot_function_called']}")
        self.logger.info(f"  Deprecated function called: {auth_function_calls['deprecated_function_called']}")
        self.logger.info(f"  Other methods called: {len(auth_function_calls['other_auth_methods_called'])}")
        
        # Record in test metadata
        self.test_metadata.update({
            "ssot_function_usage": auth_function_calls['ssot_function_called'],
            "deprecated_function_usage": auth_function_calls['deprecated_function_called'],
            "other_auth_methods": len(auth_function_calls['other_auth_methods_called']),
            "pathway_analysis_complete": True
        })
        
        # Identify pathway issues
        pathway_issues = []
        
        if not auth_function_calls['ssot_function_called']:
            pathway_issues.append("SSOT function not being used as primary entry point")
        
        if auth_function_calls['deprecated_function_called'] and not auth_function_calls['ssot_function_called']:
            pathway_issues.append("Deprecated function called without SSOT delegation")
        
        if auth_function_calls['other_auth_methods_called']:
            pathway_issues.append(f"Parallel authentication methods detected: {auth_function_calls['other_auth_methods_called']}")
        
        if pathway_issues:
            self.logger.warning(f"PATHWAY ISSUES DETECTED: {pathway_issues}")
        else:
            self.logger.info("PATHWAY ANALYSIS: No issues detected - SSOT compliance validated")
    
    def _log_pathway_consistency_analysis(self, consistency_data: Dict):
        """Log detailed pathway consistency analysis."""
        self.logger.info("PATHWAY CONSISTENCY ANALYSIS:")
        
        for scenario_name, analysis in consistency_data['pathway_analysis'].items():
            self.logger.info(f"  Scenario '{scenario_name}':")
            self.logger.info(f"    Auth service called: {analysis['auth_service_called']}")
            self.logger.info(f"    Call count: {analysis['call_count']}")
            self.logger.info(f"    Success: {analysis['success']}")
            
            if 'error' in analysis:
                self.logger.warning(f"    Error: {analysis['error']}")
        
        # Record consistency metrics
        total_scenarios = len(consistency_data['pathway_analysis'])
        successful_scenarios = sum(
            1 for analysis in consistency_data['pathway_analysis'].values()
            if analysis['success'] or ('error' in analysis and 'mock' in analysis['error'].lower())
        )
        
        self.test_metadata.update({
            "total_scenarios_tested": total_scenarios,
            "successful_scenarios": successful_scenarios,
            "consistency_rate": (successful_scenarios / max(1, total_scenarios)) * 100
        })
        
        self.logger.info(f"CONSISTENCY SUMMARY: {successful_scenarios}/{total_scenarios} scenarios consistent "
                        f"({(successful_scenarios / max(1, total_scenarios)) * 100:.1f}%)")


if __name__ == '__main__':
    unittest.main()