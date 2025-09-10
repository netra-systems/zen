"""Integration Test: Multi-User WebSocket Event Isolation

REPRODUCTION TEST - This test should FAIL initially due to singleton/global patterns.

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise) - $500K+ ARR at risk
- Business Goal: Chat Functionality Integrity & User Privacy
- Value Impact: Ensures users only receive their own WebSocket events and AI responses
- Revenue Impact: Cross-user event leakage breaks core chat value (90% of platform)

INTEGRATION VIOLATIONS UNDER TEST:
1. EventRouter singleton (websocket_event_router.py:404,390-398)
2. EventValidator global instance (event_validator.py:880-892)
3. ServiceLocator singleton (service_locator_core.py:29-38)
Combined Impact: Users receive other users' WebSocket events and AI responses

EXPECTED BEHAVIOR:
- PRE-REFACTORING: This test should FAIL - proving cross-user event leakage exists
- POST-REFACTORING: This test should PASS - proving factory pattern provides isolation

CRITICAL BUSINESS IMPACT:
If WebSocket events leak between users:
1. User A sees User B's private AI conversations and responses
2. Agent progress notifications get sent to wrong users
3. Tool execution results visible to unintended recipients
4. Complete breach of user privacy and chat functionality
"""

import asyncio
import json
import uuid
import websockets
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import asynccontextmanager

# SSOT Test Framework Compliance
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment

# Test the complete WebSocket integration stack
from netra_backend.app.websocket_core.manager import UnifiedWebSocketManager
from netra_backend.app.services.websocket_event_router import get_websocket_router, reset_websocket_router
from netra_backend.app.websocket_core.event_validator import get_websocket_validator, reset_websocket_validator
from netra_backend.app.services.service_locator_core import ServiceLocator


class TestMultiUserWebSocketEventIsolation(SSotAsyncTestCase):
    """Integration Test: Expose WebSocket event leakage between concurrent users."""
    
    async def asyncSetUp(self):
        """Set up test environment with proper isolation."""
        await super().asyncSetUp()
        
        # Reset all singleton/global state before each test
        reset_websocket_router()
        reset_websocket_validator() 
        ServiceLocator._instance = None
        
        # Create test user contexts
        self.user_a_id = str(uuid.uuid4())
        self.user_b_id = str(uuid.uuid4())
        self.user_c_id = str(uuid.uuid4())
        
        self.connection_a_id = str(uuid.uuid4())
        self.connection_b_id = str(uuid.uuid4()) 
        self.connection_c_id = str(uuid.uuid4())
        
        # Mock WebSocket connections for testing
        self.mock_websocket_a = AsyncMock()
        self.mock_websocket_a.send = AsyncMock()
        self.mock_websocket_a.closed = False
        
        self.mock_websocket_b = AsyncMock()
        self.mock_websocket_b.send = AsyncMock()
        self.mock_websocket_b.closed = False
        
        self.mock_websocket_c = AsyncMock()
        self.mock_websocket_c.send = AsyncMock()
        self.mock_websocket_c.closed = False
        
        # Track events received by each user
        self.user_a_events = []
        self.user_b_events = []
        self.user_c_events = []

    async def test_websocket_event_routing_isolation(self):
        """
        REPRODUCTION TEST - This should FAIL initially due to singleton event routing.
        
        Tests that WebSocket events are properly isolated between users and don't leak
        across user sessions due to shared singleton instances.
        """
        
        # STEP 1: Set up WebSocket managers for each user
        manager_a = UnifiedWebSocketManager()
        manager_b = UnifiedWebSocketManager()
        manager_c = UnifiedWebSocketManager()
        
        # CRITICAL CHECK: Managers should be different instances (will FAIL with singleton)
        self.assertIsNot(manager_a, manager_b,
            "🚨 WebSocketManager singleton detected - same instance shared between users!")
        self.assertIsNot(manager_b, manager_c,
            "🚨 WebSocketManager singleton detected - same instance shared between users!")
        
        # STEP 2: Register connections for each user
        await manager_a.add_connection(self.connection_a_id, self.mock_websocket_a, self.user_a_id)
        await manager_b.add_connection(self.connection_b_id, self.mock_websocket_b, self.user_b_id)
        await manager_c.add_connection(self.connection_c_id, self.mock_websocket_c, self.user_c_id)
        
        # STEP 3: Send events specific to each user
        user_a_event = {
            "type": "agent_started",
            "data": {
                "user_id": self.user_a_id,
                "agent_type": "triage",
                "message": "User A's private triage agent started",
                "sensitive_data": "user_a_confidential_info"
            },
            "user_id": self.user_a_id,
            "connection_id": self.connection_a_id
        }
        
        user_b_event = {
            "type": "agent_thinking", 
            "data": {
                "user_id": self.user_b_id,
                "agent_type": "supervisor",
                "message": "User B's private supervisor thinking process",
                "sensitive_data": "user_b_confidential_info"
            },
            "user_id": self.user_b_id,
            "connection_id": self.connection_b_id
        }
        
        user_c_event = {
            "type": "agent_completed",
            "data": {
                "user_id": self.user_c_id,
                "agent_type": "optimizer",
                "message": "User C's private optimization completed",
                "sensitive_data": "user_c_confidential_info"
            },
            "user_id": self.user_c_id,
            "connection_id": self.connection_c_id
        }
        
        # STEP 4: Emit events through their respective managers
        await manager_a.emit_to_user(self.user_a_id, user_a_event)
        await manager_b.emit_to_user(self.user_b_id, user_b_event)
        await manager_c.emit_to_user(self.user_c_id, user_c_event)
        
        # STEP 5: Verify event isolation
        # Each user should only receive their own events
        
        # Check User A only got their event
        self.mock_websocket_a.send.assert_called()
        user_a_sent_data = json.loads(self.mock_websocket_a.send.call_args[0][0])
        self.assertEqual(user_a_sent_data["data"]["user_id"], self.user_a_id)
        self.assertIn("user_a_confidential_info", user_a_sent_data["data"]["sensitive_data"])
        
        # CRITICAL: User A should NOT have received User B or C's events
        for call_args in self.mock_websocket_a.send.call_args_list:
            sent_event = json.loads(call_args[0][0])
            self.assertNotEqual(sent_event["data"]["user_id"], self.user_b_id,
                f"🚨 EVENT LEAKAGE: User A received User B's private event: {sent_event}")
            self.assertNotEqual(sent_event["data"]["user_id"], self.user_c_id,
                f"🚨 EVENT LEAKAGE: User A received User C's private event: {sent_event}")
        
        # Similar checks for User B and C
        self.mock_websocket_b.send.assert_called()
        user_b_sent_data = json.loads(self.mock_websocket_b.send.call_args[0][0])
        self.assertEqual(user_b_sent_data["data"]["user_id"], self.user_b_id)
        
        self.mock_websocket_c.send.assert_called()
        user_c_sent_data = json.loads(self.mock_websocket_c.send.call_args[0][0])
        self.assertEqual(user_c_sent_data["data"]["user_id"], self.user_c_id)

    async def test_agent_execution_event_isolation(self):
        """
        Test that agent execution events are properly isolated between users.
        Singleton patterns cause agent events to leak between user sessions.
        """
        
        # Create realistic agent execution scenarios for each user
        user_scenarios = [
            {
                "user_id": self.user_a_id,
                "connection_id": self.connection_a_id,
                "websocket": self.mock_websocket_a,
                "agent_flow": [
                    {"type": "agent_started", "agent": "triage", "query": "User A's business optimization query"},
                    {"type": "agent_thinking", "agent": "triage", "step": "analyzing_user_a_requirements"},
                    {"type": "tool_executing", "tool": "data_analyzer", "target": "user_a_data"},
                    {"type": "tool_completed", "tool": "data_analyzer", "result": "user_a_analysis_complete"},
                    {"type": "agent_completed", "agent": "triage", "result": "user_a_optimization_recommendations"}
                ]
            },
            {
                "user_id": self.user_b_id,
                "connection_id": self.connection_b_id, 
                "websocket": self.mock_websocket_b,
                "agent_flow": [
                    {"type": "agent_started", "agent": "supervisor", "query": "User B's infrastructure query"},
                    {"type": "agent_thinking", "agent": "supervisor", "step": "analyzing_user_b_infrastructure"},
                    {"type": "tool_executing", "tool": "metrics_collector", "target": "user_b_systems"},
                    {"type": "tool_completed", "tool": "metrics_collector", "result": "user_b_metrics_gathered"},
                    {"type": "agent_completed", "agent": "supervisor", "result": "user_b_infrastructure_recommendations"}
                ]
            }
        ]
        
        # Set up WebSocket managers
        managers = {}
        for scenario in user_scenarios:
            manager = UnifiedWebSocketManager()
            await manager.add_connection(
                scenario["connection_id"],
                scenario["websocket"], 
                scenario["user_id"]
            )
            managers[scenario["user_id"]] = manager
        
        # Execute agent flows concurrently to test isolation
        async def execute_user_agent_flow(scenario, manager):
            """Execute a complete agent flow for a user."""
            events_sent = []
            
            for step in scenario["agent_flow"]:
                event = {
                    "type": step["type"],
                    "data": {
                        "user_id": scenario["user_id"],
                        "connection_id": scenario["connection_id"],
                        **step
                    },
                    "user_id": scenario["user_id"],
                    "connection_id": scenario["connection_id"]
                }
                
                await manager.emit_to_user(scenario["user_id"], event)
                events_sent.append(event)
                
                # Small delay to create interleaving opportunity
                await asyncio.sleep(0.01)
            
            return events_sent
        
        # Run both user flows concurrently
        user_a_scenario = user_scenarios[0]
        user_b_scenario = user_scenarios[1]
        
        user_a_events, user_b_events = await asyncio.gather(
            execute_user_agent_flow(user_a_scenario, managers[self.user_a_id]),
            execute_user_agent_flow(user_b_scenario, managers[self.user_b_id]),
            return_exceptions=True
        )
        
        # Verify event isolation
        # Check all events sent to User A
        for call_args in self.mock_websocket_a.send.call_args_list:
            sent_event = json.loads(call_args[0][0])
            self.assertEqual(sent_event["data"]["user_id"], self.user_a_id,
                f"🚨 AGENT EVENT LEAKAGE: User A received event for different user: {sent_event}")
            
            # User A should not see User B's business data
            self.assertNotIn("user_b", sent_event["data"].get("target", "").lower())
            self.assertNotIn("user_b", sent_event["data"].get("result", "").lower())
        
        # Check all events sent to User B  
        for call_args in self.mock_websocket_b.send.call_args_list:
            sent_event = json.loads(call_args[0][0])
            self.assertEqual(sent_event["data"]["user_id"], self.user_b_id,
                f"🚨 AGENT EVENT LEAKAGE: User B received event for different user: {sent_event}")
            
            # User B should not see User A's business data
            self.assertNotIn("user_a", sent_event["data"].get("target", "").lower())
            self.assertNotIn("user_a", sent_event["data"].get("result", "").lower())

    async def test_event_validation_isolation_integration(self):
        """
        Test that event validation doesn't interfere between concurrent users.
        Integration test covering EventValidator + EventRouter + WebSocketManager.
        """
        
        # Set up integrated stack for each user
        manager_a = UnifiedWebSocketManager()
        manager_b = UnifiedWebSocketManager()
        
        await manager_a.add_connection(self.connection_a_id, self.mock_websocket_a, self.user_a_id)
        await manager_b.add_connection(self.connection_b_id, self.mock_websocket_b, self.user_b_id)
        
        # User A sends events that might affect validation state
        problematic_events_a = [
            {"type": "agent_started", "data": {"complexity": "high", "user_id": self.user_a_id}},
            {"type": "agent_error", "data": {"error": "validation_issue", "user_id": self.user_a_id}},
            {"type": "tool_failed", "data": {"failure_reason": "timeout", "user_id": self.user_a_id}},
        ]
        
        # User B sends normal events that should validate cleanly
        normal_events_b = [
            {"type": "agent_started", "data": {"simple": "request", "user_id": self.user_b_id}},
            {"type": "agent_thinking", "data": {"step": "processing", "user_id": self.user_b_id}},
            {"type": "agent_completed", "data": {"result": "success", "user_id": self.user_b_id}},
        ]
        
        # Process User A's problematic events first
        for event in problematic_events_a:
            event["user_id"] = self.user_a_id
            event["connection_id"] = self.connection_a_id
            await manager_a.emit_to_user(self.user_a_id, event)
        
        # Process User B's normal events - these should NOT be affected by User A's state
        for event in normal_events_b:
            event["user_id"] = self.user_b_id  
            event["connection_id"] = self.connection_b_id
            await manager_b.emit_to_user(self.user_b_id, event)
        
        # Verify User B's events were processed correctly despite User A's issues
        user_b_call_count = self.mock_websocket_b.send.call_count
        self.assertEqual(user_b_call_count, len(normal_events_b),
            f"🚨 VALIDATION CONTAMINATION: User B's events affected by User A's validation state. "
            f"Expected {len(normal_events_b)} events, got {user_b_call_count}")
        
        # Verify User B only received their own events
        for call_args in self.mock_websocket_b.send.call_args_list:
            sent_event = json.loads(call_args[0][0])
            self.assertEqual(sent_event["data"]["user_id"], self.user_b_id,
                f"🚨 CROSS-USER CONTAMINATION: User B received User A's event: {sent_event}")

    async def test_service_locator_websocket_integration_isolation(self):
        """
        Test ServiceLocator singleton doesn't cause WebSocket service sharing between users.
        Integration test covering ServiceLocator + WebSocket service registration.
        """
        
        # Each user should get their own WebSocket-related services
        user_a_locator = ServiceLocator()
        user_b_locator = ServiceLocator()
        
        # CRITICAL CHECK: Locators should be different instances
        self.assertIsNot(user_a_locator, user_b_locator,
            "🚨 ServiceLocator singleton sharing services between users!")
        
        # Register user-specific WebSocket services
        user_a_websocket_service = {
            "user_id": self.user_a_id,
            "connection_id": self.connection_a_id,
            "service_type": "websocket_manager"
        }
        
        user_b_websocket_service = {
            "user_id": self.user_b_id,
            "connection_id": self.connection_b_id, 
            "service_type": "websocket_manager"
        }
        
        user_a_locator.register("websocket_service", user_a_websocket_service, singleton=True)
        user_b_locator.register("websocket_service", user_b_websocket_service, singleton=True)
        
        # Verify each user gets their own service
        retrieved_service_a = user_a_locator.get("websocket_service")
        retrieved_service_b = user_b_locator.get("websocket_service")
        
        self.assertEqual(retrieved_service_a["user_id"], self.user_a_id)
        self.assertEqual(retrieved_service_b["user_id"], self.user_b_id)
        
        # CRITICAL: User A should NOT get User B's WebSocket service
        self.assertNotEqual(retrieved_service_a["user_id"], self.user_b_id,
            f"🚨 SERVICE BLEEDING: User A got User B's WebSocket service: {retrieved_service_a}")
        
        self.assertNotEqual(retrieved_service_b["user_id"], self.user_a_id,
            f"🚨 SERVICE BLEEDING: User B got User A's WebSocket service: {retrieved_service_b}")

    async def tearDown(self):
        """Clean up test environment."""
        # Reset all singleton/global state
        reset_websocket_router()
        reset_websocket_validator()
        ServiceLocator._instance = None
        await super().tearDown()


# Business Impact Documentation
"""
BUSINESS IMPACT ANALYSIS:

1. PRIVACY BREACH AND DATA LEAKAGE:
   - Users receive other users' private AI conversations and responses
   - Sensitive business data exposed across user sessions via WebSocket events
   - Agent execution results visible to unintended recipients
   - Complete violation of user privacy expectations and data protection laws

2. CORE PLATFORM VALUE DESTRUCTION:
   - Chat functionality (90% of business value) corrupted by cross-user event leakage
   - Users lose trust when seeing other users' private conversations
   - AI responses become meaningless when contaminated with wrong user's context
   - Platform becomes unusable for multi-user scenarios

3. REVENUE IMPACT:
   - $500K+ ARR immediately at risk from broken chat isolation
   - Enterprise customers will immediately churn due to data leakage concerns
   - Compliance violations lead to legal liability and penalties
   - Platform reputation destroyed by privacy breaches

4. TECHNICAL DEBT:
   - Singleton patterns prevent proper scaling to handle concurrent users
   - Debugging becomes impossible due to contaminated shared state
   - Testing multi-user scenarios is unreliable due to state bleeding
   - System performance degrades as global state accumulates across all users

REMEDIATION REQUIRED:
- Replace all singleton patterns with factory patterns using UserExecutionContext
- Ensure complete WebSocket event isolation between users
- Implement proper cleanup and session management
- Add comprehensive integration tests for multi-user concurrent scenarios

POST-REFACTORING VALIDATION:
This test should PASS after factory pattern implementation, proving:
- Each user gets completely isolated WebSocket event processing
- No cross-user event leakage in any scenario
- Clean user session boundaries with proper cleanup
- Reliable multi-user chat functionality at scale
"""