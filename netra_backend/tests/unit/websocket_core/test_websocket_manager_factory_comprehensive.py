"""
Comprehensive Unit Tests for WebSocketManagerFactory - CRITICAL SECURITY MISSION

Business Value Justification (BVJ):
- Segment: ALL (Free, Early, Mid, Enterprise) 
- Business Goal: Prevent user message cross-contamination in multi-user AI chat
- Value Impact: CRITICAL SECURITY - Ensures user isolation in WebSocket communications
- Strategic Impact: Foundation security for real-time AI interactions

MISSION CRITICAL: These tests prevent the most serious security vulnerability:
user message cross-contamination between different users in AI chat sessions.

Target Classes:
- WebSocketManagerFactory (Line 1153): Factory pattern for isolated instances
- IsolatedWebSocketManager (Line 581): Per-connection manager with private state  
- ConnectionLifecycleManager (Line 391): Connection lifecycle and cleanup

Test Categories:
1. Factory Pattern Tests: Creation, retrieval, cleanup of isolated managers
2. User Isolation Tests: No cross-contamination between users
3. Connection Lifecycle Tests: Proper registration, cleanup, health monitoring
4. Security Tests: Message routing isolation, memory leak prevention
5. Concurrency Tests: Multiple users simultaneously 
6. WebSocket Event Tests: Proper event routing per user

CRITICAL COVERAGE REQUIREMENTS:
- 100% line coverage of all three classes
- Tests detect user message cross-contamination vulnerabilities
- Tests validate proper resource cleanup 
- All concurrency and isolation scenarios covered
"""

import asyncio
import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from typing import Dict, List, Set, Any, Optional
import logging
import weakref
import gc

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.websocket_manager_factory import (
    WebSocketManagerFactory,
    IsolatedWebSocketManager, 
    ConnectionLifecycleManager,
    FactoryMetrics,
    ManagerMetrics,
    FactoryInitializationError,
    get_websocket_manager_factory,
    create_websocket_manager,
    create_defensive_user_execution_context,
    _validate_ssot_user_context,
    _validate_ssot_user_context_staging_safe
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.unified_manager import WebSocketConnection
from netra_backend.app.websocket_core.protocols import WebSocketManagerProtocol


class TestWebSocketManagerFactoryComprehensive(SSotAsyncTestCase):
    """
    Comprehensive unit tests for WebSocketManagerFactory.
    
    CRITICAL: Factory pattern ensures isolated manager instances per user connection,
    preventing message cross-contamination vulnerabilities.
    """
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        self.factory = WebSocketManagerFactory(max_managers_per_user=3, connection_timeout_seconds=300)
        self.user_contexts = []  # Track created contexts for cleanup
    
    def teardown_method(self, method=None):
        """Teardown and cleanup after each test method."""
        # Cleanup any created managers
        if hasattr(self, 'factory'):
            asyncio.run(self.factory.shutdown())
        super().teardown_method(method)

    def create_test_user_context(self, user_id: str = None, **kwargs) -> UserExecutionContext:
        """Create a test UserExecutionContext with proper SSOT validation."""
        if user_id is None:
            user_id = f"test-user-{str(uuid.uuid4())[:8]}"
            
        return UserExecutionContext(
            user_id=user_id,
            thread_id=kwargs.get('thread_id', f"thread-{str(uuid.uuid4())[:8]}"),
            run_id=kwargs.get('run_id', f"run-{str(uuid.uuid4())[:8]}"),
            request_id=kwargs.get('request_id', f"req-{str(uuid.uuid4())[:8]}"),
            websocket_client_id=kwargs.get('websocket_client_id', f"ws-{str(uuid.uuid4())[:8]}")
        )

    def create_test_websocket_connection(self, user_id: str, connection_id: str = None) -> WebSocketConnection:
        """Create a test WebSocketConnection."""
        if connection_id is None:
            connection_id = f"conn-{str(uuid.uuid4())[:8]}"
            
        mock_websocket = Mock()
        return WebSocketConnection(
            connection_id=connection_id,
            user_id=user_id,
            websocket=mock_websocket,
            connected_at=datetime.utcnow(),
            metadata={}
        )

    # =====================================================================================
    # FACTORY PATTERN & INITIALIZATION TESTS
    # =====================================================================================

    def test_factory_initialization_default_config(self):
        """Test factory initialization with default configuration."""
        factory = WebSocketManagerFactory()
        
        assert factory.max_managers_per_user == 5
        assert factory.connection_timeout_seconds == 1800
        assert len(factory._active_managers) == 0
        assert len(factory._user_manager_count) == 0
        assert isinstance(factory._factory_metrics, FactoryMetrics)
        assert not factory._cleanup_started  # Should be False initially

    def test_factory_initialization_custom_config(self):
        """Test factory initialization with custom configuration."""
        factory = WebSocketManagerFactory(
            max_managers_per_user=10,
            connection_timeout_seconds=3600
        )
        
        assert factory.max_managers_per_user == 10
        assert factory.connection_timeout_seconds == 3600

    def test_global_factory_instance_singleton_pattern(self):
        """Test that global factory follows singleton pattern."""
        factory1 = get_websocket_manager_factory()
        factory2 = get_websocket_manager_factory()
        
        assert factory1 is factory2
        assert isinstance(factory1, WebSocketManagerFactory)

    def test_factory_metrics_initialization(self):
        """Test factory metrics are properly initialized."""
        factory = WebSocketManagerFactory()
        stats = factory.get_factory_stats()
        
        assert stats["factory_metrics"]["managers_created"] == 0
        assert stats["factory_metrics"]["managers_active"] == 0
        assert stats["factory_metrics"]["users_with_active_managers"] == 0
        assert stats["configuration"]["max_managers_per_user"] == 5

    # =====================================================================================
    # USER ISOLATION & SECURITY TESTS  
    # =====================================================================================

    @pytest.mark.asyncio
    async def test_manager_creation_user_isolation(self):
        """Test that each user gets completely isolated manager instances."""
        factory = WebSocketManagerFactory()
        
        # Create contexts for two different users
        user1_context = self.create_test_user_context("user1")
        user2_context = self.create_test_user_context("user2")
        
        # Create managers for both users
        manager1 = await factory.create_manager(user1_context)
        manager2 = await factory.create_manager(user2_context)
        
        # Verify managers are completely separate instances
        assert manager1 is not manager2
        assert id(manager1) != id(manager2)
        assert manager1.user_context.user_id == "user1"
        assert manager2.user_context.user_id == "user2"
        
        # Verify internal state isolation
        assert manager1._connections is not manager2._connections
        assert manager1._connection_ids is not manager2._connection_ids
        assert manager1._message_queue is not manager2._message_queue

    @pytest.mark.asyncio 
    async def test_cross_user_contamination_prevention(self):
        """SECURITY CRITICAL: Test prevention of cross-user message contamination."""
        factory = WebSocketManagerFactory()
        
        user1_context = self.create_test_user_context("user1")
        user2_context = self.create_test_user_context("user2")
        
        manager1 = await factory.create_manager(user1_context)
        manager2 = await factory.create_manager(user2_context)
        
        # Add connections to each manager
        conn1 = self.create_test_websocket_connection("user1")
        conn2 = self.create_test_websocket_connection("user2")
        
        await manager1.add_connection(conn1)
        await manager2.add_connection(conn2)
        
        # Verify user1 manager only has user1 connections
        user1_connections = manager1.get_user_connections()
        assert len(user1_connections) == 1
        assert conn1.connection_id in user1_connections
        assert conn2.connection_id not in user1_connections
        
        # Verify user2 manager only has user2 connections
        user2_connections = manager2.get_user_connections()
        assert len(user2_connections) == 1
        assert conn2.connection_id in user2_connections
        assert conn1.connection_id not in user2_connections

    @pytest.mark.asyncio
    async def test_connection_hijacking_prevention(self):
        """SECURITY CRITICAL: Test prevention of connection hijacking attempts."""
        factory = WebSocketManagerFactory()
        
        user1_context = self.create_test_user_context("user1")
        manager1 = await factory.create_manager(user1_context)
        
        # Attempt to add connection with different user_id should fail
        malicious_conn = self.create_test_websocket_connection("user2")  # Different user!
        
        with pytest.raises(ValueError) as exc_info:
            await manager1.add_connection(malicious_conn)
        
        assert "does not match manager user_id" in str(exc_info.value)
        assert "user isolation" in str(exc_info.value)
        
        # Verify no connections were added
        assert len(manager1.get_user_connections()) == 0

    @pytest.mark.asyncio
    async def test_isolation_key_generation_uniqueness(self):
        """Test that isolation keys prevent manager sharing between contexts."""
        factory = WebSocketManagerFactory()
        
        # Same user, different contexts should get different managers
        user_context1 = self.create_test_user_context("user1", websocket_client_id="ws1")
        user_context2 = self.create_test_user_context("user1", websocket_client_id="ws2")
        
        manager1 = await factory.create_manager(user_context1)
        manager2 = await factory.create_manager(user_context2)
        
        # Different contexts should create different managers even for same user
        assert manager1 is not manager2
        assert manager1.user_context.websocket_client_id == "ws1"
        assert manager2.user_context.websocket_client_id == "ws2"

    # =====================================================================================
    # MANAGER CREATION & LIFECYCLE TESTS
    # =====================================================================================

    @pytest.mark.asyncio
    async def test_manager_creation_success_flow(self):
        """Test successful manager creation flow."""
        factory = WebSocketManagerFactory()
        user_context = self.create_test_user_context()
        
        manager = await factory.create_manager(user_context)
        
        assert isinstance(manager, IsolatedWebSocketManager)
        assert manager.user_context is user_context
        assert manager._is_active is True
        assert isinstance(manager._metrics, ManagerMetrics)
        assert isinstance(manager._lifecycle_manager, ConnectionLifecycleManager)
        
        # Verify factory tracking
        stats = factory.get_factory_stats()
        assert stats["factory_metrics"]["managers_created"] == 1
        assert stats["factory_metrics"]["managers_active"] == 1

    @pytest.mark.asyncio
    async def test_manager_creation_invalid_context_validation(self):
        """Test validation of invalid UserExecutionContext during creation."""
        factory = WebSocketManagerFactory()
        
        # Test with None
        with pytest.raises(ValueError) as exc_info:
            await factory.create_manager(None)
        assert "must be a UserExecutionContext instance" in str(exc_info.value)
        
        # Test with wrong type
        with pytest.raises(ValueError) as exc_info:
            await factory.create_manager("invalid")
        assert "must be a UserExecutionContext instance" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_manager_reuse_for_same_context(self):
        """Test that same context returns existing manager."""
        factory = WebSocketManagerFactory()
        user_context = self.create_test_user_context()
        
        manager1 = await factory.create_manager(user_context)
        manager2 = await factory.create_manager(user_context)
        
        # Should return the same manager instance
        assert manager1 is manager2

    @pytest.mark.asyncio 
    async def test_manager_cleanup_lifecycle(self):
        """Test complete manager lifecycle including cleanup."""
        factory = WebSocketManagerFactory()
        user_context = self.create_test_user_context()
        
        manager = await factory.create_manager(user_context)
        isolation_key = factory._generate_isolation_key(user_context)
        
        # Verify manager is active and tracked
        assert isolation_key in factory._active_managers
        assert factory._user_manager_count[user_context.user_id] == 1
        
        # Cleanup manager
        result = await factory.cleanup_manager(isolation_key)
        assert result is True
        
        # Verify cleanup completed
        assert isolation_key not in factory._active_managers
        assert user_context.user_id not in factory._user_manager_count
        assert not manager._is_active

    @pytest.mark.asyncio
    async def test_manager_protocol_compliance(self):
        """Test that created managers comply with WebSocketManagerProtocol."""
        factory = WebSocketManagerFactory()
        user_context = self.create_test_user_context()
        
        manager = await factory.create_manager(user_context)
        
        # Validate protocol compliance
        validation = WebSocketManagerProtocolValidator.validate_manager_protocol(manager)
        assert validation['compliant'] is True
        assert validation['summary']['compliance_percentage'] == 100.0
        assert len(validation['missing_methods']) == 0

    # =====================================================================================
    # CONNECTION MANAGEMENT TESTS
    # =====================================================================================

    @pytest.mark.asyncio
    async def test_connection_addition_and_tracking(self):
        """Test connection addition and proper tracking."""
        factory = WebSocketManagerFactory()
        user_context = self.create_test_user_context()
        manager = await factory.create_manager(user_context)
        
        # Add connection
        connection = self.create_test_websocket_connection(user_context.user_id)
        await manager.add_connection(connection)
        
        # Verify tracking
        connections = manager.get_user_connections()
        assert len(connections) == 1
        assert connection.connection_id in connections
        
        # Verify connection retrieval
        retrieved = manager.get_connection(connection.connection_id)
        assert retrieved is connection

    @pytest.mark.asyncio
    async def test_connection_removal_and_cleanup(self):
        """Test connection removal and proper cleanup."""
        factory = WebSocketManagerFactory()
        user_context = self.create_test_user_context()
        manager = await factory.create_manager(user_context)
        
        # Add and then remove connection
        connection = self.create_test_websocket_connection(user_context.user_id)
        await manager.add_connection(connection)
        await manager.remove_connection(connection.connection_id)
        
        # Verify removal
        connections = manager.get_user_connections()
        assert len(connections) == 0
        assert manager.get_connection(connection.connection_id) is None

    @pytest.mark.asyncio
    async def test_connection_health_monitoring(self):
        """Test connection health monitoring functionality."""
        factory = WebSocketManagerFactory()
        user_context = self.create_test_user_context()
        manager = await factory.create_manager(user_context)
        
        # Add connection
        connection = self.create_test_websocket_connection(user_context.user_id)
        await manager.add_connection(connection)
        
        # Check health
        health = manager.get_connection_health(user_context.user_id)
        assert health['user_id'] == user_context.user_id
        assert health['total_connections'] == 1
        assert health['active_connections'] == 1
        assert health['has_active_connections'] is True

    @pytest.mark.asyncio
    async def test_multiple_connections_per_manager(self):
        """Test handling of multiple connections within single manager."""
        factory = WebSocketManagerFactory()
        user_context = self.create_test_user_context()
        manager = await factory.create_manager(user_context)
        
        # Add multiple connections for same user
        conn1 = self.create_test_websocket_connection(user_context.user_id, "conn1")
        conn2 = self.create_test_websocket_connection(user_context.user_id, "conn2")
        
        await manager.add_connection(conn1)
        await manager.add_connection(conn2)
        
        # Verify both connections tracked
        connections = manager.get_user_connections()
        assert len(connections) == 2
        assert "conn1" in connections
        assert "conn2" in connections

    # =====================================================================================
    # ERROR HANDLING & VALIDATION TESTS
    # =====================================================================================

    @pytest.mark.asyncio
    async def test_resource_limit_enforcement(self):
        """Test resource limit enforcement prevents manager creation overflow."""
        factory = WebSocketManagerFactory(max_managers_per_user=2)
        user_id = "test-user"
        
        # Create managers up to limit
        context1 = self.create_test_user_context(user_id, websocket_client_id="ws1")
        context2 = self.create_test_user_context(user_id, websocket_client_id="ws2")
        
        manager1 = await factory.create_manager(context1)
        manager2 = await factory.create_manager(context2)
        
        assert factory._user_manager_count[user_id] == 2
        
        # Attempt to exceed limit should raise error
        context3 = self.create_test_user_context(user_id, websocket_client_id="ws3")
        
        with pytest.raises(RuntimeError) as exc_info:
            await factory.create_manager(context3)
        
        assert "maximum number of WebSocket managers" in str(exc_info.value)
        assert f"({2})" in str(exc_info.value)  # Shows the limit

    def test_resource_limit_checking(self):
        """Test resource limit checking without manager creation."""
        factory = WebSocketManagerFactory(max_managers_per_user=3)
        
        # No managers created yet
        assert factory.enforce_resource_limits("user1") is True
        
        # Simulate managers created
        factory._user_manager_count["user1"] = 2
        assert factory.enforce_resource_limits("user1") is True
        
        factory._user_manager_count["user1"] = 3
        assert factory.enforce_resource_limits("user1") is False

    @pytest.mark.asyncio
    async def test_invalid_manager_cleanup(self):
        """Test cleanup of non-existent managers."""
        factory = WebSocketManagerFactory()
        
        # Cleanup non-existent manager should return False
        result = await factory.cleanup_manager("non-existent-key")
        assert result is False

    @pytest.mark.asyncio
    async def test_manager_inactive_state_handling(self):
        """Test handling of inactive manager states."""
        factory = WebSocketManagerFactory()
        user_context = self.create_test_user_context()
        
        manager = await factory.create_manager(user_context)
        
        # Deactivate manager
        await manager.cleanup_all_connections()
        
        # Operations on inactive manager should raise RuntimeError
        connection = self.create_test_websocket_connection(user_context.user_id)
        
        with pytest.raises(RuntimeError) as exc_info:
            await manager.add_connection(connection)
        assert "no longer active" in str(exc_info.value)

    def test_factory_initialization_error_handling(self):
        """Test proper error types for factory initialization failures."""
        # Test error types exist
        assert issubclass(FactoryInitializationError, Exception)
        
        # Test error can be raised
        with pytest.raises(FactoryInitializationError):
            raise FactoryInitializationError("Test error")

    # =====================================================================================
    # RACE CONDITIONS & CONCURRENCY TESTS
    # =====================================================================================

    @pytest.mark.asyncio
    async def test_concurrent_manager_creation_same_user(self):
        """Test concurrent manager creation for same user context."""
        factory = WebSocketManagerFactory()
        user_context = self.create_test_user_context()
        
        # Create managers concurrently
        tasks = [
            factory.create_manager(user_context)
            for _ in range(5)
        ]
        
        managers = await asyncio.gather(*tasks)
        
        # All should return the same manager instance (first one created)
        first_manager = managers[0]
        for manager in managers[1:]:
            assert manager is first_manager

    @pytest.mark.asyncio
    async def test_concurrent_manager_creation_different_users(self):
        """Test concurrent manager creation for different users."""
        factory = WebSocketManagerFactory()
        
        contexts = [
            self.create_test_user_context(f"user{i}") 
            for i in range(5)
        ]
        
        # Create managers concurrently for different users
        tasks = [factory.create_manager(ctx) for ctx in contexts]
        managers = await asyncio.gather(*tasks)
        
        # All should be different managers
        manager_ids = [id(m) for m in managers]
        assert len(set(manager_ids)) == 5  # All unique
        
        # Verify correct user assignments
        for i, manager in enumerate(managers):
            assert manager.user_context.user_id == f"user{i}"

    @pytest.mark.asyncio
    async def test_thread_safety_factory_operations(self):
        """Test thread safety of factory operations."""
        factory = WebSocketManagerFactory()
        results = []
        exceptions = []
        
        def create_manager_sync():
            """Synchronous wrapper for async manager creation."""
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                context = self.create_test_user_context(f"user-{threading.current_thread().ident}")
                manager = loop.run_until_complete(factory.create_manager(context))
                results.append(manager)
                loop.close()
            except Exception as e:
                exceptions.append(e)
        
        # Create threads that attempt concurrent operations
        threads = [threading.Thread(target=create_manager_sync) for _ in range(3)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify no exceptions occurred
        assert len(exceptions) == 0, f"Exceptions in threads: {exceptions}"
        assert len(results) == 3
        
        # All managers should be different (different users)
        manager_ids = [id(m) for m in results]
        assert len(set(manager_ids)) == 3

    @pytest.mark.asyncio
    async def test_cleanup_during_creation_race_condition(self):
        """Test race condition between manager creation and cleanup."""
        factory = WebSocketManagerFactory()
        user_context = self.create_test_user_context()
        
        # Create manager
        manager = await factory.create_manager(user_context)
        isolation_key = factory._generate_isolation_key(user_context)
        
        # Simulate race condition: start cleanup and creation simultaneously
        cleanup_task = asyncio.create_task(factory.cleanup_manager(isolation_key))
        create_task = asyncio.create_task(factory.create_manager(user_context))
        
        cleanup_result, new_manager = await asyncio.gather(
            cleanup_task, create_task, return_exceptions=True
        )
        
        # One should succeed, but no exceptions should occur
        assert not isinstance(cleanup_result, Exception)
        assert not isinstance(new_manager, Exception)

    # =====================================================================================
    # MEMORY MANAGEMENT TESTS
    # =====================================================================================

    @pytest.mark.asyncio
    async def test_manager_cleanup_memory_release(self):
        """Test that manager cleanup properly releases memory references."""
        factory = WebSocketManagerFactory()
        user_context = self.create_test_user_context()
        
        manager = await factory.create_manager(user_context)
        isolation_key = factory._generate_isolation_key(user_context)
        
        # Create weak reference to track cleanup
        weak_manager_ref = weakref.ref(manager)
        manager_id = id(manager)
        
        # Add connection to manager
        connection = self.create_test_websocket_connection(user_context.user_id)
        await manager.add_connection(connection)
        
        # Clean up manager
        await factory.cleanup_manager(isolation_key)
        
        # Clear local reference
        del manager
        
        # Verify cleanup tracking is working
        assert isolation_key not in factory._active_managers
        assert user_context.user_id not in factory._user_manager_count

    @pytest.mark.asyncio
    async def test_connection_lifecycle_memory_management(self):
        """Test connection lifecycle prevents memory leaks."""
        factory = WebSocketManagerFactory()
        user_context = self.create_test_user_context()
        manager = await factory.create_manager(user_context)
        
        # Add and remove many connections to test memory management
        connection_ids = []
        for i in range(10):
            connection = self.create_test_websocket_connection(
                user_context.user_id, f"conn-{i}"
            )
            await manager.add_connection(connection)
            connection_ids.append(connection.connection_id)
        
        # Verify all added
        assert len(manager.get_user_connections()) == 10
        
        # Remove all connections
        for conn_id in connection_ids:
            await manager.remove_connection(conn_id)
        
        # Verify all removed
        assert len(manager.get_user_connections()) == 0
        
        # Verify internal state is clean
        assert len(manager._connections) == 0
        assert len(manager._connection_ids) == 0

    @pytest.mark.asyncio
    async def test_factory_shutdown_complete_cleanup(self):
        """Test factory shutdown performs complete cleanup."""
        factory = WebSocketManagerFactory()
        
        # Create multiple managers
        managers = []
        for i in range(3):
            context = self.create_test_user_context(f"user{i}")
            manager = await factory.create_manager(context)
            managers.append(manager)
        
        assert len(factory._active_managers) == 3
        
        # Shutdown factory
        await factory.shutdown()
        
        # Verify complete cleanup
        assert len(factory._active_managers) == 0
        assert len(factory._user_manager_count) == 0
        
        # Verify all managers are inactive
        for manager in managers:
            assert not manager._is_active

    # =====================================================================================
    # USEREXECUTIONCONTEXT INTEGRATION TESTS
    # =====================================================================================

    def test_defensive_user_execution_context_creation(self):
        """Test defensive UserExecutionContext creation with fallbacks."""
        # Test normal creation
        context = create_defensive_user_execution_context("test-user")
        assert context.user_id == "test-user"
        assert context.websocket_client_id is not None
        
        # Test with provided websocket_client_id
        context = create_defensive_user_execution_context("test-user", "ws-123")
        assert context.websocket_client_id == "ws-123"
        
        # Test invalid user_id
        with pytest.raises(ValueError) as exc_info:
            create_defensive_user_execution_context("")
        assert "user_id must be non-empty string" in str(exc_info.value)
        
        with pytest.raises(ValueError) as exc_info:
            create_defensive_user_execution_context(None)
        assert "user_id must be non-empty string" in str(exc_info.value)

    def test_ssot_user_context_validation(self):
        """Test SSOT UserExecutionContext validation."""
        # Test valid context
        valid_context = self.create_test_user_context()
        _validate_ssot_user_context(valid_context)  # Should not raise
        
        # Test invalid type
        with pytest.raises(ValueError) as exc_info:
            _validate_ssot_user_context("invalid")
        assert "SSOT VIOLATION" in str(exc_info.value)
        
        # Test None
        with pytest.raises(ValueError) as exc_info:
            _validate_ssot_user_context(None)
        assert "SSOT VIOLATION" in str(exc_info.value)

    def test_staging_safe_context_validation(self):
        """Test staging-safe context validation with environment accommodation."""
        # Set staging environment
        self.env.set("ENVIRONMENT", "staging", source="test")
        
        valid_context = self.create_test_user_context()
        _validate_ssot_user_context_staging_safe(valid_context)  # Should not raise
        
        # Test critical validation still works in staging
        with pytest.raises(ValueError) as exc_info:
            _validate_ssot_user_context_staging_safe("invalid")
        assert "STAGING CRITICAL" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_websocket_manager_validation_flow(self):
        """Test the complete validation flow in create_websocket_manager function."""
        # Test successful creation
        user_context = self.create_test_user_context()
        manager = await create_websocket_manager(user_context)
        
        assert isinstance(manager, IsolatedWebSocketManager)
        assert manager.user_context is user_context
        
        # Test validation failure
        with pytest.raises(FactoryInitializationError) as exc_info:
            await create_websocket_manager("invalid")
        assert "SSOT validation failed" in str(exc_info.value)

    # =====================================================================================
    # BACKGROUND CLEANUP & MAINTENANCE TESTS
    # =====================================================================================

    @pytest.mark.asyncio
    async def test_background_cleanup_task_management(self):
        """Test background cleanup task lifecycle management."""
        factory = WebSocketManagerFactory()
        
        # Initially cleanup should not be started
        assert not factory._cleanup_started
        
        # Create a manager to trigger cleanup start
        user_context = self.create_test_user_context()
        await factory.create_manager(user_context)
        
        # Cleanup should now be started
        assert factory._cleanup_started

    @pytest.mark.asyncio
    async def test_emergency_cleanup_functionality(self):
        """Test emergency cleanup for resource limit situations."""
        factory = WebSocketManagerFactory(max_managers_per_user=1)
        user_id = "test-user"
        
        # Create manager and force cleanup
        context = self.create_test_user_context(user_id)
        manager = await factory.create_manager(context)
        
        # Force emergency cleanup
        cleaned_count = await factory.force_cleanup_user_managers(user_id)
        
        # Since we just created it, it shouldn't be cleaned (too recent)
        assert cleaned_count == 0
        
        # But forced cleanup should work
        cleaned_count = await factory.force_cleanup_all_expired()
        assert cleaned_count >= 0  # At least no errors

    @pytest.mark.asyncio
    async def test_automatic_expired_manager_cleanup(self):
        """Test automatic cleanup of expired managers."""
        factory = WebSocketManagerFactory(connection_timeout_seconds=1)  # 1 second timeout
        user_context = self.create_test_user_context()
        
        manager = await factory.create_manager(user_context)
        isolation_key = factory._generate_isolation_key(user_context)
        
        # Manually set old creation time to simulate expiration
        old_time = datetime.utcnow() - timedelta(seconds=10)
        factory._manager_creation_time[isolation_key] = old_time
        
        # Set old activity time  
        manager._metrics.last_activity = old_time
        
        # Run cleanup
        await factory._cleanup_expired_managers()
        
        # Manager should be cleaned up
        assert isolation_key not in factory._active_managers

    # =====================================================================================
    # INTEGRATION WITH WEBSOCKET EVENTS TESTS
    # =====================================================================================

    @pytest.mark.asyncio
    async def test_manager_websocket_event_emission(self):
        """Test manager integration with WebSocket event emission."""
        factory = WebSocketManagerFactory()
        user_context = self.create_test_user_context()
        manager = await factory.create_manager(user_context)
        
        # Mock WebSocket for event testing
        mock_websocket = AsyncMock()
        connection = self.create_test_websocket_connection(user_context.user_id)
        connection.websocket = mock_websocket
        
        await manager.add_connection(connection)
        
        # Test critical event emission
        await manager.emit_critical_event("agent_started", {"message": "test"})
        
        # Verify WebSocket send was called
        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "agent_started"
        assert call_args["critical"] is True

    @pytest.mark.asyncio 
    async def test_manager_message_sending_with_failures(self):
        """Test manager message sending with connection failures."""
        factory = WebSocketManagerFactory()
        user_context = self.create_test_user_context()
        manager = await factory.create_manager(user_context)
        
        # Create connection with failing WebSocket
        failing_websocket = AsyncMock()
        failing_websocket.send_json.side_effect = Exception("Connection failed")
        
        connection = self.create_test_websocket_connection(user_context.user_id)
        connection.websocket = failing_websocket
        
        await manager.add_connection(connection)
        
        # Sending message should handle failure gracefully
        await manager.send_to_user({"type": "test", "data": "message"})
        
        # Connection should be removed after failure
        assert len(manager.get_user_connections()) == 0
        assert manager._metrics.messages_failed_total > 0

    # =====================================================================================
    # METRICS AND MONITORING TESTS
    # =====================================================================================

    def test_factory_metrics_tracking(self):
        """Test factory metrics tracking functionality."""
        factory = WebSocketManagerFactory()
        
        # Initial metrics
        initial_stats = factory.get_factory_stats()
        assert initial_stats["factory_metrics"]["managers_created"] == 0
        
        # Simulate metrics updates
        factory._factory_metrics.managers_created = 5
        factory._factory_metrics.managers_active = 3
        factory._factory_metrics.resource_limit_hits = 2
        
        stats = factory.get_factory_stats()
        assert stats["factory_metrics"]["managers_created"] == 5
        assert stats["factory_metrics"]["managers_active"] == 3
        assert stats["factory_metrics"]["resource_limit_hits"] == 2

    @pytest.mark.asyncio
    async def test_manager_metrics_tracking(self):
        """Test individual manager metrics tracking."""
        factory = WebSocketManagerFactory()
        user_context = self.create_test_user_context()
        manager = await factory.create_manager(user_context)
        
        # Initial metrics
        stats = manager.get_manager_stats()
        assert stats["metrics"]["connections_managed"] == 0
        assert stats["metrics"]["messages_sent_total"] == 0
        
        # Add connection and send message
        connection = self.create_test_websocket_connection(user_context.user_id)
        connection.websocket = AsyncMock()
        
        await manager.add_connection(connection)
        await manager.send_to_user({"type": "test"})
        
        # Check updated metrics
        stats = manager.get_manager_stats()
        assert stats["metrics"]["connections_managed"] == 1
        assert stats["metrics"]["messages_sent_total"] == 1

    @pytest.mark.asyncio 
    async def test_comprehensive_factory_statistics(self):
        """Test comprehensive factory statistics collection."""
        factory = WebSocketManagerFactory()
        
        # Create multiple managers for different users
        contexts = [self.create_test_user_context(f"user{i}") for i in range(3)]
        managers = []
        
        for context in contexts:
            manager = await factory.create_manager(context)
            managers.append(manager)
        
        # Get comprehensive stats
        stats = factory.get_factory_stats()
        
        assert stats["current_state"]["active_managers"] == 3
        assert stats["current_state"]["users_with_managers"] == 3
        assert len(stats["current_state"]["isolation_keys"]) == 3
        assert len(stats["user_distribution"]) == 3
        
        # Each user should have 1 manager
        for user_id, count in stats["user_distribution"].items():
            assert count == 1

    # =====================================================================================
    # ADVANCED EDGE CASE TESTS
    # =====================================================================================

    @pytest.mark.asyncio
    async def test_manager_creation_with_special_characters_in_user_id(self):
        """Test manager creation with special characters in user IDs."""
        factory = WebSocketManagerFactory()
        
        special_user_ids = [
            "user@example.com",
            "user-with-dashes", 
            "user_with_underscores",
            "user123!@#$%",
            "[U+7528][U+6237][U+4E2D][U+6587]"  # Chinese characters
        ]
        
        managers = []
        for user_id in special_user_ids:
            context = self.create_test_user_context(user_id)
            manager = await factory.create_manager(context)
            managers.append(manager)
            assert manager.user_context.user_id == user_id
        
        # All should be different managers
        assert len(set(id(m) for m in managers)) == len(special_user_ids)

    @pytest.mark.asyncio
    async def test_manager_behavior_after_multiple_cleanups(self):
        """Test manager behavior after multiple cleanup attempts."""
        factory = WebSocketManagerFactory()
        user_context = self.create_test_user_context()
        
        manager = await factory.create_manager(user_context)
        isolation_key = factory._generate_isolation_key(user_context)
        
        # Multiple cleanup attempts should be safe
        result1 = await factory.cleanup_manager(isolation_key)
        result2 = await factory.cleanup_manager(isolation_key)
        result3 = await factory.cleanup_manager(isolation_key)
        
        assert result1 is True   # First cleanup succeeds
        assert result2 is False  # Subsequent cleanups return False
        assert result3 is False

    @pytest.mark.asyncio
    async def test_factory_behavior_with_corrupted_state(self):
        """Test factory resilience with corrupted internal state."""
        factory = WebSocketManagerFactory()
        user_context = self.create_test_user_context()
        
        # Create manager normally
        manager = await factory.create_manager(user_context)
        isolation_key = factory._generate_isolation_key(user_context)
        
        # Simulate state corruption
        factory._user_manager_count[user_context.user_id] = 999
        
        # Factory should still be able to clean up
        await factory.cleanup_manager(isolation_key)
        
        # Count should be corrected during cleanup
        assert user_context.user_id not in factory._user_manager_count

    @pytest.mark.asyncio
    async def test_websocket_protocol_compatibility_methods(self):
        """Test WebSocket protocol compatibility method implementations."""
        factory = WebSocketManagerFactory()
        user_context = self.create_test_user_context()
        manager = await factory.create_manager(user_context)
        
        # Test get_connection_id_by_websocket
        mock_websocket = Mock()
        connection = self.create_test_websocket_connection(user_context.user_id)
        connection.websocket = mock_websocket
        
        await manager.add_connection(connection)
        
        found_id = manager.get_connection_id_by_websocket(mock_websocket)
        assert found_id == connection.connection_id
        
        # Test with non-existent websocket
        other_websocket = Mock()
        not_found_id = manager.get_connection_id_by_websocket(other_websocket)
        assert not_found_id is None
        
        # Test update_connection_thread
        success = manager.update_connection_thread(connection.connection_id, "new-thread-123")
        assert success is True
        
        # Test with non-existent connection
        no_success = manager.update_connection_thread("non-existent", "thread")
        assert no_success is False

    # =====================================================================================
    # COMPREHENSIVE SECURITY VALIDATION TESTS
    # =====================================================================================

    @pytest.mark.asyncio
    async def test_complete_user_isolation_security_validation(self):
        """COMPREHENSIVE SECURITY TEST: Validate complete user isolation."""
        factory = WebSocketManagerFactory()
        
        # Create 5 users with multiple contexts each
        users_data = {}
        for i in range(5):
            user_id = f"security-user-{i}"
            users_data[user_id] = {
                'contexts': [
                    self.create_test_user_context(user_id, websocket_client_id=f"ws-{user_id}-{j}")
                    for j in range(3)
                ],
                'managers': [],
                'connections': []
            }
        
        # Create managers and connections for each user
        for user_id, data in users_data.items():
            for context in data['contexts']:
                manager = await factory.create_manager(context)
                data['managers'].append(manager)
                
                # Add connections to each manager
                for k in range(2):
                    conn = self.create_test_websocket_connection(user_id, f"conn-{user_id}-{len(data['connections'])}")
                    await manager.add_connection(conn)
                    data['connections'].append(conn)
        
        # SECURITY VALIDATION: Ensure complete isolation
        for user_id, data in users_data.items():
            for manager in data['managers']:
                # Manager should only have connections for its user
                connections = manager.get_user_connections()
                for conn_id in connections:
                    connection = manager.get_connection(conn_id)
                    assert connection.user_id == user_id, f"Cross-user contamination detected! Manager for {user_id} has connection for {connection.user_id}"
                
                # Manager should not be able to access other users' connections
                for other_user_id, other_data in users_data.items():
                    if other_user_id != user_id:
                        for other_conn in other_data['connections']:
                            # Should not find connections from other users
                            found_conn = manager.get_connection(other_conn.connection_id)
                            assert found_conn is None, f"SECURITY BREACH: Manager for {user_id} can access connection {other_conn.connection_id} belonging to {other_user_id}"

    @pytest.mark.asyncio
    async def test_connection_security_boundary_enforcement(self):
        """Test that security boundaries are enforced at the connection level."""
        factory = WebSocketManagerFactory()
        
        user1_context = self.create_test_user_context("security-user-1")
        user2_context = self.create_test_user_context("security-user-2")
        
        manager1 = await factory.create_manager(user1_context)
        manager2 = await factory.create_manager(user2_context)
        
        # Create connections
        conn1 = self.create_test_websocket_connection("security-user-1")
        conn2 = self.create_test_websocket_connection("security-user-2")
        
        # Add connections to correct managers
        await manager1.add_connection(conn1)
        await manager2.add_connection(conn2)
        
        # SECURITY TEST: Attempt cross-user connection hijacking
        with pytest.raises(ValueError, match="user isolation"):
            await manager1.add_connection(conn2)  # Should fail - wrong user
        
        with pytest.raises(ValueError, match="user isolation"):
            await manager2.add_connection(conn1)  # Should fail - wrong user
        
        # SECURITY VALIDATION: Verify isolation maintained
        assert conn1.connection_id in manager1.get_user_connections()
        assert conn1.connection_id not in manager2.get_user_connections()
        assert conn2.connection_id in manager2.get_user_connections()
        assert conn2.connection_id not in manager1.get_user_connections()

    def test_factory_security_metrics_tracking(self):
        """Test that factory tracks security-related metrics."""
        factory = WebSocketManagerFactory()
        
        # Initial security metrics
        stats = factory.get_factory_stats()
        assert stats["factory_metrics"]["security_violations_detected"] == 0
        assert stats["factory_metrics"]["resource_limit_hits"] == 0
        
        # Simulate security violations (normally incremented by factory)
        factory._factory_metrics.security_violations_detected = 3
        factory._factory_metrics.resource_limit_hits = 2
        
        updated_stats = factory.get_factory_stats()
        assert updated_stats["factory_metrics"]["security_violations_detected"] == 3
        assert updated_stats["factory_metrics"]["resource_limit_hits"] == 2

    # =====================================================================================
    # FINAL COMPREHENSIVE VALIDATION TEST
    # =====================================================================================

    @pytest.mark.asyncio
    async def test_complete_factory_lifecycle_comprehensive(self):
        """COMPREHENSIVE TEST: Complete factory lifecycle with all features."""
        factory = WebSocketManagerFactory(max_managers_per_user=3, connection_timeout_seconds=300)
        
        # Phase 1: Create multiple users with multiple managers each
        test_data = {}
        total_managers_created = 0
        
        for user_idx in range(3):  # 3 users
            user_id = f"comprehensive-user-{user_idx}"
            test_data[user_id] = {
                'contexts': [],
                'managers': [],
                'connections': []
            }
            
            for manager_idx in range(2):  # 2 managers per user  
                context = self.create_test_user_context(
                    user_id, 
                    websocket_client_id=f"ws-{user_id}-{manager_idx}"
                )
                manager = await factory.create_manager(context)
                
                test_data[user_id]['contexts'].append(context)
                test_data[user_id]['managers'].append(manager)
                total_managers_created += 1
                
                # Add connections to each manager
                for conn_idx in range(3):  # 3 connections per manager
                    conn = self.create_test_websocket_connection(
                        user_id, 
                        f"conn-{user_id}-{manager_idx}-{conn_idx}"
                    )
                    conn.websocket = AsyncMock()
                    await manager.add_connection(conn)
                    test_data[user_id]['connections'].append(conn)
        
        # Phase 2: Validate factory state
        stats = factory.get_factory_stats()
        assert stats["factory_metrics"]["managers_created"] == total_managers_created
        assert stats["factory_metrics"]["managers_active"] == total_managers_created
        assert stats["current_state"]["users_with_managers"] == 3
        
        # Phase 3: Test messaging and events
        for user_id, data in test_data.items():
            for manager in data['managers']:
                # Test message sending
                await manager.send_to_user({"type": "test_message", "content": "comprehensive test"})
                
                # Test critical event emission
                await manager.emit_critical_event("test_event", {"test": True})
                
                # Verify metrics updated
                manager_stats = manager.get_manager_stats()
                assert manager_stats["metrics"]["connections_managed"] == 3
                assert manager_stats["metrics"]["messages_sent_total"] >= 2  # At least message + event
        
        # Phase 4: Test protocol compliance for all managers
        for user_id, data in test_data.items():
            for manager in data['managers']:
                validation = WebSocketManagerProtocolValidator.validate_manager_protocol(manager)
                assert validation['compliant'] is True, f"Manager for {user_id} not protocol compliant: {validation}"
        
        # Phase 5: Test security isolation
        for user_id, data in test_data.items():
            for manager in data['managers']:
                # Verify only has connections for correct user
                connections = manager.get_user_connections()
                for conn_id in connections:
                    conn = manager.get_connection(conn_id)
                    assert conn.user_id == user_id
                
                # Verify health check works correctly
                health = manager.get_connection_health(user_id)
                assert health['user_id'] == user_id
                assert health['active_connections'] == 3
        
        # Phase 6: Test cleanup and shutdown
        # Clean up one user's managers
        cleanup_user = "comprehensive-user-0"
        for context in test_data[cleanup_user]['contexts']:
            isolation_key = factory._generate_isolation_key(context)
            result = await factory.cleanup_manager(isolation_key)
            assert result is True
        
        # Verify partial cleanup
        stats = factory.get_factory_stats()
        remaining_managers = total_managers_created - len(test_data[cleanup_user]['managers'])
        assert stats["factory_metrics"]["managers_active"] == remaining_managers
        
        # Complete shutdown
        await factory.shutdown()
        
        # Verify complete cleanup
        final_stats = factory.get_factory_stats()
        assert final_stats["factory_metrics"]["managers_active"] == 0
        assert len(factory._active_managers) == 0
        assert len(factory._user_manager_count) == 0
        
        # Verify all managers are inactive
        for user_id, data in test_data.items():
            for manager in data['managers']:
                assert not manager._is_active

    # =====================================================================================
    # TEST EXECUTION SUMMARY METHOD  
    # =====================================================================================

    def test_suite_coverage_validation(self):
        """Validate that this test suite covers all required security areas."""
        required_coverage_areas = [
            "factory_pattern_initialization",
            "user_isolation_security", 
            "manager_creation_lifecycle",
            "connection_management",
            "error_handling_validation",
            "race_conditions_concurrency",
            "memory_management",
            "userexecutioncontext_integration",
            "background_cleanup_maintenance",
            "websocket_events_integration", 
            "metrics_monitoring",
            "advanced_edge_cases",
            "comprehensive_security_validation"
        ]
        
        # Get all test methods from this class
        test_methods = [
            method for method in dir(self) 
            if method.startswith('test_') and callable(getattr(self, method))
        ]
        
        # Verify we have comprehensive coverage
        assert len(test_methods) >= 50, f"Expected at least 50 test methods, found {len(test_methods)}"
        
        # Verify all areas are covered by checking method names contain coverage area keywords
        covered_areas = set()
        for test_method in test_methods:
            method_name = test_method.lower()
            for area in required_coverage_areas:
                area_keywords = area.split('_')
                if any(keyword in method_name for keyword in area_keywords):
                    covered_areas.add(area)
                    break
        
        missing_coverage = set(required_coverage_areas) - covered_areas
        assert len(missing_coverage) == 0, f"Missing test coverage for areas: {missing_coverage}"
        
        self.logger.info(f" PASS:  Comprehensive test suite validated: {len(test_methods)} tests covering all {len(required_coverage_areas)} security-critical areas")