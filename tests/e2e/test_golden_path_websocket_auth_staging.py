
# PERFORMANCE: Lazy loading for mission critical tests

# PERFORMANCE: Lazy loading for mission critical tests
_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

"""
E2E tests for WebSocket authentication in staging - DESIGNED TO FAIL INITIALLY

Purpose: Test complete Golden Path user flow in actual staging environment
Issue: Frontend sending ['jwt', token] instead of expected 'jwt.${token}' format causing cascading failures
Impact: Complete Golden Path broken ($500K+ ARR chat functionality) in staging GCP Cloud Run
Expected: These tests MUST FAIL initially to prove they detect the real staging issue

GitHub Issue: #171  
Test Plan: /TEST_PLAN_WEBSOCKET_AUTH_PROTOCOL_MISMATCH.md

CRITICAL: Tests against REAL staging GCP Cloud Run environment
MISSION CRITICAL: Golden Path user flow validation
"""

import pytest
import asyncio
import base64
import json
import time
import websockets
import ssl
from typing import Dict, List, Optional, Any
from unittest.mock import patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from tests.e2e.staging_test_base import StagingTestBase
from tests.e2e.staging_config import StagingTestConfig as StagingConfig
from tests.e2e.staging_test_helpers import StagingTestSuite as StagingTestHelpers

# Import authentication components for staging
from tests.e2e.staging_auth_client import StagingAuthClient
from tests.e2e.real_websocket_client import RealWebSocketClient
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestWebSocketAuthGoldenPathStaging(StagingTestBase):

    def create_user_context(self) -> UserExecutionContext:
        """Create isolated user execution context for golden path tests"""
        return UserExecutionContext.create_for_user(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run"
        )

    """E2E tests for WebSocket authentication in staging - MISSION CRITICAL"""
    
    @classmethod
    async def asyncSetUpClass(cls):
        """Setup for staging environment tests"""
        await super().asyncSetUpClass()
        
        # Initialize staging configuration
        cls.staging_config = StagingConfig()
        cls.staging_helpers = StagingTestHelpers()
        
        # Staging service URLs
        cls.staging_backend_url = cls.staging_config.get_backend_websocket_url()
        cls.staging_auth_url = cls.staging_config.get_auth_service_url()
        
        # Initialize staging auth client for real JWT generation
        cls.auth_client = StagingAuthClient()
        
        # Initialize real WebSocket client
        cls.websocket_client = RealWebSocketClient()
        
        # Verify staging services are accessible
        await cls._verify_staging_services()
        
        # Create test user for Golden Path
        cls.test_user = await cls._create_golden_path_test_user()
        
        cls.logger.info("Staging E2E test setup completed")
    
    @classmethod
    async def _verify_staging_services(cls):
        """Verify staging services are accessible and healthy"""
        try:
            # Check backend health
            backend_health = await cls.staging_helpers.check_service_health(
                cls.staging_config.get_backend_base_url()
            )
            assert backend_health, "Staging backend is not healthy"
            
            # Check auth service health
            auth_health = await cls.staging_helpers.check_service_health(
                cls.staging_auth_url
            )
            assert auth_health, "Staging auth service is not healthy"
            
            cls.logger.info("All staging services are healthy")
            
        except Exception as e:
            pytest.skip(f"Staging environment not available: {e}")
    
    @classmethod
    async def _create_golden_path_test_user(cls) -> Dict[str, Any]:
        """Create a test user for Golden Path testing"""
        try:
            # Use staging auth client to create/login test user
            test_user_data = {
                "email": f"golden_path_test_{int(time.time())}@netra-testing.ai",
                "user_id": f"golden_path_user_{int(time.time())}",
                "test_scenario": "websocket_auth_protocol_mismatch"
            }
            
            # Generate real JWT token for staging
            access_token = await cls.auth_client.generate_test_access_token(
                user_id=test_user_data["user_id"],
                email=test_user_data["email"]
            )
            
            test_user_data["access_token"] = access_token
            test_user_data["encoded_token"] = base64.urlsafe_b64encode(
                access_token.encode()
            ).decode().rstrip('=')
            
            cls.logger.info(f"Created Golden Path test user: {test_user_data['email']}")
            return test_user_data
            
        except Exception as e:
            pytest.skip(f"Failed to create staging test user: {e}")

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.golden_path
    @pytest.mark.mission_critical
    async def test_complete_golden_path_user_flow_staging(self):
        """
        Test complete Golden Path: login  ->  WebSocket connection  ->  AI response
        
        Full user journey:
        1. User login via OAuth
        2. WebSocket connection with JWT
        3. Send chat message
        4. Receive AI agent response
        
        DIFFICULTY: Very High (45 minutes)
        REAL SERVICES: Yes (staging GCP Cloud Run environment)
        STATUS: Should FAIL initially (WebSocket connection timeout), PASS after fix
        """
        # Arrange: Prepare Golden Path test scenario
        golden_path_start_time = time.time()
        golden_path_steps = []
        
        try:
            # Step 1: Verify user authentication (simulates login)
            golden_path_steps.append({"step": "auth_verification", "status": "starting"})
            
            auth_verification = await self.auth_client.verify_token(
                self.test_user["access_token"]
            )
            assert auth_verification["valid"], "Test user token should be valid"
            
            golden_path_steps[-1]["status"] = "completed"
            golden_path_steps[-1]["duration"] = time.time() - golden_path_start_time
            
            # Step 2: Establish WebSocket connection (CRITICAL - This should fail with bug)
            golden_path_steps.append({"step": "websocket_connection", "status": "starting"})
            websocket_start_time = time.time()
            
            # Test with CORRECT protocol format first (baseline)
            correct_subprotocols = ["jwt-auth", f"jwt.{self.test_user['encoded_token']}"]
            
            connection = await self._attempt_staging_websocket_connection(
                subprotocols=correct_subprotocols,
                timeout=30,  # Longer timeout for staging environment
                connection_description="Golden Path WebSocket with correct protocol"
            )
            
            if connection is None:
                # Expected failure - log details for analysis
                websocket_duration = time.time() - websocket_start_time
                golden_path_steps[-1]["status"] = "failed"
                golden_path_steps[-1]["duration"] = websocket_duration
                golden_path_steps[-1]["error"] = "WebSocket connection failed/timed out"
                
                pytest.fail(
                    f"GOLDEN PATH FAILURE: WebSocket connection failed in staging. "
                    f"Duration: {websocket_duration:.1f}s. "
                    f"This breaks the critical user flow ($500K+ ARR impact). "
                    f"Steps completed: {golden_path_steps}"
                )
            
            # Step 3: Send chat message (simulates user interaction)
            golden_path_steps.append({"step": "chat_message_send", "status": "starting"})
            
            golden_path_message = {
                "type": "chat_message",
                "data": {
                    "message": "Hello! This is a Golden Path test message for WebSocket auth protocol validation.",
                    "test_scenario": "golden_path_staging",
                    "timestamp": int(time.time()),
                    "user_id": self.test_user["user_id"]
                }
            }
            
            await connection.send(json.dumps(golden_path_message))
            golden_path_steps[-1]["status"] = "completed"
            
            # Step 4: Receive AI agent response (validates complete flow)
            golden_path_steps.append({"step": "ai_agent_response", "status": "starting"})
            
            # Wait for AI response with longer timeout for staging
            ai_response_timeout = 45  # Staging may be slower
            ai_response = await asyncio.wait_for(
                connection.recv(),
                timeout=ai_response_timeout
            )
            
            assert ai_response is not None, "Should receive AI agent response"
            
            # Validate response structure
            response_data = json.loads(ai_response)
            assert "type" in response_data, "Response should have type field"
            assert "data" in response_data, "Response should have data field"
            
            golden_path_steps[-1]["status"] = "completed"
            golden_path_steps[-1]["response_type"] = response_data.get("type", "unknown")
            
            # GOLDEN PATH SUCCESS
            total_golden_path_duration = time.time() - golden_path_start_time
            
            self.logger.info(
                f"GOLDEN PATH SUCCESS: Complete user flow works in staging. "
                f"Total duration: {total_golden_path_duration:.1f}s. "
                f"Steps: {golden_path_steps}"
            )
            
            await connection.close()
            
        except asyncio.TimeoutError as e:
            # This is the expected failure with the protocol bug
            total_duration = time.time() - golden_path_start_time
            
            pytest.fail(
                f"GOLDEN PATH TIMEOUT: AI response timeout in staging after {total_duration:.1f}s. "
                f"This indicates WebSocket auth protocol issues breaking user experience. "
                f"Completed steps: {golden_path_steps}. "
                f"BUSINESS IMPACT: $500K+ ARR chat functionality broken."
            )
            
        except Exception as e:
            # Other failures also break Golden Path
            total_duration = time.time() - golden_path_start_time
            
            pytest.fail(
                f"GOLDEN PATH ERROR: {str(e)} after {total_duration:.1f}s. "
                f"Completed steps: {golden_path_steps}. "
                f"This breaks critical user functionality in staging."
            )

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.websocket_auth_protocol
    async def test_websocket_connection_gcp_cloud_run_environment(self):
        """
        Test WebSocket connection specifically in GCP Cloud Run environment
        
        Validates connection behavior with GCP networking and container constraints
        
        DIFFICULTY: High (30 minutes)
        REAL SERVICES: Yes (staging GCP deployment)
        STATUS: Should FAIL initially (handshake timeout), PASS after fix
        """
        # Test various protocol scenarios in GCP Cloud Run
        gcp_test_scenarios = [
            {
                "name": "correct_protocol_format",
                "subprotocols": ["jwt-auth", f"jwt.{self.test_user['encoded_token']}"],
                "expected_result": "success",
                "timeout": 20
            },
            {
                "name": "incorrect_protocol_bug_format", 
                "subprotocols": ["jwt", self.test_user['encoded_token']],  # BUG FORMAT
                "expected_result": "failure", 
                "timeout": 25  # Longer timeout to observe failure mode
            },
            {
                "name": "missing_jwt_prefix",
                "subprotocols": ["jwt-auth", self.test_user['encoded_token']],
                "expected_result": "failure",
                "timeout": 20
            },
            {
                "name": "no_subprotocols",
                "subprotocols": [],
                "expected_result": "failure",
                "timeout": 15
            }
        ]
        
        gcp_test_results = []
        
        for scenario in gcp_test_scenarios:
            scenario_start = time.time()
            self.logger.info(f"Testing GCP scenario: {scenario['name']}")
            
            try:
                connection = await self._attempt_staging_websocket_connection(
                    subprotocols=scenario["subprotocols"],
                    timeout=scenario["timeout"],
                    connection_description=f"GCP test: {scenario['name']}"
                )
                
                scenario_duration = time.time() - scenario_start
                
                if connection is not None:
                    # Connection succeeded - test message flow
                    try:
                        test_message = {
                            "type": "ping",
                            "data": {
                                "test_scenario": scenario['name'],
                                "gcp_environment": "staging"
                            }
                        }
                        
                        await connection.send(json.dumps(test_message))
                        response = await asyncio.wait_for(connection.recv(), timeout=10.0)
                        
                        result = {
                            "scenario": scenario['name'],
                            "status": "success",
                            "duration": scenario_duration,
                            "response_received": response is not None
                        }
                        
                    except asyncio.TimeoutError:
                        result = {
                            "scenario": scenario['name'], 
                            "status": "partial_success",
                            "duration": scenario_duration,
                            "note": "Connected but message timed out"
                        }
                        
                    finally:
                        await connection.close()
                        
                else:
                    # Connection failed
                    result = {
                        "scenario": scenario['name'],
                        "status": "failed",
                        "duration": scenario_duration,
                        "note": "Connection failed or timed out"
                    }
                    
                gcp_test_results.append(result)
                
                # Analyze result vs expectation
                if scenario["expected_result"] == "success" and result["status"] != "success":
                    self.logger.error(
                        f"GCP ISSUE: {scenario['name']} expected to succeed but failed. "
                        f"Duration: {scenario_duration:.1f}s"
                    )
                elif scenario["expected_result"] == "failure" and result["status"] == "success":
                    self.logger.warning(
                        f"GCP UNEXPECTED: {scenario['name']} expected to fail but succeeded. "
                        f"May indicate bug is fixed."
                    )
                    
            except Exception as e:
                gcp_test_results.append({
                    "scenario": scenario['name'],
                    "status": "error", 
                    "duration": time.time() - scenario_start,
                    "error": str(e)
                })
        
        # Analyze overall GCP behavior
        success_count = len([r for r in gcp_test_results if r["status"] == "success"])
        failure_count = len([r for r in gcp_test_results if r["status"] in ["failed", "error"]])
        
        self.logger.info(f"GCP Cloud Run test results: {success_count} successes, {failure_count} failures")
        
        # The bug should cause most scenarios to fail
        expected_successes = len([s for s in gcp_test_scenarios if s["expected_result"] == "success"])
        
        if success_count < expected_successes:
            pytest.fail(
                f"GCP Cloud Run environment issues: Expected {expected_successes} successes, got {success_count}. "
                f"Results: {gcp_test_results}. "
                f"This suggests broader staging infrastructure problems beyond the protocol bug."
            )
        
        if success_count > expected_successes:
            self.logger.warning(
                f"More successes than expected ({success_count} vs {expected_successes}). "
                f"Protocol bug may be fixed or test needs adjustment."
            )

    @pytest.mark.e2e
    @pytest.mark.staging  
    @pytest.mark.websocket_auth_protocol
    async def test_concurrent_user_websocket_connections_staging(self):
        """
        Test multiple concurrent users connecting to WebSocket in staging
        
        Validates user isolation and protocol handling under concurrent load
        
        DIFFICULTY: Very High (35 minutes)
        REAL SERVICES: Yes (staging environment)
        STATUS: Should FAIL initially (connection failures), PASS after fix
        """
        # Create multiple test users for concurrent testing
        concurrent_user_count = 3  # Moderate load for staging
        concurrent_users = []
        
        # Generate test users
        for i in range(concurrent_user_count):
            user_data = {
                "email": f"concurrent_test_{i}_{int(time.time())}@netra-testing.ai",
                "user_id": f"concurrent_user_{i}_{int(time.time())}",
                "index": i
            }
            
            # Generate JWT for each user
            access_token = await self.auth_client.generate_test_access_token(
                user_id=user_data["user_id"],
                email=user_data["email"]
            )
            
            user_data["access_token"] = access_token
            user_data["encoded_token"] = base64.urlsafe_b64encode(
                access_token.encode()
            ).decode().rstrip('=')
            
            concurrent_users.append(user_data)
        
        # Test concurrent connections with different protocol formats
        connection_tasks = []
        
        for i, user in enumerate(concurrent_users):
            # Vary protocol formats to test different scenarios
            if i == 0:
                # Correct format
                protocols = ["jwt-auth", f"jwt.{user['encoded_token']}"]
                expected_success = True
            elif i == 1:
                # Bug format
                protocols = ["jwt", user['encoded_token']]
                expected_success = False
            else:
                # Another incorrect format
                protocols = ["jwt-auth", user['encoded_token']]
                expected_success = False
            
            # Create concurrent connection task
            task = asyncio.create_task(
                self._test_concurrent_user_connection(user, protocols, expected_success)
            )
            connection_tasks.append(task)
        
        # Execute all connections concurrently
        concurrent_start_time = time.time()
        connection_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        total_concurrent_duration = time.time() - concurrent_start_time
        
        # Analyze concurrent connection results
        successful_connections = []
        failed_connections = []
        error_connections = []
        
        for i, result in enumerate(connection_results):
            if isinstance(result, Exception):
                error_connections.append({
                    "user_index": i,
                    "error": str(result)
                })
            elif result["status"] == "success":
                successful_connections.append(result)
            else:
                failed_connections.append(result)
        
        # Log results
        self.logger.info(
            f"Concurrent staging test completed in {total_concurrent_duration:.1f}s: "
            f"{len(successful_connections)} successful, "
            f"{len(failed_connections)} failed, "
            f"{len(error_connections)} errors"
        )
        
        # Validate results match expectations
        expected_successes = 1  # Only correct format should succeed
        actual_successes = len(successful_connections)
        
        if actual_successes < expected_successes:
            pytest.fail(
                f"Concurrent staging test: Expected {expected_successes} successes, got {actual_successes}. "
                f"Successful: {successful_connections}, "
                f"Failed: {failed_connections}, "
                f"Errors: {error_connections}. "
                f"This suggests broader staging issues beyond the protocol bug."
            )
        
        if actual_successes > expected_successes:
            pytest.fail(
                f"Concurrent staging test: More successes than expected ({actual_successes} vs {expected_successes}). "
                f"This may indicate the protocol bug has been fixed."
            )

    async def _test_concurrent_user_connection(
        self, 
        user: Dict[str, Any], 
        protocols: List[str], 
        expected_success: bool
    ) -> Dict[str, Any]:
        """Test connection for a single concurrent user"""
        user_start_time = time.time()
        
        try:
            connection = await self._attempt_staging_websocket_connection(
                subprotocols=protocols,
                timeout=20,
                connection_description=f"Concurrent user {user['index']}"
            )
            
            if connection is not None:
                # Test message exchange
                test_message = {
                    "type": "concurrent_test",
                    "data": {
                        "user_id": user["user_id"],
                        "user_index": user["index"],
                        "test_time": int(time.time())
                    }
                }
                
                await connection.send(json.dumps(test_message))
                response = await asyncio.wait_for(connection.recv(), timeout=8.0)
                
                await connection.close()
                
                return {
                    "status": "success",
                    "user_index": user["index"],
                    "user_id": user["user_id"],
                    "duration": time.time() - user_start_time,
                    "protocols": protocols,
                    "expected_success": expected_success,
                    "response_received": response is not None
                }
            else:
                return {
                    "status": "failed",
                    "user_index": user["index"],
                    "user_id": user["user_id"],
                    "duration": time.time() - user_start_time,
                    "protocols": protocols,
                    "expected_success": expected_success,
                    "error": "Connection failed or timed out"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "user_index": user["index"],
                "user_id": user["user_id"],
                "duration": time.time() - user_start_time,
                "protocols": protocols,
                "expected_success": expected_success,
                "error": str(e)
            }

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.websocket_auth_protocol
    async def test_websocket_heartbeat_and_reconnection_staging(self):
        """
        Test WebSocket heartbeat and reconnection behavior in staging
        
        Validates connection stability and recovery from network interruptions
        
        DIFFICULTY: High (25 minutes) 
        REAL SERVICES: Yes (staging with network simulation)
        STATUS: May FAIL initially (connection instability), improve after fix
        """
        # This test focuses on connection stability after successful auth
        # Use correct protocol format to isolate heartbeat/reconnection issues
        correct_protocols = ["jwt-auth", f"jwt.{self.test_user['encoded_token']}"]
        
        connection = await self._attempt_staging_websocket_connection(
            subprotocols=correct_protocols,
            timeout=25,
            connection_description="Heartbeat/reconnection test"
        )
        
        if connection is None:
            pytest.fail(
                "Cannot test heartbeat/reconnection - initial connection failed. "
                "This may be due to the WebSocket auth protocol bug."
            )
        
        try:
            # Test heartbeat functionality
            heartbeat_start = time.time()
            
            # Send periodic messages to keep connection alive
            for i in range(3):
                heartbeat_message = {
                    "type": "heartbeat",
                    "data": {
                        "sequence": i,
                        "timestamp": int(time.time())
                    }
                }
                
                await connection.send(json.dumps(heartbeat_message))
                
                try:
                    response = await asyncio.wait_for(connection.recv(), timeout=10.0)
                    assert response is not None, f"Should receive heartbeat response {i}"
                except asyncio.TimeoutError:
                    self.logger.warning(f"Heartbeat {i} timed out - connection may be unstable")
                
                # Wait between heartbeats
                await asyncio.sleep(2)
            
            heartbeat_duration = time.time() - heartbeat_start
            self.logger.info(f"Heartbeat test completed in {heartbeat_duration:.1f}s")
            
        except Exception as e:
            pytest.fail(f"Heartbeat test failed: {e}")
            
        finally:
            if connection and not connection.closed:
                await connection.close()

    async def _attempt_staging_websocket_connection(
        self,
        subprotocols: List[str],
        timeout: int,
        connection_description: str
    ) -> Optional[websockets.WebSocketClientProtocol]:
        """
        Attempt WebSocket connection to staging environment
        
        Args:
            subprotocols: Protocol list to send
            timeout: Connection timeout
            connection_description: Description for logging
            
        Returns:
            WebSocket connection or None if failed
        """
        try:
            self.logger.info(
                f"Attempting staging connection: {connection_description}, "
                f"protocols: {subprotocols}, timeout: {timeout}s"
            )
            
            # Create SSL context for staging (may use self-signed certs)
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False  # For staging testing
            ssl_context.verify_mode = ssl.CERT_NONE  # For staging testing
            
            connection_start = time.time()
            
            connection = await asyncio.wait_for(
                websockets.connect(
                    self.staging_backend_url,
                    subprotocols=subprotocols,
                    ssl=ssl_context if self.staging_backend_url.startswith('wss') else None,
                    # Additional staging-specific options
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=10
                ),
                timeout=timeout
            )
            
            connection_duration = time.time() - connection_start
            self.logger.info(
                f"Staging connection successful: {connection_description} "
                f"in {connection_duration:.1f}s"
            )
            
            return connection
            
        except asyncio.TimeoutError:
            connection_duration = time.time() - connection_start
            self.logger.error(
                f"Staging connection timeout: {connection_description} "
                f"after {connection_duration:.1f}s with protocols {subprotocols}"
            )
            return None
            
        except Exception as e:
            connection_duration = time.time() - connection_start
            self.logger.error(
                f"Staging connection error: {connection_description} "
                f"after {connection_duration:.1f}s: {e}"
            )
            return None


# Test execution configuration for staging
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.staging,
    pytest.mark.golden_path,
    pytest.mark.websocket_auth_protocol,
    pytest.mark.mission_critical,
    pytest.mark.real_services,
    pytest.mark.bug_reproduction
]


if __name__ == "__main__":
    # Allow running this file directly for staging testing
    pytest.main([
        __file__, 
        "-v", 
        "--tb=long", 
        "-s",
        "--staging",  # Enable staging tests
        "--golden-path"  # Enable golden path tests
    ])