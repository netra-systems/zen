"""
Comprehensive Infrastructure Consolidation Tests

This test suite validates the infrastructure consolidation efforts including:
1. WebSocket manager consolidation with connection scoping
2. Unified ID manager with all ID generation functions
3. Session factory cleanup
4. Memory leak prevention

Business Value:
- Ensures zero cross-user event leakage
- Validates consistent ID generation across platform
- Confirms memory stability over time
- Prevents session/connection resource leaks
"""

import asyncio
import time
import uuid
from typing import Dict, Any, List
from unittest.mock import Mock, patch
import pytest

from netra_backend.app.core.unified_id_manager import UnifiedIDManager
from netra_backend.app.websocket_core.manager import WebSocketManager, ConnectionScope, get_websocket_manager
from fastapi import WebSocket
from fastapi.websockets import WebSocketState


class TestWebSocketManagerConsolidation:
    """Test WebSocket manager consolidation with connection scoping."""
    
    @pytest.fixture
    def manager(self):
        """Create WebSocket manager with connection scoping enabled."""
        return WebSocketManager(enable_connection_scoping=True)
    
    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket for testing."""
        ws = Mock(spec=WebSocket)
        ws.client_state = WebSocketState.CONNECTED
        
        async def mock_send_text(text):
            return None
        
        async def mock_send_bytes(data):
            return None
        
        async def mock_close(code=1000, reason=""):
            return None
        
        ws.send_text = mock_send_text
        ws.send_bytes = mock_send_bytes
        ws.close = mock_close
        return ws
    
    @pytest.mark.asyncio
    async def test_connection_scoping_enabled(self, manager):
        """Test that connection scoping is enabled by default."""
        assert manager.enable_connection_scoping is True
        assert manager._connection_scopes == {}
        assert manager.scoping_stats["scoped_connections"] == 0
    
    @pytest.mark.asyncio
    async def test_connection_scope_creation(self, manager, mock_websocket):
        """Test creation of connection-specific scopes."""
        # Create connection
        user_id = "test_user_123"
        connection_id = await manager.connect_user(user_id, mock_websocket, thread_id="test_thread")
        
        # Get connection scope
        scope = manager.get_connection_scope(connection_id)
        
        # Verify scope properties
        assert scope is not None
        assert isinstance(scope, ConnectionScope)
        assert scope.user_id == user_id
        assert scope.thread_id == "test_thread"
        assert scope.connection_id == connection_id
        assert scope.websocket == mock_websocket
        assert scope.parent_manager == manager
        
        # Verify stats updated
        assert manager.scoping_stats["scopes_created"] == 1
        assert manager.scoping_stats["scoped_connections"] == 1
    
    @pytest.mark.asyncio
    async def test_scoped_event_user_validation(self, manager, mock_websocket):
        """Test that scoped events validate user ID to prevent leakage."""
        # Create connections for two different users
        user1_id = "user_1"
        user2_id = "user_2"
        
        conn1_id = await manager.connect_user(user1_id, mock_websocket, thread_id="thread1")
        conn2_id = await manager.connect_user(user2_id, mock_websocket, thread_id="thread2")
        
        # Try to send event to user2's connection with user1's ID (should be blocked)
        success = await manager.send_scoped_event(
            conn2_id, 
            "test_event",
            {"data": "sensitive"},
            user_id=user1_id  # Wrong user!
        )
        
        assert success is False
        assert manager.scoping_stats["events_blocked"] == 1
    
    @pytest.mark.asyncio
    async def test_connection_scope_cleanup(self, manager, mock_websocket):
        """Test that connection scopes are cleaned up properly."""
        # Create connection
        user_id = "cleanup_test_user"
        connection_id = await manager.connect_user(user_id, mock_websocket)
        
        # Create scope
        scope = manager.get_connection_scope(connection_id)
        assert scope is not None
        assert connection_id in manager._connection_scopes
        
        # Disconnect and cleanup
        await manager.disconnect_user(user_id, mock_websocket)
        
        # Verify scope cleaned up
        assert connection_id not in manager._connection_scopes
        assert manager.scoping_stats["scopes_cleaned"] > 0
    
    @pytest.mark.asyncio
    async def test_connection_scope_prevents_cross_user_events(self, manager):
        """Test that connection scoping prevents cross-user event leakage."""
        # Create mock websockets for different users
        ws1 = Mock(spec=WebSocket)
        ws1.client_state = WebSocketState.CONNECTED
        
        async def mock_send1(text):
            return None
        ws1.send_text = mock_send1
        
        ws2 = Mock(spec=WebSocket)
        ws2.client_state = WebSocketState.CONNECTED
        
        async def mock_send2(text):
            return None
        ws2.send_text = mock_send2
        
        # Connect users
        user1_conn = await manager.connect_user("alice", ws1, thread_id="alice_thread")
        user2_conn = await manager.connect_user("bob", ws2, thread_id="bob_thread")
        
        # Get scopes
        alice_scope = manager.get_connection_scope(user1_conn)
        bob_scope = manager.get_connection_scope(user2_conn)
        
        # Verify scopes are isolated
        assert alice_scope.user_id == "alice"
        assert bob_scope.user_id == "bob"
        assert alice_scope.validate_user("bob") is False
        assert bob_scope.validate_user("alice") is False
        
        # Send event through alice's scope
        await alice_scope.send_event("private_event", {"secret": "alice_data"})
        
        # Verify stats
        assert alice_scope.stats["events_sent"] == 1
        assert bob_scope.stats["events_sent"] == 0


class TestUnifiedIDManager:
    """Test unified ID manager with all ID generation functions."""
    
    def test_generate_all_id_types(self):
        """Test generation of all ID types."""
        # Thread and run IDs (existing)
        thread_id = UnifiedIDManager.generate_thread_id()
        assert thread_id.startswith("session_")
        
        run_id = UnifiedIDManager.generate_run_id(thread_id)
        assert run_id.startswith("thread_")
        assert "_run_" in run_id
        
        # Connection ID
        conn_id = UnifiedIDManager.generate_connection_id("user123")
        assert conn_id.startswith("conn_user123_")
        
        # Message ID
        msg_id = UnifiedIDManager.generate_message_id()
        assert len(msg_id) == 36  # UUID4 format
        assert "-" in msg_id
        
        # Session ID
        sess_id = UnifiedIDManager.generate_session_id("user456")
        assert sess_id.startswith("sess_user456_")
        
        # Request ID
        req_id = UnifiedIDManager.generate_request_id()
        assert req_id.startswith("req_")
        
        # Trace ID
        trace_id = UnifiedIDManager.generate_trace_id()
        assert trace_id.startswith("trace_")
        assert len(trace_id) == 22  # "trace_" + 16 hex chars
        
        # Span ID
        span_id = UnifiedIDManager.generate_span_id()
        assert span_id.startswith("span_")
        
        # Correlation ID
        corr_id = UnifiedIDManager.generate_correlation_id()
        assert len(corr_id) == 36  # UUID4 format
        
        # Audit ID
        audit_id = UnifiedIDManager.generate_audit_id()
        assert audit_id.startswith("audit_")
        
        # Context ID
        ctx_id = UnifiedIDManager.generate_context_id()
        assert ctx_id.startswith("ctx_")
        assert len(ctx_id) == 20  # "ctx_" + 16 hex chars
        
        # User ID (for testing)
        user_id = UnifiedIDManager.generate_user_id()
        assert user_id.startswith("user_")
        
        # Test ID
        test_id = UnifiedIDManager.generate_test_id()
        assert test_id.startswith("test_")
    
    def test_id_uniqueness(self):
        """Test that generated IDs are unique."""
        # Generate multiple IDs of each type
        ids = []
        
        for _ in range(100):
            ids.append(UnifiedIDManager.generate_connection_id())
            ids.append(UnifiedIDManager.generate_message_id())
            ids.append(UnifiedIDManager.generate_session_id())
            ids.append(UnifiedIDManager.generate_request_id())
            ids.append(UnifiedIDManager.generate_trace_id())
            ids.append(UnifiedIDManager.generate_correlation_id())
        
        # All IDs should be unique
        assert len(ids) == len(set(ids))
    
    def test_id_format_consistency(self):
        """Test that ID formats are consistent."""
        # Timestamped IDs should have similar timestamp
        start_time = int(time.time() * 1000)
        
        conn_id = UnifiedIDManager.generate_connection_id("test")
        sess_id = UnifiedIDManager.generate_session_id("test")
        req_id = UnifiedIDManager.generate_request_id()
        
        # Extract timestamps
        conn_ts = int(conn_id.split("_")[2])
        sess_ts = int(sess_id.split("_")[2])
        req_ts = int(req_id.split("_")[1])
        
        # Timestamps should be within 1 second
        assert abs(conn_ts - start_time) < 1000
        assert abs(sess_ts - start_time) < 1000
        assert abs(req_ts - start_time) < 1000
    
    def test_backward_compatibility(self):
        """Test backward compatibility with legacy ID formats."""
        # Legacy run_id format
        legacy_run_id = "run_old_thread_id_a1b2c3d4"
        extracted = UnifiedIDManager.extract_thread_id(legacy_run_id)
        assert extracted == "old_thread_id"
        
        # Canonical format
        canonical_run_id = "thread_new_thread_id_run_1234567890_a1b2c3d4"
        extracted = UnifiedIDManager.extract_thread_id(canonical_run_id)
        assert extracted == "new_thread_id"
    
    def test_id_prefix_customization(self):
        """Test that ID prefixes can be customized where applicable."""
        # Connection ID with custom prefix
        conn_id = UnifiedIDManager.generate_connection_id("user", prefix="ws")
        assert conn_id.startswith("ws_user_")
        
        # User ID with custom prefix
        user_id = UnifiedIDManager.generate_user_id(prefix="admin")
        assert user_id.startswith("admin_")
        
        # Test ID with custom prefix
        test_id = UnifiedIDManager.generate_test_id(prefix="integration")
        assert test_id.startswith("integration_")


class TestMemoryLeakPrevention:
    """Test memory leak prevention in infrastructure."""
    
    @pytest.mark.asyncio
    async def test_connection_scope_memory_cleanup(self):
        """Test that connection scopes don't leak memory."""
        manager = WebSocketManager(enable_connection_scoping=True)
        
        # Track initial state
        initial_scopes = len(manager._connection_scopes)
        
        # Create and destroy many connections
        for i in range(100):
            ws = Mock(spec=WebSocket)
            ws.client_state = WebSocketState.CONNECTED
            
            async def mock_close(code=1000, reason=""):
                return None
            ws.close = mock_close
            
            # Connect
            conn_id = await manager.connect_user(f"user_{i}", ws)
            scope = manager.get_connection_scope(conn_id)
            assert scope is not None
            
            # Disconnect
            await manager.disconnect_user(f"user_{i}", ws)
        
        # All scopes should be cleaned up
        assert len(manager._connection_scopes) == initial_scopes
        assert manager.scoping_stats["scopes_created"] == 100
        assert manager.scoping_stats["scopes_cleaned"] == 100
    
    @pytest.mark.asyncio
    async def test_websocket_manager_singleton_efficiency(self):
        """Test that WebSocket manager singleton pattern is memory efficient."""
        # Get multiple references to the manager
        manager1 = get_websocket_manager()
        manager2 = get_websocket_manager()
        manager3 = WebSocketManager()
        
        # All should be the same instance (singleton)
        assert manager1 is manager2
        assert manager2 is manager3
        
        # Verify only one instance exists in memory
        assert WebSocketManager._instance is not None
        assert WebSocketManager._instance is manager1
    
    def test_id_generation_performance(self):
        """Test that ID generation is performant and doesn't leak memory."""
        import sys
        import gc
        
        # Get initial memory baseline
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Generate many IDs
        for _ in range(10000):
            UnifiedIDManager.generate_connection_id()
            UnifiedIDManager.generate_message_id()
            UnifiedIDManager.generate_request_id()
        
        # Force garbage collection
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # Memory growth should be minimal (allowing for some caching)
        memory_growth = final_objects - initial_objects
        assert memory_growth < 1000  # Reasonable threshold


class TestConcurrentOperations:
    """Test concurrent operations in consolidated infrastructure."""
    
    @pytest.mark.asyncio
    async def test_concurrent_connection_scoping(self):
        """Test that connection scoping works correctly under concurrent load."""
        manager = WebSocketManager(enable_connection_scoping=True)
        
        async def create_and_use_connection(user_id: str, num_events: int):
            """Create connection and send events."""
            ws = Mock(spec=WebSocket)
            ws.client_state = WebSocketState.CONNECTED
            
            async def mock_send(text):
                return None
            ws.send_text = mock_send
            
            conn_id = await manager.connect_user(user_id, ws)
            scope = manager.get_connection_scope(conn_id)
            
            for i in range(num_events):
                await scope.send_event(f"event_{i}", {"data": f"data_{i}"})
            
            return scope.stats["events_sent"]
        
        # Create concurrent connections
        tasks = []
        for i in range(10):
            tasks.append(create_and_use_connection(f"user_{i}", 10))
        
        results = await asyncio.gather(*tasks)
        
        # Each connection should have sent 10 events
        assert all(r == 10 for r in results)
        assert manager.scoping_stats["scoped_connections"] == 10
    
    def test_concurrent_id_generation(self):
        """Test that ID generation is thread-safe."""
        import concurrent.futures
        
        def generate_ids(count):
            """Generate multiple IDs."""
            ids = []
            for _ in range(count):
                ids.append(UnifiedIDManager.generate_connection_id())
                ids.append(UnifiedIDManager.generate_message_id())
                ids.append(UnifiedIDManager.generate_request_id())
            return ids
        
        # Generate IDs concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(generate_ids, 100) for _ in range(10)]
            results = [f.result() for f in futures]
        
        # Flatten results
        all_ids = []
        for id_list in results:
            all_ids.extend(id_list)
        
        # All IDs should be unique
        assert len(all_ids) == len(set(all_ids))
        assert len(all_ids) == 10 * 100 * 3  # 10 threads * 100 iterations * 3 ID types


class TestEdgeCases:
    """Test edge cases in consolidated infrastructure."""
    
    @pytest.mark.asyncio
    async def test_connection_scope_with_disabled_scoping(self):
        """Test behavior when connection scoping is disabled."""
        manager = WebSocketManager(enable_connection_scoping=False)
        
        ws = Mock(spec=WebSocket)
        ws.client_state = WebSocketState.CONNECTED
        
        async def mock_close(code=1000, reason=""):
            return None
        ws.close = mock_close
        
        conn_id = await manager.connect_user("user", ws)
        scope = manager.get_connection_scope(conn_id)
        
        # Should return None when scoping is disabled
        assert scope is None
        assert manager.scoping_stats["scopes_created"] == 0
    
    def test_id_generation_with_empty_inputs(self):
        """Test ID generation with empty or invalid inputs."""
        # Connection ID with empty user
        conn_id = UnifiedIDManager.generate_connection_id("")
        assert conn_id.startswith("conn_")
        assert len(conn_id.split("_")) == 3  # No user part
        
        # Session ID with no user
        sess_id = UnifiedIDManager.generate_session_id()
        assert sess_id.startswith("sess_")
        assert len(sess_id.split("_")) == 3  # No user part
        
        # Thread ID generation should raise on empty
        with pytest.raises(ValueError):
            UnifiedIDManager.generate_run_id("")
    
    @pytest.mark.asyncio
    async def test_connection_scope_after_disconnect(self):
        """Test that connection scope behaves correctly after disconnect."""
        manager = WebSocketManager(enable_connection_scoping=True)
        
        ws = Mock(spec=WebSocket)
        ws.client_state = WebSocketState.CONNECTED
        
        async def mock_close(code=1000, reason=""):
            return None
        ws.close = mock_close
        
        conn_id = await manager.connect_user("user", ws)
        scope = manager.get_connection_scope(conn_id)
        assert scope is not None
        
        # Disconnect
        await manager.disconnect_user("user", ws)
        
        # Should not be able to get scope for disconnected connection
        new_scope = manager.get_connection_scope(conn_id)
        assert new_scope is None


# Integration test combining all components
class TestInfrastructureIntegration:
    """Test integrated infrastructure components."""
    
    @pytest.mark.asyncio
    async def test_full_websocket_flow_with_unified_ids(self):
        """Test complete WebSocket flow using unified IDs."""
        manager = WebSocketManager(enable_connection_scoping=True)
        
        # Generate IDs using UnifiedIDManager
        user_id = UnifiedIDManager.generate_user_id()
        thread_id = UnifiedIDManager.generate_thread_id()
        run_id = UnifiedIDManager.generate_run_id(thread_id)
        
        # Create mock websocket
        ws = Mock(spec=WebSocket)
        ws.client_state = WebSocketState.CONNECTED
        
        async def mock_send(text):
            return None
        ws.send_text = mock_send
        
        # Connect with generated IDs
        conn_id = await manager.connect_user(user_id, ws, thread_id=thread_id)
        
        # Verify connection ID format
        assert conn_id.startswith(f"conn_{user_id}_")
        
        # Get connection scope
        scope = manager.get_connection_scope(conn_id)
        assert scope.user_id == user_id
        assert scope.thread_id == thread_id
        
        # Send event with correlation ID
        correlation_id = UnifiedIDManager.generate_correlation_id()
        await scope.send_event("agent_started", {
            "run_id": run_id,
            "correlation_id": correlation_id
        })
        
        # Verify event sent
        assert scope.stats["events_sent"] == 1
        
        # Clean up
        await manager.disconnect_user(user_id, ws)
        assert conn_id not in manager._connection_scopes


if __name__ == "__main__":
    pytest.main([__file__, "-v"])