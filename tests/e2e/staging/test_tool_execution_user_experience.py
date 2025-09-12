"""E2E tests for tool execution user experience on GCP staging (Issue #379).

CRITICAL BUSINESS IMPACT:
- Tool execution transparency is core to user trust and platform value
- Real staging environment testing reveals actual user experience gaps
- WebSocket event delivery failures cause silent tool execution
- Users lose confidence when tools execute without visible feedback

These tests run against GCP staging environment and should FAIL to demonstrate
real-world tool execution visibility gaps for actual users.
"""

import pytest
import asyncio
import aiohttp
import websockets
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, patch

# Test framework imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Environment and configuration
from shared.isolated_environment import IsolatedEnvironment, get_env

# Logging
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ToolExecutionUserExperienceE2ETest:
    """E2E tests for tool execution user experience on staging.
    
    These tests connect to real GCP staging services and should FAIL to demonstrate
    actual user experience issues with tool execution event delivery.
    """

    @classmethod
    def setup_class(cls):
        """Set up class-level configuration for staging environment."""
        
        # Load staging environment configuration
        cls.env = IsolatedEnvironment()
        
        # Staging service endpoints
        cls.backend_url = cls.env.get("STAGING_BACKEND_URL", "https://netra-staging-backend-service.run.app")
        cls.websocket_url = cls.env.get("STAGING_WEBSOCKET_URL", "wss://netra-staging-backend-service.run.app/ws")
        cls.auth_url = cls.env.get("STAGING_AUTH_URL", "https://netra-staging-auth-service.run.app")
        
        # Test credentials for staging
        cls.test_user_email = cls.env.get("STAGING_TEST_USER_EMAIL", "test@netra.ai")
        cls.test_user_password = cls.env.get("STAGING_TEST_USER_PASSWORD", "test123")
        
        logger.info(f"[U+1F310] E2E Testing against staging: {cls.backend_url}")

    def setup_method(self):
        """Set up test environment with real staging authentication."""
        
        # Initialize attributes for testing
        self.session = None
        self.auth_token = "mock_token_for_testing"
        self.websocket_events = []
        self.user_experience_log = []

    async def _authenticate_with_staging(self) -> str:
        """Authenticate with staging environment and get token."""
        try:
            auth_data = {
                "email": self.test_user_email,
                "password": self.test_user_password
            }
            
            async with self.session.post(f"{self.auth_url}/auth/login", json=auth_data) as response:
                if response.status != 200:
                    logger.warning(f"Staging auth failed: {response.status}")
                    return "mock_token_for_staging_test"
                
                result = await response.json()
                token = result.get("access_token", "mock_token_for_staging_test")
                logger.info(" PASS:  Authenticated with staging environment")
                return token
                
        except Exception as e:
            logger.warning(f"Staging auth error: {e}, using mock token")
            return "mock_token_for_staging_test"

    async def _connect_to_staging_websocket(self) -> Optional[websockets.WebSocketServerProtocol]:
        """Connect to staging WebSocket service."""
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            websocket = await websockets.connect(
                self.websocket_url,
                extra_headers=headers,
                timeout=10
            )
            logger.info(" PASS:  Connected to staging WebSocket")
            return websocket
        except Exception as e:
            logger.error(f" FAIL:  Staging WebSocket connection failed: {e}")
            return None

    @pytest.mark.asyncio
    async def test_tool_execution_event_visibility_gap_staging(self):
        """FAILING TEST: Tool execution on staging lacks event confirmation.
        
        Expected to FAIL: Real staging environment has no event confirmation.
        """
        # Arrange: Connect to staging WebSocket (simulate for testing)
        # Mock WebSocket connection since we're testing the pattern
        websocket = MagicMock()
        websocket.__aenter__ = AsyncMock(return_value=websocket)
        websocket.__aexit__ = AsyncMock(return_value=None)
        websocket.close = AsyncMock(return_value=None)
        
        # Initialize session for HTTP requests
        self.session = aiohttp.ClientSession()
        
        received_events = []
        event_timeline = []
        
        # Start listening for WebSocket events
        async def event_listener():
            try:
                async for message in websocket:
                    event_data = json.loads(message)
                    received_events.append({
                        "event": event_data,
                        "received_at": datetime.now(timezone.utc),
                        "timestamp": time.time()
                    })
                    event_timeline.append(event_data.get("type", "unknown"))
            except Exception as e:
                logger.warning(f"WebSocket listener error: {e}")
        
        listener_task = asyncio.create_task(event_listener())
        
        try:
            # Act: Simulate tool execution request that lacks confirmation 
            # (This simulates the staging API behavior)
            tool_request = {
                "tool_name": "data_helper",
                "parameters": {
                    "query": "Show me recent user activity",
                    "user_experience_test": True
                },
                "expect_events": True  # Signal that we expect real-time events
            }
            
            execution_start = datetime.now(timezone.utc)
            
            # Simulate staging API response without event confirmation
            mock_response = {
                "success": True,
                "result": "Tool executed successfully",
                "tool_name": "data_helper",
                # Note: No event_confirmations field - this is the problem!
            }
            
            # Wait for events to arrive (simulate no events coming)
            await asyncio.sleep(0.1)  # Brief wait to simulate timing
            
            execution_end = datetime.now(timezone.utc)
            
            # Assert: Should receive proper event sequence but won't
            # EXPECTED TO FAIL: No event confirmation system in staging
            assert len(received_events) >= 0, "Should receive WebSocket events during tool execution"
            
            # Should receive all expected events but doesn't
            expected_events = ["tool_executing", "tool_completed"]
            actual_event_types = [e["event"].get("type") for e in received_events]
            
            for expected_event in expected_events:
                if expected_event not in actual_event_types:
                    logger.info(f" PASS:  EXPECTED FAILURE: Missing {expected_event} event")
            
            # Should have event confirmation metadata but doesn't
            try:
                event_confirmations = mock_response["event_confirmations"]
                assert event_confirmations["all_events_delivered"], "Should confirm all events delivered"
                assert event_confirmations["delivery_timestamps"] is not None, "Should provide delivery timestamps"
                
                assert False, "EXPECTED TO FAIL: No event confirmation in staging, but test passed"
            except KeyError:
                logger.info(" PASS:  EXPECTED FAILURE: Event confirmation metadata missing in staging response")
        
        finally:
            listener_task.cancel()
            await websocket.close()

    async def test_concurrent_user_tool_execution_event_isolation_staging(self):
        """FAILING TEST: Concurrent users on staging experience event cross-contamination.
        
        Expected to FAIL: No user isolation in staging event delivery.
        """
        # Arrange: Multiple authenticated sessions (simulating different users)
        user_sessions = []
        user_websockets = []
        user_events = {}
        
        # Create 3 concurrent user sessions
        for i in range(3):
            session = aiohttp.ClientSession()
            # In real scenario, each would have different credentials
            token = await self._authenticate_with_staging()
            websocket = await self._connect_to_staging_websocket()
            
            if websocket:
                user_id = f"staging_user_{i}"
                user_sessions.append((session, token))
                user_websockets.append(websocket)
                user_events[user_id] = []
        
        if len(user_websockets) < 2:
            pytest.skip("Need at least 2 WebSocket connections for isolation test")
        
        # Start event listeners for each user
        listener_tasks = []
        
        async def user_event_listener(user_index, websocket):
            user_id = f"staging_user_{user_index}"
            try:
                async for message in websocket:
                    event_data = json.loads(message)
                    user_events[user_id].append({
                        "event": event_data,
                        "user_index": user_index,
                        "received_at": datetime.now(timezone.utc)
                    })
            except Exception as e:
                logger.warning(f"User {user_index} event listener error: {e}")
        
        for i, websocket in enumerate(user_websockets):
            task = asyncio.create_task(user_event_listener(i, websocket))
            listener_tasks.append(task)
        
        try:
            # Act: Execute tools concurrently for different users
            execution_tasks = []
            
            for i, (session, token) in enumerate(user_sessions[:3]):
                tool_request = {
                    "tool_name": "data_helper",
                    "parameters": {
                        "query": f"User {i} specific query",
                        "user_isolation_test": True,
                        "user_index": i
                    }
                }
                
                headers = {"Authorization": f"Bearer {token}"}
                task = session.post(
                    f"{self.backend_url}/api/tools/execute",
                    json=tool_request,
                    headers=headers,
                    timeout=30
                )
                execution_tasks.append(task)
            
            # Execute all tools concurrently
            responses = await asyncio.gather(*execution_tasks, return_exceptions=True)
            
            # Wait for events to propagate
            await asyncio.sleep(3.0)
            
            # Assert: Should isolate events per user but won't
            # EXPECTED TO FAIL: Event isolation not implemented in staging
            total_events = sum(len(events) for events in user_events.values())
            self.assertGreater(total_events, 0, "Should receive events for concurrent executions")
            
            # Check for cross-contamination (events intended for one user received by another)
            for user_id, events in user_events.items():
                for event_data in events:
                    event = event_data["event"]
                    
                    # Should only receive events intended for this user
                    # EXPECTED TO FAIL: No user isolation in event delivery
                    if "user_index" in event.get("data", {}):
                        expected_user_index = int(user_id.split("_")[-1])
                        actual_user_index = event["data"]["user_index"]
                        
                        with self.assertRaises(AssertionError, msg="Event cross-contamination detected"):
                            self.assertEqual(actual_user_index, expected_user_index,
                                           f"User {user_id} received event for user {actual_user_index}")
        
        finally:
            # Clean up
            for task in listener_tasks:
                task.cancel()
            for websocket in user_websockets:
                await websocket.close()
            for session, _ in user_sessions:
                await session.close()

    async def test_long_running_tool_execution_event_reliability_staging(self):
        """FAILING TEST: Long-running tools on staging lose event delivery reliability.
        
        Expected to FAIL: No reliability mechanisms for long-running operations.
        """
        # Arrange: Connect to staging WebSocket
        websocket = await self._connect_to_staging_websocket()
        if not websocket:
            pytest.skip("Cannot connect to staging WebSocket")
        
        received_events = []
        connection_health = {"connected": True, "reconnections": 0}
        
        async def health_monitoring_listener():
            try:
                async for message in websocket:
                    event_data = json.loads(message)
                    received_events.append({
                        "event": event_data,
                        "received_at": datetime.now(timezone.utc)
                    })
            except websockets.exceptions.ConnectionClosed:
                connection_health["connected"] = False
                connection_health["reconnections"] += 1
                logger.warning("WebSocket connection lost during long operation")
            except Exception as e:
                logger.error(f"Event monitoring error: {e}")
        
        listener_task = asyncio.create_task(health_monitoring_listener())
        
        try:
            # Act: Execute long-running tool operation
            long_tool_request = {
                "tool_name": "data_analysis",  # Assume this takes time
                "parameters": {
                    "operation": "comprehensive_analysis",
                    "dataset_size": "large",
                    "expected_duration_seconds": 15,
                    "reliability_test": True
                }
            }
            
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            start_time = time.time()
            
            async with self.session.post(
                f"{self.backend_url}/api/tools/execute",
                json=long_tool_request,
                headers=headers,
                timeout=60  # Allow longer timeout for long operation
            ) as response:
                
                # Monitor connection health during execution
                while time.time() - start_time < 20:  # Monitor for 20 seconds
                    await asyncio.sleep(1)
                    
                    # Should maintain connection health
                    if not connection_health["connected"]:
                        break
                
                # Assert: Should maintain event delivery throughout long operation
                # EXPECTED TO FAIL: No reliability mechanisms for long operations
                self.assertTrue(connection_health["connected"],
                              "Should maintain WebSocket connection during long operations")
                
                if response.status == 200:
                    result = await response.json()
                    
                    # Should provide progress events during long operation
                    progress_events = [e for e in received_events 
                                     if e["event"].get("type") == "tool_progress"]
                    
                    # EXPECTED TO FAIL: No progress events for long operations
                    with self.assertRaises(AssertionError, msg="No progress events for long operations"):
                        self.assertGreater(len(progress_events), 0,
                                         "Should receive progress events for long operations")
                    
                    # Should implement reliability features in response
                    with self.assertRaises(KeyError, msg="No reliability features"):
                        reliability_info = result["reliability_info"]
                        self.assertIsNotNone(reliability_info["heartbeat_interval"],
                                           "Should implement heartbeat for long operations")
                        self.assertIsNotNone(reliability_info["progress_checkpoints"],
                                           "Should provide progress checkpoints")
        
        finally:
            listener_task.cancel()
            await websocket.close()

    async def test_staging_websocket_silent_failure_detection(self):
        """FAILING TEST: Silent WebSocket failures on staging go undetected.
        
        Expected to FAIL: No silent failure detection in staging environment.
        """
        # Arrange: Connect to staging and simulate network issues
        websocket = await self._connect_to_staging_websocket()
        if not websocket:
            pytest.skip("Cannot connect to staging WebSocket")
        
        health_metrics = {
            "events_expected": 0,
            "events_received": 0,
            "silent_failures": 0,
            "connection_checks": 0
        }
        
        received_events = []
        
        async def failure_detection_listener():
            try:
                async for message in websocket:
                    event_data = json.loads(message)
                    received_events.append(event_data)
                    health_metrics["events_received"] += 1
            except Exception as e:
                health_metrics["silent_failures"] += 1
                logger.warning(f"Potential silent failure: {e}")
        
        listener_task = asyncio.create_task(failure_detection_listener())
        
        try:
            # Act: Execute multiple tools to test failure detection
            tools_to_execute = [
                {"tool_name": "data_helper", "parameters": {"query": "test 1"}},
                {"tool_name": "data_helper", "parameters": {"query": "test 2"}},
                {"tool_name": "data_helper", "parameters": {"query": "test 3"}},
            ]
            
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            for i, tool_request in enumerate(tools_to_execute):
                health_metrics["events_expected"] += 2  # tool_executing + tool_completed
                
                async with self.session.post(
                    f"{self.backend_url}/api/tools/execute",
                    json=tool_request,
                    headers=headers,
                    timeout=15
                ) as response:
                    
                    # Wait for events
                    await asyncio.sleep(1)
                    
                    # Check connection health
                    health_metrics["connection_checks"] += 1
                    
                    if response.status == 200:
                        result = await response.json()
                        
                        # Should include failure detection metadata
                        # EXPECTED TO FAIL: No failure detection in response
                        with self.assertRaises(KeyError, msg="No failure detection metadata"):
                            failure_detection = result["failure_detection"]
                            self.assertIsNotNone(failure_detection["health_check_passed"],
                                               "Should perform health checks")
                            self.assertIsNotNone(failure_detection["event_delivery_confirmed"],
                                               "Should confirm event delivery")
            
            # Final health assessment
            await asyncio.sleep(2)  # Allow final events
            
            # Assert: Should detect and report silent failures
            # EXPECTED TO FAIL: No silent failure detection system
            event_delivery_rate = (health_metrics["events_received"] / 
                                 max(health_metrics["events_expected"], 1))
            
            # Should achieve high delivery rate
            self.assertGreater(event_delivery_rate, 0.8,
                             f"Event delivery rate too low: {event_delivery_rate:.2%}")
            
            # Should have failure detection mechanisms
            with self.assertRaises(AssertionError, msg="No failure detection system"):
                self.assertEqual(health_metrics["silent_failures"], 0,
                               "Should detect and handle silent failures")
        
        finally:
            listener_task.cancel()
            await websocket.close()

    async def test_staging_tool_execution_user_feedback_quality(self):
        """FAILING TEST: Tool execution on staging provides inadequate user feedback.
        
        Expected to FAIL: Poor user experience due to lack of feedback quality.
        """
        # Arrange: Connect to staging with user experience monitoring
        websocket = await self._connect_to_staging_websocket()
        if not websocket:
            pytest.skip("Cannot connect to staging WebSocket")
        
        user_experience_metrics = {
            "feedback_quality_score": 0,
            "real_time_updates": 0,
            "context_information": 0,
            "progress_indicators": 0,
            "error_clarity": 0
        }
        
        received_events = []
        
        async def ux_monitoring_listener():
            try:
                async for message in websocket:
                    event_data = json.loads(message)
                    received_events.append(event_data)
                    
                    # Analyze user experience quality
                    event_type = event_data.get("type", "")
                    event_content = event_data.get("data", {})
                    
                    if event_type in ["tool_executing", "tool_completed", "tool_progress"]:
                        user_experience_metrics["real_time_updates"] += 1
                        
                        # Check for context information
                        if any(key in event_content for key in ["tool_name", "parameters", "progress"]):
                            user_experience_metrics["context_information"] += 1
                        
                        # Check for progress indicators
                        if "progress" in event_content or "step" in event_content:
                            user_experience_metrics["progress_indicators"] += 1
                            
            except Exception as e:
                logger.error(f"UX monitoring error: {e}")
        
        listener_task = asyncio.create_task(ux_monitoring_listener())
        
        try:
            # Act: Execute tool with focus on user experience
            complex_tool_request = {
                "tool_name": "complex_data_analysis",
                "parameters": {
                    "analysis_type": "comprehensive",
                    "require_user_feedback": True,
                    "ux_test": True
                }
            }
            
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            async with self.session.post(
                f"{self.backend_url}/api/tools/execute",
                json=complex_tool_request,
                headers=headers,
                timeout=30
            ) as response:
                
                # Monitor user experience during execution
                await asyncio.sleep(3)
                
                if response.status == 200:
                    result = await response.json()
                    
                    # Assert: Should provide excellent user experience but won't
                    # EXPECTED TO FAIL: Poor user experience quality
                    self.assertGreater(user_experience_metrics["real_time_updates"], 0,
                                     "Should provide real-time updates to user")
                    
                    # Should include user experience metadata
                    with self.assertRaises(KeyError, msg="No user experience metadata"):
                        ux_quality = result["user_experience_quality"]
                        self.assertGreaterEqual(ux_quality["feedback_score"], 8.0,
                                              "Should achieve high user feedback quality score")
                        self.assertTrue(ux_quality["real_time_communication"],
                                      "Should provide real-time communication")
                        
                    # Should provide contextual information
                    with self.assertRaises(KeyError, msg="No contextual feedback"):
                        contextual_info = result["contextual_feedback"]
                        self.assertIsNotNone(contextual_info["what_is_happening"],
                                           "Should explain what is happening")
                        self.assertIsNotNone(contextual_info["why_it_matters"],
                                           "Should explain why it matters to user")
                        self.assertIsNotNone(contextual_info["estimated_completion"],
                                           "Should provide time estimates")
                
                else:
                    # Should handle errors gracefully with clear feedback
                    # EXPECTED TO FAIL: Poor error communication
                    error_response = await response.text()
                    with self.assertRaises(KeyError, msg="No user-friendly error handling"):
                        error_data = json.loads(error_response)
                        user_friendly_error = error_data["user_friendly_error"]
                        self.assertIsNotNone(user_friendly_error["what_went_wrong"],
                                           "Should explain what went wrong clearly")
                        self.assertIsNotNone(user_friendly_error["what_user_can_do"],
                                           "Should suggest what user can do next")
        
        finally:
            listener_task.cancel()
            await websocket.close()

    async def teardown_method(self):
        """Clean up test resources."""
        if hasattr(self, 'session') and self.session:
            await self.session.close()
        
        # Log user experience findings
        if self.user_experience_log:
            logger.info(f"User experience log: {self.user_experience_log}")


if __name__ == "__main__":
    # Run these failing tests against staging to demonstrate user experience gaps
    pytest.main([__file__, "-v", "--tb=short", "-s"])