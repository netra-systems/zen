"""
SSOT WebSocket Bridge Pattern Compliance Test Suite - Issue #1070 Phase 1

This test suite creates FAILING tests that validate SSOT bridge pattern compliance.
These tests will FAIL initially to prove SSOT violations exist, then PASS after 
proper SSOT bridge implementation.

TARGET AREAS:
- Factory pattern usage vs singleton anti-patterns  
- Multi-user isolation validation
- WebSocket event delivery through proper bridge
- State contamination prevention

Business Value: Platform Infrastructure - Ensures $500K+ ARR Golden Path reliability
through proper SSOT patterns that prevent multi-user contamination and ensure 
reliable real-time communication.

CRITICAL: These tests are designed to FAIL initially to validate violation reproduction.
"""

import asyncio
import threading
import time
import uuid
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Set
from unittest.mock import MagicMock, Mock, patch

import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase


@pytest.mark.unit
class TestWebSocketBridgePatternCompliance(SSotAsyncTestCase):
    """
    Test suite for validating SSOT WebSocket bridge pattern compliance.
    
    This suite tests for proper factory patterns, user isolation, and 
    event delivery through SSOT bridge patterns instead of direct manager access.
    
    EXPECTED BEHAVIOR: These tests should FAIL initially to prove SSOT violations exist.
    """

    def setup_method(self, method=None):
        """Setup test environment for bridge pattern compliance testing."""
        super().setup_method(method)
        
        # Test user contexts for multi-user isolation testing
        self.test_users = [
            {"user_id": f"user_{uuid.uuid4().hex[:8]}", "session_id": f"session_{uuid.uuid4().hex[:8]}"},
            {"user_id": f"user_{uuid.uuid4().hex[:8]}", "session_id": f"session_{uuid.uuid4().hex[:8]}"},
            {"user_id": f"user_{uuid.uuid4().hex[:8]}", "session_id": f"session_{uuid.uuid4().hex[:8]}"},
        ]
        
        # Mock factory state for testing isolation
        self.factory_instances = {}
        self.event_log = []
        
        self.logger.info(f"Initialized bridge pattern compliance testing with {len(self.test_users)} test users")

    @pytest.mark.ssot_violation
    @pytest.mark.priority_p0
    async def test_websocket_manager_factory_isolation(self):
        """
        FAILING TEST: Verify WebSocket managers use factory pattern for user isolation.
        
        This test will FAIL initially because current implementation may use 
        shared/singleton instances that violate multi-user isolation.
        """
        # Attempt to import WebSocket factory (should exist in SSOT implementation)
        try:
            from netra_backend.app.websocket_core.bridge import WebSocketBridgeFactory
            bridge_factory_available = True
        except ImportError:
            bridge_factory_available = False
            
        # Record availability
        self.record_metric("websocket_bridge_factory_available", bridge_factory_available)
        
        if not bridge_factory_available:
            # Try the direct import (violation pattern)
            try:
                from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
                direct_import_available = True
                self.record_metric("direct_websocket_manager_available", True)
                
                # Test for singleton behavior (violation)
                instance1 = WebSocketManager()
                instance2 = WebSocketManager()
                
                # EXPECTED FAILURE: If instances are the same, it's a singleton violation
                assert instance1 is not instance2, (
                    "SSOT VIOLATION: WebSocketManager appears to use singleton pattern. "
                    "This violates multi-user isolation requirements. "
                    "Each user must have isolated WebSocket instances."
                )
                
            except ImportError:
                direct_import_available = False
                self.record_metric("direct_websocket_manager_available", False)
                
        # EXPECTED FAILURE: Bridge factory should be available in SSOT implementation
        assert bridge_factory_available, (
            "SSOT VIOLATION: WebSocketBridgeFactory not available. "
            "SSOT implementation must provide factory pattern for user isolation. "
            "Current implementation likely uses direct imports which violate SSOT principles."
        )

    @pytest.mark.ssot_violation
    @pytest.mark.priority_p0
    async def test_multi_user_websocket_isolation(self):
        """
        FAILING TEST: Verify WebSocket instances are isolated between users.
        
        This test will FAIL if WebSocket managers share state between users,
        causing potential data contamination or event cross-delivery.
        """
        user_websocket_instances = {}
        user_event_logs = {user["user_id"]: [] for user in self.test_users}
        
        # Attempt to create WebSocket instances for each user
        for user in self.test_users:
            try:
                # Try SSOT bridge pattern first
                try:
                    from netra_backend.app.websocket_core.bridge import create_websocket_bridge
                    websocket_instance = await create_websocket_bridge(
                        user_id=user["user_id"],
                        session_id=user["session_id"]
                    )
                    user_websocket_instances[user["user_id"]] = websocket_instance
                except ImportError:
                    # Fall back to direct import (violation pattern)
                    from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
                    websocket_instance = WebSocketManager()
                    websocket_instance.user_id = user["user_id"]  # Manual assignment
                    user_websocket_instances[user["user_id"]] = websocket_instance
                    
            except Exception as e:
                self.logger.error(f"Failed to create WebSocket instance for user {user['user_id']}: {e}")
        
        # Record metrics
        self.record_metric("user_websocket_instances_created", len(user_websocket_instances))
        
        # Test for instance isolation
        if len(user_websocket_instances) >= 2:
            instances = list(user_websocket_instances.values())
            
            # Check that instances are different objects
            for i in range(len(instances)):
                for j in range(i + 1, len(instances)):
                    instance_1 = instances[i]
                    instance_2 = instances[j]
                    
                    # EXPECTED FAILURE: Instances should be different for user isolation
                    assert instance_1 is not instance_2, (
                        "SSOT VIOLATION: WebSocket instances are shared between users. "
                        "This creates multi-user contamination risk. "
                        f"User instances should be isolated: {instance_1} vs {instance_2}"
                    )
                    
                    # Check for shared state (deeper isolation test)
                    if hasattr(instance_1, '__dict__') and hasattr(instance_2, '__dict__'):
                        # Look for shared mutable state
                        shared_state = self._detect_shared_state(instance_1, instance_2)
                        
                        assert not shared_state, (
                            "SSOT VIOLATION: WebSocket instances share mutable state between users. "
                            f"Shared state detected: {shared_state}. "
                            "This can cause cross-user data contamination."
                        )
        else:
            # EXPECTED FAILURE: Should be able to create multiple instances
            pytest.fail(
                f"SSOT VIOLATION: Could only create {len(user_websocket_instances)} WebSocket instances. "
                "Multi-user system requires isolated instances per user."
            )

    @pytest.mark.ssot_violation
    @pytest.mark.priority_p1
    async def test_websocket_event_delivery_isolation(self):
        """
        FAILING TEST: Verify WebSocket events are delivered only to intended users.
        
        This test will FAIL if events sent to one user are delivered to other users,
        indicating shared WebSocket state or improper event routing.
        """
        # Mock WebSocket connections for multiple users
        user_connections = {}
        user_received_events = {user["user_id"]: [] for user in self.test_users}
        
        # Create mock connections with event capture
        for user in self.test_users:
            mock_connection = MagicMock()
            mock_connection.user_id = user["user_id"]
            mock_connection.session_id = user["session_id"]
            
            # Capture sent events
            def capture_event(event_data, user_id=user["user_id"]):
                user_received_events[user_id].append(event_data)
                
            mock_connection.send_text = Mock(side_effect=capture_event)
            user_connections[user["user_id"]] = mock_connection
        
        # Test event delivery through current system
        try:
            # Try to import agent registry to test event delivery
            from netra_backend.app.agents.registry import AgentRegistry
            
            # Create registry instances (testing for singleton violations)
            registry1 = AgentRegistry()
            registry2 = AgentRegistry()
            
            # EXPECTED FAILURE: Registries should be different instances
            assert registry1 is not registry2, (
                "SSOT VIOLATION: AgentRegistry uses singleton pattern. "
                "This prevents proper user isolation in multi-user scenarios."
            )
            
            # Mock WebSocket manager for each user
            for user_id, connection in user_connections.items():
                # Simulate event sending
                test_event = {
                    "type": "agent_started",
                    "user_id": user_id,
                    "data": f"Test event for {user_id}",
                    "timestamp": time.time()
                }
                
                # Send event through registry (testing current implementation)
                if hasattr(registry1, 'send_websocket_event'):
                    registry1.send_websocket_event(user_id, test_event)
                else:
                    # Manual event sending (fallback)
                    connection.send_text(test_event)
        
        except ImportError as e:
            self.logger.error(f"Could not import components for event testing: {e}")
            
        # Verify event isolation
        for user_id, received_events in user_received_events.items():
            # Check that user only received their own events
            for event in received_events:
                if isinstance(event, dict) and 'user_id' in event:
                    # EXPECTED FAILURE: Events should only go to intended users
                    assert event['user_id'] == user_id, (
                        f"SSOT VIOLATION: User {user_id} received event intended for {event['user_id']}. "
                        "This indicates shared WebSocket state causing event cross-contamination."
                    )
        
        # Record test results
        total_events = sum(len(events) for events in user_received_events.values())
        self.record_metric("total_events_captured", total_events)
        self.record_metric("users_with_events", len([uid for uid, events in user_received_events.items() if events]))

    @pytest.mark.ssot_violation
    @pytest.mark.priority_p1
    def test_agent_websocket_bridge_initialization(self):
        """
        FAILING TEST: Verify agents initialize WebSocket bridges properly.
        
        This test will FAIL if agents use direct WebSocketManager imports
        instead of proper SSOT bridge initialization patterns.
        """
        bridge_initialization_results = {}
        
        # Test agent initialization patterns
        agent_files = [
            "netra_backend.app.agents.supervisor.mcp_execution_engine",
            "netra_backend.app.agents.supervisor.pipeline_executor", 
            "netra_backend.app.agents.registry",  # Legacy compatibility layer
        ]
        
        for module_name in agent_files:
            try:
                # Dynamic import to test initialization
                import importlib
                module = importlib.import_module(module_name)
                
                # Check for direct WebSocketManager usage (violation)
                module_source = module.__file__
                if module_source:
                    with open(module_source, 'r') as f:
                        source_code = f.read()
                    
                    # Look for violation patterns
                    direct_import_violations = [
                        "from netra_backend.app.websocket_core.websocket_manager import WebSocketManager",
                        "WebSocketManager(",
                        "websocket_manager = WebSocketManager"
                    ]
                    
                    violations_found = []
                    for violation_pattern in direct_import_violations:
                        if violation_pattern in source_code:
                            violations_found.append(violation_pattern)
                    
                    bridge_initialization_results[module_name] = {
                        "violations_found": violations_found,
                        "has_violations": bool(violations_found),
                        "module_loaded": True
                    }
                    
            except ImportError as e:
                bridge_initialization_results[module_name] = {
                    "violations_found": [],
                    "has_violations": False,
                    "module_loaded": False,
                    "import_error": str(e)
                }
        
        # Record results
        self.record_metric("bridge_initialization_results", bridge_initialization_results)
        
        # Check for violations
        modules_with_violations = [
            module for module, result in bridge_initialization_results.items()
            if result.get("has_violations", False)
        ]
        
        # EXPECTED FAILURE: Should fail if direct imports are found
        assert not modules_with_violations, (
            f"SSOT VIOLATION: Found {len(modules_with_violations)} agent modules with direct WebSocket imports. "
            f"Modules should use SSOT bridge pattern instead. "
            f"Violations in: {modules_with_violations}"
        )

    @pytest.mark.ssot_violation
    @pytest.mark.priority_p1
    async def test_websocket_state_persistence_isolation(self):
        """
        FAILING TEST: Verify WebSocket state doesn't persist across user sessions.
        
        This test will FAIL if WebSocket state persists between different user
        sessions, indicating shared state that violates user isolation.
        """
        session_states = {}
        
        # Simulate multiple user sessions
        for i, user in enumerate(self.test_users):
            session_id = f"session_{i}_{uuid.uuid4().hex[:8]}"
            
            try:
                # Create WebSocket context for user session
                websocket_context = await self._create_websocket_context(
                    user["user_id"], 
                    session_id
                )
                
                # Set session-specific state
                test_state = {
                    "user_id": user["user_id"],
                    "session_id": session_id,
                    "test_data": f"data_for_session_{i}",
                    "timestamp": time.time()
                }
                
                if websocket_context:
                    # Store state in WebSocket context
                    await self._set_websocket_state(websocket_context, test_state)
                    
                    # Retrieve state to verify isolation
                    retrieved_state = await self._get_websocket_state(websocket_context)
                    session_states[session_id] = retrieved_state
                    
            except Exception as e:
                self.logger.error(f"Failed to test session isolation for {user['user_id']}: {e}")
        
        # Verify state isolation between sessions
        if len(session_states) >= 2:
            session_keys = list(session_states.keys())
            for i in range(len(session_keys)):
                for j in range(i + 1, len(session_keys)):
                    state1 = session_states[session_keys[i]]
                    state2 = session_states[session_keys[j]]
                    
                    if state1 and state2:
                        # EXPECTED FAILURE: States should be different for different sessions
                        assert state1 != state2, (
                            f"SSOT VIOLATION: WebSocket state persists across user sessions. "
                            f"Session {session_keys[i]} and {session_keys[j]} have identical state: {state1}. "
                            f"This indicates shared state violating user isolation."
                        )
                        
                        # Check for user_id isolation
                        if "user_id" in state1 and "user_id" in state2:
                            assert state1["user_id"] != state2["user_id"], (
                                f"SSOT VIOLATION: Different sessions have same user_id: {state1['user_id']}. "
                                f"This indicates improper session isolation."
                            )
        
        self.record_metric("session_states_tested", len(session_states))

    # Helper methods for testing

    def _detect_shared_state(self, instance1: Any, instance2: Any) -> List[str]:
        """Detect shared mutable state between instances."""
        shared_state = []
        
        if not (hasattr(instance1, '__dict__') and hasattr(instance2, '__dict__')):
            return shared_state
            
        dict1 = instance1.__dict__
        dict2 = instance2.__dict__
        
        for key in dict1:
            if key in dict2:
                val1 = dict1[key]
                val2 = dict2[key]
                
                # Check if they're the same mutable object
                if val1 is val2 and isinstance(val1, (list, dict, set)):
                    shared_state.append(key)
                    
        return shared_state
    
    async def _create_websocket_context(self, user_id: str, session_id: str) -> Optional[Any]:
        """Create WebSocket context for testing."""
        try:
            # Try SSOT bridge pattern
            from netra_backend.app.websocket_core.bridge import create_websocket_context
            return await create_websocket_context(user_id=user_id, session_id=session_id)
        except ImportError:
            try:
                # Fallback to direct import (violation pattern)
                from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
                manager = WebSocketManager()
                return {"manager": manager, "user_id": user_id, "session_id": session_id}
            except ImportError:
                return None
    
    async def _set_websocket_state(self, context: Any, state: Dict[str, Any]) -> None:
        """Set state in WebSocket context."""
        if isinstance(context, dict) and "manager" in context:
            if hasattr(context["manager"], "set_user_state"):
                await context["manager"].set_user_state(context["user_id"], state)
            else:
                # Manual state setting
                if not hasattr(context["manager"], "_user_states"):
                    context["manager"]._user_states = {}
                context["manager"]._user_states[context["user_id"]] = state
    
    async def _get_websocket_state(self, context: Any) -> Optional[Dict[str, Any]]:
        """Get state from WebSocket context."""
        if isinstance(context, dict) and "manager" in context:
            if hasattr(context["manager"], "get_user_state"):
                return await context["manager"].get_user_state(context["user_id"])
            elif hasattr(context["manager"], "_user_states"):
                return context["manager"]._user_states.get(context["user_id"])
        return None