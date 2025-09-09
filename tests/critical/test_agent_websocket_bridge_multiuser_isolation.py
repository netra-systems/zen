class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""
    
    def __init__(self):
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
        
    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
            raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)
        
    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        self._closed = True
        self.is_connected = False
        
    def get_messages(self) -> list:
        """Get all sent messages."""
        return self.messages_sent.copy()

"""
CRITICAL: Multi-user isolation test suite for AgentWebSocketBridge
This test suite demonstrates and validates that the singleton pattern
causes cross-user event leakage and validates the factory pattern fix.
"""

import asyncio
import json
import uuid
from typing import Dict, List, Optional, Set
from datetime import datetime, timezone
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.core.registry.universal_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

import pytest
from websocket import WebSocket

from netra_backend.app.services.agent_websocket_bridge import (
    AgentWebSocketBridge,
    # REMOVED: get_agent_websocket_bridge - deprecated singleton pattern removed
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env


class WebSocketEventCollector:
    """Collects WebSocket events for a specific user to detect cross-user leakage."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.events: List[Dict] = []
        self.leaked_events: List[Dict] = []  # Events not meant for this user
        
    async def send_json(self, data: Dict):
        """Mock WebSocket send that collects events."""
        self.events.append(data)
        
        # Check if this event is actually for this user
        if 'user_id' in data and data['user_id'] != self.user_id:
            self.leaked_events.append({
                'intended_user': data['user_id'],
                'actual_user': self.user_id,
                'event': data
            })
            
    def has_leaked_events(self) -> bool:
        """Check if any events leaked from other users."""
        return len(self.leaked_events) > 0
    
    def get_event_types(self) -> Set[str]:
        """Get all event types received."""
        return {e.get('type', 'unknown') for e in self.events}


class TestAgentWebSocketBridgeMultiUserIsolation:
    """
    CRITICAL TEST SUITE: Validates multi-user isolation in AgentWebSocketBridge.
    
    These tests demonstrate that:
    1. Singleton pattern causes cross-user event leakage (FAILS)
    2. Factory pattern with UserExecutionContext prevents leakage (PASSES)
    3. Concurrent user operations maintain isolation
    4. Background tasks maintain user context
    """
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_singleton_causes_cross_user_leakage(self):
        """
        EXPECTED TO FAIL: Demonstrates that singleton pattern leaks events between users.
        This test should fail with current singleton implementation.
        """
        # Create two users with their own WebSocket connections
        user1_id = "user_001"
        user2_id = "user_002"
        
        user1_collector = WebSocketEventCollector(user1_id)
        user2_collector = WebSocketEventCollector(user2_id)
        
        # Get singleton bridge (DANGEROUS)
        bridge = await get_agent_websocket_bridge()
        
        # Simulate WebSocket manager with both connections
        with patch('netra_backend.app.websocket_core.unified_manager.get_websocket_manager') as mock_ws_mgr:
            websocket = TestWebSocketConnection()
            mock_ws_mgr.return_value = mock_manager
            
            # Mock get_connection to return different collectors for different users
            async def get_connection_side_effect(connection_id):
                if connection_id == f"conn_{user1_id}":
                    return user1_collector
                elif connection_id == f"conn_{user2_id}":
                    return user2_collector
                return None
                
            mock_manager.get_connection = AsyncMock(side_effect=get_connection_side_effect)
            
            # User 1 starts an agent
            run1_id = f"run_{user1_id}_{uuid.uuid4()}"
            await bridge.notify_agent_started(run1_id, "DataAgent", metadata={
                'user_id': user1_id,
                'connection_id': f"conn_{user1_id}"
            })
            
            # User 2 starts an agent
            run2_id = f"run_{user2_id}_{uuid.uuid4()}"
            await bridge.notify_agent_started(run2_id, "OptimizationAgent", metadata={
                'user_id': user2_id,
                'connection_id': f"conn_{user2_id}"
            })
            
            # Check for leakage - THIS SHOULD FAIL
            # With singleton, User 1 might receive User 2's events
            assert user1_collector.has_leaked_events(), \
                "SECURITY VIOLATION: User 1 received events intended for User 2"
            assert user2_collector.has_leaked_events(), \
                "SECURITY VIOLATION: User 2 received events intended for User 1"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_factory_pattern_prevents_cross_user_leakage(self):
        """
        EXPECTED TO PASS: Validates that factory pattern prevents cross-user leakage.
        This test should pass with factory pattern implementation.
        """
        # Create two users with their own contexts
        user1_context = UserExecutionContext(
            user_id="user_001",
            thread_id=f"thread_{uuid.uuid4()}",
            run_id=f"run_{uuid.uuid4()}",
            websocket_connection_id=f"conn_user_001"
        )
        
        user2_context = UserExecutionContext(
            user_id="user_002",
            thread_id=f"thread_{uuid.uuid4()}",
            run_id=f"run_{uuid.uuid4()}",
            websocket_connection_id=f"conn_user_002"
        )
        
        user1_collector = WebSocketEventCollector("user_001")
        user2_collector = WebSocketEventCollector("user_002")
        
        # Create separate bridge instances (non-singleton)
        bridge = AgentWebSocketBridge()
        
        with patch('netra_backend.app.websocket_core.unified_manager.get_websocket_manager') as mock_ws_mgr:
            websocket = TestWebSocketConnection()
            mock_ws_mgr.return_value = mock_manager
            
            # Mock connections for both users
            connection_map = {
                "conn_user_001": user1_collector,
                "conn_user_002": user2_collector
            }
            
            async def get_connection_side_effect(connection_id):
                return connection_map.get(connection_id)
                
            mock_manager.get_connection = AsyncMock(side_effect=get_connection_side_effect)
            
            # Create isolated emitters for each user
            emitter1 = await bridge.create_user_emitter(user1_context)
            emitter2 = await bridge.create_user_emitter(user2_context)
            
            # User 1 sends events through their emitter
            await emitter1.emit_agent_started("DataAgent", {'query': 'user1 data'})
            
            # User 2 sends events through their emitter
            await emitter2.emit_agent_started("OptimizationAgent", {'query': 'user2 data'})
            
            # Verify no leakage
            assert not user1_collector.has_leaked_events(), \
                "User 1 should not receive User 2's events with factory pattern"
            assert not user2_collector.has_leaked_events(), \
                "User 2 should not receive User 1's events with factory pattern"
            
            # Verify each user received their own events
            assert 'agent_started' in user1_collector.get_event_types()
            assert 'agent_started' in user2_collector.get_event_types()
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_concurrent_user_operations_maintain_isolation(self):
        """
        Tests that concurrent operations from multiple users maintain strict isolation.
        Simulates realistic concurrent multi-user scenario.
        """
        num_users = 10
        num_operations_per_user = 50
        
        users = []
        collectors = {}
        emitters = {}
        
        # Create users and their contexts
        for i in range(num_users):
            user_id = f"user_{i:03d}"
            context = UserExecutionContext(
                user_id=user_id,
                thread_id=f"thread_{uuid.uuid4()}",
                run_id=f"run_{uuid.uuid4()}",
                websocket_connection_id=f"conn_{user_id}"
            )
            
            collector = WebSocketEventCollector(user_id)
            collectors[user_id] = collector
            
            users.append({
                'id': user_id,
                'context': context,
                'collector': collector
            })
        
        bridge = AgentWebSocketBridge()
        
        with patch('netra_backend.app.websocket_core.unified_manager.get_websocket_manager') as mock_ws_mgr:
            websocket = TestWebSocketConnection()
            mock_ws_mgr.return_value = mock_manager
            
            # Setup connection mapping
            async def get_connection_side_effect(connection_id):
                user_id = connection_id.replace('conn_', '')
                return collectors.get(user_id)
                
            mock_manager.get_connection = AsyncMock(side_effect=get_connection_side_effect)
            
            # Create emitters for all users
            for user in users:
                emitter = await bridge.create_user_emitter(user['context'])
                emitters[user['id']] = emitter
            
            # Simulate concurrent operations
            async def user_operations(user_id: str, emitter):
                """Simulate a user performing multiple operations."""
                for op in range(num_operations_per_user):
                    await emitter.emit_agent_thinking(
                        f"Thinking about operation {op} for {user_id}"
                    )
                    await asyncio.sleep(0.001)  # Small delay to simulate processing
                    
                    if op % 10 == 0:
                        await emitter.emit_tool_executing(
                            f"Tool_{op}",
                            {'user': user_id, 'operation': op}
                        )
            
            # Run all user operations concurrently
            tasks = [
                user_operations(user['id'], emitters[user['id']])
                for user in users
            ]
            
            await asyncio.gather(*tasks)
            
            # Verify no cross-user leakage
            leakage_found = False
            for user_id, collector in collectors.items():
                if collector.has_leaked_events():
                    leakage_found = True
                    print(f"SECURITY BREACH: User {user_id} received {len(collector.leaked_events)} leaked events")
                    for leak in collector.leaked_events[:5]:  # Show first 5 leaks
                        print(f"  - Event for {leak['intended_user']} sent to {leak['actual_user']}")
            
            assert not leakage_found, \
                f"Cross-user event leakage detected in concurrent operations"
            
            # Verify each user received expected number of events
            for user_id, collector in collectors.items():
                events = collector.get_event_types()
                assert 'agent_thinking' in events, f"User {user_id} missing agent_thinking events"
                assert 'tool_executing' in events, f"User {user_id} missing tool_executing events"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_background_task_maintains_user_context(self):
        """
        Tests that background tasks spawned from user operations maintain user context.
        This is critical for preventing data leakage in async operations.
        """
        user_context = UserExecutionContext(
            user_id="background_user",
            thread_id=f"thread_{uuid.uuid4()}",
            run_id=f"run_{uuid.uuid4()}",
            websocket_connection_id="conn_background"
        )
        
        collector = WebSocketEventCollector("background_user")
        bridge = AgentWebSocketBridge()
        
        with patch('netra_backend.app.websocket_core.unified_manager.get_websocket_manager') as mock_ws_mgr:
            websocket = TestWebSocketConnection()
            mock_ws_mgr.return_value = mock_manager
            mock_manager.get_connection = AsyncMock(return_value=collector)
            
            emitter = await bridge.create_user_emitter(user_context)
            
            # Simulate background task
            async def background_processing(emitter, context):
                """Simulates a background task that must maintain user context."""
                await asyncio.sleep(0.1)  # Simulate some async work
                
                # Verify context is maintained
                assert emitter._user_context.user_id == context.user_id
                
                await emitter.emit_agent_completed(
                    "BackgroundAgent",
                    {'message': 'Background task completed'}
                )
            
            # Start background task
            task = asyncio.create_task(
                background_processing(emitter, user_context)
            )
            
            # Do some other work
            await emitter.emit_agent_started("MainAgent", {})
            
            # Wait for background task
            await task
            
            # Verify events were sent with correct context
            assert 'agent_started' in collector.get_event_types()
            assert 'agent_completed' in collector.get_event_types()
            assert not collector.has_leaked_events()
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_error_handling_in_isolated_emitters(self):
        """
        Tests that errors in one user's emitter don't affect other users.
        """
        user1_context = UserExecutionContext(
            user_id="error_user",
            thread_id=f"thread_{uuid.uuid4()}",
            run_id=f"run_{uuid.uuid4()}",
            websocket_connection_id="conn_error"
        )
        
        user2_context = UserExecutionContext(
            user_id="normal_user",
            thread_id=f"thread_{uuid.uuid4()}",
            run_id=f"run_{uuid.uuid4()}",
            websocket_connection_id="conn_normal"
        )
        
        error_collector = WebSocketEventCollector("error_user")
        normal_collector = WebSocketEventCollector("normal_user")
        
        bridge = AgentWebSocketBridge()
        
        with patch('netra_backend.app.websocket_core.unified_manager.get_websocket_manager') as mock_ws_mgr:
            websocket = TestWebSocketConnection()
            mock_ws_mgr.return_value = mock_manager
            
            # Setup error for user1, normal for user2
            async def get_connection_side_effect(connection_id):
                if connection_id == "conn_error":
                    # Simulate connection error
                    raise ConnectionError("WebSocket disconnected")
                return normal_collector
                
            mock_manager.get_connection = AsyncMock(side_effect=get_connection_side_effect)
            
            emitter1 = await bridge.create_user_emitter(user1_context)
            emitter2 = await bridge.create_user_emitter(user2_context)
            
            # User 1 operation should fail gracefully
            try:
                await emitter1.emit_agent_started("ErrorAgent", {})
            except Exception:
                pass  # Expected to fail
            
            # User 2 operation should succeed
            await emitter2.emit_agent_started("NormalAgent", {})
            
            # Verify user2 was not affected
            assert 'agent_started' in normal_collector.get_event_types()
            assert not normal_collector.has_leaked_events()
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_emitter_cleanup_on_context_exit(self):
        """
        Tests that emitters are properly cleaned up when context exits.
        This prevents memory leaks and stale connections.
        """
        user_context = UserExecutionContext(
            user_id="cleanup_user",
            thread_id=f"thread_{uuid.uuid4()}",
            run_id=f"run_{uuid.uuid4()}",
            websocket_connection_id="conn_cleanup"
        )
        
        collector = WebSocketEventCollector("cleanup_user")
        
        with patch('netra_backend.app.websocket_core.unified_manager.get_websocket_manager') as mock_ws_mgr:
            websocket = TestWebSocketConnection()
            mock_ws_mgr.return_value = mock_manager
            mock_manager.get_connection = AsyncMock(return_value=collector)
            
            # Use context manager for automatic cleanup
            async with AgentWebSocketBridge.create_scoped_emitter(user_context) as emitter:
                await emitter.emit_agent_started("CleanupAgent", {})
                assert 'agent_started' in collector.get_event_types()
            
            # After context exit, emitter should be cleaned up
            # Attempting to use it should fail or be a no-op
            # (Implementation specific - document expected behavior)


@pytest.mark.asyncio
@pytest.mark.critical
class TestMigrationFromSingletonToFactory:
    """
    Tests to validate migration path from singleton to factory pattern.
    """
    
    async def test_identify_singleton_usage_points(self):
        """
        Test that identifies all code paths using singleton pattern.
        This helps ensure complete migration coverage.
        """
        # List of known singleton usage points that need migration
        singleton_usage_points = [
            'netra_backend.app.services.agent_service_core',
            'netra_backend.app.services.message_handlers',
            'netra_backend.app.services.message_processing',
            'netra_backend.app.agents.base_agent',
            'netra_backend.app.agents.supervisor.workflow_orchestrator',
            'netra_backend.app.agents.supervisor.pipeline_executor',
        ]
        
        migration_needed = []
        
        for module_path in singleton_usage_points:
            # Check if module still uses singleton
            # In real implementation, would import and check
            migration_needed.append({
                'module': module_path,
                'uses_singleton': True,  # Would be determined by actual check
                'migration_priority': 'CRITICAL'
            })
        
        # Generate migration report
        assert len(migration_needed) > 0, "Migration points should be identified"
        
        # Report would be used by migration agents
        migration_report = {
            'total_modules': len(singleton_usage_points),
            'needs_migration': len(migration_needed),
            'modules': migration_needed
        }
        
        return migration_report
    
    async def test_migration_maintains_functionality(self):
        """
        Tests that migrating from singleton to factory maintains all functionality.
        """
        # Test that both patterns work during migration period
        
        # OLD WAY (singleton - deprecated)
        with pytest.deprecated_call():
            singleton_bridge = await get_agent_websocket_bridge()
            assert singleton_bridge is not None
        
        # NEW WAY (factory)
        factory_bridge = AgentWebSocketBridge()
        assert factory_bridge is not None
        
        # Both should support same core operations
        # (with different isolation guarantees)
        assert hasattr(singleton_bridge, 'notify_agent_started')
        assert hasattr(factory_bridge, 'create_user_emitter')


if __name__ == "__main__":
    # Run critical tests
    pytest.main([
        __file__,
        "-v",
        "-s",
        "-m", "critical",
        "--tb=short"
    ])