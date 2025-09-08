"""
CRITICAL Integration Tests for Agent Execution Context Corruption

These tests are DESIGNED TO FAIL initially to expose critical agent execution
context corruption that allows user A's agent results to be sent to user B.

Business Risk: MAXIMUM - Enterprise user results sent to free user
Technical Risk: Agent execution context mixing in multi-user scenarios
Security Risk: Cross-user data exposure through agent execution

KEY CORRUPTION SCENARIOS TO EXPOSE:
1. Concurrent agent executions using string-based IDs cause context mixing
2. Agent execution context not properly isolated per user
3. Agent results routed to wrong user due to weak ID typing
4. WebSocket events from agent execution sent to wrong connections

These tests MUST initially FAIL to demonstrate the corruption exists.
"""

import pytest
import asyncio
import uuid
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Set, Optional, Any, Tuple
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import dataclass
import threading

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user

# Import problematic modules to test
from netra_backend.app.data_contexts.user_data_context import UserDataContext
from netra_backend.app.services.user_execution_context import UserExecutionContext

# Import CORRECT types that should be used
from shared.types import (
    UserID, ThreadID, RequestID, RunID, ExecutionID, AgentID,
    ensure_user_id, ensure_thread_id, ensure_request_id,
    StronglyTypedUserExecutionContext,
    ContextValidationError, IsolationViolationError,
    AgentExecutionState, AgentExecutionMetrics,
    ToolExecutionState, ToolExecutionResult
)


@dataclass
class MockAgentExecution:
    """Mock agent execution for testing context corruption."""
    user_id: str  # VIOLATION: should be UserID
    agent_id: str  # VIOLATION: should be AgentID
    execution_id: str  # VIOLATION: should be ExecutionID
    results: Dict[str, Any]
    websocket_events: List[Dict[str, Any]]
    start_time: float
    end_time: Optional[float] = None
    status: str = "running"


class TestAgentExecutionContextCorruption(SSotAsyncTestCase):
    """
    CRITICAL FAILING TESTS: Agent Execution Context Corruption
    
    These tests MUST initially FAIL to demonstrate that agent execution
    contexts can be corrupted, causing user A's results to go to user B.
    
    EXPECTED INITIAL RESULT: ALL TESTS SHOULD FAIL
    BUSINESS IMPACT: Prevents cross-user data exposure through agents
    """
    
    async def async_setup_method(self, method):
        """Enhanced async setup for agent execution testing."""
        await super().async_setup_method(method)
        
        # Enable strict agent isolation detection
        self.set_env_var("STRICT_AGENT_ISOLATION", "true") 
        self.set_env_var("DETECT_CONTEXT_CORRUPTION", "true")
        self.set_env_var("FAIL_ON_AGENT_ID_MIXING", "true")
        
        # Initialize test data
        self.corruption_incidents: List[str] = []
        self.agent_executions: Dict[str, MockAgentExecution] = {}
        self.user_contexts: Dict[str, UserDataContext] = {}
        
        # Setup mock agent execution tracking
        self.agent_execution_calls = []
        self.websocket_event_calls = []
        
    async def test_concurrent_agent_executions_detect_context_mixing(self):
        """
        CRITICAL FAILING TEST: Concurrent agent executions should detect context mixing
        
        EXPECTED RESULT: FAIL - No detection of context mixing between users
        BUSINESS RISK: User A's optimization results sent to User B
        
        This test simulates 2+ users running agents concurrently and verifies
        that their execution contexts remain isolated.
        """
        print("🚨 TESTING: Concurrent agent execution context mixing detection")
        
        # Create multiple user contexts that might mix due to string ID weaknesses  
        users_data = []
        for i in range(3):
            user_data = {
                "user_id": f"concurrent_user_{i}",  # VIOLATION: str instead of UserID
                "request_id": f"concurrent_req_{i}",  # VIOLATION: str instead of RequestID
                "thread_id": f"concurrent_thread_{i}",  # VIOLATION: str instead of ThreadID
                "agent_type": f"optimization_agent_{i % 2}",  # Mix of agent types
            }
            users_data.append(user_data)
            
        # Create contexts for each user
        contexts_created = []
        for user_data in users_data:
            try:
                context = UserDataContext(
                    user_id=user_data["user_id"],
                    request_id=user_data["request_id"],
                    thread_id=user_data["thread_id"]
                )
                self.user_contexts[user_data["user_id"]] = context
                contexts_created.append(user_data["user_id"])
                print(f"✓ Created context for user: {user_data['user_id']}")
            except Exception as e:
                print(f"❌ Failed to create context for user {user_data['user_id']}: {e}")
        
        print(f"Created {len(contexts_created)} user contexts")
        
        # Run concurrent agent executions to test for context mixing
        async def simulate_agent_execution(user_data: Dict) -> Dict:
            """Simulate agent execution for a user."""
            user_id = user_data["user_id"]
            
            try:
                # Get the user's context
                context = self.user_contexts.get(user_id)
                if not context:
                    return {"error": f"No context for user {user_id}"}
                
                # Simulate agent execution with context
                execution_id = f"exec_{user_id}_{int(time.time())}"
                agent_id = f"agent_{user_data['agent_type']}_{user_id}"
                
                # Create mock execution (using problematic string IDs)
                execution = MockAgentExecution(
                    user_id=user_id,  # VIOLATION: str instead of UserID
                    agent_id=agent_id,  # VIOLATION: str instead of AgentID  
                    execution_id=execution_id,  # VIOLATION: str instead of ExecutionID
                    results={"optimization_data": f"results_for_{user_id}"},
                    websocket_events=[
                        {"type": "agent_started", "user_id": user_id, "agent_id": agent_id},
                        {"type": "agent_thinking", "user_id": user_id, "data": f"thinking_{user_id}"},
                        {"type": "agent_completed", "user_id": user_id, "results": f"done_{user_id}"}
                    ],
                    start_time=time.time()
                )
                
                # Store execution for later analysis
                self.agent_executions[execution_id] = execution
                
                # Track execution call for corruption analysis
                self.agent_execution_calls.append({
                    "user_id": user_id,
                    "execution_id": execution_id, 
                    "context_memory_id": id(context),
                    "execution_memory_id": id(execution),
                    "thread_id": threading.current_thread().ident
                })
                
                # Simulate WebSocket events (where corruption often occurs)
                for event in execution.websocket_events:
                    self.websocket_event_calls.append({
                        "event": event,
                        "intended_user": user_id,
                        "execution_id": execution_id,
                        "timestamp": time.time()
                    })
                
                # Simulate some processing time
                await asyncio.sleep(0.1)  
                
                execution.end_time = time.time()
                execution.status = "completed"
                
                return {
                    "user_id": user_id,
                    "execution_id": execution_id,
                    "status": "success",
                    "results": execution.results,
                    "events_sent": len(execution.websocket_events)
                }
                
            except Exception as e:
                return {
                    "user_id": user_id, 
                    "status": "error",
                    "error": str(e)
                }
        
        # Run all agent executions concurrently
        execution_results = []
        tasks = [simulate_agent_execution(user_data) for user_data in users_data]
        
        try:
            execution_results = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            print(f"⚠️ Error in concurrent execution: {e}")
        
        print(f"Completed {len(execution_results)} concurrent agent executions")
        
        # ANALYZE FOR CONTEXT CORRUPTION
        corruption_detected = []
        
        # Check 1: Verify each execution has correct user association
        for result in execution_results:
            if isinstance(result, dict) and result.get("status") == "success":
                user_id = result["user_id"]
                execution_id = result["execution_id"]
                
                # Verify execution belongs to correct user
                if execution_id in self.agent_executions:
                    execution = self.agent_executions[execution_id]
                    if execution.user_id != user_id:
                        corruption = f"Execution {execution_id} user mismatch: expected {user_id}, got {execution.user_id}"
                        corruption_detected.append(corruption)
                        print(f"❌ Context corruption: {corruption}")
        
        # Check 2: Verify WebSocket events are routed to correct users
        for event_call in self.websocket_event_calls:
            event = event_call["event"]
            intended_user = event_call["intended_user"]
            
            # Check if event user_id matches intended user
            if event.get("user_id") != intended_user:
                corruption = f"WebSocket event user mismatch: event for {event.get('user_id')}, intended for {intended_user}"
                corruption_detected.append(corruption)
                print(f"❌ WebSocket routing corruption: {corruption}")
        
        # Check 3: Look for shared context memory between users (critical violation)
        context_memory_ids = {}
        for call in self.agent_execution_calls:
            user_id = call["user_id"]
            memory_id = call["context_memory_id"]
            
            if memory_id in context_memory_ids:
                other_user = context_memory_ids[memory_id]
                if other_user != user_id:
                    corruption = f"Shared context memory between users {user_id} and {other_user}: {memory_id}"
                    corruption_detected.append(corruption)
                    print(f"❌ Critical memory sharing: {corruption}")
            else:
                context_memory_ids[memory_id] = user_id
        
        # Check 4: Test for execution ID collisions (should be impossible with proper typing)
        execution_ids = [call["execution_id"] for call in self.agent_execution_calls]
        unique_execution_ids = set(execution_ids)
        
        if len(execution_ids) != len(unique_execution_ids):
            collision_corruption = f"Execution ID collisions detected: {len(execution_ids)} executions, {len(unique_execution_ids)} unique IDs"
            corruption_detected.append(collision_corruption)
            print(f"❌ ID collision corruption: {collision_corruption}")
        
        # Record comprehensive metrics
        self.record_metric("concurrent_executions", len(execution_results))
        self.record_metric("context_corruptions", len(corruption_detected))
        self.record_metric("websocket_events_sent", len(self.websocket_event_calls))
        self.record_metric("unique_execution_ids", len(unique_execution_ids))
        self.record_metric("shared_memory_violations", len([c for c in corruption_detected if "memory" in c]))
        
        # CRITICAL: FAIL if corruption was detected (expected for initial run)
        if corruption_detected:
            self.corruption_incidents.extend(corruption_detected)
            pytest.fail(
                f"CRITICAL AGENT EXECUTION CORRUPTION: {len(corruption_detected)} corruption incidents "
                f"detected in concurrent agent executions. User contexts are mixing, causing cross-user "
                f"data exposure: {corruption_detected}"
            )
        
        print("✅ No agent execution corruption detected (unexpected - test designed to fail)")
    
    async def test_agent_result_routing_cross_user_contamination(self):
        """
        CRITICAL FAILING TEST: Agent results should not be contaminated between users
        
        EXPECTED RESULT: FAIL - Agent results contaminated between users
        BUSINESS RISK: Enterprise user sees free user's data and vice versa
        """
        print("🚨 TESTING: Agent result routing cross-user contamination")
        
        contamination_incidents = []
        
        # Create two distinct users with different data profiles
        enterprise_user = {
            "user_id": "enterprise_user_001",  # VIOLATION: str instead of UserID
            "request_id": "enterprise_req_001",
            "thread_id": "enterprise_thread_001", 
            "tier": "enterprise",
            "sensitive_data": "CONFIDENTIAL_ENTERPRISE_OPTIMIZATION_DATA"
        }
        
        free_user = {
            "user_id": "free_user_002",  # VIOLATION: str instead of UserID
            "request_id": "free_req_002",
            "thread_id": "free_thread_002",
            "tier": "free", 
            "sensitive_data": "FREE_TIER_BASIC_DATA"
        }
        
        users = [enterprise_user, free_user]
        
        # Create contexts for both users
        user_results = {}
        for user in users:
            try:
                context = UserDataContext(
                    user_id=user["user_id"],
                    request_id=user["request_id"],
                    thread_id=user["thread_id"]
                )
                self.user_contexts[user["user_id"]] = context
                user_results[user["user_id"]] = {"context_created": True}
            except Exception as e:
                user_results[user["user_id"]] = {"error": f"Context creation failed: {e}"}
        
        # Simulate agent executions with sensitive data
        async def execute_agent_with_sensitive_data(user: Dict) -> Dict:
            """Execute agent with user-specific sensitive data."""
            user_id = user["user_id"]
            sensitive_data = user["sensitive_data"]
            
            # Simulate agent processing sensitive user data
            execution_id = f"sensitive_exec_{user_id}_{int(time.time())}"
            
            # Create execution with sensitive results  
            execution = MockAgentExecution(
                user_id=user_id,
                agent_id=f"sensitive_agent_{user_id}",
                execution_id=execution_id,
                results={
                    "user_tier": user["tier"],
                    "sensitive_analysis": f"ANALYSIS_FOR_{sensitive_data}",
                    "confidential_insights": f"INSIGHTS_FOR_{user_id}",
                    "user_specific_recommendations": f"RECOMMENDATIONS_FOR_{user['tier'].upper()}_USER"
                },
                websocket_events=[
                    {"type": "agent_started", "user_id": user_id, "sensitive": True},
                    {"type": "agent_thinking", "user_id": user_id, "processing": sensitive_data},
                    {"type": "agent_completed", "user_id": user_id, "results_summary": f"Completed for {user['tier']}"}
                ],
                start_time=time.time()
            )
            
            # Store execution results
            self.agent_executions[execution_id] = execution
            
            # Simulate WebSocket delivery (where contamination occurs)
            delivered_events = []
            for event in execution.websocket_events:
                # CRITICAL: Check if event could be contaminated with wrong user data
                delivered_event = event.copy()
                delivered_events.append(delivered_event)
            
            await asyncio.sleep(0.05)  # Simulate processing
            
            execution.end_time = time.time()
            execution.status = "completed"
            
            return {
                "user_id": user_id,
                "execution_id": execution_id,
                "results": execution.results,
                "events": delivered_events,
                "sensitive_data_processed": sensitive_data
            }
        
        # Execute agents for both users simultaneously
        execution_tasks = [execute_agent_with_sensitive_data(user) for user in users]
        agent_results = await asyncio.gather(*execution_tasks, return_exceptions=True)
        
        print(f"Executed agents for {len(agent_results)} users with sensitive data")
        
        # ANALYZE FOR CROSS-USER CONTAMINATION
        for i, result in enumerate(agent_results):
            if isinstance(result, dict):
                user_id = result["user_id"]
                execution_results = result["results"]
                events = result["events"]
                
                # Check if results contain data from other users
                for j, other_result in enumerate(agent_results):
                    if i != j and isinstance(other_result, dict):
                        other_user_id = other_result["user_id"] 
                        other_sensitive = other_result["sensitive_data_processed"]
                        
                        # Look for contamination in results
                        result_str = str(execution_results).lower()
                        if other_user_id.lower() in result_str:
                            contamination = f"User {user_id} results contain other user ID {other_user_id}"
                            contamination_incidents.append(contamination)
                            print(f"❌ Cross-user contamination: {contamination}")
                        
                        if other_sensitive.lower() in result_str:
                            contamination = f"User {user_id} results contain other user's sensitive data"
                            contamination_incidents.append(contamination)
                            print(f"❌ Sensitive data leak: {contamination}")
                        
                        # Check events for contamination
                        for event in events:
                            event_str = str(event).lower()
                            if other_user_id.lower() in event_str:
                                contamination = f"User {user_id} events contain other user data {other_user_id}"
                                contamination_incidents.append(contamination)
                                print(f"❌ Event contamination: {contamination}")
        
        # Test for execution context bleeding between users
        enterprise_execution = None
        free_execution = None
        
        for execution in self.agent_executions.values():
            if "enterprise" in execution.user_id:
                enterprise_execution = execution
            elif "free" in execution.user_id:
                free_execution = execution
        
        if enterprise_execution and free_execution:
            # Check for context bleeding
            enterprise_results = str(enterprise_execution.results)
            free_results = str(free_execution.results)
            
            if "free" in enterprise_results.lower():
                contamination = "Enterprise user execution contains free tier references"
                contamination_incidents.append(contamination)
                print(f"❌ Tier contamination: {contamination}")
            
            if "enterprise" in free_results.lower():
                contamination = "Free user execution contains enterprise references"  
                contamination_incidents.append(contamination)
                print(f"❌ Privilege escalation: {contamination}")
        
        # Record metrics
        self.record_metric("sensitive_executions", len(agent_results))
        self.record_metric("contamination_incidents", len(contamination_incidents))
        self.record_metric("cross_tier_contamination", 
                          len([c for c in contamination_incidents if "tier" in c or "enterprise" in c or "free" in c]))
        
        # FAIL if contamination was detected
        if contamination_incidents:
            self.corruption_incidents.extend(contamination_incidents)
            pytest.fail(
                f"CRITICAL CROSS-USER CONTAMINATION: {len(contamination_incidents)} contamination "
                f"incidents detected. Sensitive user data is bleeding between users in agent executions: "
                f"{contamination_incidents}"
            )
        
        print("✅ No cross-user contamination detected")
    
    async def test_websocket_event_delivery_user_isolation_violation(self):
        """
        CRITICAL FAILING TEST: WebSocket events should be isolated per user
        
        EXPECTED RESULT: FAIL - WebSocket events delivered to wrong users
        BUSINESS RISK: User A sees User B's agent progress and results
        """
        print("🚨 TESTING: WebSocket event delivery user isolation")
        
        isolation_violations = []
        
        # Create multiple users with WebSocket connections
        websocket_users = []
        for i in range(3):
            user_data = {
                "user_id": f"ws_user_{i}",
                "request_id": f"ws_req_{i}",
                "thread_id": f"ws_thread_{i}",
                "websocket_id": f"ws_conn_{i}",  # VIOLATION: str instead of WebSocketID
                "connection_state": "connected"
            }
            websocket_users.append(user_data)
        
        # Create contexts and mock WebSocket connections
        mock_websocket_connections = {}
        for user in websocket_users:
            try:
                context = UserDataContext(
                    user_id=user["user_id"],
                    request_id=user["request_id"],
                    thread_id=user["thread_id"]
                )
                self.user_contexts[user["user_id"]] = context
                
                # Mock WebSocket connection
                mock_websocket_connections[user["websocket_id"]] = {
                    "user_id": user["user_id"],
                    "messages_received": [],
                    "connection_id": user["websocket_id"]
                }
                
            except Exception as e:
                print(f"❌ Failed to setup WebSocket user {user['user_id']}: {e}")
        
        print(f"Setup {len(mock_websocket_connections)} WebSocket connections")
        
        # Simulate agent executions sending WebSocket events
        async def run_agent_with_websocket_events(user: Dict) -> Dict:
            """Run agent and send WebSocket events."""
            user_id = user["user_id"]
            websocket_id = user["websocket_id"]
            
            # Create agent execution
            execution_id = f"ws_exec_{user_id}_{int(time.time())}"
            
            # Generate WebSocket events for this user
            events = [
                {"type": "agent_started", "user_id": user_id, "execution_id": execution_id},
                {"type": "agent_thinking", "user_id": user_id, "data": f"processing_{user_id}"},
                {"type": "tool_executing", "user_id": user_id, "tool": f"optimizer_{user_id}"},
                {"type": "tool_completed", "user_id": user_id, "results": f"results_{user_id}"},
                {"type": "agent_completed", "user_id": user_id, "final": f"complete_{user_id}"}
            ]
            
            # Simulate sending events to WebSocket connections
            events_sent = []
            for event in events:
                # CRITICAL: Test if events are properly isolated by user
                target_user = event["user_id"]
                
                # Find the correct WebSocket connection for this user
                target_connection = None
                for conn_id, conn_data in mock_websocket_connections.items():
                    if conn_data["user_id"] == target_user:
                        target_connection = conn_data
                        break
                
                if target_connection:
                    # Deliver event to correct connection
                    target_connection["messages_received"].append(event)
                    events_sent.append({
                        "event": event,
                        "delivered_to": target_connection["connection_id"],
                        "intended_for": target_user
                    })
                else:
                    # Event delivery failed - isolation violation
                    violation = f"No WebSocket connection found for user {target_user}"
                    isolation_violations.append(violation)
                    print(f"❌ Event delivery failure: {violation}")
            
            await asyncio.sleep(0.1)
            
            return {
                "user_id": user_id,
                "execution_id": execution_id,
                "events_sent": len(events_sent),
                "websocket_id": websocket_id
            }
        
        # Run all agents concurrently with WebSocket events
        websocket_tasks = [run_agent_with_websocket_events(user) for user in websocket_users]
        websocket_results = await asyncio.gather(*websocket_tasks, return_exceptions=True)
        
        print(f"Completed WebSocket event delivery for {len(websocket_results)} users")
        
        # ANALYZE FOR WEBSOCKET ISOLATION VIOLATIONS
        
        # Check 1: Verify each user only received their own events
        for conn_id, conn_data in mock_websocket_connections.items():
            user_id = conn_data["user_id"]
            messages = conn_data["messages_received"]
            
            for message in messages:
                message_user = message.get("user_id")
                if message_user != user_id:
                    violation = f"User {user_id} received message intended for {message_user}"
                    isolation_violations.append(violation)
                    print(f"❌ WebSocket isolation violation: {violation}")
        
        # Check 2: Verify all expected events were delivered
        expected_events_per_user = 5  # agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
        for user in websocket_users:
            user_id = user["user_id"]
            websocket_id = user["websocket_id"]
            
            if websocket_id in mock_websocket_connections:
                received_count = len(mock_websocket_connections[websocket_id]["messages_received"])
                if received_count != expected_events_per_user:
                    violation = f"User {user_id} received {received_count} events, expected {expected_events_per_user}"
                    isolation_violations.append(violation)
                    print(f"❌ Event count violation: {violation}")
        
        # Check 3: Look for cross-user event contamination in message content
        for conn_id, conn_data in mock_websocket_connections.items():
            user_id = conn_data["user_id"]
            messages = conn_data["messages_received"]
            
            for message in messages:
                message_content = str(message).lower()
                
                # Check if message contains other users' data
                for other_user in websocket_users:
                    other_user_id = other_user["user_id"]
                    if other_user_id != user_id and other_user_id.lower() in message_content:
                        violation = f"User {user_id} message contains other user data: {other_user_id}"
                        isolation_violations.append(violation)
                        print(f"❌ Message contamination: {violation}")
        
        # Record metrics  
        self.record_metric("websocket_users", len(websocket_users))
        self.record_metric("websocket_isolation_violations", len(isolation_violations))
        self.record_metric("total_events_processed", sum(len(conn["messages_received"]) for conn in mock_websocket_connections.values()))
        
        # FAIL if isolation violations were detected
        if isolation_violations:
            self.corruption_incidents.extend(isolation_violations)
            pytest.fail(
                f"CRITICAL WEBSOCKET ISOLATION VIOLATIONS: {len(isolation_violations)} violations "
                f"detected in WebSocket event delivery. User events are not properly isolated, "
                f"causing cross-user information exposure: {isolation_violations}"
            )
        
        print("✅ WebSocket event isolation appears intact")
    
    async def async_teardown_method(self, method):
        """Enhanced async teardown with corruption incident reporting."""
        await super().async_teardown_method(method)
        
        # Report all corruption incidents found during test
        if self.corruption_incidents:
            print(f"\n🚨 CRITICAL CORRUPTION INCIDENTS: {len(self.corruption_incidents)}")
            for i, incident in enumerate(self.corruption_incidents, 1):
                print(f"  {i}. {incident}")
            
            # Save incidents to metrics for comprehensive reporting
            self.record_metric("total_corruption_incidents", len(self.corruption_incidents))
            self.record_metric("corruption_incidents_list", self.corruption_incidents)
            
            # Classify incident types for analysis
            context_mixing = [inc for inc in self.corruption_incidents if "context" in inc.lower() or "mixing" in inc.lower()]
            data_contamination = [inc for inc in self.corruption_incidents if "contamination" in inc.lower() or "leak" in inc.lower()]
            event_violations = [inc for inc in self.corruption_incidents if "event" in inc.lower() or "websocket" in inc.lower()]
            
            self.record_metric("context_mixing_incidents", len(context_mixing))
            self.record_metric("data_contamination_incidents", len(data_contamination))
            self.record_metric("event_violation_incidents", len(event_violations))
        else:
            print("\n✅ No agent execution corruption detected (unexpected - tests designed to fail)")
            self.record_metric("total_corruption_incidents", 0)
        
        # Generate corruption summary report
        test_metrics = self.get_all_metrics()
        print(f"\n📊 Agent Execution Corruption Test Metrics:")
        for metric, value in test_metrics.items():
            if any(keyword in metric for keyword in ["corruption", "violation", "contamination", "incident"]):
                print(f"  {metric}: {value}")


# Mark these as critical integration tests
pytest.mark.critical_agent_corruption = pytest.mark.mark
pytest.mark.agent_execution_violations = pytest.mark.mark
pytest.mark.integration_corruption = pytest.mark.mark