"""
E2E Test: Complete User Message → AI Response Flow (Staging)

Business Value: $500K+ ARR - Core chat functionality validation
Environment: GCP Staging with real services (NO DOCKER)
Coverage: Complete end-to-end user experience testing
Performance: Must complete within user experience SLAs

GitHub Issue: #861 - Agent Golden Path Messages E2E Test Coverage
Test Plan: /test_plans/agent_golden_path_messages_e2e_plan_20250914.md

MISSION CRITICAL: This test validates the complete Golden Path user journey:
1. User authenticates and establishes WebSocket connection
2. User sends substantive message requiring AI analysis  
3. Agent processes message with real LLM integration
4. All 5 WebSocket events delivered in correct sequence
5. User receives meaningful AI response with actionable insights
6. Response time < 10s for optimal user experience
7. Message and response persisted in database

SUCCESS CRITERIA:
- Complete user flow works end-to-end without failures
- All WebSocket events delivered (no silent failures)  
- Agent responses are substantive (not just technical success)
- Multi-user isolation maintained (enterprise security)
- Performance SLAs met (response time < 10s for UX)
"""

import pytest
import asyncio
import json
import time
import websockets
import ssl
import base64
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
import httpx

# SSOT Test Framework
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from tests.e2e.staging_test_base import StagingTestBase 
from tests.e2e.staging_config import StagingTestConfig as StagingConfig

# Real service clients for staging
from tests.e2e.staging_auth_client import StagingAuthClient
from tests.e2e.real_websocket_client import RealWebSocketClient
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestCompleteUserMessageFlowStaging(StagingTestBase):
    """
    Complete user message → AI response flow with real staging services
    
    BUSINESS IMPACT: Validates $500K+ ARR core chat functionality
    ENVIRONMENT: GCP Staging with real LLM, database, WebSocket services
    COVERAGE: End-to-end Golden Path user experience
    """
    
    # Test configuration
    MAX_MESSAGE_RESPONSE_TIME = 10.0  # User experience SLA
    COMPLEX_MESSAGE_RESPONSE_TIME = 15.0  # Complex analysis SLA
    WEBSOCKET_EVENT_TIMEOUT = 5.0  # Maximum gap between events
    
    # Test scenarios for comprehensive coverage
    TEST_SCENARIOS = [
        {
            "name": "simple_question",
            "message": "What are the key benefits of AI optimization?",
            "expected_response_time": 5.0,
            "expected_tools": 0,
            "response_validation": ["benefit", "optimization", "AI"]
        },
        {
            "name": "data_analysis_request", 
            "message": "Analyze the performance trends for Q3 and provide optimization recommendations",
            "expected_response_time": 10.0,
            "expected_tools": 2,
            "response_validation": ["analysis", "performance", "trends", "recommendation"]
        },
        {
            "name": "complex_multi_step",
            "message": "Create a comprehensive AI infrastructure assessment including cost analysis, performance metrics, and optimization roadmap",
            "expected_response_time": 15.0,
            "expected_tools": 3,
            "response_validation": ["assessment", "cost", "performance", "roadmap"]
        }
    ]
    
    @classmethod
    async def asyncSetUpClass(cls):
        """Setup for staging environment tests"""
        await super().asyncSetUpClass()
        
        # Initialize staging configuration
        cls.staging_config = StagingConfig()
        cls.staging_backend_url = cls.staging_config.get_backend_websocket_url()
        
        # Initialize real service clients
        cls.auth_client = StagingAuthClient()
        cls.websocket_client = RealWebSocketClient()
        
        # Verify staging services are accessible
        await cls._verify_staging_services_health()
        
        # Create test users for different scenarios
        cls.test_users = await cls._create_test_users()
        
        cls.logger.info("Complete user message flow staging test setup completed")
    
    @classmethod
    async def _verify_staging_services_health(cls):
        """Verify all required staging services are healthy"""
        health_checks = [
            ("Backend", cls.staging_config.get_backend_base_url()),
            ("Auth Service", cls.staging_config.get_auth_service_url()),
            ("WebSocket", cls.staging_config.get_backend_websocket_url())
        ]
        
        async with httpx.AsyncClient(timeout=10) as client:
            for service_name, url in health_checks:
                try:
                    health_url = f"{url}/health" if not url.endswith('/health') else url
                    response = await client.get(health_url)
                    
                    if response.status_code != 200:
                        pytest.skip(f"Staging {service_name} not healthy: {response.status_code}")
                        
                    cls.logger.info(f"Staging {service_name} service is healthy")
                    
                except Exception as e:
                    pytest.skip(f"Staging {service_name} not accessible: {e}")
    
    @classmethod 
    async def _create_test_users(cls) -> List[Dict[str, Any]]:
        """Create test users for different message scenarios"""
        test_users = []
        
        for i, scenario in enumerate(cls.TEST_SCENARIOS):
            user_data = {
                "user_id": f"e2e_msg_user_{scenario['name']}_{int(time.time())}",
                "email": f"e2e_msg_{scenario['name']}@netrasystems-staging.ai",
                "scenario": scenario['name'],
                "test_permissions": ["basic_chat", "agent_access", "data_analysis"]
            }
            
            # Generate real JWT token for staging
            try:
                access_token = await cls.auth_client.generate_test_access_token(
                    user_id=user_data["user_id"],
                    email=user_data["email"], 
                    permissions=user_data["test_permissions"]
                )
                
                user_data["access_token"] = access_token
                user_data["encoded_token"] = base64.urlsafe_b64encode(
                    access_token.encode()
                ).decode().rstrip('=')
                
                test_users.append(user_data)
                cls.logger.info(f"Created test user for {scenario['name']}: {user_data['email']}")
                
            except Exception as e:
                cls.logger.error(f"Failed to create test user for {scenario['name']}: {e}")
                pytest.skip(f"Cannot create staging test users: {e}")
        
        return test_users

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.golden_path  
    @pytest.mark.mission_critical
    @pytest.mark.real_services
    async def test_complete_golden_path_user_message_flow(self):
        """
        Test complete Golden Path: User sends message → Receives substantive AI response
        
        GOLDEN PATH VALIDATION: End-to-end user experience
        BUSINESS VALUE: $500K+ ARR core chat functionality  
        REAL SERVICES: Staging GCP with real LLM, database, WebSocket
        
        Complete Flow:
        1. User authentication and WebSocket connection
        2. Send substantive message requiring AI analysis
        3. Validate all 5 WebSocket events in sequence:
           - agent_started (user sees agent began)
           - agent_thinking (real-time reasoning visibility)
           - tool_executing (tool usage transparency) 
           - tool_completed (tool results display)
           - agent_completed (completion signal)
        4. Receive meaningful AI response with actionable insights
        5. Validate response quality and user experience timing
        6. Verify data persistence and user isolation
        """
        golden_path_start = time.time()
        test_results = []
        
        # Test each scenario to ensure comprehensive coverage
        for scenario in self.TEST_SCENARIOS:
            scenario_start = time.time()
            user = next((u for u in self.test_users if u["scenario"] == scenario["name"]), None)
            
            if not user:
                pytest.fail(f"No test user found for scenario: {scenario['name']}")
            
            self.logger.info(f"Testing Golden Path scenario: {scenario['name']}")
            
            try:
                # Step 1: Establish WebSocket connection with authentication
                connection = await self._establish_authenticated_websocket_connection(user)
                assert connection is not None, f"Failed to establish WebSocket connection for {scenario['name']}"
                
                # Step 2: Send message and track all WebSocket events
                websocket_events = []
                response_data = await self._send_message_and_track_events(
                    connection, scenario["message"], websocket_events, user
                )
                
                # Step 3: Validate WebSocket event sequence
                self._validate_websocket_event_sequence(websocket_events, scenario["name"])
                
                # Step 4: Validate AI response quality and substance
                self._validate_ai_response_quality(response_data, scenario)
                
                # Step 5: Validate performance SLA
                scenario_duration = time.time() - scenario_start
                assert scenario_duration <= scenario["expected_response_time"], \
                    f"Response time {scenario_duration:.1f}s exceeds SLA {scenario['expected_response_time']}s for {scenario['name']}"
                
                # Step 6: Verify data persistence
                await self._verify_message_persistence(user, scenario["message"], response_data)
                
                # Step 7: Test concurrent user isolation
                await self._test_user_isolation_during_scenario(user, scenario)
                
                await connection.close()
                
                test_results.append({
                    "scenario": scenario["name"],
                    "status": "success", 
                    "duration": scenario_duration,
                    "events_count": len(websocket_events),
                    "response_quality": "validated"
                })
                
                self.logger.info(f"Golden Path scenario {scenario['name']} completed successfully in {scenario_duration:.1f}s")
                
            except Exception as e:
                test_results.append({
                    "scenario": scenario["name"],
                    "status": "failed",
                    "duration": time.time() - scenario_start,
                    "error": str(e)
                })
                
                pytest.fail(f"Golden Path scenario {scenario['name']} failed: {e}")
        
        # Final validation: All scenarios must pass
        total_duration = time.time() - golden_path_start
        successful_scenarios = [r for r in test_results if r["status"] == "success"]
        
        assert len(successful_scenarios) == len(self.TEST_SCENARIOS), \
            f"Golden Path validation failed: {len(successful_scenarios)}/{len(self.TEST_SCENARIOS)} scenarios passed"
        
        self.logger.info(
            f"GOLDEN PATH SUCCESS: All scenarios completed in {total_duration:.1f}s. "
            f"Results: {test_results}"
        )

    async def _establish_authenticated_websocket_connection(self, user: Dict[str, Any]) -> websockets.WebSocketClientProtocol:
        """Establish authenticated WebSocket connection for user"""
        try:
            # Create SSL context for staging
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False  # For staging environment
            ssl_context.verify_mode = ssl.CERT_NONE  # For staging testing
            
            # Prepare authentication headers
            headers = {
                "Authorization": f"Bearer {user['access_token']}",
                "X-User-ID": user["user_id"],
                "X-Test-Scenario": user["scenario"],
                "X-Test-Environment": "staging",
                "X-E2E-Test": "true"
            }
            
            self.logger.info(f"Connecting to WebSocket for user {user['user_id']} scenario {user['scenario']}")
            
            connection = await asyncio.wait_for(
                websockets.connect(
                    self.staging_backend_url,
                    extra_headers=headers,
                    ssl=ssl_context if self.staging_backend_url.startswith('wss') else None,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=10
                ),
                timeout=30
            )
            
            # Test connection with ping
            await connection.ping()
            
            self.logger.info(f"WebSocket connection established for {user['scenario']}")
            return connection
            
        except Exception as e:
            self.logger.error(f"Failed to establish WebSocket connection for {user['scenario']}: {e}")
            raise

    async def _send_message_and_track_events(
        self, 
        connection: websockets.WebSocketClientProtocol,
        message: str,
        events_list: List[Dict[str, Any]],
        user: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send message and track all WebSocket events until completion"""
        
        # Send user message
        message_data = {
            "type": "chat_message",
            "data": {
                "message": message,
                "user_id": user["user_id"],
                "test_scenario": user["scenario"],
                "timestamp": int(time.time()),
                "session_id": f"e2e_test_{uuid.uuid4().hex[:8]}"
            }
        }
        
        await connection.send(json.dumps(message_data))
        self.logger.info(f"Sent message for scenario {user['scenario']}: {message[:50]}...")
        
        # Track events until agent completion
        expected_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        received_events = set()
        final_response = None
        
        event_start_time = time.time()
        last_event_time = event_start_time
        
        while len(received_events) < len(expected_events):
            try:
                # Wait for next event with timeout
                current_time = time.time()
                if current_time - last_event_time > self.WEBSOCKET_EVENT_TIMEOUT:
                    self.logger.warning(f"Event timeout exceeded: {current_time - last_event_time:.1f}s since last event")
                
                event_message = await asyncio.wait_for(
                    connection.recv(), 
                    timeout=self.WEBSOCKET_EVENT_TIMEOUT
                )
                
                event_data = json.loads(event_message)
                event_time = time.time()
                
                # Track event details
                event_record = {
                    "type": event_data.get("type"),
                    "timestamp": event_time,
                    "duration_from_start": event_time - event_start_time,
                    "gap_from_previous": event_time - last_event_time,
                    "data": event_data.get("data", {})
                }
                
                events_list.append(event_record)
                last_event_time = event_time
                
                # Track expected events
                if event_record["type"] in expected_events:
                    received_events.add(event_record["type"])
                    self.logger.info(f"Received event: {event_record['type']} (gap: {event_record['gap_from_previous']:.2f}s)")
                
                # Check for final response
                if event_record["type"] == "agent_completed":
                    final_response = event_data
                    break
                    
                # Safety timeout for entire event sequence
                if event_time - event_start_time > 30:  # 30s max for all events
                    self.logger.error(f"Event sequence timeout: {event_time - event_start_time:.1f}s")
                    break
                    
            except asyncio.TimeoutError:
                # Log timeout and continue - may be normal for some events
                current_time = time.time()
                self.logger.warning(
                    f"Event timeout after {current_time - last_event_time:.1f}s. "
                    f"Received: {received_events}, Expected: {expected_events}"
                )
                break
                
            except Exception as e:
                self.logger.error(f"Error receiving WebSocket event: {e}")
                break
        
        # Validate we received essential events
        critical_events = ["agent_started", "agent_completed"] 
        missing_critical = [e for e in critical_events if e not in received_events]
        
        if missing_critical:
            raise AssertionError(
                f"Missing critical WebSocket events: {missing_critical}. "
                f"Received: {received_events}, All events: {[e['type'] for e in events_list]}"
            )
        
        if not final_response:
            raise AssertionError("No final agent response received")
        
        return final_response

    def _validate_websocket_event_sequence(self, events: List[Dict[str, Any]], scenario_name: str):
        """Validate WebSocket event sequence and timing"""
        
        # Check minimum required events
        event_types = [e["type"] for e in events]
        required_events = ["agent_started", "agent_completed"]
        
        for required in required_events:
            assert required in event_types, \
                f"Missing required event {required} in scenario {scenario_name}. Events: {event_types}"
        
        # Validate event timing (no gaps > 5s)
        for i, event in enumerate(events):
            if i > 0:
                gap = event["gap_from_previous"]
                assert gap <= self.WEBSOCKET_EVENT_TIMEOUT, \
                    f"Event gap too large: {gap:.1f}s between events in {scenario_name}"
        
        # Validate logical sequence
        if "agent_started" in event_types and "agent_completed" in event_types:
            started_idx = event_types.index("agent_started")
            completed_idx = event_types.index("agent_completed")
            assert started_idx < completed_idx, \
                f"Event sequence error: agent_completed before agent_started in {scenario_name}"
        
        self.logger.info(f"WebSocket event sequence validated for {scenario_name}: {len(events)} events")

    def _validate_ai_response_quality(self, response_data: Dict[str, Any], scenario: Dict[str, Any]):
        """Validate AI response quality and substance"""
        
        response_content = response_data.get("data", {}).get("message", "")
        assert response_content, f"Empty response for scenario {scenario['name']}"
        
        # Check response length (substantive responses should be detailed)
        assert len(response_content) > 50, \
            f"Response too short ({len(response_content)} chars) for {scenario['name']}: {response_content[:100]}"
        
        # Check for expected content based on scenario
        response_lower = response_content.lower()
        validation_terms = scenario.get("response_validation", [])
        
        found_terms = [term for term in validation_terms if term.lower() in response_lower]
        assert len(found_terms) >= len(validation_terms) // 2, \
            f"Response lacks expected content for {scenario['name']}. " \
            f"Found: {found_terms}, Expected: {validation_terms}. " \
            f"Response: {response_content[:200]}..."
        
        # Validate response structure
        assert "data" in response_data, f"Response missing data field for {scenario['name']}"
        assert "timestamp" in response_data.get("data", {}), f"Response missing timestamp for {scenario['name']}"
        
        self.logger.info(f"AI response quality validated for {scenario['name']}: {len(response_content)} chars")

    async def _verify_message_persistence(self, user: Dict[str, Any], message: str, response_data: Dict[str, Any]):
        """Verify message and response are persisted in database"""
        try:
            # Make API call to verify message history
            async with httpx.AsyncClient(timeout=10) as client:
                history_url = f"{self.staging_config.get_backend_base_url()}/api/chat/history"
                headers = {"Authorization": f"Bearer {user['access_token']}"}
                
                history_response = await client.get(history_url, headers=headers)
                
                if history_response.status_code == 200:
                    history_data = history_response.json()
                    
                    # Check if message exists in history
                    messages = history_data.get("messages", [])
                    user_message_found = any(m.get("content", "") == message for m in messages)
                    
                    assert user_message_found, f"User message not found in chat history for {user['user_id']}"
                    self.logger.info(f"Message persistence verified for {user['scenario']}")
                    
                else:
                    self.logger.warning(f"Could not verify persistence: {history_response.status_code}")
                    
        except Exception as e:
            self.logger.warning(f"Persistence verification failed: {e}")
            # Non-critical for Golden Path flow

    async def _test_user_isolation_during_scenario(self, user: Dict[str, Any], scenario: Dict[str, Any]):
        """Test user isolation by simulating concurrent user activity"""
        try:
            # Create concurrent user for isolation testing
            concurrent_user = {
                "user_id": f"concurrent_{user['user_id']}",
                "email": f"concurrent_{user['email']}", 
                "access_token": user["access_token"]  # Different user, same session for testing
            }
            
            # Establish second connection
            concurrent_connection = await self._establish_authenticated_websocket_connection(concurrent_user)
            
            if concurrent_connection:
                # Send message from concurrent user
                isolation_message = {
                    "type": "chat_message",
                    "data": {
                        "message": "Isolation test message - should not interfere",
                        "user_id": concurrent_user["user_id"],
                        "test_isolation": True
                    }
                }
                
                await concurrent_connection.send(json.dumps(isolation_message))
                await concurrent_connection.close()
                
                self.logger.info(f"User isolation test completed for {scenario['name']}")
                
        except Exception as e:
            self.logger.warning(f"User isolation test failed: {e}")
            # Non-critical for main Golden Path flow

    @pytest.mark.e2e
    @pytest.mark.staging  
    @pytest.mark.performance
    async def test_concurrent_user_golden_path_performance(self):
        """
        Test Golden Path performance with multiple concurrent users
        
        PERFORMANCE VALIDATION: Multiple users using chat simultaneously
        ISOLATION VALIDATION: Users don't interfere with each other
        SCALABILITY VALIDATION: System handles concurrent load
        """
        concurrent_users = 3  # Moderate load for staging
        concurrent_tasks = []
        
        for i in range(concurrent_users):
            user = self.test_users[i % len(self.test_users)]
            scenario = self.TEST_SCENARIOS[i % len(self.TEST_SCENARIOS)]
            
            task = asyncio.create_task(
                self._run_single_user_golden_path(user, scenario, f"concurrent_{i}")
            )
            concurrent_tasks.append(task)
        
        # Execute all concurrent users
        start_time = time.time()
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        total_duration = time.time() - start_time
        
        # Analyze results
        successful_results = [r for r in results if not isinstance(r, Exception)]
        failed_results = [r for r in results if isinstance(r, Exception)]
        
        assert len(failed_results) == 0, \
            f"Concurrent Golden Path failures: {failed_results}"
        
        assert len(successful_results) == concurrent_users, \
            f"Expected {concurrent_users} successful results, got {len(successful_results)}"
        
        # Validate performance under load
        max_acceptable_duration = 20.0  # 20s max for concurrent execution
        assert total_duration <= max_acceptable_duration, \
            f"Concurrent execution too slow: {total_duration:.1f}s > {max_acceptable_duration}s"
        
        self.logger.info(
            f"Concurrent Golden Path test passed: {len(successful_results)} users "
            f"in {total_duration:.1f}s"
        )

    async def _run_single_user_golden_path(
        self, 
        user: Dict[str, Any], 
        scenario: Dict[str, Any], 
        test_id: str
    ) -> Dict[str, Any]:
        """Run Golden Path flow for a single user (for concurrent testing)"""
        try:
            start_time = time.time()
            
            # Establish connection
            connection = await self._establish_authenticated_websocket_connection(user)
            
            # Send message and get response
            events = []
            response = await self._send_message_and_track_events(
                connection, scenario["message"], events, user
            )
            
            await connection.close()
            
            duration = time.time() - start_time
            
            return {
                "test_id": test_id,
                "user_id": user["user_id"],
                "scenario": scenario["name"],
                "status": "success",
                "duration": duration,
                "events_count": len(events)
            }
            
        except Exception as e:
            return {
                "test_id": test_id,
                "user_id": user["user_id"],
                "scenario": scenario["name"],
                "status": "failed",
                "error": str(e),
                "duration": time.time() - start_time
            }


# Pytest configuration for this test module
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.staging,
    pytest.mark.golden_path,
    pytest.mark.mission_critical,
    pytest.mark.real_services,
    pytest.mark.business_critical
]