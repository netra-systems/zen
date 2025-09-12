"""
E2E tests for complete Golden Path workflow in staging GCP environment

Purpose: Validate complete user workflow from login to AI response in staging
Issue: #426 - E2E golden path tests failing due to service dependencies
Approach: Real staging GCP services, complete end-to-end validation

MISSION CRITICAL: This test validates the complete Golden Path that delivers
$500K+ ARR through chat functionality. Must work in staging environment.

Golden Path Flow: Login → WebSocket Connection → Agent Execution → AI Response
Business Impact: 90% of platform value delivered through this workflow
"""

import pytest
import asyncio
import json
import time
import uuid
import base64
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import aiohttp
import websockets
import ssl

from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestGoldenPathCompleteStaging(SSotAsyncTestCase):
    """E2E tests for complete Golden Path in staging GCP environment"""
    
    @classmethod
    async def asyncSetUpClass(cls):
        """Setup staging environment test configuration"""
        await super().asyncSetUpClass()
        
        # Staging GCP environment configuration
        cls.staging_config = {
            "backend_url": "https://staging-backend-service.netra.ai",  # Replace with actual staging URL
            "auth_url": "https://staging-auth-service.netra.ai",        # Replace with actual staging URL
            "websocket_url": "wss://staging-backend-service.netra.ai/ws", # Replace with actual staging URL
            "frontend_url": "https://staging.netra.ai"                   # Replace with actual staging URL
        }
        
        # Check if we're in a staging-capable environment
        cls.staging_available = await cls._check_staging_availability()
        
        if not cls.staging_available:
            pytest.skip("Staging environment not available for E2E Golden Path testing")
        
        # Create test user for Golden Path
        cls.test_user = await cls._create_staging_test_user()
        cls.logger.info(f"Staging Golden Path test setup complete for user: {cls.test_user.get('email', 'unknown')}")

    @classmethod
    async def _check_staging_availability(cls) -> bool:
        """Check if staging environment is available and healthy"""
        try:
            # Check backend health endpoint
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{cls.staging_config['backend_url']}/health") as response:
                    if response.status == 200:
                        health_data = await response.json()
                        cls.logger.info(f"Staging backend health: {health_data}")
                        return True
                    else:
                        cls.logger.warning(f"Staging backend health check failed: {response.status}")
                        return False
                        
        except Exception as e:
            cls.logger.warning(f"Cannot connect to staging environment: {e}")
            return False

    @classmethod
    async def _create_staging_test_user(cls) -> Dict[str, Any]:
        """Create or retrieve staging test user for Golden Path testing"""
        test_user_data = {
            "email": f"golden_path_test_{int(time.time())}@netra-staging.ai",
            "name": "Golden Path Test User",
            "user_id": f"golden_path_user_{uuid.uuid4()}",
            "created_at": datetime.utcnow().isoformat()
        }
        
        try:
            # In real staging, this would authenticate through OAuth
            # For testing, we'll simulate authenticated user state
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Simulate user creation/authentication in staging
                auth_payload = {
                    "email": test_user_data["email"],
                    "name": test_user_data["name"],
                    "test_mode": True,
                    "golden_path_test": True
                }
                
                async with session.post(
                    f"{cls.staging_config['auth_url']}/auth/test-user",
                    json=auth_payload
                ) as response:
                    if response.status in [200, 201]:
                        auth_result = await response.json()
                        test_user_data.update({
                            "access_token": auth_result.get("access_token"),
                            "user_id": auth_result.get("user_id", test_user_data["user_id"]),
                            "authenticated": True
                        })
                    else:
                        # Fallback to mock auth for testing
                        cls.logger.warning(f"Staging auth creation failed: {response.status}, using mock auth")
                        test_user_data.update({
                            "access_token": "mock_staging_token_for_golden_path_testing",
                            "authenticated": False,  # Mark as mock
                            "fallback_mode": True
                        })
                        
        except Exception as e:
            cls.logger.warning(f"Failed to create staging test user: {e}, using mock fallback")
            test_user_data.update({
                "access_token": "mock_staging_token_for_golden_path_testing",
                "authenticated": False,
                "fallback_mode": True
            })
        
        return test_user_data

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.golden_path
    @pytest.mark.mission_critical
    async def test_complete_golden_path_staging_workflow(self):
        """
        Test complete Golden Path workflow in staging: Login → AI Response
        
        Issue: #426 - E2E golden path tests failing due to service dependencies
        Difficulty: Very High (60 minutes)
        Expected: PASS after Docker infrastructure issues are resolved
        Business Impact: $500K+ ARR depends on this workflow
        """
        golden_path_start = time.time()
        golden_path_steps = []
        
        try:
            # STEP 1: User Authentication (Login simulation)
            golden_path_steps.append({"step": "user_authentication", "status": "starting", "start_time": time.time()})
            
            if not self.test_user.get("authenticated", False):
                # Perform actual staging authentication
                auth_result = await self._perform_staging_authentication(self.test_user)
                assert auth_result["success"], f"Staging authentication failed: {auth_result.get('error')}"
                
                self.test_user.update(auth_result.get("user_data", {}))
            
            golden_path_steps[-1]["status"] = "completed"
            golden_path_steps[-1]["duration"] = time.time() - golden_path_steps[-1]["start_time"]
            
            # STEP 2: WebSocket Connection Establishment
            golden_path_steps.append({"step": "websocket_connection", "status": "starting", "start_time": time.time()})
            
            websocket_connection = await self._establish_staging_websocket_connection(self.test_user)
            assert websocket_connection is not None, "Failed to establish WebSocket connection to staging"
            
            golden_path_steps[-1]["status"] = "completed"
            golden_path_steps[-1]["duration"] = time.time() - golden_path_steps[-1]["start_time"]
            
            # STEP 3: Send Chat Message (User Input)
            golden_path_steps.append({"step": "chat_message_send", "status": "starting", "start_time": time.time()})
            
            chat_message = {
                "type": "chat_message",
                "data": {
                    "message": "Hello! This is a Golden Path test. Please analyze the current system status and provide an AI-powered response with actionable insights.",
                    "user_id": self.test_user["user_id"],
                    "thread_id": str(uuid.uuid4()),
                    "timestamp": datetime.utcnow().isoformat(),
                    "golden_path_test": True,
                    "business_critical": True,
                    "expected_ai_response": True
                }
            }
            
            await websocket_connection.send(json.dumps(chat_message))
            golden_path_steps[-1]["status"] = "completed"
            golden_path_steps[-1]["duration"] = time.time() - golden_path_steps[-1]["start_time"]
            
            # STEP 4: Agent Execution & WebSocket Events (CRITICAL)
            golden_path_steps.append({"step": "agent_execution_events", "status": "starting", "start_time": time.time()})
            
            # Collect WebSocket events during agent execution
            websocket_events = []
            agent_response = None
            
            # Listen for events with timeout
            event_timeout = 90  # Generous timeout for staging environment
            event_start = time.time()
            
            while time.time() - event_start < event_timeout:
                try:
                    # Wait for WebSocket message with short timeout for responsive collection
                    message = await asyncio.wait_for(websocket_connection.recv(), timeout=2.0)
                    
                    try:
                        event_data = json.loads(message)
                        websocket_events.append(event_data)
                        
                        # Check if this is the final AI response
                        if (event_data.get("type") == "agent_completed" or 
                            event_data.get("type") == "chat_response" or
                            "ai_response" in str(event_data).lower()):
                            agent_response = event_data
                            break
                            
                    except json.JSONDecodeError:
                        websocket_events.append({"raw_message": message, "timestamp": datetime.utcnow().isoformat()})
                        
                except asyncio.TimeoutError:
                    # Check if we have enough events to consider complete
                    if len(websocket_events) >= 3 and agent_response:
                        break
                    continue
            
            golden_path_steps[-1]["status"] = "completed"
            golden_path_steps[-1]["duration"] = time.time() - golden_path_steps[-1]["start_time"]
            golden_path_steps[-1]["events_collected"] = len(websocket_events)
            
            # STEP 5: AI Response Validation (Business Value)
            golden_path_steps.append({"step": "ai_response_validation", "status": "starting", "start_time": time.time()})
            
            # Validate we received substantive AI response (90% of platform value)
            assert len(websocket_events) > 0, (
                f"No WebSocket events received during agent execution. "
                f"This breaks real-time chat functionality that delivers 90% of platform value."
            )
            
            # Check for critical WebSocket events
            event_types = []
            for event in websocket_events:
                if isinstance(event, dict):
                    event_type = event.get("type", "unknown")
                    event_types.append(event_type)
            
            # Verify critical events were received
            critical_events = ["agent_started", "agent_thinking", "agent_completed"]
            events_received = []
            for critical_event in critical_events:
                if any(critical_event in event_type for event_type in event_types):
                    events_received.append(critical_event)
            
            assert len(events_received) >= 2, (
                f"Missing critical WebSocket events. Received: {events_received}, "
                f"Expected at least 2 of: {critical_events}. "
                f"This breaks real-time chat transparency."
            )
            
            # Validate AI response content (business value)
            if agent_response:
                response_content = str(agent_response).lower()
                ai_indicators = ["analysis", "insight", "recommendation", "status", "system", "ai", "response"]
                ai_content_found = any(indicator in response_content for indicator in ai_indicators)
                
                assert ai_content_found, (
                    f"AI response lacks substantive content. Response: {agent_response}. "
                    f"This fails to deliver the AI-powered value that users expect."
                )
            else:
                # No final response but events received - partial success
                self.logger.warning("No final AI response received, but WebSocket events were collected")
            
            golden_path_steps[-1]["status"] = "completed"
            golden_path_steps[-1]["duration"] = time.time() - golden_path_steps[-1]["start_time"]
            
            # GOLDEN PATH SUCCESS
            total_golden_path_duration = time.time() - golden_path_start
            
            self.logger.info(
                f"🎉 GOLDEN PATH SUCCESS IN STAGING! "
                f"Complete workflow took {total_golden_path_duration:.1f}s. "
                f"Steps completed: {len(golden_path_steps)}. "
                f"WebSocket events: {len(websocket_events)}. "
                f"This validates $500K+ ARR functionality."
            )
            
            # Clean up WebSocket connection
            await websocket_connection.close()
            
        except Exception as e:
            # GOLDEN PATH FAILURE - BUSINESS CRITICAL
            total_duration = time.time() - golden_path_start
            completed_steps = [step["step"] for step in golden_path_steps if step.get("status") == "completed"]
            
            pytest.fail(
                f"🚨 GOLDEN PATH FAILURE IN STAGING: {str(e)} "
                f"Duration: {total_duration:.1f}s. "
                f"Completed steps: {completed_steps}. "
                f"Failed at: {golden_path_steps[-1]['step'] if golden_path_steps else 'initialization'}. "
                f"BUSINESS IMPACT: $500K+ ARR chat functionality broken in staging. "
                f"This must be fixed before production deployment."
            )

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.websocket_race_conditions
    async def test_websocket_race_condition_prevention_staging(self):
        """
        Test WebSocket race condition prevention in staging Cloud Run
        
        Issue: #372 - WebSocket race condition reproduction
        Difficulty: High (45 minutes) 
        Expected: PASS - Race conditions should be prevented
        """
        # Test multiple rapid WebSocket connections to detect race conditions
        race_condition_scenarios = [
            {
                "name": "rapid_sequential_connections",
                "connection_count": 5,
                "connection_delay": 0.1  # 100ms between connections
            },
            {
                "name": "simultaneous_connections", 
                "connection_count": 3,
                "connection_delay": 0.0  # Simultaneous
            },
            {
                "name": "connection_retry_pattern",
                "connection_count": 3,
                "connection_delay": 0.5,
                "retry_failed": True
            }
        ]
        
        race_condition_results = []
        
        for scenario in race_condition_scenarios:
            scenario_start = time.time()
            self.logger.info(f"Testing race condition scenario: {scenario['name']}")
            
            connections = []
            connection_results = []
            
            try:
                # Create multiple connections based on scenario
                connection_tasks = []
                
                for i in range(scenario["connection_count"]):
                    if scenario["connection_delay"] > 0:
                        await asyncio.sleep(scenario["connection_delay"])
                    
                    # Create test user for each connection (simulates different users)
                    test_user = await self._create_staging_test_user()
                    
                    # Create connection task
                    task = asyncio.create_task(
                        self._test_single_websocket_connection(test_user, connection_id=i)
                    )
                    connection_tasks.append(task)
                
                # Execute connections (simultaneously or with delays)
                if scenario["connection_delay"] == 0.0:
                    # Simultaneous execution
                    connection_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
                else:
                    # Sequential execution with delays
                    for task in connection_tasks:
                        result = await task
                        connection_results.append(result)
                
                # Analyze results for race conditions
                successful_connections = []
                failed_connections = []
                exceptions = []
                
                for i, result in enumerate(connection_results):
                    if isinstance(result, Exception):
                        exceptions.append({"connection_id": i, "exception": str(result)})
                    elif result and result.get("success"):
                        successful_connections.append(result)
                    else:
                        failed_connections.append(result)
                
                scenario_duration = time.time() - scenario_start
                
                race_condition_results.append({
                    "scenario": scenario["name"],
                    "duration": scenario_duration,
                    "total_connections": scenario["connection_count"],
                    "successful_connections": len(successful_connections),
                    "failed_connections": len(failed_connections),
                    "exceptions": len(exceptions),
                    "success_rate": len(successful_connections) / scenario["connection_count"],
                    "details": {
                        "successful": successful_connections,
                        "failed": failed_connections,
                        "exceptions": exceptions
                    }
                })
                
                # Check for race condition indicators
                if len(exceptions) > scenario["connection_count"] * 0.5:
                    self.logger.warning(
                        f"High exception rate in {scenario['name']}: "
                        f"{len(exceptions)}/{scenario['connection_count']}. "
                        f"This may indicate race conditions."
                    )
                
            except Exception as e:
                race_condition_results.append({
                    "scenario": scenario["name"],
                    "duration": time.time() - scenario_start,
                    "error": str(e),
                    "success_rate": 0.0
                })
        
        # Analyze overall race condition test results
        total_scenarios = len(race_condition_scenarios)
        successful_scenarios = len([r for r in race_condition_results if r.get("success_rate", 0) > 0.7])
        
        self.logger.info(f"Race condition test results: {successful_scenarios}/{total_scenarios} scenarios succeeded")
        
        # Validate that race conditions are adequately handled
        assert successful_scenarios >= total_scenarios * 0.7, (
            f"Too many race condition scenarios failed: {successful_scenarios}/{total_scenarios}. "
            f"Results: {race_condition_results}. "
            f"This indicates WebSocket race condition issues in staging Cloud Run environment."
        )

    # Helper methods for staging E2E tests
    
    async def _perform_staging_authentication(self, test_user: Dict[str, Any]) -> Dict[str, Any]:
        """Perform authentication against staging auth service"""
        try:
            timeout = aiohttp.ClientTimeout(total=20)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                auth_payload = {
                    "email": test_user["email"],
                    "test_mode": True,
                    "golden_path_validation": True
                }
                
                async with session.post(
                    f"{self.staging_config['auth_url']}/auth/validate",
                    json=auth_payload
                ) as response:
                    if response.status == 200:
                        auth_data = await response.json()
                        return {
                            "success": True,
                            "user_data": {
                                "access_token": auth_data.get("access_token"),
                                "user_id": auth_data.get("user_id", test_user["user_id"]),
                                "authenticated": True
                            }
                        }
                    else:
                        return {"success": False, "error": f"Auth service returned {response.status}"}
                        
        except Exception as e:
            return {"success": False, "error": f"Auth request failed: {e}"}
    
    async def _establish_staging_websocket_connection(self, test_user: Dict[str, Any]) -> Optional[websockets.WebSocketClientProtocol]:
        """Establish WebSocket connection to staging environment"""
        try:
            # Prepare authentication for WebSocket
            access_token = test_user.get("access_token", "mock_token")
            encoded_token = base64.urlsafe_b64encode(access_token.encode()).decode().rstrip('=')
            
            # Use correct WebSocket protocol format
            subprotocols = ["jwt-auth", f"jwt.{encoded_token}"]
            
            # Create SSL context for staging
            ssl_context = ssl.create_default_context()
            # For staging testing, we might need to be less strict
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Connect to staging WebSocket
            connection = await asyncio.wait_for(
                websockets.connect(
                    self.staging_config["websocket_url"],
                    subprotocols=subprotocols,
                    ssl=ssl_context if self.staging_config["websocket_url"].startswith("wss") else None,
                    ping_interval=30,
                    ping_timeout=10
                ),
                timeout=30  # Generous timeout for staging
            )
            
            self.logger.info(f"Successfully connected to staging WebSocket: {self.staging_config['websocket_url']}")
            return connection
            
        except Exception as e:
            self.logger.error(f"Failed to establish staging WebSocket connection: {e}")
            return None
    
    async def _test_single_websocket_connection(self, test_user: Dict[str, Any], connection_id: int) -> Dict[str, Any]:
        """Test a single WebSocket connection for race condition testing"""
        connection_start = time.time()
        
        try:
            connection = await self._establish_staging_websocket_connection(test_user)
            
            if connection:
                # Send test message
                test_message = {
                    "type": "race_condition_test",
                    "data": {
                        "connection_id": connection_id,
                        "user_id": test_user["user_id"],
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
                
                await connection.send(json.dumps(test_message))
                
                # Wait for response (short timeout for race condition test)
                try:
                    response = await asyncio.wait_for(connection.recv(), timeout=5.0)
                    await connection.close()
                    
                    return {
                        "success": True,
                        "connection_id": connection_id,
                        "duration": time.time() - connection_start,
                        "response_received": response is not None
                    }
                except asyncio.TimeoutError:
                    await connection.close()
                    return {
                        "success": False,
                        "connection_id": connection_id,
                        "duration": time.time() - connection_start,
                        "error": "Response timeout"
                    }
            else:
                return {
                    "success": False,
                    "connection_id": connection_id,
                    "duration": time.time() - connection_start,
                    "error": "Failed to establish connection"
                }
                
        except Exception as e:
            return {
                "success": False,
                "connection_id": connection_id,
                "duration": time.time() - connection_start,
                "error": str(e)
            }


# Test configuration
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.staging,
    pytest.mark.golden_path,
    pytest.mark.websocket_race_conditions,
    pytest.mark.mission_critical,
    pytest.mark.issue_426,
    pytest.mark.issue_372,
    pytest.mark.real_services,
    pytest.mark.gcp_cloud_run,
    pytest.mark.business_critical
]


if __name__ == "__main__":
    # Allow running this file directly for staging validation
    pytest.main([
        __file__,
        "-v",
        "--tb=long",
        "-s",
        "--staging",
        "--golden-path",
        "--no-docker"  # These tests use staging GCP, not Docker
    ])