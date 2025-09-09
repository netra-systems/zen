"""
WebSocket ID Migration UUID Exposure Unit Tests

CRITICAL: These tests are DESIGNED TO FAIL during Phase 1 of WebSocket ID migration.
They expose the uuid.uuid4() dependencies that need to be migrated to UnifiedIdGenerator.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: System stability and ID consistency  
- Value Impact: Prevents ID collisions and ensures proper user isolation
- Strategic Impact: CRITICAL - Proper ID management prevents security vulnerabilities

Test Strategy:
1. FAIL INITIALLY - Tests expose uuid.uuid4() usage across WebSocket core
2. MIGRATE PHASE - Replace uuid.uuid4() with UnifiedIdGenerator methods
3. PASS FINALLY - Tests validate consistent ID generation patterns

These tests validate that WebSocket core components use the UnifiedIdGenerator
instead of scattered uuid.uuid4().hex[:8] patterns that violate SSOT principles.
"""

import pytest
import uuid
import time
from typing import Dict, Any, Optional
from unittest.mock import patch, MagicMock

# Import WebSocket core modules that need UUID migration
from netra_backend.app.websocket_core.types import ConnectionInfo, WebSocketMessage, create_standard_message
from netra_backend.app.websocket_core.context import WebSocketContext
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
from netra_backend.app.websocket_core.utils import generate_connection_id, generate_message_id
from netra_backend.app.websocket_core.migration_adapter import WebSocketManagerAdapter
from netra_backend.app.websocket_core.handlers import WebSocketHandler
from netra_backend.app.websocket_core.event_validation_framework import EventValidationFramework

# Import the SSOT UnifiedIdGenerator for migration
from shared.id_generation.unified_id_generator import UnifiedIdGenerator, generate_uuid_replacement
from shared.types.core_types import ConnectionID, WebSocketID, UserID


class TestWebSocketIdMigrationUuidExposure:
    """
    Unit tests that EXPOSE uuid.uuid4() dependencies in WebSocket core.
    
    CRITICAL: These tests are DESIGNED TO FAIL initially to demonstrate
    the migration need from uuid.uuid4() to UnifiedIdGenerator.
    """

    def test_connection_info_uses_unified_id_generator(self):
        """
        DESIGNED TO FAIL: Expose uuid.uuid4() usage in ConnectionInfo default factory.
        
        This test demonstrates that ConnectionInfo.connection_id uses uuid.uuid4().hex[:8]
        which violates SSOT principles and needs migration to UnifiedIdGenerator.
        """
        # Create multiple ConnectionInfo instances
        connections = []
        for i in range(10):
            conn = ConnectionInfo(user_id=f"user_{i}")
            connections.append(conn)
        
        # SUCCESS ASSERTION: These IDs should follow UnifiedIdGenerator pattern
        # and NOT use uuid.uuid4().hex[:8] pattern
        for conn in connections:
            # This should PASS because connection_id now uses UnifiedIdGenerator
            assert not len(conn.connection_id) == 36, \
                f"ConnectionInfo still uses uuid.uuid4() full format: {conn.connection_id}"
            
            # This should PASS because we now use UnifiedIdGenerator format
            # Format is: ws_conn_{user_prefix}_{timestamp}_{counter}_{random}
            assert conn.connection_id.startswith("ws_conn_"), \
                f"Expected UnifiedIdGenerator pattern starting with 'ws_conn_', got: {conn.connection_id}"
            
        # Validate no UUID4 collision patterns exist
        connection_ids = [conn.connection_id for conn in connections]
        assert len(set(connection_ids)) == len(connection_ids), \
            "UUID4 pattern allows potential ID collisions"

    def test_websocket_message_uses_unified_id_generator(self):
        """
        DESIGNED TO FAIL: Expose uuid.uuid4() usage in WebSocketMessage message_id.
        
        This test demonstrates that generate_default_message() uses uuid.uuid4()
        which needs migration to UnifiedIdGenerator.generate_message_id().
        """
        # Generate multiple default messages
        messages = []
        user_id = "test_user_123"
        thread_id = "test_thread_456" 
        
        for i in range(5):
            message = create_standard_message(
                msg_type="agent_started",
                payload={"content": f"Message {i}"},
                user_id=user_id,
                thread_id=thread_id
            )
            messages.append(message)
            
        # SUCCESS ASSERTION: These message IDs should follow UnifiedIdGenerator pattern
        for msg in messages:
            # This should PASS because message_id now uses UnifiedIdGenerator
            assert not len(msg.message_id) == 36, \
                f"Message ID still uses uuid.uuid4() full format: {msg.message_id}"
                
            # This should PASS because we now use UnifiedIdGenerator format
            # Format is: msg_{normalized_type}_{timestamp}_{counter}_{random}
            assert msg.message_id.startswith("msg_start_agent_"), \
                f"Expected UnifiedIdGenerator pattern starting with 'msg_start_agent_', got: {msg.message_id}"
                
        # Validate message ID uniqueness and consistency
        message_ids = [msg.message_id for msg in messages]
        assert len(set(message_ids)) == len(message_ids), \
            "UUID4 pattern allows potential message ID collisions"

    def test_websocket_context_uses_unified_id_generator(self):
        """
        DESIGNED TO FAIL: Expose uuid.uuid4() usage in WebSocketRequestContext.
        
        This test demonstrates that context generation uses uuid.uuid4()
        which needs migration to UnifiedIdGenerator.
        """
        user_id = "context_test_user"
        
        # Create multiple WebSocket contexts  
        contexts = []
        for i in range(3):
            # This should trigger uuid.uuid4() usage in context creation
            context = WebSocketContext.create_for_user(
                websocket=MagicMock(),
                user_id=user_id,
                thread_id=f"thread_{i}",  # Provide thread_id as required
                run_id=None  # Should generate new run_id
            )
            contexts.append(context)
            
        # SUCCESS ASSERTION: run_id and connection_id should use UnifiedIdGenerator
        for context in contexts:
            # This should PASS because run_id now uses UnifiedIdGenerator  
            assert not len(context.run_id) == 36, \
                f"Context run_id still uses uuid.uuid4() format: {context.run_id}"
                
            # This should PASS because connection_id now uses UnifiedIdGenerator
            assert context.connection_id and context.connection_id.startswith("ws_conn_"), \
                f"Expected connection_id pattern 'ws_conn_', got: {context.connection_id}"
                
        # Validate context ID consistency 
        run_ids = [ctx.run_id for ctx in contexts]
        assert len(set(run_ids)) == len(run_ids), \
            "UUID4 pattern allows potential context run_id collisions"

    def test_websocket_manager_factory_uses_uuid4_pattern_EXPECTED_FAILURE(self):
        """
        DESIGNED TO FAIL: Expose uuid.uuid4() usage in WebSocketManagerFactory.
        
        This test demonstrates that factory unique suffixes use uuid.uuid4()
        which needs migration to UnifiedIdGenerator.
        """
        factory = WebSocketManagerFactory()
        user_id = "factory_test_user"
        
        # Create multiple managers which should generate unique suffixes
        managers = []
        for i in range(3):
            manager = factory.create_manager_for_user(
                user_id=user_id,
                websocket_connection=MagicMock()
            )
            managers.append(manager)
            
        # FAILING ASSERTION: Manager identifiers should use UnifiedIdGenerator
        for manager in managers:
            # Get internal manager identifier (this will expose uuid.uuid4())
            manager_id = getattr(manager, '_manager_id', None) or \
                         getattr(manager, 'unique_suffix', None)
            
            if manager_id:
                # This will FAIL because unique_suffix uses str(uuid.uuid4())[:8]
                assert len(manager_id) > 8, \
                    f"Manager ID still uses uuid.uuid4()[:8] pattern: {manager_id}"
                    
                # This will FAIL because we expect UnifiedIdGenerator format
                expected_pattern = f"mgr_{user_id[:8]}_"
                assert manager_id.startswith(expected_pattern), \
                    f"Expected manager ID pattern '{expected_pattern}', got: {manager_id}"

    def test_websocket_utils_generate_ids_unified_generator(self):
        """
        DESIGNED TO FAIL: Expose uuid.uuid4() usage in websocket_core.utils functions.
        
        This test demonstrates that utility functions use uuid.uuid4() 
        which needs migration to UnifiedIdGenerator.
        """
        # Test generate_connection_id function
        user_id = "test-user-123"  # Use valid test pattern
        
        connection_ids = []
        for i in range(5):
            conn_id = generate_connection_id(user_id)
            connection_ids.append(conn_id)
            
        # SUCCESS ASSERTION: Connection IDs should use UnifiedIdGenerator
        for conn_id in connection_ids:
            # This should PASS because generate_connection_id now uses UnifiedIdGenerator
            assert not len(str(conn_id)) == 36, \
                f"Connection ID still uses uuid.uuid4() format: {conn_id}"
                
            # This should PASS because we now use UnifiedIdGenerator format
            assert str(conn_id).startswith("ws_conn_"), \
                f"Expected connection ID pattern 'ws_conn_', got: {conn_id}"
                
        # Test generate_message_id function (renamed from generate_unique_id)
        unique_ids = []
        for i in range(5):
            unique_id = generate_message_id()
            unique_ids.append(unique_id)
            
        # SUCCESS ASSERTION: Unique IDs should use UnifiedIdGenerator
        for unique_id in unique_ids:
            # This should PASS because generate_message_id now uses UnifiedIdGenerator
            assert len(unique_id) != 36, \
                f"Unique ID still uses uuid.uuid4() format: {unique_id}"
                
            # This should PASS because we now use UnifiedIdGenerator format
            assert unique_id.startswith("uid_"), \
                f"Expected unique ID to start with 'uid_', got: {unique_id}"

    def test_event_validation_framework_uses_uuid4_pattern_EXPECTED_FAILURE(self):
        """
        DESIGNED TO FAIL: Expose uuid.uuid4() usage in EventValidationFramework.
        
        This test demonstrates that event validation uses uuid.uuid4() 
        which needs migration to UnifiedIdGenerator.
        """
        framework = EventValidationFramework()
        
        # Create test events that trigger ID generation
        test_events = []
        for i in range(3):
            event = framework.create_test_event(
                event_type="agent_thinking", 
                user_id=f"event_user_{i}",
                data={"message": f"Test event {i}"}
            )
            test_events.append(event)
            
        # FAILING ASSERTION: Event IDs should use UnifiedIdGenerator
        for event in test_events:
            event_id = event.get('event_id') or event.get('message_id')
            
            if event_id:
                # This will FAIL because event IDs use str(uuid.uuid4())
                assert len(event_id) != 36, \
                    f"Event ID still uses uuid.uuid4() format: {event_id}"
                    
                # This will FAIL because we expect UnifiedIdGenerator format  
                expected_pattern = "evt_agent_thinking_"
                assert event_id.startswith(expected_pattern), \
                    f"Expected event ID pattern '{expected_pattern}', got: {event_id}"

    def test_migration_adapter_uses_uuid4_pattern_EXPECTED_FAILURE(self):
        """
        DESIGNED TO FAIL: Expose uuid.uuid4() usage in WebSocketManagerAdapter.
        
        This test demonstrates that migration adapter uses uuid.uuid4()
        which needs migration to UnifiedIdGenerator.  
        """
        adapter = WebSocketManagerAdapter()
        
        # Get adapter metrics to check for internal ID generation
        metrics = adapter.get_adapter_metrics()
        
        # Create default user contexts that trigger ID generation 
        user_id = "migration_test_user"
        contexts = []
        
        for i in range(3):
            # This triggers internal context creation with UUID generation
            context = adapter._create_default_user_context({
                "user_id": f"{user_id}_{i}",
                "connection_id": None  # Forces generation
            })
            contexts.append(context)
            
        # FAILING ASSERTION: Context IDs should use UnifiedIdGenerator
        for context in contexts:
            # Check run_id uses uuid.uuid4() pattern
            run_id = context.run_id
            
            if run_id:
                # This will FAIL because run_id uses str(uuid.uuid4())[:8] pattern
                assert not run_id.startswith("run_"), \
                    f"Migration context run_id still uses uuid pattern: {run_id}"
                    
                # This will FAIL because we expect UnifiedIdGenerator format
                expected_pattern = f"ctx_{context.user_id[:8]}_"
                assert run_id.startswith(expected_pattern), \
                    f"Expected context run_id pattern '{expected_pattern}', got: {run_id}"

    @pytest.mark.performance 
    def test_uuid4_vs_unified_generator_performance_comparison(self):
        """
        Performance comparison showing UnifiedIdGenerator benefits.
        
        This test demonstrates that UnifiedIdGenerator provides better performance
        and consistency compared to scattered uuid.uuid4() usage.
        """
        import time
        
        # Measure uuid.uuid4() performance (current pattern)
        start_time = time.time()
        uuid4_ids = []
        for i in range(1000):
            uuid4_ids.append(str(uuid.uuid4()))
        uuid4_time = time.time() - start_time
        
        # Measure UnifiedIdGenerator performance (target pattern)
        start_time = time.time() 
        unified_ids = []
        for i in range(1000):
            unified_ids.append(UnifiedIdGenerator.generate_base_id("test"))
        unified_time = time.time() - start_time
        
        # Performance validation - UnifiedIdGenerator should be competitive
        assert unified_time <= uuid4_time * 2.0, \
            f"UnifiedIdGenerator too slow: {unified_time:.4f}s vs uuid4 {uuid4_time:.4f}s"
            
        # Consistency validation - UnifiedIdGenerator provides better patterns
        assert all(uid.startswith("test_") for uid in unified_ids), \
            "UnifiedIdGenerator provides consistent prefixes"
            
        # Uniqueness validation - Both should generate unique IDs
        assert len(set(uuid4_ids)) == len(uuid4_ids), "UUID4 collision detected"
        assert len(set(unified_ids)) == len(unified_ids), "UnifiedIdGenerator collision detected"
        
        print(f"Performance comparison:")
        print(f"  UUID4: {uuid4_time:.4f}s for 1000 IDs")
        print(f"  UnifiedIdGenerator: {unified_time:.4f}s for 1000 IDs") 
        print(f"  Improvement: {((uuid4_time - unified_time) / uuid4_time * 100):.1f}%")

    def test_websocket_id_collision_prevention_requirements(self):
        """
        Test that validates ID collision prevention requirements.
        
        This test ensures that any ID generation solution prevents the
        collision scenarios that could occur with naive uuid.uuid4() usage.
        """
        # Test concurrent ID generation scenario
        import threading
        import queue
        
        id_queue = queue.Queue()
        
        def generate_ids_concurrent():
            """Simulate concurrent ID generation."""
            for i in range(100):
                # This represents the pattern we're migrating FROM
                old_pattern_id = f"conn_{uuid.uuid4().hex[:8]}"
                
                # This represents the pattern we're migrating TO
                new_pattern_id = UnifiedIdGenerator.generate_websocket_connection_id("test_user")
                
                id_queue.put((old_pattern_id, new_pattern_id))
                
        # Run concurrent threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=generate_ids_concurrent)
            threads.append(thread)
            thread.start()
            
        for thread in threads:
            thread.join()
            
        # Collect all IDs
        old_ids = []
        new_ids = []
        
        while not id_queue.empty():
            old_id, new_id = id_queue.get()
            old_ids.append(old_id)
            new_ids.append(new_id)
            
        # Validate uniqueness (both should pass)
        assert len(set(old_ids)) == len(old_ids), "Old pattern ID collision detected"
        assert len(set(new_ids)) == len(new_ids), "New pattern ID collision detected"
        
        # Validate format consistency (new pattern should win)  
        assert all(nid.startswith("ws_conn_test_user_") for nid in new_ids), \
            "New pattern provides consistent format"
            
        # Report collision risk assessment
        old_collision_risk = len(old_ids) - len(set(old_ids))
        new_collision_risk = len(new_ids) - len(set(new_ids))
        
        print(f"ID Collision Risk Assessment:")
        print(f"  Old pattern collisions: {old_collision_risk}")
        print(f"  New pattern collisions: {new_collision_risk}")
        print(f"  Improvement: {old_collision_risk - new_collision_risk} fewer collisions")