"""
Unit Tests for WebSocket Connection ID Generation - Issue #618

CRITICAL: These tests are designed to expose connection ID format inconsistencies 
that cause message routing failures between different WebSocket components.

Business Value Justification:
- Segment: All (affects all users)
- Business Goal: System reliability and message delivery  
- Value Impact: Fixes "Message routing failed" errors that break chat functionality
- Strategic Impact: CRITICAL - Chat is 90% of platform value

Test Strategy:
1. EXPOSE inconsistencies between conn_ and ws_conn_ prefixes
2. DEMONSTRATE routing failures due to ID format mismatches  
3. VALIDATE connection ID generation across different components
4. PROVE demo user routing edge cases cause failures

These tests should initially FAIL to demonstrate the routing issues,
then PASS after fixes are implemented.
"""

import pytest
import uuid
import time
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List, Optional

# Import WebSocket core modules to test
from netra_backend.app.websocket_core.utils import generate_connection_id, generate_message_id
from netra_backend.app.websocket_core.types import ConnectionInfo, WebSocketMessage, MessageType, create_standard_message
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
from netra_backend.app.websocket_core.connection_manager import ConnectionManager

# Import ID generation components
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from shared.types.core_types import ConnectionID, UserID, ensure_user_id

# Import test framework
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestConnectionIdGenerationRouting(SSotBaseTestCase):
    """
    Unit tests that expose connection ID generation inconsistencies causing routing failures.
    
    ISSUE #618: These tests demonstrate the exact ID format mismatches that cause
    "Message routing failed" errors in the WebSocket system.
    """
    
    def setup_method(self):
        """Set up test fixtures with different user types."""
        super().setup_method()
        
        # Test users that expose different routing behaviors
        self.regular_user_id = "user-test-12345"  
        self.demo_user_id = "demo-user-67890"
        self.enterprise_user_id = "enterprise-user-999"
        
        # Connection manager for testing routing
        self.connection_manager = ConnectionManager()
        
        # Factory for testing manager creation patterns
        self.factory = WebSocketManagerFactory()

    def test_connection_id_format_consistency_across_components(self):
        """
        DESIGNED TO EXPOSE: Connection ID format inconsistencies between components.
        
        This test demonstrates that different WebSocket components generate
        connection IDs with different prefixes (conn_ vs ws_conn_), causing
        routing failures when messages can't find the correct connections.
        """
        user_id = self.regular_user_id
        
        # Test ID generation from different components
        connection_ids = {}
        
        # 1. Generate ID using utils.py function
        utils_connection_id = generate_connection_id(user_id)
        connection_ids['utils'] = str(utils_connection_id)
        
        # 2. Generate ID using ConnectionInfo default factory
        conn_info = ConnectionInfo(user_id=user_id)
        connection_ids['connection_info'] = conn_info.connection_id
        
        # 3. Generate ID using UnifiedIdGenerator directly 
        direct_id = UnifiedIdGenerator.generate_websocket_connection_id(user_id)
        connection_ids['unified_generator'] = direct_id
        
        # 4. Generate ID through WebSocketManagerFactory
        mock_websocket = Mock()
        manager = self.factory.create_manager_for_user(
            user_id=user_id,
            websocket_connection=mock_websocket
        )
        # Extract connection ID from manager (this may expose different patterns)
        factory_id = getattr(manager, 'connection_id', None) or getattr(manager, '_connection_id', None)
        if factory_id:
            connection_ids['factory'] = str(factory_id)
        
        print(f"Connection ID patterns for user {user_id}:")
        for component, conn_id in connection_ids.items():
            print(f"  {component}: {conn_id}")
        
        # CRITICAL TEST: All components should generate the same format
        all_ids = list(connection_ids.values())
        all_ids = [id for id in all_ids if id is not None]  # Filter None values
        
        if len(all_ids) > 1:
            # Check if all IDs have the same prefix pattern
            prefixes = set()
            for conn_id in all_ids:
                if conn_id.startswith('ws_conn_'):
                    prefixes.add('ws_conn_')
                elif conn_id.startswith('conn_'):
                    prefixes.add('conn_')
                elif '_' in conn_id:
                    prefix = conn_id.split('_')[0] + '_'
                    prefixes.add(prefix)
            
            # THIS TEST SHOULD EXPOSE THE INCONSISTENCY
            assert len(prefixes) == 1, \
                f"ROUTING FAILURE: Inconsistent connection ID prefixes found: {prefixes}. " \
                f"This causes routing failures because components can't find each other's connections. " \
                f"IDs: {connection_ids}"
        
        # All IDs should follow SSOT pattern
        for component, conn_id in connection_ids.items():
            if conn_id:
                assert conn_id.startswith('ws_conn_'), \
                    f"Component '{component}' generates non-SSOT connection ID: {conn_id}"

    def test_demo_user_connection_id_routing_edge_case(self):
        """
        DESIGNED TO EXPOSE: Demo user routing failures.
        
        Demo users may have special handling that causes connection ID
        generation to follow different patterns, breaking routing.
        """
        demo_user_id = self.demo_user_id
        
        # Generate connection IDs for demo user
        demo_connection_id = generate_connection_id(demo_user_id)
        demo_conn_info = ConnectionInfo(user_id=demo_user_id)
        
        print(f"Demo user connection patterns:")
        print(f"  utils connection_id: {demo_connection_id}")
        print(f"  ConnectionInfo id: {demo_conn_info.connection_id}")
        
        # Create a routing scenario
        # Simulate ConnectionManager tracking demo connections
        self.connection_manager.register_connection(
            connection_id=str(demo_connection_id),
            user_id=demo_user_id,
            websocket=Mock()
        )
        
        # Try to find the connection using different ID formats
        # This exposes routing failures when IDs don't match
        
        # Test 1: Can we find by the generated connection ID?
        found_by_generated = self.connection_manager.get_connection(str(demo_connection_id))
        
        # Test 2: Can we find by ConnectionInfo ID?
        found_by_conn_info = self.connection_manager.get_connection(demo_conn_info.connection_id)
        
        # Test 3: Legacy format compatibility (this might be the issue)
        legacy_format_id = f"conn_{demo_user_id}_{int(time.time())}"
        found_by_legacy = self.connection_manager.get_connection(legacy_format_id)
        
        print(f"Routing test results:")
        print(f"  Found by generated ID: {found_by_generated is not None}")
        print(f"  Found by ConnectionInfo ID: {found_by_conn_info is not None}")
        print(f"  Found by legacy format: {found_by_legacy is not None}")
        
        # CRITICAL: At least the first two should work
        assert found_by_generated is not None, \
            f"DEMO USER ROUTING FAILURE: Cannot find demo connection by generated ID {demo_connection_id}"
        
        # These should be the same connection if IDs are consistent
        if found_by_conn_info is not None:
            assert found_by_generated == found_by_conn_info, \
                "DEMO USER ROUTING FAILURE: Same demo user connection found with different IDs"

    def test_connection_id_collision_prevention(self):
        """
        DESIGNED TO EXPOSE: Connection ID collision scenarios.
        
        Tests that demonstrate how ID format inconsistencies can lead to
        collisions or missed connections in concurrent scenarios.
        """
        base_user_id = "collision-test-user"
        
        # Generate multiple connection IDs rapidly (simulating concurrent connections)
        connection_ids = []
        for i in range(20):  # Test concurrent scenario
            user_id = f"{base_user_id}-{i}"
            conn_id = generate_connection_id(user_id)
            connection_ids.append((user_id, str(conn_id)))
        
        # Check for collisions
        id_values = [conn_id for _, conn_id in connection_ids]
        unique_ids = set(id_values)
        
        collision_count = len(id_values) - len(unique_ids)
        assert collision_count == 0, \
            f"CONNECTION ID COLLISIONS: {collision_count} collisions found in {len(id_values)} IDs. " \
            f"This causes routing failures when multiple users get same connection ID."
        
        # Check format consistency
        formats = set()
        for user_id, conn_id in connection_ids:
            if conn_id.startswith('ws_conn_'):
                formats.add('ws_conn')
            elif conn_id.startswith('conn_'):
                formats.add('conn')
            else:
                formats.add('unknown')
        
        print(f"Connection ID formats found: {formats}")
        
        # Should only have one consistent format
        assert len(formats) == 1, \
            f"ROUTING FAILURE: Multiple connection ID formats found: {formats}. " \
            f"This breaks routing logic that expects consistent patterns."

    def test_message_routing_with_mismatched_connection_ids(self):
        """
        DESIGNED TO EXPOSE: Message routing failures due to ID format mismatches.
        
        This test demonstrates how messages fail to route when connection IDs
        are generated with different patterns by different components.
        """
        user_id = self.regular_user_id
        thread_id = f"thread_{user_id}_{int(time.time())}"
        
        # Create a connection using one ID format
        connection_id_v1 = f"conn_{user_id}_{uuid.uuid4().hex[:8]}"  # Legacy format
        
        # Register connection with legacy format
        mock_websocket = Mock()
        self.connection_manager.register_connection(
            connection_id=connection_id_v1,
            user_id=user_id,
            websocket=mock_websocket
        )
        
        # Create message using SSOT format (this is the mismatch)
        connection_id_v2 = generate_connection_id(user_id)  # SSOT format
        
        message = create_standard_message(
            msg_type="agent_started",
            payload={"content": "Test message"},
            user_id=user_id,
            thread_id=thread_id
        )
        
        print(f"Routing test scenario:")
        print(f"  Connection registered with ID: {connection_id_v1}")
        print(f"  Message targeting connection ID: {connection_id_v2}")
        print(f"  ID formats match: {connection_id_v1 == str(connection_id_v2)}")
        
        # Try to route message to connection
        registered_connection = self.connection_manager.get_connection(connection_id_v1)
        ssot_connection = self.connection_manager.get_connection(str(connection_id_v2))
        
        assert registered_connection is not None, "Connection should be found with registered ID"
        
        # CRITICAL TEST: This exposes the routing failure
        # If SSOT format is different from legacy, routing will fail
        if str(connection_id_v2) != connection_id_v1:
            assert ssot_connection is None, \
                f"ROUTING FAILURE EXPOSED: Message with SSOT ID {connection_id_v2} " \
                f"cannot find connection registered with legacy ID {connection_id_v1}. " \
                f"This is the root cause of 'Message routing failed' errors."
        
        # Document the ID format differences
        print(f"ID format analysis:")
        print(f"  Legacy format: {connection_id_v1}")
        print(f"  SSOT format: {connection_id_v2}")
        print(f"  Formats compatible: {str(connection_id_v2) == connection_id_v1}")

    def test_websocket_manager_connection_id_consistency(self):
        """
        DESIGNED TO EXPOSE: WebSocketManager connection ID inconsistencies.
        
        Tests that WebSocketManager instances use consistent connection IDs
        for routing messages to the correct connections.
        """
        user_id = self.enterprise_user_id
        mock_websocket = Mock()
        
        # Create manager through factory
        manager = self.factory.create_manager_for_user(
            user_id=user_id,
            websocket_connection=mock_websocket
        )
        
        # Extract connection ID from manager
        manager_connection_id = None
        for attr_name in ['connection_id', '_connection_id', 'conn_id']:
            if hasattr(manager, attr_name):
                manager_connection_id = getattr(manager, attr_name)
                break
        
        if manager_connection_id is None:
            # Try to get from manager's connection info
            if hasattr(manager, 'connection_info'):
                manager_connection_id = manager.connection_info.connection_id
        
        # Generate connection ID using utils
        utils_connection_id = generate_connection_id(user_id)
        
        print(f"WebSocketManager connection ID analysis:")
        print(f"  Manager connection ID: {manager_connection_id}")
        print(f"  Utils connection ID: {utils_connection_id}")
        
        if manager_connection_id:
            # Test routing consistency
            # Both IDs should be able to route to the same logical connection
            
            # Check format consistency
            manager_format = "unknown"
            utils_format = "unknown"
            
            if manager_connection_id and isinstance(manager_connection_id, str):
                if manager_connection_id.startswith('ws_conn_'):
                    manager_format = "ssot"
                elif manager_connection_id.startswith('conn_'):
                    manager_format = "legacy"
            
            if str(utils_connection_id).startswith('ws_conn_'):
                utils_format = "ssot"
            elif str(utils_connection_id).startswith('conn_'):
                utils_format = "legacy"
            
            print(f"  Manager format: {manager_format}")
            print(f"  Utils format: {utils_format}")
            
            # CRITICAL: Formats should match for proper routing
            assert manager_format == utils_format, \
                f"WEBSOCKET MANAGER ROUTING FAILURE: Manager uses {manager_format} format " \
                f"({manager_connection_id}) but utils uses {utils_format} format " \
                f"({utils_connection_id}). This breaks message routing between components."

    def test_connection_state_machine_id_compatibility(self):
        """
        DESIGNED TO EXPOSE: Connection state machine ID compatibility issues.
        
        Tests that connection state machines can find connections using
        the connection IDs generated by various components.
        """
        user_id = self.regular_user_id
        
        # Generate connection ID using standard method
        connection_id = generate_connection_id(user_id)
        
        # Mock connection state machine lookup
        # This simulates the state machine trying to find a connection
        from unittest.mock import patch
        
        with patch('netra_backend.app.websocket_core.connection_state_machine.get_connection_state_machine') as mock_get_state:
            # Mock state machine that would be found by connection ID
            mock_state_machine = Mock()
            mock_state_machine.current_state = 'connected'
            mock_state_machine.can_process_messages.return_value = True
            
            # This is the key test: does state machine lookup work with generated ID?
            mock_get_state.return_value = mock_state_machine
            
            # Import the function that would use state machine
            from netra_backend.app.websocket_core.utils import is_websocket_connected_and_ready
            
            mock_websocket = Mock()
            mock_websocket.client_state = Mock()
            mock_websocket.client_state.__eq__ = Mock(return_value=True)
            mock_websocket.receive = Mock()
            mock_websocket.send = Mock()
            
            # Test connection readiness check
            is_ready = is_websocket_connected_and_ready(mock_websocket, str(connection_id))
            
            # Verify state machine was called with correct connection ID
            mock_get_state.assert_called_with(str(connection_id))
            
            print(f"State machine compatibility test:")
            print(f"  Connection ID: {connection_id}")
            print(f"  State machine lookup called: {mock_get_state.called}")
            print(f"  Connection ready: {is_ready}")
            
            # CRITICAL: State machine should be found with generated connection ID
            assert mock_get_state.called, \
                f"STATE MACHINE ROUTING FAILURE: Connection readiness check did not " \
                f"attempt to find state machine for connection ID {connection_id}"

    def test_user_id_validation_in_connection_routing(self):
        """
        DESIGNED TO EXPOSE: User ID validation failures in connection routing.
        
        Tests edge cases where user ID validation affects connection ID generation
        and routing, particularly for special user types like demo users.
        """
        test_user_ids = [
            "user-test-123",           # Standard user
            "demo-user-456",           # Demo user  
            "enterprise-user-789",     # Enterprise user
            "user_with_underscore",    # Different separator
            "user-with-dashes-123",    # Multiple dashes
            "",                        # Empty (should fail)
            None,                      # None (should fail)
        ]
        
        routing_results = []
        
        for user_id in test_user_ids:
            try:
                if user_id in [None, ""]:
                    # These should fail validation
                    with pytest.raises((ValueError, TypeError)):
                        connection_id = generate_connection_id(user_id)
                    routing_results.append((user_id, "validation_failed", None))
                else:
                    # These should succeed
                    connection_id = generate_connection_id(user_id)
                    
                    # Test if connection can be registered and found
                    mock_websocket = Mock()
                    self.connection_manager.register_connection(
                        connection_id=str(connection_id),
                        user_id=user_id,
                        websocket=mock_websocket
                    )
                    
                    found_connection = self.connection_manager.get_connection(str(connection_id))
                    
                    routing_results.append((
                        user_id, 
                        "success" if found_connection else "routing_failed",
                        str(connection_id)
                    ))
                    
            except Exception as e:
                routing_results.append((user_id, f"error: {e}", None))
        
        print("User ID routing test results:")
        for user_id, status, conn_id in routing_results:
            print(f"  User '{user_id}': {status} -> {conn_id}")
        
        # Analyze results for routing failures
        failed_routing = [r for r in routing_results if 'failed' in r[1] or 'error' in r[1]]
        
        if failed_routing:
            failure_details = [f"{r[0]}: {r[1]}" for r in failed_routing]
            # Only assert if we have unexpected failures (not validation errors)
            unexpected_failures = [r for r in failed_routing if r[0] not in [None, ""]]
            
            if unexpected_failures:
                pytest.fail(f"UNEXPECTED ROUTING FAILURES: {failure_details}")

    def teardown_method(self):
        """Clean up test fixtures."""
        super().teardown_method()
        
        # Clear connection manager state
        if hasattr(self.connection_manager, 'clear_all_connections'):
            self.connection_manager.clear_all_connections()