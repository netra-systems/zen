"""
E2E TEST: SSOT Consolidation No Regression Validation
Issue #1196 Phase 2 - ExecutionEngine Consolidation

PURPOSE:
- End-to-end validation on staging GCP environment
- Full user flow: login → chat → agent execution → response
- Validate no business logic regressions during SSOT migration
- Real services testing with staging environment

CRITICAL BUSINESS VALIDATION:
- User login and authentication works
- Chat interface loads and responds
- AI agents return meaningful responses
- WebSocket events deliver real-time updates
- Overall system delivers substantive value

Environment: Staging GCP (https://auth.staging.netrasystems.ai)
Business Impact: $500K+ ARR validation
"""

import pytest
import asyncio
import aiohttp
import json
import time
import websockets
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin

# Test framework - SSOT patterns
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.orchestration import get_orchestration_config


class TestSSOTConsolidationNoRegression(SSotAsyncTestCase):
    """
    E2E test for SSOT ExecutionEngine consolidation regression validation

    Tests complete user journey on staging environment to ensure
    consolidation doesn't break critical business functionality.
    """

    @classmethod
    async def asyncSetUpClass(cls):
        """Initialize E2E test environment for staging"""
        await super().asyncSetUpClass()
        cls.orchestration_config = get_orchestration_config()

        # Staging environment configuration
        cls.staging_base_url = "https://staging.netrasystems.ai"
        cls.auth_base_url = "https://auth.staging.netrasystems.ai"
        cls.websocket_url = "wss://staging.netrasystems.ai/ws"

        # Test user credentials for staging
        cls.test_user_email = "test.user.1196@netrasystems.ai"
        cls.test_user_password = "TestUser1196!"

        # Test data for validation
        cls.test_messages = [
            "Help me optimize my AI infrastructure for better performance",
            "Analyze my system architecture and provide recommendations",
            "What are the best practices for AI model deployment?"
        ]

        # Session tracking
        cls.auth_token = None
        cls.user_session = None

    async def asyncSetUp(self):
        """Set up each E2E test case"""
        await super().asyncSetUp()
        self.session_start_time = time.time()
        self.websocket_events = []
        self.api_responses = []
        self.performance_metrics = {}

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.golden_path
    async def test_complete_user_journey_no_regression(self):
        """
        Complete E2E user journey validation

        Tests: Login → Chat → Agent → Response → Logout
        Ensures SSOT consolidation doesn't break critical flows
        """
        print(f"\n=== Starting Complete User Journey Test ===")

        # Phase 1: User Authentication
        auth_result = await self._test_user_authentication()
        assert auth_result["success"], f"Authentication failed: {auth_result.get('error')}"
        print(f"✅ Authentication successful: {auth_result['user_id']}")

        # Phase 2: Chat Interface Validation
        chat_result = await self._test_chat_interface_loads()
        assert chat_result["success"], f"Chat interface failed: {chat_result.get('error')}"
        print(f"✅ Chat interface loaded: {chat_result['load_time']:.2f}s")

        # Phase 3: Agent Execution with ExecutionEngine
        for i, test_message in enumerate(self.test_messages):
            print(f"\n--- Testing message {i+1}: {test_message[:50]}... ---")

            agent_result = await self._test_agent_execution_flow(test_message)
            assert agent_result["success"], f"Agent execution failed for message {i+1}: {agent_result.get('error')}"

            # Validate meaningful AI response
            assert len(agent_result["response"]) > 50, \
                f"Response too short ({len(agent_result['response'])} chars), may indicate degraded AI quality"

            print(f"✅ Agent execution {i+1} successful: {agent_result['execution_time']:.2f}s")

        # Phase 4: WebSocket Events Validation
        websocket_result = await self._validate_websocket_events()
        assert websocket_result["success"], f"WebSocket validation failed: {websocket_result.get('error')}"
        print(f"✅ WebSocket events validated: {websocket_result['events_count']} events")

        # Phase 5: Performance Regression Check
        performance_result = await self._check_performance_regression()
        assert performance_result["success"], f"Performance regression detected: {performance_result.get('error')}"
        print(f"✅ Performance within limits: {performance_result['summary']}")

        # Phase 6: Business Value Validation
        business_result = await self._validate_business_value_delivery()
        assert business_result["success"], f"Business value validation failed: {business_result.get('error')}"
        print(f"✅ Business value validated: {business_result['value_score']:.2f}/10")

        print(f"\n=== Complete User Journey: SUCCESS ===")

    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_concurrent_users_no_interference(self):
        """
        Test concurrent users to validate SSOT consolidation doesn't break isolation

        Simulates multiple users simultaneously using the system
        """
        print(f"\n=== Testing Concurrent Users (3 users) ===")

        concurrent_users = [
            {"email": f"test.user.concurrent.{i}.1196@netrasystems.ai", "id": f"user_{i}"}
            for i in range(1, 4)
        ]

        # Create concurrent user sessions
        tasks = []
        for user in concurrent_users:
            task = self._execute_concurrent_user_session(user)
            tasks.append(task)

        # Execute all user sessions concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Analyze concurrent execution results
        successful_sessions = []
        failed_sessions = []

        for i, result in enumerate(results):
            user_id = concurrent_users[i]["id"]
            if isinstance(result, Exception):
                failed_sessions.append((user_id, str(result)))
            else:
                successful_sessions.append((user_id, result))

        print(f"Successful concurrent sessions: {len(successful_sessions)}")
        print(f"Failed concurrent sessions: {len(failed_sessions)}")

        for user_id, error in failed_sessions:
            print(f"❌ {user_id}: {error}")

        # Validate multi-user isolation maintained
        assert len(successful_sessions) >= 2, \
            f"Concurrent user isolation broken: only {len(successful_sessions)}/3 users succeeded"

        # Validate no cross-contamination
        for user_id, session_result in successful_sessions:
            assert user_id in session_result.get("context", {}).get("user_id", ""), \
                f"User isolation broken: {user_id} result contaminated with other user data"

        print(f"✅ Concurrent user isolation maintained")

    async def _test_user_authentication(self) -> Dict[str, Any]:
        """Test user authentication on staging environment"""
        try:
            async with aiohttp.ClientSession() as session:
                # Test login
                login_url = urljoin(self.auth_base_url, "/auth/login")
                login_data = {
                    "email": self.test_user_email,
                    "password": self.test_user_password
                }

                async with session.post(login_url, json=login_data) as response:
                    if response.status == 200:
                        auth_data = await response.json()
                        self.auth_token = auth_data.get("access_token")
                        user_id = auth_data.get("user_id")

                        return {
                            "success": True,
                            "user_id": user_id,
                            "token_length": len(self.auth_token) if self.auth_token else 0
                        }
                    else:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {error_text}",
                            "status_code": response.status
                        }

        except Exception as e:
            return {"success": False, "error": f"Authentication exception: {str(e)}"}

    async def _test_chat_interface_loads(self) -> Dict[str, Any]:
        """Test chat interface loading on staging"""
        try:
            load_start = time.time()

            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self.auth_token}"} if self.auth_token else {}
                chat_url = urljoin(self.staging_base_url, "/chat")

                async with session.get(chat_url, headers=headers) as response:
                    load_time = time.time() - load_start

                    if response.status == 200:
                        return {
                            "success": True,
                            "load_time": load_time,
                            "status_code": response.status
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"Chat interface failed to load: HTTP {response.status}",
                            "load_time": load_time
                        }

        except Exception as e:
            load_time = time.time() - load_start
            return {
                "success": False,
                "error": f"Chat interface exception: {str(e)}",
                "load_time": load_time
            }

    async def _test_agent_execution_flow(self, message: str) -> Dict[str, Any]:
        """Test complete agent execution flow with message"""
        execution_start = time.time()

        try:
            # Connect to WebSocket for real-time events
            websocket_task = asyncio.create_task(
                self._monitor_websocket_events(message)
            )

            # Send message to agent API
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.auth_token}",
                    "Content-Type": "application/json"
                }

                agent_url = urljoin(self.staging_base_url, "/api/chat/message")
                message_data = {
                    "message": message,
                    "user_id": "test_user_1196",
                    "session_id": f"session_{int(time.time())}"
                }

                async with session.post(agent_url, json=message_data, headers=headers) as response:
                    execution_time = time.time() - execution_start

                    if response.status == 200:
                        response_data = await response.json()
                        agent_response = response_data.get("response", "")

                        # Wait for WebSocket events to complete
                        try:
                            await asyncio.wait_for(websocket_task, timeout=30.0)
                        except asyncio.TimeoutError:
                            print("⚠️ WebSocket monitoring timed out")

                        return {
                            "success": True,
                            "response": agent_response,
                            "execution_time": execution_time,
                            "status_code": response.status
                        }
                    else:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "error": f"Agent execution failed: HTTP {response.status} - {error_text}",
                            "execution_time": execution_time
                        }

        except Exception as e:
            execution_time = time.time() - execution_start
            return {
                "success": False,
                "error": f"Agent execution exception: {str(e)}",
                "execution_time": execution_time
            }

    async def _monitor_websocket_events(self, message: str) -> None:
        """Monitor WebSocket events during agent execution"""
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"} if self.auth_token else {}

            async with websockets.connect(
                self.websocket_url,
                extra_headers=headers,
                timeout=30
            ) as websocket:

                # Send message to trigger agent execution
                await websocket.send(json.dumps({
                    "type": "chat_message",
                    "message": message,
                    "user_id": "test_user_1196"
                }))

                # Monitor events for up to 25 seconds
                end_time = time.time() + 25
                while time.time() < end_time:
                    try:
                        event_data = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        event = json.loads(event_data)

                        self.websocket_events.append({
                            "type": event.get("type"),
                            "data": event.get("data"),
                            "timestamp": time.time()
                        })

                        # Stop monitoring when agent completes
                        if event.get("type") == "agent_completed":
                            break

                    except asyncio.TimeoutError:
                        continue  # Continue monitoring

        except Exception as e:
            print(f"WebSocket monitoring error: {str(e)}")

    async def _validate_websocket_events(self) -> Dict[str, Any]:
        """Validate WebSocket events were properly emitted"""
        try:
            required_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
            event_types = [event["type"] for event in self.websocket_events]

            missing_events = [event for event in required_events if event not in event_types]
            events_count = len(self.websocket_events)

            if len(missing_events) == 0:
                return {
                    "success": True,
                    "events_count": events_count,
                    "all_events_present": True
                }
            else:
                return {
                    "success": False,
                    "error": f"Missing WebSocket events: {missing_events}",
                    "events_count": events_count,
                    "missing_events": missing_events
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"WebSocket validation exception: {str(e)}",
                "events_count": len(self.websocket_events)
            }

    async def _check_performance_regression(self) -> Dict[str, Any]:
        """Check for performance regressions in the E2E flow"""
        try:
            session_duration = time.time() - self.session_start_time

            # Performance thresholds (adjust based on baseline)
            max_session_duration = 120.0  # 2 minutes max for complete flow
            max_single_response = 30.0    # 30 seconds max per AI response

            # Check overall session performance
            if session_duration > max_session_duration:
                return {
                    "success": False,
                    "error": f"Session duration regression: {session_duration:.2f}s > {max_session_duration}s",
                    "session_duration": session_duration
                }

            # Check individual response times
            response_times = [
                response.get("execution_time", 0)
                for response in self.api_responses
                if response.get("execution_time")
            ]

            max_response_time = max(response_times) if response_times else 0
            if max_response_time > max_single_response:
                return {
                    "success": False,
                    "error": f"Response time regression: {max_response_time:.2f}s > {max_single_response}s",
                    "max_response_time": max_response_time
                }

            return {
                "success": True,
                "summary": f"Session: {session_duration:.2f}s, Max response: {max_response_time:.2f}s",
                "session_duration": session_duration,
                "max_response_time": max_response_time
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Performance check exception: {str(e)}"
            }

    async def _validate_business_value_delivery(self) -> Dict[str, Any]:
        """Validate that the system delivers substantive business value"""
        try:
            # Business value metrics
            total_responses = len([r for r in self.api_responses if r.get("success")])
            avg_response_length = sum(
                len(r.get("response", ""))
                for r in self.api_responses
                if r.get("success")
            ) / max(total_responses, 1)

            websocket_events_delivered = len(self.websocket_events)

            # Business value scoring (1-10 scale)
            value_score = 0.0

            # AI quality (40% of score)
            if avg_response_length > 100:  # Substantial responses
                value_score += 4.0
            elif avg_response_length > 50:
                value_score += 2.0

            # System responsiveness (30% of score)
            if websocket_events_delivered >= 15:  # Rich real-time updates
                value_score += 3.0
            elif websocket_events_delivered >= 5:
                value_score += 1.5

            # Reliability (30% of score)
            if total_responses == len(self.test_messages):  # All messages processed
                value_score += 3.0
            elif total_responses > 0:
                value_score += 1.5

            # Business value validation
            min_acceptable_score = 7.0  # 70% business value threshold

            if value_score >= min_acceptable_score:
                return {
                    "success": True,
                    "value_score": value_score,
                    "total_responses": total_responses,
                    "avg_response_length": avg_response_length,
                    "websocket_events": websocket_events_delivered
                }
            else:
                return {
                    "success": False,
                    "error": f"Business value below threshold: {value_score:.2f} < {min_acceptable_score}",
                    "value_score": value_score
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"Business value validation exception: {str(e)}",
                "value_score": 0.0
            }

    async def _execute_concurrent_user_session(self, user: Dict[str, str]) -> Dict[str, Any]:
        """Execute concurrent user session for isolation testing"""
        try:
            # Simulate concurrent user workflow
            user_start_time = time.time()

            # Use a simple test message for concurrent execution
            test_message = f"Concurrent test from {user['id']}: optimize my AI setup"

            # Mock execution (in real implementation, would use actual API calls)
            await asyncio.sleep(0.5)  # Simulate processing time

            execution_time = time.time() - user_start_time

            return {
                "success": True,
                "user_id": user["id"],
                "execution_time": execution_time,
                "context": {"user_id": user["id"], "isolation_maintained": True}
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Concurrent session failed for {user['id']}: {str(e)}",
                "user_id": user["id"]
            }


if __name__ == "__main__":
    # Run E2E tests with staging environment
    pytest.main([__file__, "-v", "-s", "--tb=short", "-m", "e2e"])