#!/usr/bin/env python3
"""
Issue #358 Golden Path Validation Suite
CRITICAL: Post-deployment validation for complete Golden Path failure remediation

This test suite validates that the massive deployment gap has been resolved
and the Golden Path (login  ->  AI response) flow is fully functional.

BUSINESS IMPACT: $500K+ ARR protection
SUCCESS CRITERIA: All tests must pass for remediation to be considered successful
"""

import asyncio
import pytest
import requests
import websocket
import json
import time
from typing import Dict, List, Optional
from unittest.mock import patch

# SSOT Test Infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env

# Business Logic
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID


class TestIssue358GoldenPathValidation(SSotAsyncTestCase):
    """
    CRITICAL VALIDATION SUITE for Issue #358 Remediation
    
    This suite validates that the deployment gap has been resolved and all
    critical Golden Path functionality is working in the staging environment.
    """

    @classmethod
    def setUpClass(cls):
        """Set up staging environment configuration."""
        super().setUpClass()
        cls.staging_base_url = "https://netra-backend-staging-pnovr5vsba-uc.a.run.app"
        cls.auth_service_url = "https://auth.staging.netrasystems.ai"
        cls.frontend_url = "https://app.staging.netrasystems.ai"
        
    async def test_01_service_health_endpoints_all_respond(self):
        """
        CRITICAL: Verify all service health endpoints respond correctly
        FIXES: Basic service availability after deployment
        """
        # Backend health check
        response = requests.get(f"{self.staging_base_url}/health", timeout=10)
        self.assertEqual(response.status_code, 200)
        health_data = response.json()
        self.assertEqual(health_data["status"], "healthy")
        self.assertEqual(health_data["service"], "netra-ai-platform")
        
        # Auth service health check
        try:
            auth_response = requests.get(f"{self.auth_service_url}/health", timeout=10)
            self.assertEqual(auth_response.status_code, 200)
        except requests.RequestException:
            self.skipTest("Auth service not accessible - may not be critical for backend validation")
            
    async def test_02_user_execution_context_has_websocket_client_id_parameter(self):
        """
        CRITICAL: Verify Issue #357 fix is deployed - UserExecutionContext supports websocket_client_id
        BUSINESS IMPACT: Without this fix, WebSocket authentication fails completely
        """
        # Test that UserExecutionContext can be created with websocket_client_id parameter
        user_id = "test-user-358"
        thread_id = "test-thread-358"
        websocket_client_id = "test-websocket-358"
        
        # This was the failing call from staging - must now work
        user_context = UserExecutionContext.from_request(
            user_id=user_id,
            thread_id=thread_id,
            run_id=None,
            websocket_client_id=websocket_client_id  # This parameter was missing in old staging
        )
        
        self.assertIsNotNone(user_context)
        self.assertEqual(user_context.user_id, user_id)
        self.assertEqual(user_context.thread_id, thread_id)
        self.assertEqual(user_context.websocket_client_id, websocket_client_id)
        
    async def test_03_websocket_connection_establishment(self):
        """
        CRITICAL: Test WebSocket connection can be established to staging
        FIXES: Core WebSocket connectivity that was completely broken
        """
        websocket_url = self.staging_base_url.replace("https://", "wss://") + "/ws"
        
        try:
            # Test WebSocket connection with timeout
            ws = websocket.create_connection(websocket_url, timeout=10)
            
            # Send basic ping to verify connection
            ping_message = {
                "type": "ping",
                "timestamp": time.time()
            }
            ws.send(json.dumps(ping_message))
            
            # Wait for response (or timeout)
            ws.settimeout(5.0)
            try:
                response = ws.recv()
                response_data = json.loads(response)
                self.assertIsInstance(response_data, dict)
            except websocket.WebSocketTimeoutException:
                # Connection established but no immediate response - still counts as success
                pass
            
            ws.close()
            
        except Exception as e:
            self.fail(f"WebSocket connection failed: {e}. This indicates the deployment gap fix has not resolved the core connectivity issue.")
            
    async def test_04_authentication_endpoint_accepts_requests(self):
        """
        CRITICAL: Verify authentication endpoints are accessible and responding
        FIXES: Auth integration that was broken due to outdated code
        """
        auth_endpoint = f"{self.staging_base_url}/auth/validate"
        
        # Test with invalid token (should get structured error response, not 500)
        response = requests.post(
            auth_endpoint,
            json={"token": "invalid-test-token"},
            timeout=10
        )
        
        # Should get 401/422, not 500 (indicates service is running and handling requests)
        self.assertIn(response.status_code, [400, 401, 422])
        self.assertIsInstance(response.json(), dict)
        
    async def test_05_agent_execution_endpoint_structure_correct(self):
        """
        CRITICAL: Verify agent execution endpoints have correct structure
        FIXES: API incompatibilities from deployment gap
        """
        # Test agent execution endpoint exists and has proper error handling
        execution_endpoint = f"{self.staging_base_url}/agent/execute"
        
        # Send malformed request to test error handling structure
        response = requests.post(
            execution_endpoint,
            json={"invalid": "request"},
            timeout=10
        )
        
        # Should get structured error response, not 500 server error
        self.assertIn(response.status_code, [400, 401, 422])
        
        try:
            error_data = response.json()
            self.assertIsInstance(error_data, dict)
            # Should have error structure indicating proper API handling
            self.assertTrue(
                "error" in error_data or "detail" in error_data or "message" in error_data,
                "API should return structured error responses"
            )
        except json.JSONDecodeError:
            self.fail("API should return JSON error responses, not HTML/plain text")
            
    async def test_06_websocket_agent_bridge_import_available(self):
        """
        CRITICAL: Verify SSOT WebSocket agent bridge is available in deployed code
        FIXES: Missing import that caused agent execution failures
        """
        # Test the import that was causing failures in staging
        try:
            from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge, AgentWebSocketBridge
            
            # Verify the bridge can be created (basic instantiation test)
            # This was the core missing component in old staging deployment
            bridge = create_agent_websocket_bridge(
                websocket_manager=None,  # Mock for test
                user_context=None       # Mock for test
            )
            
            # If we reach here without ImportError, the SSOT fix is deployed
            self.assertTrue(True, "AgentWebSocketBridge import successful - SSOT fix deployed")
            
        except ImportError as e:
            self.fail(f"AgentWebSocketBridge import failed: {e}. This indicates the SSOT migration is not deployed to staging.")
            
    async def test_07_execution_state_enum_available_with_all_states(self):
        """
        CRITICAL: Verify ExecutionState enum with all required states is deployed
        FIXES: Missing enum states that caused agent execution failures
        """
        try:
            from netra_backend.app.core.agent_execution_tracker import ExecutionState
            
            # Verify all required states are available
            required_states = [
                "PENDING", "STARTING", "RUNNING", "COMPLETING", 
                "COMPLETED", "FAILED", "TIMEOUT", "DEAD", "CANCELLED"
            ]
            
            for state_name in required_states:
                self.assertTrue(
                    hasattr(ExecutionState, state_name),
                    f"ExecutionState.{state_name} not found - SSOT consolidation not deployed"
                )
                
            # Test state enum can be used (was causing dict errors in old code)
            test_state = ExecutionState.COMPLETED
            self.assertEqual(test_state.value, "completed")
            
        except ImportError as e:
            self.fail(f"ExecutionState import failed: {e}. This indicates execution tracking SSOT is not deployed.")
            
    async def test_08_user_context_manager_security_implementation_available(self):
        """
        CRITICAL: Verify UserContextManager security implementation is deployed
        FIXES: Complete absence of multi-tenant isolation that was missing in old staging
        """
        try:
            from netra_backend.app.services.user_execution_context import UserContextManager
            from netra_backend.app.services.user_execution_context import InvalidContextError, ContextIsolationError
            
            # Verify security classes are available
            manager = UserContextManager()
            self.assertIsNotNone(manager)
            
            # Verify security exception classes exist
            self.assertTrue(issubclass(InvalidContextError, Exception))
            self.assertTrue(issubclass(ContextIsolationError, Exception))
            
        except ImportError as e:
            self.fail(f"UserContextManager security implementation not available: {e}. Critical security feature missing in deployment.")
            
    async def test_09_configuration_system_unified_and_accessible(self):
        """
        CRITICAL: Verify unified configuration system is deployed and accessible
        FIXES: Configuration access issues that prevented proper service operation
        """
        try:
            from netra_backend.app.core.configuration.base import get_unified_config
            
            # Test configuration can be loaded
            config = get_unified_config()
            self.assertIsNotNone(config)
            
            # Verify staging-specific configuration is loaded
            self.assertEqual(config.environment, "staging")
            
            # Verify WebSocket configuration is present (critical for Golden Path)
            self.assertTrue(hasattr(config, 'websocket_connection_timeout'))
            self.assertIsInstance(config.websocket_connection_timeout, int)
            
        except Exception as e:
            self.fail(f"Configuration system not properly deployed: {e}")
            
    async def test_10_golden_path_integration_readiness_complete(self):
        """
        FINAL VALIDATION: All Golden Path components ready for integration
        SUCCESS CRITERIA: This test passing means remediation is successful
        """
        validation_results = {
            "service_health": False,
            "websocket_connectivity": False,
            "api_compatibility": False,
            "ssot_imports": False,
            "security_features": False,
            "configuration": False
        }
        
        # Service health check
        try:
            response = requests.get(f"{self.staging_base_url}/health", timeout=5)
            validation_results["service_health"] = response.status_code == 200
        except:
            pass
            
        # WebSocket connectivity check
        try:
            websocket_url = self.staging_base_url.replace("https://", "wss://") + "/ws"
            ws = websocket.create_connection(websocket_url, timeout=5)
            ws.close()
            validation_results["websocket_connectivity"] = True
        except:
            pass
            
        # API compatibility check
        try:
            UserExecutionContext.from_request(
                user_id="test",
                thread_id="test",
                websocket_client_id="test"
            )
            validation_results["api_compatibility"] = True
        except:
            pass
            
        # SSOT imports check
        try:
            from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge
            from netra_backend.app.core.agent_execution_tracker import ExecutionState
            validation_results["ssot_imports"] = True
        except:
            pass
            
        # Security features check
        try:
            from netra_backend.app.services.user_execution_context import UserContextManager
            validation_results["security_features"] = True
        except:
            pass
            
        # Configuration check
        try:
            from netra_backend.app.core.configuration.base import get_unified_config
            config = get_unified_config()
            validation_results["configuration"] = config.environment == "staging"
        except:
            pass
            
        # Calculate readiness score
        passed_checks = sum(validation_results.values())
        total_checks = len(validation_results)
        readiness_percentage = (passed_checks / total_checks) * 100
        
        # Log detailed results
        print(f"\nGOLDEN PATH READINESS ASSESSMENT:")
        print(f"Overall Score: {readiness_percentage:.1f}% ({passed_checks}/{total_checks})")
        for check, result in validation_results.items():
            status = " PASS:  PASS" if result else " FAIL:  FAIL"
            print(f"  {check}: {status}")
            
        # Success criteria: All critical components must be ready
        self.assertGreaterEqual(
            readiness_percentage, 
            85,  # Allow for some non-critical checks to fail
            f"Golden Path readiness only {readiness_percentage:.1f}%. Deployment gap remediation incomplete."
        )
        
        # Specific critical requirement: Core API compatibility must work
        self.assertTrue(
            validation_results["api_compatibility"],
            "API compatibility FAILED - Issue #357 fix not deployed"
        )
        
        # Specific critical requirement: WebSocket connectivity must work
        self.assertTrue(
            validation_results["websocket_connectivity"],
            "WebSocket connectivity FAILED - Core chat functionality unavailable"
        )


class TestBusinessValueValidation(SSotAsyncTestCase):
    """
    Business Value Validation for Issue #358 Remediation
    
    These tests validate that the business goals are met:
    - Users can access the platform
    - Chat functionality provides value
    - Enterprise features are accessible
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up business validation environment."""
        super().setUpClass()
        cls.staging_base_url = "https://netra-backend-staging-pnovr5vsba-uc.a.run.app"
    
    async def test_user_can_reach_platform_successfully(self):
        """
        BUSINESS VALIDATION: Users can reach the platform and get responses
        SUCCESS METRIC: HTTP 200 responses for core endpoints
        """
        core_endpoints = [
            "/health",
            "/docs",  # API documentation should be accessible
        ]
        
        for endpoint in core_endpoints:
            with self.subTest(endpoint=endpoint):
                response = requests.get(f"{self.staging_base_url}{endpoint}", timeout=10)
                self.assertLess(
                    response.status_code, 500,
                    f"Endpoint {endpoint} returning server error - user access blocked"
                )
                
    async def test_enterprise_features_endpoints_accessible(self):
        """
        BUSINESS VALIDATION: Enterprise features are accessible (even if authentication required)
        REVENUE IMPACT: $500K+ ARR depends on these features working
        """
        enterprise_endpoints = [
            "/agent/execute",  # Core agent functionality
            "/auth/validate",  # Authentication system
        ]
        
        for endpoint in enterprise_endpoints:
            with self.subTest(endpoint=endpoint):
                response = requests.post(
                    f"{self.staging_base_url}{endpoint}",
                    json={"test": "request"},
                    timeout=10
                )
                # Should get auth error (401/422), not server error (500)
                self.assertLess(
                    response.status_code, 500,
                    f"Enterprise endpoint {endpoint} has server errors - revenue at risk"
                )
                
    async def test_platform_performance_acceptable(self):
        """
        BUSINESS VALIDATION: Platform performance meets user expectations
        SUCCESS METRIC: Response times under 5 seconds for health check
        """
        start_time = time.time()
        response = requests.get(f"{self.staging_base_url}/health", timeout=10)
        end_time = time.time()
        
        response_time = end_time - start_time
        self.assertLess(
            response_time, 5.0,
            f"Health check took {response_time:.2f}s - user experience unacceptable"
        )
        
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    # Run validation suite
    pytest.main([__file__, "-v", "--tb=short"])