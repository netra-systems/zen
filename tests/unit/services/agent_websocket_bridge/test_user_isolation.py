"""
AgentWebSocketBridge User Isolation Unit Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal (Mission Critical Security)
- Business Goal: Protect $500K+ ARR by preventing cross-user event leakage
- Value Impact: Validates multi-tenant security preventing data breach incidents
- Strategic Impact: Core security testing for multi-user WebSocket isolation

This test suite validates the user isolation patterns of AgentWebSocketBridge,
ensuring complete separation between user contexts and preventing cross-user
event delivery that could result in data leakage or security breaches.

SECURITY CRITICAL: These tests validate that user isolation prevents:
- Cross-user WebSocket event delivery
- User context data leakage 
- Concurrent user session interference
- Unauthorized access to user-specific data

@compliance CLAUDE.md - SSOT patterns, multi-user security requirements
@compliance SPEC/user_context_architecture.xml - User isolation patterns
"""

import asyncio
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List
from unittest.mock import AsyncMock, MagicMock, patch

# SSOT Test Infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.real_services_test_fixtures import real_services_fixture

# Bridge Components
from netra_backend.app.services.agent_websocket_bridge import (
    AgentWebSocketBridge,
    IntegrationState,
    IntegrationConfig,
    create_agent_websocket_bridge
)

# User Context Components
from netra_backend.app.services.user_execution_context import UserExecutionContext

# WebSocket Dependencies
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager

# Shared utilities
from shared.isolated_environment import get_env
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class AgentWebSocketBridgeUserIsolationTests(SSotAsyncTestCase):
    """
    Test AgentWebSocketBridge user isolation and multi-tenant security.
    
    SECURITY CRITICAL: These tests validate that user contexts are properly
    isolated and prevent cross-user event delivery or data leakage.
    """
    
    def setup_method(self, method):
        """Set up test environment with multiple user contexts."""
        super().setup_method(method)
        
        # Create multiple test user contexts for isolation testing
        self.user_contexts = []
        self.bridges = []
        
        for i in range(3):
            user_context = UserExecutionContext(
                user_id=f"user_{i}_{uuid.uuid4()}",
                thread_id=f"thread_{i}_{uuid.uuid4()}",
                run_id=f"run_{i}_{uuid.uuid4()}",
                request_id=f"req_{i}_{uuid.uuid4()}",
                agent_context={
                    "user_index": i,
                    "test_data": f"sensitive_data_user_{i}",
                    "permissions": ["read", "write"] if i == 0 else ["read"]
                },
                audit_metadata={
                    "test_suite": "user_isolation",
                    "security_level": "high" if i == 0 else "normal"
                }
            )
            self.user_contexts.append(user_context)
            self.bridges.append(AgentWebSocketBridge(user_context=user_context))
    
    def teardown_method(self, method):
        """Clean up test resources."""
        super().teardown_method(method)
    
    @pytest.mark.unit
    @pytest.mark.security_critical
    def test_user_context_binding_isolation(self):
        """
        Test that each bridge is bound to its specific user context.
        
        SECURITY CRITICAL: Incorrect user context binding could lead
        to cross-user data exposure and security breaches.
        """
        # Verify each bridge has the correct user context
        for i, bridge in enumerate(self.bridges):
            assert bridge.user_context is self.user_contexts[i], f"Bridge {i} should have correct user context"
            assert bridge.user_id == self.user_contexts[i].user_id, f"Bridge {i} should have correct user ID"
            assert bridge.user_context.thread_id == self.user_contexts[i].thread_id, f"Bridge {i} should have correct thread ID"
            assert bridge.user_context.request_id == self.user_contexts[i].request_id, f"Bridge {i} should have correct request ID"
        
        # Verify user contexts are completely independent
        for i in range(len(self.bridges)):
            for j in range(i + 1, len(self.bridges)):
                assert self.bridges[i].user_context is not self.bridges[j].user_context, \
                    f"Bridge {i} and {j} should have different user contexts"
                assert self.bridges[i].user_id != self.bridges[j].user_id, \
                    f"Bridge {i} and {j} should have different user IDs"
    
    @pytest.mark.unit
    @pytest.mark.security_critical
    def test_user_context_data_isolation(self):
        """
        Test that user context data is properly isolated between bridges.
        
        SECURITY CRITICAL: User context data contains sensitive information
        that must not leak between different user sessions.
        """
        # Verify user context data isolation
        for i, bridge in enumerate(self.bridges):
            user_context = bridge.user_context
            
            # Check agent context isolation
            assert user_context.agent_context["user_index"] == i, f"Bridge {i} should have correct user index"
            assert f"sensitive_data_user_{i}" in user_context.agent_context["test_data"], \
                f"Bridge {i} should have correct sensitive data"
            
            # Check audit metadata isolation
            assert user_context.audit_metadata["test_suite"] == "user_isolation", \
                f"Bridge {i} should have correct audit metadata"
            
            # Verify permissions are correctly isolated
            if i == 0:
                assert user_context.agent_context["permissions"] == ["read", "write"], \
                    "User 0 should have admin permissions"
                assert user_context.audit_metadata["security_level"] == "high", \
                    "User 0 should have high security level"
            else:
                assert user_context.agent_context["permissions"] == ["read"], \
                    f"User {i} should have read-only permissions"
                assert user_context.audit_metadata["security_level"] == "normal", \
                    f"User {i} should have normal security level"
    
    @pytest.mark.unit
    @pytest.mark.security_critical
    def test_bridge_instance_isolation(self):
        """
        Test that bridge instances are completely independent.
        
        SECURITY CRITICAL: Bridge instance isolation prevents shared state
        that could lead to cross-user contamination.
        """
        # Verify all bridges are independent instances
        for i in range(len(self.bridges)):
            for j in range(i + 1, len(self.bridges)):
                assert self.bridges[i] is not self.bridges[j], \
                    f"Bridge {i} and {j} should be different instances"
        
        # Verify internal state is independent
        for i, bridge in enumerate(self.bridges):
            # Each bridge should have its own configuration
            assert bridge.config is not None, f"Bridge {i} should have config"
            
            # Each bridge should have its own locks
            assert hasattr(bridge, 'initialization_lock'), f"Bridge {i} should have initialization lock"
            assert hasattr(bridge, 'recovery_lock'), f"Bridge {i} should have recovery lock"
            assert hasattr(bridge, 'health_lock'), f"Bridge {i} should have health lock"
            
            # Each bridge should have its own event history
            assert hasattr(bridge, '_event_history'), f"Bridge {i} should have event history"
            assert isinstance(bridge._event_history, list), f"Bridge {i} event history should be list"
        
        # Verify locks are independent between bridges
        for i in range(len(self.bridges)):
            for j in range(i + 1, len(self.bridges)):
                assert self.bridges[i].initialization_lock is not self.bridges[j].initialization_lock, \
                    f"Bridge {i} and {j} should have independent initialization locks"
                assert self.bridges[i].recovery_lock is not self.bridges[j].recovery_lock, \
                    f"Bridge {i} and {j} should have independent recovery locks"
                assert self.bridges[i].health_lock is not self.bridges[j].health_lock, \
                    f"Bridge {i} and {j} should have independent health locks"
    
    @pytest.mark.unit
    @pytest.mark.security_critical
    def test_user_id_property_isolation(self):
        """
        Test that user_id property returns correct isolated values.
        
        SECURITY CRITICAL: user_id property is used for routing WebSocket
        events and must return the correct user ID for each bridge.
        """
        # Verify user_id property returns correct values
        for i, bridge in enumerate(self.bridges):
            user_id = bridge.user_id
            expected_user_id = self.user_contexts[i].user_id
            
            assert user_id == expected_user_id, f"Bridge {i} should return correct user ID"
            assert user_id is not None, f"Bridge {i} user ID should not be None"
            assert isinstance(user_id, str), f"Bridge {i} user ID should be string"
            assert len(user_id) > 0, f"Bridge {i} user ID should not be empty"
        
        # Verify user IDs are unique across bridges
        user_ids = [bridge.user_id for bridge in self.bridges]
        assert len(user_ids) == len(set(user_ids)), "All user IDs should be unique"
    
    @pytest.mark.unit
    @pytest.mark.security_critical
    def test_no_user_context_bridge_isolation(self):
        """
        Test that bridges without user context are properly isolated from user bridges.
        
        SECURITY CRITICAL: System-level bridges must not have access to
        user contexts or user-specific data.
        """
        # Create bridge without user context (system bridge)
        system_bridge = AgentWebSocketBridge()
        
        # Verify system bridge has no user context
        assert system_bridge.user_context is None, "System bridge should have no user context"
        assert system_bridge.user_id is None, "System bridge should have no user ID"
        
        # Verify system bridge is isolated from user bridges
        for i, user_bridge in enumerate(self.bridges):
            assert system_bridge is not user_bridge, f"System bridge should be different from user bridge {i}"
            assert system_bridge.user_context is not user_bridge.user_context, \
                f"System bridge should have different context from user bridge {i}"
            assert system_bridge.user_id != user_bridge.user_id, \
                f"System bridge should have different user ID from user bridge {i}"
    
    @pytest.mark.unit
    @pytest.mark.concurrent_isolation
    async def test_concurrent_user_bridge_operations(self):
        """
        Test concurrent operations on bridges with different user contexts.
        
        SECURITY CRITICAL: Concurrent operations must maintain user isolation
        and prevent cross-user data contamination.
        """
        # Define concurrent operations for each bridge
        async def perform_bridge_operations(bridge, user_index, results):
            """Perform operations on a bridge and collect results."""
            operations = []
            
            # Access user properties multiple times
            for i in range(5):
                user_id = bridge.user_id
                operations.append(("user_id", user_id))
                
                user_context = bridge.user_context
                operations.append(("user_context_id", user_context.user_id if user_context else None))
                
                await asyncio.sleep(0.001)  # Small delay to increase concurrency
            
            results[user_index] = operations
        
        # Run concurrent operations on all bridges
        results = [[] for _ in range(len(self.bridges))]
        tasks = [
            perform_bridge_operations(self.bridges[i], i, results)
            for i in range(len(self.bridges))
        ]
        
        await asyncio.gather(*tasks)
        
        # Verify results maintain user isolation
        for i, operations in enumerate(results):
            expected_user_id = self.user_contexts[i].user_id
            
            # Check that all operations returned correct user data
            for operation_type, value in operations:
                if operation_type in ["user_id", "user_context_id"]:
                    assert value == expected_user_id, \
                        f"User {i} operation {operation_type} should return correct user ID"
    
    @pytest.mark.unit
    @pytest.mark.factory_isolation
    def test_factory_method_user_isolation(self):
        """
        Test that factory methods create properly isolated bridges.
        
        SECURITY CRITICAL: Factory methods must maintain user isolation
        and prevent shared state between different user contexts.
        """
        # Create bridges using factory methods
        factory_bridges = []
        for user_context in self.user_contexts:
            bridge = create_agent_websocket_bridge(user_context=user_context)
            factory_bridges.append(bridge)
        
        # Verify factory-created bridges are properly isolated
        for i, bridge in enumerate(factory_bridges):
            assert bridge.user_context is self.user_contexts[i], \
                f"Factory bridge {i} should have correct user context"
            assert bridge.user_id == self.user_contexts[i].user_id, \
                f"Factory bridge {i} should have correct user ID"
        
        # Verify factory bridges are independent from direct-created bridges
        for i in range(len(factory_bridges)):
            assert factory_bridges[i] is not self.bridges[i], \
                f"Factory bridge {i} should be different instance from direct bridge {i}"
            assert factory_bridges[i].user_context is self.bridges[i].user_context, \
                f"Factory bridge {i} should have same user context as direct bridge {i}"
    
    @pytest.mark.unit
    @pytest.mark.memory_isolation
    def test_event_history_isolation(self):
        """
        Test that event history is properly isolated between user bridges.
        
        SECURITY CRITICAL: Event history contains user-specific event data
        that must not leak between different user sessions.
        """
        # Verify each bridge has independent event history
        for i, bridge in enumerate(self.bridges):
            assert hasattr(bridge, '_event_history'), f"Bridge {i} should have event history"
            assert isinstance(bridge._event_history, list), f"Bridge {i} event history should be list"
            assert len(bridge._event_history) == 0, f"Bridge {i} event history should be empty initially"
        
        # Simulate adding events to one bridge
        test_event = {"event": "test", "user_data": "sensitive"}
        self.bridges[0]._event_history.append(test_event)
        
        # Verify event is isolated to specific bridge
        assert len(self.bridges[0]._event_history) == 1, "Bridge 0 should have one event"
        assert self.bridges[0]._event_history[0] == test_event, "Bridge 0 should have correct event"
        
        # Verify other bridges are unaffected
        for i in range(1, len(self.bridges)):
            assert len(self.bridges[i]._event_history) == 0, \
                f"Bridge {i} event history should remain empty"
    
    @pytest.mark.unit
    @pytest.mark.connection_isolation
    def test_connection_status_isolation(self):
        """
        Test that connection status is properly isolated between bridges.
        
        BUSINESS VALUE: Connection status isolation ensures that one user's
        connection issues don't affect other users' bridge status.
        """
        # Verify all bridges start with connected status
        for i, bridge in enumerate(self.bridges):
            assert bridge.is_connected is True, f"Bridge {i} should start connected"
        
        # Modify connection status of one bridge
        self.bridges[0].is_connected = False
        
        # Verify isolation - other bridges should remain connected
        assert self.bridges[0].is_connected is False, "Bridge 0 should be disconnected"
        for i in range(1, len(self.bridges)):
            assert self.bridges[i].is_connected is True, \
                f"Bridge {i} should remain connected"
    
    @pytest.mark.unit
    @pytest.mark.websocket_manager_isolation
    def test_websocket_manager_isolation(self):
        """
        Test that WebSocket manager references are properly isolated.
        
        SECURITY CRITICAL: WebSocket manager isolation prevents cross-user
        message delivery and maintains WebSocket routing security.
        """
        # Verify all bridges start with no WebSocket manager
        for i, bridge in enumerate(self.bridges):
            assert bridge.websocket_manager is None, f"Bridge {i} should have no WebSocket manager initially"
        
        # Create mock WebSocket managers for testing
        mock_managers = []
        for i in range(len(self.bridges)):
            mock_manager = MagicMock()
            mock_manager.send_to_thread = AsyncMock()
            mock_manager.user_id = self.user_contexts[i].user_id
            mock_managers.append(mock_manager)
        
        # Assign different WebSocket managers to each bridge
        for i, bridge in enumerate(self.bridges):
            bridge.websocket_manager = mock_managers[i]
        
        # Verify each bridge has correct WebSocket manager
        for i, bridge in enumerate(self.bridges):
            assert bridge.websocket_manager is mock_managers[i], \
                f"Bridge {i} should have correct WebSocket manager"
            assert bridge.websocket_manager.user_id == self.user_contexts[i].user_id, \
                f"Bridge {i} WebSocket manager should have correct user ID"
        
        # Verify WebSocket managers are isolated between bridges
        for i in range(len(self.bridges)):
            for j in range(i + 1, len(self.bridges)):
                assert self.bridges[i].websocket_manager is not self.bridges[j].websocket_manager, \
                    f"Bridge {i} and {j} should have different WebSocket managers"
