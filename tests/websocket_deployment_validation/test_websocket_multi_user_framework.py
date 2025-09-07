#!/usr/bin/env python
"""ADVANCED MULTI-USER WEBSOCKET TESTING FRAMEWORK

Comprehensive framework for testing WebSocket functionality under multi-user scenarios.
Validates user isolation, concurrent connections, and business value delivery.

Business Value: Ensures $180K+ MRR chat functionality works reliably for concurrent users
Critical: Tests the real-world scenario where multiple users interact simultaneously
"""

import asyncio
import json
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
import threading
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

import pytest
import websockets
from loguru import logger

from shared.isolated_environment import get_env
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper


@dataclass
class WebSocketUser:
    """Represents a test user with WebSocket connection."""
    
    user_id: str
    websocket: Optional[Any] = None
    jwt_token: Optional[str] = None
    connection_id: Optional[str] = None
    thread_id: Optional[str] = None
    messages_sent: int = 0
    messages_received: int = 0
    events_received: List[Dict[str, Any]] = None
    connection_time: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    errors: List[str] = None
    
    def __post_init__(self):
        if self.events_received is None:
            self.events_received = []
        if self.errors is None:
            self.errors = []
        if self.thread_id is None:
            self.thread_id = str(uuid.uuid4())


@dataclass  
class MultiUserTestScenario:
    """Defines a multi-user test scenario."""
    
    name: str
    description: str
    user_count: int
    concurrent_connections: bool = True
    message_pattern: str = "sequential"  # sequential, broadcast, targeted
    duration_seconds: int = 60
    expected_events: List[str] = None
    business_scenario: str = "chat"  # chat, agent_execution, mixed
    
    def __post_init__(self):
        if self.expected_events is None:
            self.expected_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]


class MultiUserWebSocketTester:
    """Framework for running advanced multi-user WebSocket tests."""
    
    def __init__(self, environment: str = "staging"):
        self.environment = environment
        self.auth_helper = E2EAuthHelper()
        self.users: List[WebSocketUser] = []
        self.active_connections: Dict[str, Any] = {}
        self.test_results: Dict[str, Any] = {}
        self.env = get_env()
        
        # Concurrency control
        self.max_concurrent_users = 10  # Safety limit
        self.connection_semaphore = asyncio.Semaphore(self.max_concurrent_users)
        
    def create_test_users(self, count: int) -> List[WebSocketUser]:
        """Create test users for multi-user scenario."""
        users = []
        
        for i in range(count):
            user = WebSocketUser(
                user_id=f"test_user_{i+1}_{int(time.time())}",
                thread_id=str(uuid.uuid4())
            )
            users.append(user)
            
        self.users = users
        logger.info(f"Created {count} test users for multi-user WebSocket testing")
        return users
        
    async def setup_user_connection(self, user: WebSocketUser) -> bool:
        """Setup WebSocket connection for a single user."""
        
        async with self.connection_semaphore:
            try:
                # Get JWT token for user
                user.jwt_token = await self.auth_helper.get_test_jwt_token(user_id=user.user_id)
                
                # Create WebSocket connection
                websocket_url = self._get_websocket_url()
                headers = {"Authorization": f"Bearer {user.jwt_token}"}
                
                user.websocket = await websockets.connect(
                    websocket_url,
                    extra_headers=headers,
                    timeout=15
                )
                
                user.connection_time = datetime.utcnow()
                user.last_activity = datetime.utcnow()
                
                # Wait for connection established message
                try:
                    welcome_msg = await asyncio.wait_for(user.websocket.recv(), timeout=10)
                    welcome_data = json.loads(welcome_msg)
                    
                    if welcome_data.get("type") == "connection_established":
                        user.connection_id = welcome_data.get("connection_id")
                        logger.info(f"✅ User {user.user_id} connected successfully (connection_id: {user.connection_id})")
                        return True
                    else:
                        logger.warning(f"⚠️ User {user.user_id} received unexpected welcome message: {welcome_data}")
                        return True  # Still connected, but unexpected format
                        
                except asyncio.TimeoutError:
                    logger.error(f"❌ User {user.user_id} did not receive welcome message within timeout")
                    return False
                    
            except Exception as e:
                logger.error(f"❌ Failed to setup connection for user {user.user_id}: {e}")
                user.errors.append(f"Connection setup failed: {e}")
                return False
                
    async def teardown_user_connection(self, user: WebSocketUser) -> None:
        """Teardown WebSocket connection for a user."""
        
        if user.websocket:
            try:
                await user.websocket.close()
                logger.info(f"🔌 Disconnected user {user.user_id}")
            except Exception as e:
                logger.warning(f"Error disconnecting user {user.user_id}: {e}")
                
    async def run_multi_user_scenario(self, scenario: MultiUserTestScenario) -> Dict[str, Any]:
        """Run a complete multi-user WebSocket test scenario."""
        
        logger.info(f"🚀 Starting multi-user scenario: {scenario.name}")
        logger.info(f"   Users: {scenario.user_count}, Pattern: {scenario.message_pattern}, Duration: {scenario.duration_seconds}s")
        
        scenario_results = {
            "scenario": scenario.name,
            "description": scenario.description,
            "start_time": datetime.utcnow().isoformat(),
            "users": {},
            "summary": {},
            "isolation_validated": False,
            "business_value_delivered": False
        }
        
        try:
            # Create test users
            users = self.create_test_users(scenario.user_count)
            
            # Setup connections (concurrent or sequential based on scenario)
            if scenario.concurrent_connections:
                logger.info("Setting up concurrent user connections...")
                connection_tasks = [self.setup_user_connection(user) for user in users]
                connection_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
            else:
                logger.info("Setting up sequential user connections...")
                connection_results = []
                for user in users:
                    result = await self.setup_user_connection(user)
                    connection_results.append(result)
                    await asyncio.sleep(1)  # Brief delay between connections
                    
            # Count successful connections
            successful_connections = sum(1 for result in connection_results if result is True)
            
            if successful_connections == 0:
                raise Exception("No users could connect - test scenario cannot proceed")
                
            logger.info(f"✅ {successful_connections}/{scenario.user_count} users connected successfully")
            
            # Filter to only successfully connected users
            connected_users = [user for user, result in zip(users, connection_results) if result is True]
            
            # Run the main test scenario
            if scenario.message_pattern == "sequential":
                await self._run_sequential_messaging(connected_users, scenario)
            elif scenario.message_pattern == "broadcast":
                await self._run_broadcast_messaging(connected_users, scenario)
            elif scenario.message_pattern == "targeted":
                await self._run_targeted_messaging(connected_users, scenario)
            else:
                raise ValueError(f"Unknown message pattern: {scenario.message_pattern}")
                
            # Collect results from all users
            for user in connected_users:
                user_result = {
                    "user_id": user.user_id,
                    "connection_id": user.connection_id,
                    "messages_sent": user.messages_sent,
                    "messages_received": user.messages_received,
                    "events_received_count": len(user.events_received),
                    "events_received": user.events_received,
                    "errors": user.errors,
                    "connection_duration": (datetime.utcnow() - user.connection_time).total_seconds() if user.connection_time else 0
                }
                scenario_results["users"][user.user_id] = user_result
                
            # Validate user isolation
            isolation_valid = await self._validate_user_isolation(connected_users)
            scenario_results["isolation_validated"] = isolation_valid
            
            # Validate business value delivery
            business_value_valid = await self._validate_business_value_delivery(connected_users, scenario)
            scenario_results["business_value_delivered"] = business_value_valid
            
            # Generate summary
            scenario_results["summary"] = {
                "total_users": scenario.user_count,
                "connected_users": successful_connections,
                "connection_success_rate": (successful_connections / scenario.user_count) * 100,
                "total_messages_sent": sum(user.messages_sent for user in connected_users),
                "total_messages_received": sum(user.messages_received for user in connected_users),
                "total_events_received": sum(len(user.events_received) for user in connected_users),
                "total_errors": sum(len(user.errors) for user in connected_users),
                "isolation_maintained": isolation_valid,
                "business_value_delivered": business_value_valid,
                "overall_success": isolation_valid and business_value_valid and successful_connections >= scenario.user_count * 0.8
            }
            
            # Cleanup connections
            cleanup_tasks = [self.teardown_user_connection(user) for user in connected_users]
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"❌ Multi-user scenario {scenario.name} failed: {e}")
            scenario_results["error"] = str(e)
            scenario_results["summary"] = {"overall_success": False}
            
        finally:
            scenario_results["end_time"] = datetime.utcnow().isoformat()
            
        return scenario_results
        
    async def _run_sequential_messaging(self, users: List[WebSocketUser], scenario: MultiUserTestScenario) -> None:
        """Run sequential messaging pattern - users send messages one after another."""
        
        logger.info("🔄 Running sequential messaging pattern...")
        
        messages_per_user = max(1, scenario.duration_seconds // len(users))
        
        for round_num in range(messages_per_user):
            for user in users:
                try:
                    # Send agent request message
                    message = {
                        "type": "agent_request",
                        "payload": {
                            "agent": "data_sub_agent",
                            "message": f"Sequential message {round_num + 1} from {user.user_id}",
                            "thread_id": user.thread_id
                        }
                    }
                    
                    await user.websocket.send(json.dumps(message))
                    user.messages_sent += 1
                    user.last_activity = datetime.utcnow()
                    
                    logger.debug(f"📤 User {user.user_id} sent message {round_num + 1}")
                    
                    # Collect responses for a brief period
                    await self._collect_user_responses(user, duration_seconds=3)
                    
                    # Brief pause between users
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Error in sequential messaging for user {user.user_id}: {e}")
                    user.errors.append(f"Sequential messaging error: {e}")
                    
    async def _run_broadcast_messaging(self, users: List[WebSocketUser], scenario: MultiUserTestScenario) -> None:
        """Run broadcast messaging pattern - all users send messages simultaneously."""
        
        logger.info("📡 Running broadcast messaging pattern...")
        
        rounds = max(1, scenario.duration_seconds // 10)  # One round every 10 seconds
        
        for round_num in range(rounds):
            logger.info(f"🔄 Broadcast round {round_num + 1}/{rounds}")
            
            # All users send messages simultaneously
            send_tasks = []
            for user in users:
                task = self._send_user_message(user, f"Broadcast message {round_num + 1}", user.thread_id)
                send_tasks.append(task)
                
            # Execute all sends concurrently
            await asyncio.gather(*send_tasks, return_exceptions=True)
            
            # Collect responses from all users
            response_tasks = []
            for user in users:
                task = self._collect_user_responses(user, duration_seconds=8)
                response_tasks.append(task)
                
            await asyncio.gather(*response_tasks, return_exceptions=True)
            
            # Pause between broadcast rounds
            await asyncio.sleep(2)
            
    async def _run_targeted_messaging(self, users: List[WebSocketUser], scenario: MultiUserTestScenario) -> None:
        """Run targeted messaging pattern - users send messages to specific targets."""
        
        logger.info("🎯 Running targeted messaging pattern...")
        
        if len(users) < 2:
            logger.warning("Targeted messaging requires at least 2 users - falling back to sequential")
            await self._run_sequential_messaging(users, scenario)
            return
            
        rounds = max(1, scenario.duration_seconds // 15)  # One round every 15 seconds
        
        for round_num in range(rounds):
            logger.info(f"🎯 Targeted messaging round {round_num + 1}/{rounds}")
            
            # Create user pairs for targeted messaging
            for i, user in enumerate(users):
                target_user = users[(i + 1) % len(users)]  # Next user in list (circular)
                
                try:
                    # Send message mentioning the target user
                    message = {
                        "type": "agent_request",
                        "payload": {
                            "agent": "data_sub_agent",
                            "message": f"Targeted message {round_num + 1} from {user.user_id} to {target_user.user_id}",
                            "thread_id": user.thread_id,
                            "metadata": {"target_user": target_user.user_id}
                        }
                    }
                    
                    await user.websocket.send(json.dumps(message))
                    user.messages_sent += 1
                    user.last_activity = datetime.utcnow()
                    
                    logger.debug(f"🎯 User {user.user_id} sent targeted message to {target_user.user_id}")
                    
                except Exception as e:
                    logger.error(f"Error in targeted messaging for user {user.user_id}: {e}")
                    user.errors.append(f"Targeted messaging error: {e}")
                    
            # Collect responses from all users
            response_tasks = [self._collect_user_responses(user, duration_seconds=10) for user in users]
            await asyncio.gather(*response_tasks, return_exceptions=True)
            
            await asyncio.sleep(3)  # Pause between rounds
            
    async def _send_user_message(self, user: WebSocketUser, message_content: str, thread_id: str) -> None:
        """Send a message from a specific user."""
        
        try:
            message = {
                "type": "agent_request",
                "payload": {
                    "agent": "data_sub_agent",
                    "message": message_content,
                    "thread_id": thread_id
                }
            }
            
            await user.websocket.send(json.dumps(message))
            user.messages_sent += 1
            user.last_activity = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Error sending message for user {user.user_id}: {e}")
            user.errors.append(f"Send message error: {e}")
            
    async def _collect_user_responses(self, user: WebSocketUser, duration_seconds: int = 5) -> None:
        """Collect WebSocket responses for a user over a specified duration."""
        
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        try:
            while time.time() < end_time:
                try:
                    # Receive message with timeout
                    response = await asyncio.wait_for(user.websocket.recv(), timeout=1.0)
                    response_data = json.loads(response)
                    
                    user.messages_received += 1
                    user.events_received.append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "event": response_data
                    })
                    
                    # Check for specific event types
                    event_type = response_data.get("type", "unknown")
                    if event_type in ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]:
                        logger.debug(f"📥 User {user.user_id} received {event_type} event")
                        
                except asyncio.TimeoutError:
                    # No message received in timeout period, continue
                    continue
                except websockets.exceptions.ConnectionClosed:
                    logger.error(f"Connection closed for user {user.user_id}")
                    user.errors.append("Connection closed during response collection")
                    break
                    
        except Exception as e:
            logger.error(f"Error collecting responses for user {user.user_id}: {e}")
            user.errors.append(f"Response collection error: {e}")
            
    async def _validate_user_isolation(self, users: List[WebSocketUser]) -> bool:
        """Validate that users are properly isolated from each other."""
        
        logger.info("🔒 Validating user isolation...")
        
        isolation_violations = []
        
        # Check 1: Users should not receive messages meant for other users
        for user in users:
            for event_record in user.events_received:
                event = event_record["event"]
                
                # Check if event contains thread_id
                event_thread_id = event.get("thread_id")
                if event_thread_id and event_thread_id != user.thread_id:
                    # This user received an event for a different thread - isolation violation
                    isolation_violations.append({
                        "user": user.user_id,
                        "violation": "cross_thread_contamination",
                        "expected_thread": user.thread_id,
                        "received_thread": event_thread_id,
                        "event": event
                    })
                    
                # Check if event contains user_id references to other users
                event_user_id = event.get("user_id")
                if event_user_id and event_user_id != user.user_id:
                    # Check if this is a legitimate event or contamination
                    other_users = [u.user_id for u in users if u.user_id != user.user_id]
                    if event_user_id in other_users:
                        isolation_violations.append({
                            "user": user.user_id,
                            "violation": "cross_user_contamination", 
                            "expected_user": user.user_id,
                            "received_user": event_user_id,
                            "event": event
                        })
                        
        # Check 2: Connection IDs should be unique
        connection_ids = [user.connection_id for user in users if user.connection_id]
        unique_connection_ids = set(connection_ids)
        
        if len(connection_ids) != len(unique_connection_ids):
            isolation_violations.append({
                "violation": "duplicate_connection_ids",
                "connection_ids": connection_ids,
                "unique_count": len(unique_connection_ids)
            })
            
        # Log violations
        if isolation_violations:
            logger.error(f"❌ User isolation violations detected: {len(isolation_violations)}")
            for violation in isolation_violations:
                logger.error(f"   - {violation['violation']}: {violation}")
                
            return False
        else:
            logger.success("✅ User isolation validation passed - no violations detected")
            return True
            
    async def _validate_business_value_delivery(self, users: List[WebSocketUser], scenario: MultiUserTestScenario) -> bool:
        """Validate that business value (chat functionality) is properly delivered to all users."""
        
        logger.info("💰 Validating business value delivery...")
        
        business_value_issues = []
        
        for user in users:
            user_issues = []
            
            # Check 1: User should have received agent events (core business value)
            event_types_received = set()
            for event_record in user.events_received:
                event_type = event_record["event"].get("type", "unknown")
                event_types_received.add(event_type)
                
            expected_events = set(scenario.expected_events)
            missing_events = expected_events - event_types_received
            
            if missing_events:
                user_issues.append({
                    "issue": "missing_critical_events",
                    "missing": list(missing_events),
                    "received": list(event_types_received)
                })
                
            # Check 2: User should have received responses to their messages
            if user.messages_sent > 0 and user.messages_received == 0:
                user_issues.append({
                    "issue": "no_responses_received",
                    "messages_sent": user.messages_sent,
                    "messages_received": user.messages_received
                })
                
            # Check 3: Agent completion events should be received for sent messages
            agent_started_count = sum(
                1 for event_record in user.events_received
                if event_record["event"].get("type") == "agent_started"
            )
            agent_completed_count = sum(
                1 for event_record in user.events_received  
                if event_record["event"].get("type") == "agent_completed"
            )
            
            # Should have roughly equal started and completed events
            if agent_started_count > 0 and agent_completed_count == 0:
                user_issues.append({
                    "issue": "incomplete_agent_workflows",
                    "started": agent_started_count,
                    "completed": agent_completed_count
                })
                
            # Check 4: Connection should be stable (no excessive errors)
            if len(user.errors) > 2:
                user_issues.append({
                    "issue": "excessive_connection_errors",
                    "error_count": len(user.errors),
                    "errors": user.errors
                })
                
            if user_issues:
                business_value_issues.append({
                    "user": user.user_id,
                    "issues": user_issues
                })
                
        # Assess overall business value delivery
        if business_value_issues:
            affected_users = len(business_value_issues)
            total_users = len(users)
            impact_percentage = (affected_users / total_users) * 100
            
            logger.error(f"❌ Business value delivery issues detected: {affected_users}/{total_users} users affected ({impact_percentage:.1f}%)")
            for issue in business_value_issues:
                logger.error(f"   User {issue['user']}: {len(issue['issues'])} issues")
                for user_issue in issue['issues']:
                    logger.error(f"     - {user_issue['issue']}: {user_issue}")
                    
            # Business value is acceptable if less than 20% of users are affected
            return impact_percentage < 20
        else:
            logger.success("✅ Business value delivery validation passed - all users received proper chat functionality")
            return True
            
    def _get_websocket_url(self) -> str:
        """Get WebSocket URL for testing."""
        if self.environment == "staging":
            return "wss://staging.netrasystems.ai/api/ws"
        elif self.environment == "production":
            return "wss://app.netrasystems.ai/api/ws"
        else:
            return "ws://localhost:8000/api/ws"


class MultiUserWebSocketTestSuite:
    """Test suite for running multiple multi-user WebSocket scenarios."""
    
    def __init__(self, environment: str = "staging"):
        self.environment = environment
        self.tester = MultiUserWebSocketTester(environment)
        
        # Define standard test scenarios
        self.scenarios = [
            MultiUserTestScenario(
                name="basic_concurrent_chat",
                description="Basic concurrent chat functionality with 5 users",
                user_count=5,
                concurrent_connections=True,
                message_pattern="sequential",
                duration_seconds=30,
                business_scenario="chat"
            ),
            MultiUserTestScenario(
                name="stress_concurrent_connections", 
                description="Stress test with 10 concurrent user connections",
                user_count=10,
                concurrent_connections=True,
                message_pattern="broadcast",
                duration_seconds=45,
                business_scenario="chat"
            ),
            MultiUserTestScenario(
                name="isolation_validation",
                description="Validate user isolation with targeted messaging",
                user_count=6,
                concurrent_connections=True,
                message_pattern="targeted",
                duration_seconds=40,
                business_scenario="mixed"
            ),
            MultiUserTestScenario(
                name="agent_workflow_concurrent",
                description="Test concurrent agent workflows across multiple users", 
                user_count=4,
                concurrent_connections=True,
                message_pattern="sequential",
                duration_seconds=60,
                business_scenario="agent_execution"
            )
        ]
        
    async def run_all_scenarios(self) -> Dict[str, Any]:
        """Run all multi-user WebSocket test scenarios."""
        
        logger.info(f"🚀 Starting multi-user WebSocket test suite with {len(self.scenarios)} scenarios...")
        
        suite_results = {
            "test_suite": "multi_user_websocket",
            "environment": self.environment,
            "start_time": datetime.utcnow().isoformat(),
            "scenarios": {},
            "summary": {}
        }
        
        scenario_results = []
        
        for scenario in self.scenarios:
            try:
                logger.info(f"▶️ Running scenario: {scenario.name}")
                result = await self.tester.run_multi_user_scenario(scenario)
                scenario_results.append(result)
                suite_results["scenarios"][scenario.name] = result
                
                # Log scenario result
                if result.get("summary", {}).get("overall_success", False):
                    logger.success(f"✅ Scenario {scenario.name} PASSED")
                else:
                    logger.error(f"❌ Scenario {scenario.name} FAILED")
                    
                # Brief pause between scenarios to avoid overwhelming the system
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"❌ Scenario {scenario.name} failed with exception: {e}")
                error_result = {
                    "scenario": scenario.name,
                    "error": str(e),
                    "summary": {"overall_success": False}
                }
                scenario_results.append(error_result)
                suite_results["scenarios"][scenario.name] = error_result
                
        # Generate overall summary
        total_scenarios = len(scenario_results)
        successful_scenarios = sum(
            1 for result in scenario_results
            if result.get("summary", {}).get("overall_success", False)
        )
        
        success_rate = (successful_scenarios / total_scenarios * 100) if total_scenarios > 0 else 0
        
        suite_results["end_time"] = datetime.utcnow().isoformat()
        suite_results["summary"] = {
            "total_scenarios": total_scenarios,
            "successful_scenarios": successful_scenarios,
            "failed_scenarios": total_scenarios - successful_scenarios,
            "success_rate": round(success_rate, 1),
            "overall_success": success_rate >= 80,  # 80% threshold
            "deployment_ready": success_rate >= 85  # Higher bar for deployment
        }
        
        # Log final results
        if suite_results["summary"]["deployment_ready"]:
            logger.success(f"🎉 Multi-user WebSocket test suite PASSED: {success_rate}% success rate")
            logger.success("✅ Multi-user WebSocket functionality validated for deployment")
        else:
            logger.error(f"❌ Multi-user WebSocket test suite FAILED: {success_rate}% success rate")
            logger.error("🚫 Multi-user WebSocket functionality NOT ready for deployment")
            
        return suite_results


# ============================================================================
# PYTEST INTEGRATION
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.deployment
@pytest.mark.websocket
class TestMultiUserWebSocket:
    """Pytest integration for multi-user WebSocket testing."""
    
    @pytest.fixture(scope="class")
    def environment(self):
        return os.getenv("TEST_ENVIRONMENT", "staging")
        
    @pytest.fixture(scope="class") 
    def test_suite(self, environment):
        return MultiUserWebSocketTestSuite(environment)
        
    async def test_basic_concurrent_chat(self, test_suite):
        """Test basic concurrent chat functionality."""
        scenario = MultiUserTestScenario(
            name="basic_concurrent_chat_pytest",
            description="Basic concurrent chat test via pytest",
            user_count=3,  # Smaller for pytest
            concurrent_connections=True,
            message_pattern="sequential",
            duration_seconds=20,
            business_scenario="chat"
        )
        
        result = await test_suite.tester.run_multi_user_scenario(scenario)
        
        assert result["summary"]["overall_success"] == True, f"Basic concurrent chat failed: {result.get('error')}"
        assert result["summary"]["connection_success_rate"] >= 80, "Connection success rate too low"
        assert result["isolation_validated"] == True, "User isolation not maintained"
        assert result["business_value_delivered"] == True, "Business value not delivered"
        
    async def test_user_isolation_validation(self, test_suite):
        """Test that user isolation is properly maintained."""
        scenario = MultiUserTestScenario(
            name="isolation_test_pytest",
            description="User isolation validation test",
            user_count=4,
            concurrent_connections=True,
            message_pattern="targeted",
            duration_seconds=25,
            business_scenario="mixed"
        )
        
        result = await test_suite.tester.run_multi_user_scenario(scenario)
        
        assert result["summary"]["overall_success"] == True, f"Isolation test failed: {result.get('error')}"
        assert result["isolation_validated"] == True, "User isolation violations detected"
        
        # Check that no user received events meant for other users
        for user_id, user_data in result["users"].items():
            assert len(user_data["errors"]) <= 1, f"User {user_id} had too many errors: {user_data['errors']}"
            
    async def test_concurrent_agent_workflows(self, test_suite):
        """Test concurrent agent workflow execution."""
        scenario = MultiUserTestScenario(
            name="concurrent_agents_pytest",
            description="Concurrent agent workflow test",
            user_count=3,
            concurrent_connections=True,
            message_pattern="broadcast",
            duration_seconds=30,
            business_scenario="agent_execution"
        )
        
        result = await test_suite.tester.run_multi_user_scenario(scenario)
        
        assert result["summary"]["overall_success"] == True, f"Concurrent agent test failed: {result.get('error')}"
        assert result["business_value_delivered"] == True, "Agent workflows not properly executed"
        
        # Verify all users received agent events
        for user_id, user_data in result["users"].items():
            assert user_data["events_received_count"] >= 3, f"User {user_id} received too few events"
            
    async def test_stress_concurrent_connections(self, test_suite):
        """Test WebSocket under stress with multiple concurrent connections."""
        scenario = MultiUserTestScenario(
            name="stress_test_pytest",
            description="Stress test with concurrent connections",
            user_count=8,  # Higher load for stress test
            concurrent_connections=True,
            message_pattern="broadcast",
            duration_seconds=35,
            business_scenario="mixed"
        )
        
        result = await test_suite.tester.run_multi_user_scenario(scenario)
        
        # More lenient requirements for stress test
        assert result["summary"]["connection_success_rate"] >= 70, "Stress test connection rate too low"
        assert result["isolation_validated"] == True, "Isolation failed under stress"
        
        # At least 70% business value delivery under stress
        if not result["business_value_delivered"]:
            # Check if failure rate is acceptable for stress test
            failed_users = len([
                user_data for user_data in result["users"].values()
                if len(user_data["errors"]) > 2
            ])
            failure_rate = (failed_users / len(result["users"]) * 100) if result["users"] else 100
            assert failure_rate <= 30, f"Stress test failure rate too high: {failure_rate}%"


# ============================================================================
# CLI EXECUTION
# ============================================================================

async def main():
    """Main CLI execution for multi-user WebSocket testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Multi-User WebSocket Testing Framework")
    parser.add_argument("--environment", default="staging", choices=["staging", "production", "development"])
    parser.add_argument("--scenario", help="Run specific scenario by name")
    parser.add_argument("--users", type=int, help="Override user count for scenarios")
    parser.add_argument("--duration", type=int, help="Override duration for scenarios")
    parser.add_argument("--output-file", help="Save results to JSON file")
    
    args = parser.parse_args()
    
    # Initialize test suite
    test_suite = MultiUserWebSocketTestSuite(args.environment)
    
    try:
        if args.scenario:
            # Run specific scenario
            scenario = next((s for s in test_suite.scenarios if s.name == args.scenario), None)
            if not scenario:
                logger.error(f"Scenario '{args.scenario}' not found")
                logger.info(f"Available scenarios: {[s.name for s in test_suite.scenarios]}")
                return 1
                
            # Apply overrides
            if args.users:
                scenario.user_count = args.users
            if args.duration:
                scenario.duration_seconds = args.duration
                
            logger.info(f"Running scenario: {scenario.name}")
            results = await test_suite.tester.run_multi_user_scenario(scenario)
            
        else:
            # Run all scenarios
            logger.info("Running all multi-user WebSocket test scenarios...")
            results = await test_suite.run_all_scenarios()
            
        # Save results if requested
        if args.output_file:
            with open(args.output_file, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"Results saved to {args.output_file}")
            
        # Exit with appropriate code
        if isinstance(results, dict) and results.get("summary", {}).get("overall_success", False):
            logger.success("Multi-user WebSocket testing completed successfully")
            return 0
        else:
            logger.error("Multi-user WebSocket testing failed")
            return 1
            
    except Exception as e:
        logger.error(f"Multi-user WebSocket testing error: {e}")
        return 1


if __name__ == "__main__":
    import asyncio
    exit_code = asyncio.run(main())
    sys.exit(exit_code)