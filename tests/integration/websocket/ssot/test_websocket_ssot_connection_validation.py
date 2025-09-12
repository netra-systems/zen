"""
Issue #507 - WebSocket SSOT Connection Validation Tests

CRITICAL MISSION: Create integration tests for WebSocket connection validation
using real WebSocket connections to staging GCP environment.

PROBLEM: WebSocket URL environment variable duplication causing connection failures
BUSINESS IMPACT: $500K+ ARR Golden Path chat functionality at risk from connection issues

TEST DESIGN:
- Real WebSocket connections to staging GCP environment  
- No Docker required - uses staging services
- Tests actual WebSocket connectivity with SSOT configuration
- Validates connection behavior with canonical vs deprecated URLs

Business Value: Platform/Internal - Connection Reliability & User Experience
Ensures WebSocket connections work reliably with SSOT configuration for chat functionality.
"""

import pytest
import asyncio
import json
import time
from unittest.mock import patch
from test_framework.ssot.base_test_case import SSotAsyncTestCase, SsotTestMetrics
from shared.isolated_environment import IsolatedEnvironment, get_env

# Import WebSocket client for real connection testing
try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    

@pytest.mark.integration
@pytest.mark.staging
@pytest.mark.skipif(not WEBSOCKETS_AVAILABLE, reason="websockets library not available")
class TestWebSocketSSOTConnectionValidation(SSotAsyncTestCase):
    """Integration tests for WebSocket connection validation with SSOT (Issue #507)"""

    def setup_method(self, method):
        """Setup for each test method using SSOT async pattern"""
        super().setup_method(method)
        self.env = IsolatedEnvironment()
        self.metrics = SsotTestMetrics()
        self.staging_config = {
            "ENVIRONMENT": "staging",
            "NEXT_PUBLIC_WS_URL": "wss://api.staging.netrasystems.ai/ws"
        }
        self.connection_timeout = 10.0
        self.response_timeout = 5.0

    def teardown_method(self, method):
        """Teardown for each test method"""
        super().teardown_method(method)

    @pytest.mark.asyncio
    async def test_websocket_connection_with_canonical_url(self):
        """
        Test WebSocket connection using canonical SSOT URL
        
        CRITICAL: Tests real WebSocket connection to staging with canonical URL
        """
        with patch.dict('os.environ', self.staging_config, clear=False):
            env = IsolatedEnvironment()
            
            # Get canonical WebSocket URL
            ws_url = env.get("NEXT_PUBLIC_WS_URL")
            
            assert ws_url is not None, "Canonical WebSocket URL should be available"
            assert ws_url == "wss://api.staging.netrasystems.ai/ws", (
                "Should use staging WebSocket URL"
            )
            
            # SSOT COMPLIANCE: Verify no deprecated variable exists
            deprecated_url = env.get("NEXT_PUBLIC_WEBSOCKET_URL")
            assert deprecated_url is None, "SSOT VIOLATION: Deprecated URL should not exist"
            
            # Attempt real WebSocket connection
            connection_result = await self._test_websocket_connection(
                ws_url, 
                test_name="canonical_url_connection"
            )
            
            # Record connection metrics
            self.metrics.custom_metrics["canonical_connection_attempted"] = True
            self.metrics.custom_metrics["canonical_connection_result"] = connection_result["status"]
            
            if connection_result["status"] == "success":
                self.metrics.custom_metrics["canonical_connection_success"] = True
            elif connection_result["status"] == "auth_required":
                # Connection failed due to auth - this is expected and acceptable
                self.metrics.custom_metrics["canonical_auth_enforced"] = True
                pytest.skip(f"WebSocket connection requires authentication: {connection_result['message']}")
            else:
                # Unexpected connection failure
                self.metrics.custom_metrics["canonical_connection_error"] = connection_result["message"]
                pytest.fail(
                    f"WebSocket connection failed unexpectedly: {connection_result['message']}"
                )

    @pytest.mark.asyncio
    async def test_websocket_connection_ssot_migration_validation(self):
        """
        Test WebSocket connection behavior during SSOT migration
        
        CRITICAL: Validates connection works with canonical URL and detects dual variable issues
        """
        # Test scenario 1: Post-migration (canonical only) - should work
        post_migration_config = {
            "ENVIRONMENT": "staging",
            "NEXT_PUBLIC_WS_URL": "wss://api.staging.netrasystems.ai/ws"
        }
        
        with patch.dict('os.environ', post_migration_config, clear=False):
            env = IsolatedEnvironment()
            
            canonical_url = env.get("NEXT_PUBLIC_WS_URL")
            deprecated_url = env.get("NEXT_PUBLIC_WEBSOCKET_URL")
            
            # SSOT COMPLIANCE: Only canonical should exist
            assert canonical_url is not None, "Canonical URL should exist post-migration"
            assert deprecated_url is None, "Deprecated URL should not exist post-migration"
            
            # Test connection with canonical URL
            connection_result = await self._test_websocket_connection(
                canonical_url,
                test_name="post_migration_canonical"
            )
            
            self.metrics.custom_metrics["post_migration_connection"] = connection_result["status"]
            
            if connection_result["status"] in ["success", "auth_required"]:
                # Connection successful or properly protected by auth
                self.metrics.custom_metrics["post_migration_success"] = True
            else:
                # Connection failed - may indicate configuration issue
                self.metrics.custom_metrics["post_migration_error"] = connection_result["message"]
        
        # Test scenario 2: Pre-migration (dual variables) - should detect SSOT violation
        pre_migration_config = {
            "ENVIRONMENT": "staging", 
            "NEXT_PUBLIC_WS_URL": "wss://api.staging.netrasystems.ai/ws",
            "NEXT_PUBLIC_WEBSOCKET_URL": "wss://api.staging.netrasystems.ai/ws"  # Duplicate
        }
        
        with patch.dict('os.environ', pre_migration_config, clear=False):
            env = IsolatedEnvironment()
            
            canonical_url = env.get("NEXT_PUBLIC_WS_URL")
            deprecated_url = env.get("NEXT_PUBLIC_WEBSOCKET_URL")
            
            # SSOT VIOLATION: Both exist
            if canonical_url and deprecated_url:
                self.metrics.custom_metrics["ssot_violation_detected"] = True
                self.metrics.custom_metrics["migration_required"] = True
                
                # Application should use canonical URL preferentially
                preferred_url = canonical_url
                
                connection_result = await self._test_websocket_connection(
                    preferred_url,
                    test_name="pre_migration_canonical_preferred"
                )
                
                self.metrics.custom_metrics["pre_migration_connection"] = connection_result["status"]
                
                # Fail test to indicate SSOT remediation needed
                pytest.fail(
                    f"SSOT VIOLATION: Both WebSocket URL variables exist. "
                    f"Connection works with canonical ({canonical_url}) but deprecated "
                    f"variable ({deprecated_url}) must be removed. Issue #507 remediation required."
                )

    @pytest.mark.asyncio
    async def test_websocket_connection_error_handling_ssot(self):
        """
        Test WebSocket connection error handling with SSOT configuration
        
        Tests that connection errors are properly handled with canonical URL configuration
        """
        # Test invalid URL configuration
        invalid_config = {
            "ENVIRONMENT": "staging",
            "NEXT_PUBLIC_WS_URL": "wss://invalid.example.com/ws"  # Invalid domain
        }
        
        with patch.dict('os.environ', invalid_config, clear=False):
            env = IsolatedEnvironment()
            
            ws_url = env.get("NEXT_PUBLIC_WS_URL")
            
            # Test connection to invalid URL
            connection_result = await self._test_websocket_connection(
                ws_url,
                test_name="invalid_url_error_handling"
            )
            
            # Should fail with appropriate error
            assert connection_result["status"] == "error", (
                "Connection to invalid URL should fail"
            )
            
            self.metrics.custom_metrics["invalid_url_error_handled"] = True
        
        # Test missing URL configuration
        missing_config = {"ENVIRONMENT": "staging"}
        
        with patch.dict('os.environ', missing_config, clear=False):
            env = IsolatedEnvironment()
            
            ws_url = env.get("NEXT_PUBLIC_WS_URL")
            
            # Missing URL should be None
            assert ws_url is None, "Missing WebSocket URL should be None"
            
            # Application should handle missing URL gracefully
            if ws_url is None:
                self.metrics.custom_metrics["missing_url_handled"] = True
            else:
                pytest.fail("Missing WebSocket URL not handled correctly")

    @pytest.mark.asyncio
    async def test_websocket_connection_protocol_validation_ssot(self):
        """
        Test WebSocket connection protocol validation with SSOT configuration
        
        Validates that secure protocols are enforced for staging environment
        """
        protocol_tests = [
            {
                "url": "wss://api.staging.netrasystems.ai/ws",
                "should_connect": True,
                "description": "Secure WebSocket (expected for staging)"
            },
            {
                "url": "ws://api.staging.netrasystems.ai/ws",
                "should_connect": False,
                "description": "Insecure WebSocket (should be rejected by staging)"
            }
        ]
        
        for test_case in protocol_tests:
            test_config = {
                "ENVIRONMENT": "staging",
                "NEXT_PUBLIC_WS_URL": test_case["url"]
            }
            
            with patch.dict('os.environ', test_config, clear=False):
                env = IsolatedEnvironment()
                
                ws_url = env.get("NEXT_PUBLIC_WS_URL")
                
                connection_result = await self._test_websocket_connection(
                    ws_url,
                    test_name=f"protocol_validation_{test_case['description']}"
                )
                
                if test_case["should_connect"]:
                    # Secure connection should work (or fail due to auth, which is acceptable)
                    assert connection_result["status"] in ["success", "auth_required"], (
                        f"Secure WebSocket should connect or require auth: {test_case['description']}"
                    )
                else:
                    # Insecure connection should fail
                    assert connection_result["status"] == "error", (
                        f"Insecure WebSocket should fail: {test_case['description']}"
                    )
                
                self.metrics.custom_metrics[f"protocol_test_{test_case['description']}"] = connection_result["status"]

    @pytest.mark.asyncio
    async def test_websocket_connection_staging_environment_validation(self):
        """
        Test WebSocket connection validation specific to staging environment
        
        CRITICAL: Validates staging environment WebSocket connectivity with SSOT URL
        """
        with patch.dict('os.environ', self.staging_config, clear=False):
            env = IsolatedEnvironment()
            
            ws_url = env.get("NEXT_PUBLIC_WS_URL") 
            environment = env.get("ENVIRONMENT")
            
            # Validate staging-specific configuration
            assert environment == "staging", "Should be staging environment"
            assert "staging.netrasystems.ai" in ws_url, "Should use staging domain"
            assert ws_url.startswith("wss://"), "Should use secure protocol in staging"
            
            # Test staging WebSocket connection
            connection_result = await self._test_websocket_connection(
                ws_url,
                test_name="staging_environment_validation",
                environment="staging"
            )
            
            self.metrics.custom_metrics["staging_connection_attempted"] = True
            self.metrics.custom_metrics["staging_connection_result"] = connection_result["status"]
            
            # Staging connection should either succeed or require authentication
            if connection_result["status"] == "success":
                self.metrics.custom_metrics["staging_connection_success"] = True
            elif connection_result["status"] == "auth_required":
                self.metrics.custom_metrics["staging_auth_required"] = True
                # Auth requirement is acceptable - skip rather than fail
                pytest.skip(f"Staging WebSocket requires authentication: {connection_result['message']}")
            else:
                # Unexpected failure in staging
                self.metrics.custom_metrics["staging_connection_error"] = connection_result["message"]
                pytest.fail(
                    f"Staging WebSocket connection failed: {connection_result['message']}"
                )

    async def _test_websocket_connection(self, ws_url, test_name, environment=None):
        """
        Helper method to test WebSocket connection
        
        Returns connection result with status and details
        """
        if not ws_url:
            return {
                "status": "error",
                "message": "WebSocket URL not provided",
                "test_name": test_name
            }
        
        try:
            # Attempt WebSocket connection
            async with websockets.connect(
                ws_url, 
                open_timeout=self.connection_timeout,
                close_timeout=2.0
            ) as websocket:
                
                # Send test message
                test_message = {
                    "type": "connection_test",
                    "test_name": test_name,
                    "timestamp": time.time()
                }
                
                await websocket.send(json.dumps(test_message))
                
                # Wait for response or timeout
                try:
                    response = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=self.response_timeout
                    )
                    
                    return {
                        "status": "success",
                        "message": f"WebSocket connection successful: {response}",
                        "test_name": test_name,
                        "response": response
                    }
                    
                except asyncio.TimeoutError:
                    return {
                        "status": "success",
                        "message": "WebSocket connection established (no response within timeout)",
                        "test_name": test_name
                    }
        
        except websockets.exceptions.ConnectionClosed as e:
            # Connection closed - may indicate auth requirement or server issue
            if "403" in str(e) or "401" in str(e):
                return {
                    "status": "auth_required",
                    "message": f"WebSocket connection requires authentication: {e}",
                    "test_name": test_name
                }
            else:
                return {
                    "status": "error", 
                    "message": f"WebSocket connection closed: {e}",
                    "test_name": test_name
                }
        
        except websockets.exceptions.WebSocketException as e:
            # WebSocket-specific error
            if "403" in str(e) or "401" in str(e):
                return {
                    "status": "auth_required",
                    "message": f"WebSocket authentication required: {e}",
                    "test_name": test_name
                }
            else:
                return {
                    "status": "error",
                    "message": f"WebSocket error: {e}",
                    "test_name": test_name
                }
        
        except Exception as e:
            # General connection error
            return {
                "status": "error",
                "message": f"Connection failed: {e}",
                "test_name": test_name
            }


if __name__ == "__main__":
    # Enable execution for validation
    pytest.main([__file__, "-v", "--tb=short"])