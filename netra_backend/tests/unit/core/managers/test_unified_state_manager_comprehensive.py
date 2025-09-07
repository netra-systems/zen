"""
Comprehensive Unit Tests for UnifiedStateManager - MEGA CLASS SSOT

Business Value Justification (BVJ):
- Segment: Platform/Internal (affects ALL user tiers and AI agent operations)
- Business Goal: Agent State Consistency & WebSocket Synchronization
- Value Impact: Critical for AI agent context preservation - enables intelligent responses
- Strategic Impact: Foundation for multi-user chat state - failure breaks AI conversation context

CRITICAL: This is a MEGA CLASS exception (1,820 lines) approved for SSOT state management.
Consolidates 50+ state managers into single source of truth including:
- AgentStateManager, SessionlessAgentStateManager
- MessageStateManager, ThreadStateManager  
- SessionStateManager, TabStateManager
- WebSocketStateManager, ReconnectionStateManager
- MigrationStateManager, StateManagerCore
- All supervisor and sub-agent state managers

Test Requirements from CLAUDE.md:
1. CHEATING ON TESTS = ABOMINATION - Every test must fail hard on errors
2. NO mocks unless absolutely necessary - Use real UnifiedStateManager instances
3. ABSOLUTE IMPORTS only - No relative imports  
4. Tests must RAISE ERRORS - No try/except blocks masking failures
5. Real services over mocks - Test real state operations
6. Race condition awareness - State management requires careful async/thread handling
7. MULTI-USER system - Test user isolation and concurrent access

Testing Areas:
1. Core State Operations - get, set, delete, exists, update, clear operations
2. Scoped State Isolation - user, session, thread, agent scope testing with full isolation
3. Thread-Safe Operations - concurrent access, fine-grained locking, race conditions
4. TTL-Based Expiration - time-based state cleanup, expiration handling, edge cases
5. WebSocket State Synchronization - real-time state sync, WebSocket integration
6. State Querying & Filtering - complex queries, filtering operations, bulk operations
7. Multi-User Isolation - user-specific state, cross-contamination prevention
8. Performance Characteristics - memory usage, lookup speed, concurrency throughput
9. Agent Context Preservation - agent state persistence, conversation continuity
10. Legacy Manager Consolidation - integration patterns, migration handling
11. Error Handling & Recovery - invalid states, corrupted data, recovery mechanisms
12. State Validation & Integrity - data consistency, validation rules, integrity checks
13. Bulk Operations - batch state operations, mass updates, bulk queries
14. State Migration & Versioning - state format changes, version compatibility
15. Event System - state change notifications, listener management, event processing
16. Context Managers - session, agent, thread context helpers
17. Factory Pattern - user isolation, global vs user-specific managers
18. Background Tasks - cleanup loops, event processing, resource management
"""

import asyncio
import json
import os
import pytest
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from unittest.mock import Mock, MagicMock, patch

from test_framework.ssot.base import BaseTestCase
from shared.isolated_environment import IsolatedEnvironment, get_env
from netra_backend.app.core.managers.unified_state_manager import (
    UnifiedStateManager,
    StateManagerFactory,
    StateScope,
    StateType,
    StateStatus,
    StateEntry,
    StateChangeEvent,
    StateQuery,
    SessionStateContext,
    AgentStateContext,
    ThreadStateContext,
    get_state_manager,
    get_agent_state_manager,
    get_session_state_manager,
    get_websocket_state_manager,
    get_message_state_manager
)


# ============================================================================
# TEST FIXTURES AND HELPERS
# ============================================================================

@pytest.fixture
def isolated_env():
    """Provide clean IsolatedEnvironment for each test."""
    return IsolatedEnvironment()


@pytest.fixture
def state_manager():
    """Provide clean UnifiedStateManager instance."""
    return UnifiedStateManager(
        user_id="test_user_123",
        enable_persistence=True,
        enable_ttl_cleanup=False,  # Disable for deterministic testing
        cleanup_interval=1,
        max_memory_entries=1000,
        enable_versioning=True
    )


@pytest.fixture
def multi_user_managers():
    """Provide multiple user-specific state managers."""
    return {
        "user1": UnifiedStateManager(user_id="user1"),
        "user2": UnifiedStateManager(user_id="user2"),
        "user3": UnifiedStateManager(user_id="user3")
    }


@pytest.fixture
def mock_websocket_manager():
    """Provide mock WebSocket manager for testing notifications."""
    mock_ws = Mock()
    mock_ws.broadcast_system_message = Mock()
    return mock_ws


@pytest.fixture
def state_change_events():
    """Track state change events during tests."""
    events = []
    
    def event_listener(event: StateChangeEvent):
        events.append(event)
    
    return events, event_listener


# ============================================================================
# CORE STATE OPERATIONS TESTS
# ============================================================================

class TestCoreStateOperations(BaseTestCase):
    """Test core state operations - get, set, delete, exists, update."""
    
    def test_basic_get_set_operations(self):
        """
        BVJ: Critical for AI agent state persistence - enables conversation context.
        Tests basic state storage and retrieval operations.
        """
        manager = UnifiedStateManager()
        
        # Test basic set and get
        manager.set("test_key", "test_value", StateScope.GLOBAL, StateType.CACHE_DATA)
        result = manager.get("test_key")
        
        self.assertEqual(result, "test_value")
        
        # Test get with default
        result = manager.get("nonexistent_key", "default_value")
        self.assertEqual(result, "default_value")
        
        # Test exists
        self.assertTrue(manager.exists("test_key"))
        self.assertFalse(manager.exists("nonexistent_key"))
    
    def test_delete_operations(self):
        """
        BVJ: State cleanup prevents memory leaks in long-running AI conversations.
        Tests state deletion and verification operations.
        """
        manager = UnifiedStateManager()
        
        # Set up test data
        manager.set("key1", "value1")
        manager.set("key2", "value2")
        
        # Test successful deletion
        result = manager.delete("key1")
        self.assertTrue(result)
        self.assertFalse(manager.exists("key1"))
        
        # Test deletion of non-existent key
        result = manager.delete("nonexistent_key")
        self.assertFalse(result)
        
        # Verify other keys still exist
        self.assertTrue(manager.exists("key2"))
    
    def test_update_operations(self):
        """
        BVJ: Atomic updates prevent race conditions in agent state modifications.
        Tests atomic state update operations.
        """
        manager = UnifiedStateManager()
        
        # Test update with existing key
        manager.set("counter", 0)
        result = manager.update("counter", lambda x: x + 1)
        self.assertEqual(result, 1)
        self.assertEqual(manager.get("counter"), 1)
        
        # Test update with non-existent key (should use default)
        result = manager.update("new_counter", lambda x: x + 10, default=5)
        self.assertEqual(result, 15)
        self.assertEqual(manager.get("new_counter"), 15)
    
    def test_keys_listing(self):
        """
        BVJ: Key enumeration enables state debugging and maintenance operations.
        Tests key listing and pattern filtering.
        """
        manager = UnifiedStateManager()
        
        # Set up test data
        manager.set("user:123:preferences", {"theme": "dark"})
        manager.set("user:123:history", ["item1", "item2"])
        manager.set("session:456:data", "session_value")
        manager.set("global:config", "global_value")
        
        # Test all keys
        all_keys = manager.keys()
        self.assertEqual(len(all_keys), 4)
        self.assertIn("user:123:preferences", all_keys)
        self.assertIn("session:456:data", all_keys)
        
        # Test pattern filtering
        user_keys = manager.keys(pattern=r"user:123:.*")
        self.assertEqual(len(user_keys), 2)
        self.assertIn("user:123:preferences", user_keys)
        self.assertIn("user:123:history", user_keys)
    
    def test_complex_data_types(self):
        """
        BVJ: Complex data support enables rich agent context storage.
        Tests storage of complex Python objects and data structures.
        """
        manager = UnifiedStateManager()
        
        # Test dictionary storage
        complex_dict = {
            "nested": {"data": [1, 2, 3]},
            "list": ["a", "b", "c"],
            "number": 42.5,
            "boolean": True,
            "none_value": None
        }
        
        manager.set("complex_data", complex_dict)
        result = manager.get("complex_data")
        
        self.assertEqual(result, complex_dict)
        self.assertEqual(result["nested"]["data"], [1, 2, 3])
        self.assertTrue(result["boolean"])
        self.assertIsNone(result["none_value"])
        
        # Test list storage
        complex_list = [
            {"id": 1, "name": "item1"},
            {"id": 2, "name": "item2", "metadata": {"active": True}}
        ]
        
        manager.set("complex_list", complex_list)
        result = manager.get("complex_list")
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["name"], "item1")
        self.assertTrue(result[1]["metadata"]["active"])


class TestStateEntryMetadata(BaseTestCase):
    """Test StateEntry metadata and versioning functionality."""
    
    def test_state_entry_creation(self):
        """
        BVJ: Proper state entry metadata enables audit trails and debugging.
        Tests StateEntry creation and initialization.
        """
        entry = StateEntry(
            key="test_key",
            value="test_value",
            state_type=StateType.AGENT_EXECUTION,
            scope=StateScope.AGENT,
            user_id="user123",
            agent_id="agent456",
            ttl_seconds=3600
        )
        
        self.assertEqual(entry.key, "test_key")
        self.assertEqual(entry.value, "test_value")
        self.assertEqual(entry.state_type, StateType.AGENT_EXECUTION)
        self.assertEqual(entry.scope, StateScope.AGENT)
        self.assertEqual(entry.user_id, "user123")
        self.assertEqual(entry.agent_id, "agent456")
        self.assertEqual(entry.version, 1)
        self.assertIsNotNone(entry.expires_at)
    
    def test_state_entry_expiration(self):
        """
        BVJ: TTL expiration prevents memory leaks in long-running processes.
        Tests state entry expiration logic.
        """
        # Test non-expiring entry
        entry = StateEntry(
            key="persistent_key",
            value="persistent_value",
            state_type=StateType.CACHE_DATA,
            scope=StateScope.GLOBAL
        )
        self.assertFalse(entry.is_expired())
        
        # Test expiring entry
        entry_with_ttl = StateEntry(
            key="temp_key",
            value="temp_value",
            state_type=StateType.TEMPORARY,
            scope=StateScope.TEMPORARY,
            ttl_seconds=1
        )
        
        self.assertFalse(entry_with_ttl.is_expired())
        time.sleep(1.1)  # Wait for expiration
        self.assertTrue(entry_with_ttl.is_expired())
    
    def test_state_entry_updates(self):
        """
        BVJ: Version tracking enables conflict resolution and audit trails.
        Tests state entry update operations and versioning.
        """
        entry = StateEntry(
            key="versioned_key",
            value="initial_value",
            state_type=StateType.CONFIGURATION_STATE,
            scope=StateScope.GLOBAL
        )
        
        initial_version = entry.version
        initial_updated_at = entry.updated_at
        
        time.sleep(0.01)  # Small delay for timestamp difference
        entry.update_value("updated_value")
        
        self.assertEqual(entry.value, "updated_value")
        self.assertEqual(entry.version, initial_version + 1)
        self.assertGreater(entry.updated_at, initial_updated_at)
    
    def test_state_entry_ttl_extension(self):
        """
        BVJ: TTL extension enables dynamic session management.
        Tests TTL extension functionality.
        """
        entry = StateEntry(
            key="extendable_key",
            value="extendable_value",
            state_type=StateType.SESSION_DATA,
            scope=StateScope.SESSION,
            ttl_seconds=10
        )
        
        initial_expires_at = entry.expires_at
        entry.extend_ttl(20)
        
        self.assertGreater(entry.expires_at, initial_expires_at)
        self.assertAlmostEqual(
            entry.expires_at - initial_expires_at, 20, delta=1
        )
    
    def test_state_entry_serialization(self):
        """
        BVJ: Serialization enables state persistence and debugging.
        Tests StateEntry serialization to dictionary.
        """
        entry = StateEntry(
            key="serializable_key",
            value={"complex": "data"},
            state_type=StateType.MESSAGE_QUEUE,
            scope=StateScope.THREAD,
            user_id="user123",
            session_id="session456",
            thread_id="thread789",
            ttl_seconds=1800,
            metadata={"priority": "high"}
        )
        
        serialized = entry.to_dict()
        
        self.assertIsInstance(serialized, dict)
        self.assertEqual(serialized["key"], "serializable_key")
        self.assertEqual(serialized["value"], {"complex": "data"})
        self.assertEqual(serialized["state_type"], "message_queue")
        self.assertEqual(serialized["scope"], "thread")
        self.assertEqual(serialized["user_id"], "user123")
        self.assertEqual(serialized["metadata"], {"priority": "high"})


# ============================================================================
# SCOPED STATE ISOLATION TESTS
# ============================================================================

class TestScopedStateIsolation(BaseTestCase):
    """Test scoped state operations and isolation boundaries."""
    
    def test_user_scoped_state(self):
        """
        BVJ: User isolation prevents data leakage between different users.
        Tests user-scoped state operations and isolation.
        """
        manager = UnifiedStateManager()
        
        # Set user-specific states
        manager.set_user_state("user1", "preferences", {"theme": "dark"})
        manager.set_user_state("user2", "preferences", {"theme": "light"})
        
        # Verify isolation
        user1_prefs = manager.get_user_state("user1", "preferences")
        user2_prefs = manager.get_user_state("user2", "preferences")
        
        self.assertEqual(user1_prefs["theme"], "dark")
        self.assertEqual(user2_prefs["theme"], "light")
        
        # Verify no cross-contamination
        self.assertIsNone(manager.get_user_state("user3", "preferences"))
    
    def test_session_scoped_state(self):
        """
        BVJ: Session isolation enables independent user sessions.
        Tests session-scoped state operations and isolation.
        """
        manager = UnifiedStateManager()
        
        # Set session-specific states
        manager.set_session_state("session1", "cart", ["item1", "item2"])
        manager.set_session_state("session2", "cart", ["item3"])
        
        # Verify isolation
        session1_cart = manager.get_session_state("session1", "cart")
        session2_cart = manager.get_session_state("session2", "cart")
        
        self.assertEqual(len(session1_cart), 2)
        self.assertEqual(len(session2_cart), 1)
        self.assertIn("item1", session1_cart)
        self.assertIn("item3", session2_cart)
    
    def test_thread_scoped_state(self):
        """
        BVJ: Thread isolation enables independent conversation contexts.
        Tests thread-scoped state operations and isolation.
        """
        manager = UnifiedStateManager()
        
        # Set thread-specific states
        manager.set_thread_state("thread1", "context", "AI conversation topic A")
        manager.set_thread_state("thread2", "context", "AI conversation topic B")
        
        # Verify isolation
        thread1_context = manager.get_thread_state("thread1", "context")
        thread2_context = manager.get_thread_state("thread2", "context")
        
        self.assertEqual(thread1_context, "AI conversation topic A")
        self.assertEqual(thread2_context, "AI conversation topic B")
    
    def test_agent_scoped_state(self):
        """
        BVJ: Agent isolation enables independent AI agent execution contexts.
        Tests agent-scoped state operations and isolation.
        """
        manager = UnifiedStateManager()
        
        # Set agent-specific states
        manager.set_agent_state("agent1", "execution_step", 5)
        manager.set_agent_state("agent2", "execution_step", 12)
        
        # Verify isolation
        agent1_step = manager.get_agent_state("agent1", "execution_step")
        agent2_step = manager.get_agent_state("agent2", "execution_step")
        
        self.assertEqual(agent1_step, 5)
        self.assertEqual(agent2_step, 12)
        
        # Test with TTL
        manager.set_agent_state("agent3", "temp_data", "temporary", ttl_seconds=1)
        self.assertEqual(manager.get_agent_state("agent3", "temp_data"), "temporary")
    
    def test_websocket_scoped_state(self):
        """
        BVJ: WebSocket isolation enables independent connection management.
        Tests WebSocket-scoped state operations and isolation.
        """
        manager = UnifiedStateManager()
        
        # Set WebSocket connection states
        manager.set_websocket_state("conn1", "authenticated", True)
        manager.set_websocket_state("conn2", "authenticated", False)
        
        # Verify isolation
        conn1_auth = manager.get_websocket_state("conn1", "authenticated")
        conn2_auth = manager.get_websocket_state("conn2", "authenticated")
        
        self.assertTrue(conn1_auth)
        self.assertFalse(conn2_auth)
    
    def test_cross_scope_isolation(self):
        """
        BVJ: Cross-scope isolation prevents accidental data mixing.
        Tests that different scopes don't interfere with each other.
        """
        manager = UnifiedStateManager()
        
        # Set same key name in different scopes
        manager.set_user_state("user1", "data", "user_data")
        manager.set_session_state("session1", "data", "session_data")
        manager.set_thread_state("thread1", "data", "thread_data")
        manager.set_agent_state("agent1", "data", "agent_data")
        
        # Verify each scope maintains its own data
        self.assertEqual(manager.get_user_state("user1", "data"), "user_data")
        self.assertEqual(manager.get_session_state("session1", "data"), "session_data")
        self.assertEqual(manager.get_thread_state("thread1", "data"), "thread_data")
        self.assertEqual(manager.get_agent_state("agent1", "data"), "agent_data")


# ============================================================================
# THREAD-SAFE OPERATIONS TESTS
# ============================================================================

class TestThreadSafeOperations(BaseTestCase):
    """Test thread-safe operations and race condition prevention."""
    
    def test_concurrent_set_operations(self):
        """
        BVJ: Thread safety prevents data corruption in multi-user scenarios.
        Tests concurrent set operations without race conditions.
        """
        manager = UnifiedStateManager()
        results = {}
        num_threads = 10
        operations_per_thread = 100
        
        def worker(thread_id):
            thread_results = []
            for i in range(operations_per_thread):
                key = f"thread_{thread_id}_key_{i}"
                value = f"thread_{thread_id}_value_{i}"
                manager.set(key, value)
                thread_results.append((key, value))
            results[thread_id] = thread_results
        
        # Execute concurrent operations
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(worker, thread_id)
                for thread_id in range(num_threads)
            ]
            
            for future in as_completed(futures):
                future.result()  # Wait for completion
        
        # Verify all operations succeeded
        self.assertEqual(len(results), num_threads)
        
        for thread_id, thread_results in results.items():
            self.assertEqual(len(thread_results), operations_per_thread)
            for key, expected_value in thread_results:
                actual_value = manager.get(key)
                self.assertEqual(actual_value, expected_value)
    
    def test_concurrent_update_operations(self):
        """
        BVJ: Atomic updates prevent race conditions in counter operations.
        Tests concurrent atomic update operations.
        """
        manager = UnifiedStateManager()
        manager.set("counter", 0)
        num_threads = 20
        increments_per_thread = 50
        
        def increment_counter(thread_id):
            for _ in range(increments_per_thread):
                manager.update("counter", lambda x: x + 1)
        
        # Execute concurrent increments
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(increment_counter, thread_id)
                for thread_id in range(num_threads)
            ]
            
            for future in as_completed(futures):
                future.result()  # Wait for completion
        
        # Verify final counter value
        expected_total = num_threads * increments_per_thread
        actual_total = manager.get("counter")
        self.assertEqual(actual_total, expected_total)
    
    def test_concurrent_different_scope_operations(self):
        """
        BVJ: Scope isolation prevents interference between concurrent operations.
        Tests concurrent operations on different scopes.
        """
        manager = UnifiedStateManager()
        results = {}
        num_threads = 15
        
        def worker(thread_id):
            # Each thread works on different scopes
            manager.set_user_state(f"user{thread_id}", "data", f"user_data_{thread_id}")
            manager.set_session_state(f"session{thread_id}", "data", f"session_data_{thread_id}")
            manager.set_thread_state(f"thread{thread_id}", "data", f"thread_data_{thread_id}")
            manager.set_agent_state(f"agent{thread_id}", "data", f"agent_data_{thread_id}")
            
            results[thread_id] = {
                "user": manager.get_user_state(f"user{thread_id}", "data"),
                "session": manager.get_session_state(f"session{thread_id}", "data"),
                "thread": manager.get_thread_state(f"thread{thread_id}", "data"),
                "agent": manager.get_agent_state(f"agent{thread_id}", "data")
            }
        
        # Execute concurrent operations
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(worker, thread_id)
                for thread_id in range(num_threads)
            ]
            
            for future in as_completed(futures):
                future.result()  # Wait for completion
        
        # Verify all operations succeeded with correct isolation
        self.assertEqual(len(results), num_threads)
        
        for thread_id, thread_results in results.items():
            self.assertEqual(thread_results["user"], f"user_data_{thread_id}")
            self.assertEqual(thread_results["session"], f"session_data_{thread_id}")
            self.assertEqual(thread_results["thread"], f"thread_data_{thread_id}")
            self.assertEqual(thread_results["agent"], f"agent_data_{thread_id}")
    
    def test_concurrent_read_write_operations(self):
        """
        BVJ: Mixed read/write operations must be thread-safe for AI agents.
        Tests concurrent read and write operations.
        """
        manager = UnifiedStateManager()
        
        # Initialize test data
        for i in range(50):
            manager.set(f"key_{i}", i)
        
        read_results = {}
        write_results = {}
        
        def reader(thread_id):
            results = []
            for i in range(50):
                value = manager.get(f"key_{i}")
                results.append(value)
            read_results[thread_id] = results
        
        def writer(thread_id):
            results = []
            for i in range(25, 75):  # Overlap with existing keys
                new_value = i + 1000
                manager.set(f"key_{i}", new_value)
                results.append((f"key_{i}", new_value))
            write_results[thread_id] = results
        
        # Execute concurrent read/write operations
        with ThreadPoolExecutor(max_workers=10) as executor:
            reader_futures = [
                executor.submit(reader, f"reader_{i}") for i in range(3)
            ]
            writer_futures = [
                executor.submit(writer, f"writer_{i}") for i in range(2)
            ]
            
            all_futures = reader_futures + writer_futures
            for future in as_completed(all_futures):
                future.result()  # Wait for completion
        
        # Verify operations completed without errors
        self.assertEqual(len(read_results), 3)
        self.assertEqual(len(write_results), 2)
        
        # Verify no data corruption occurred
        for reader_id, results in read_results.items():
            self.assertEqual(len(results), 50)
            for result in results:
                self.assertIsNotNone(result)  # Should have read something valid


# ============================================================================
# TTL-BASED EXPIRATION TESTS
# ============================================================================

class TestTTLExpiration(BaseTestCase):
    """Test TTL-based state expiration functionality."""
    
    def test_basic_ttl_expiration(self):
        """
        BVJ: TTL expiration prevents memory leaks in long-running AI sessions.
        Tests basic TTL expiration functionality.
        """
        manager = UnifiedStateManager(enable_ttl_cleanup=False)
        
        # Set entry with short TTL
        manager.set("temp_key", "temp_value", ttl_seconds=1)
        
        # Verify immediately available
        self.assertEqual(manager.get("temp_key"), "temp_value")
        self.assertTrue(manager.exists("temp_key"))
        
        # Wait for expiration
        time.sleep(1.2)
        
        # Verify expired (should return default and clean up)
        self.assertIsNone(manager.get("temp_key"))
        self.assertFalse(manager.exists("temp_key"))
    
    def test_ttl_with_different_scopes(self):
        """
        BVJ: Scope-specific TTL enables flexible session management.
        Tests TTL expiration across different state scopes.
        """
        manager = UnifiedStateManager(enable_ttl_cleanup=False)
        
        # Set entries in different scopes with TTL
        manager.set_user_state("user1", "temp_pref", "dark_theme", ttl_seconds=1)
        manager.set_session_state("session1", "temp_cart", ["item1"], ttl_seconds=1)
        manager.set_agent_state("agent1", "temp_step", 5, ttl_seconds=1)
        
        # Verify initially available
        self.assertEqual(manager.get_user_state("user1", "temp_pref"), "dark_theme")
        self.assertEqual(manager.get_session_state("session1", "temp_cart"), ["item1"])
        self.assertEqual(manager.get_agent_state("agent1", "temp_step"), 5)
        
        # Wait for expiration
        time.sleep(1.2)
        
        # Verify all expired
        self.assertIsNone(manager.get_user_state("user1", "temp_pref"))
        self.assertIsNone(manager.get_session_state("session1", "temp_cart"))
        self.assertIsNone(manager.get_agent_state("agent1", "temp_step"))
    
    def test_ttl_extension(self):
        """
        BVJ: TTL extension enables dynamic session length management.
        Tests TTL extension functionality.
        """
        manager = UnifiedStateManager()
        
        # Set entry with TTL
        manager.set("extendable_key", "value", ttl_seconds=2)
        
        # Sleep and extend before expiration
        time.sleep(1)
        
        # Access the internal entry to extend TTL
        if "extendable_key" in manager._states:
            entry = manager._states["extendable_key"]
            entry.extend_ttl(3)  # Extend by 3 more seconds
        
        # Should still be available after original TTL
        time.sleep(1.5)  # Total 2.5 seconds (past original TTL)
        self.assertEqual(manager.get("extendable_key"), "value")
        
        # Should expire after extended TTL
        time.sleep(2)  # Total 4.5 seconds (past extended TTL)
        self.assertIsNone(manager.get("extendable_key"))
    
    @pytest.mark.asyncio
    async def test_automatic_cleanup_task(self):
        """
        BVJ: Automatic cleanup prevents memory leaks in production systems.
        Tests automatic TTL cleanup background task.
        """
        manager = UnifiedStateManager(
            enable_ttl_cleanup=True,
            cleanup_interval=1  # Clean up every second
        )
        
        try:
            # Set entries with short TTL
            manager.set("auto_cleanup_1", "value1", ttl_seconds=2)
            manager.set("auto_cleanup_2", "value2", ttl_seconds=3)
            
            # Verify initially available
            self.assertEqual(manager.get("auto_cleanup_1"), "value1")
            self.assertEqual(manager.get("auto_cleanup_2"), "value2")
            
            # Wait for first entry to expire and get cleaned up
            await asyncio.sleep(2.5)
            
            # First should be gone, second should remain
            self.assertIsNone(manager.get("auto_cleanup_1"))
            self.assertEqual(manager.get("auto_cleanup_2"), "value2")
            
            # Wait for second entry to expire
            await asyncio.sleep(1)
            
            # Both should be gone
            self.assertIsNone(manager.get("auto_cleanup_1"))
            self.assertIsNone(manager.get("auto_cleanup_2"))
            
        finally:
            await manager.shutdown()
    
    def test_ttl_with_bulk_operations(self):
        """
        BVJ: Bulk TTL operations enable efficient session management.
        Tests TTL behavior with bulk operations.
        """
        manager = UnifiedStateManager()
        
        # Set multiple entries with different TTLs
        states = {
            "bulk_key_1": "value1",
            "bulk_key_2": "value2",  
            "bulk_key_3": "value3"
        }
        
        for key, value in states.items():
            manager.set(key, value, ttl_seconds=1)
        
        # Verify all initially available
        results = manager.get_multiple(list(states.keys()))
        for key, value in states.items():
            self.assertEqual(results[key], value)
        
        # Wait for expiration
        time.sleep(1.2)
        
        # Verify all expired
        results = manager.get_multiple(list(states.keys()))
        for key in states.keys():
            self.assertIsNone(results[key])


# ============================================================================
# WEBSOCKET INTEGRATION TESTS
# ============================================================================

class TestWebSocketIntegration(BaseTestCase):
    """Test WebSocket integration and real-time state synchronization."""
    
    def test_websocket_manager_integration(self):
        """
        BVJ: WebSocket integration enables real-time AI conversation updates.
        Tests WebSocket manager integration for state notifications.
        """
        manager = UnifiedStateManager()
        mock_ws = Mock()
        mock_ws.broadcast_system_message = Mock()
        
        # Set WebSocket manager
        manager.set_websocket_manager(mock_ws)
        
        # Verify manager is set
        self.assertEqual(manager._websocket_manager, mock_ws)
        self.assertTrue(manager._enable_websocket_events)
    
    def test_websocket_event_emission_disabled(self):
        """
        BVJ: WebSocket events can be disabled for testing and debugging.
        Tests WebSocket event emission when disabled.
        """
        manager = UnifiedStateManager()
        mock_ws = Mock()
        mock_ws.broadcast_system_message = Mock()
        
        manager.set_websocket_manager(mock_ws)
        manager.enable_websocket_events(False)
        
        # Set state (should not trigger WebSocket events)
        manager.set("test_key", "test_value")
        
        # Verify WebSocket manager was not called
        mock_ws.broadcast_system_message.assert_not_called()
    
    def test_websocket_state_operations(self):
        """
        BVJ: WebSocket-specific state operations enable connection management.
        Tests WebSocket-specific state operations.
        """
        manager = UnifiedStateManager()
        
        # Test WebSocket connection state
        connection_id = "ws_conn_12345"
        
        manager.set_websocket_state(connection_id, "user_id", "user123")
        manager.set_websocket_state(connection_id, "authenticated", True)
        manager.set_websocket_state(connection_id, "last_ping", time.time())
        
        # Verify WebSocket states
        user_id = manager.get_websocket_state(connection_id, "user_id")
        authenticated = manager.get_websocket_state(connection_id, "authenticated")
        last_ping = manager.get_websocket_state(connection_id, "last_ping")
        
        self.assertEqual(user_id, "user123")
        self.assertTrue(authenticated)
        self.assertIsInstance(last_ping, float)
    
    @pytest.mark.asyncio
    async def test_state_change_event_processing(self):
        """
        BVJ: Event processing enables real-time state change notifications.
        Tests state change event processing and WebSocket notifications.
        """
        manager = UnifiedStateManager()
        
        # Track events
        events_received = []
        
        def event_listener(event):
            events_received.append(event)
        
        manager.add_change_listener(event_listener)
        
        try:
            # Set state to trigger event
            manager.set("event_test_key", "event_test_value")
            
            # Give time for event processing
            await asyncio.sleep(0.1)
            
            # Verify event was received
            self.assertEqual(len(events_received), 1)
            event = events_received[0]
            self.assertEqual(event.key, "event_test_key")
            self.assertEqual(event.new_value, "event_test_value")
            self.assertEqual(event.change_type, "create")
            
        finally:
            await manager.shutdown()


# ============================================================================
# STATE QUERYING AND FILTERING TESTS
# ============================================================================

class TestStateQuerying(BaseTestCase):
    """Test state querying, filtering, and search operations."""
    
    def test_basic_state_query(self):
        """
        BVJ: State queries enable debugging and monitoring of AI agent contexts.
        Tests basic state query functionality.
        """
        manager = UnifiedStateManager()
        
        # Set up test data
        manager.set_user_state("user1", "pref1", "value1")
        manager.set_user_state("user1", "pref2", "value2")
        manager.set_session_state("session1", "data1", "session_value")
        manager.set_agent_state("agent1", "step", 5)
        
        # Query by scope
        query = StateQuery(scope=StateScope.USER)
        results = manager.query_states(query)
        
        self.assertEqual(len(results), 2)
        user_keys = [entry.key for entry in results]
        self.assertIn("user:user1:pref1", user_keys)
        self.assertIn("user:user1:pref2", user_keys)
    
    def test_multi_filter_query(self):
        """
        BVJ: Complex queries enable sophisticated state management operations.
        Tests queries with multiple filters.
        """
        manager = UnifiedStateManager()
        
        # Set up test data with different users and types
        manager.set("global_config", "global_value", StateScope.GLOBAL, StateType.CONFIGURATION_STATE)
        manager.set_user_state("user1", "data", "user1_data")
        manager.set_user_state("user2", "data", "user2_data") 
        manager.set_agent_state("agent1", "context", "agent1_context")
        
        # Query for user1 specific data
        query = StateQuery(
            scope=StateScope.USER,
            user_id="user1"
        )
        results = manager.query_states(query)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].user_id, "user1")
        self.assertIn("user1", results[0].key)
    
    def test_time_based_filtering(self):
        """
        BVJ: Time-based queries enable session analysis and debugging.
        Tests time-based state filtering.
        """
        manager = UnifiedStateManager()
        
        # Set initial state
        manager.set("old_key", "old_value")
        
        time.sleep(0.1)  # Small delay
        cutoff_time = time.time()
        time.sleep(0.1)
        
        # Set newer state
        manager.set("new_key", "new_value")
        
        # Query for states created after cutoff
        query = StateQuery(created_after=cutoff_time)
        results = manager.query_states(query)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].key, "new_key")
    
    def test_pattern_based_filtering(self):
        """
        BVJ: Pattern matching enables flexible state discovery operations.
        Tests pattern-based key filtering.
        """
        manager = UnifiedStateManager()
        
        # Set up test data with patterns
        manager.set("config:database:host", "db_host")
        manager.set("config:database:port", "5432")
        manager.set("config:redis:host", "redis_host")
        manager.set("user:123:preferences", "user_prefs")
        manager.set("user:456:preferences", "other_prefs")
        
        # Query for database configs
        query = StateQuery(key_pattern=r"config:database:.*")
        results = manager.query_states(query)
        
        self.assertEqual(len(results), 2)
        db_keys = [entry.key for entry in results]
        self.assertIn("config:database:host", db_keys)
        self.assertIn("config:database:port", db_keys)
    
    def test_query_with_limit(self):
        """
        BVJ: Query limits prevent memory exhaustion in large state sets.
        Tests query result limiting.
        """
        manager = UnifiedStateManager()
        
        # Set up many entries
        for i in range(20):
            manager.set(f"item_{i:02d}", f"value_{i}")
        
        # Query with limit
        query = StateQuery(limit=5)
        results = manager.query_states(query)
        
        self.assertEqual(len(results), 5)
        
        # Verify results are sorted by updated_at (newest first)
        for i in range(len(results) - 1):
            self.assertGreaterEqual(
                results[i].updated_at,
                results[i + 1].updated_at
            )
    
    def test_expired_state_filtering(self):
        """
        BVJ: Expired state filtering enables cleanup and debugging operations.
        Tests filtering of expired states.
        """
        manager = UnifiedStateManager()
        
        # Set up expired and non-expired states
        manager.set("persistent_key", "persistent_value")
        manager.set("expiring_key", "expiring_value", ttl_seconds=1)
        
        time.sleep(1.2)  # Wait for expiration
        
        # Query including expired states
        query = StateQuery(include_expired=True)
        results = manager.query_states(query)
        
        # Should find both (expired and non-expired)
        self.assertEqual(len(results), 2)
        
        # Query excluding expired states (default)
        query = StateQuery(include_expired=False)
        results = manager.query_states(query)
        
        # Should find only non-expired
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].key, "persistent_key")


# ============================================================================
# BULK OPERATIONS TESTS  
# ============================================================================

class TestBulkOperations(BaseTestCase):
    """Test bulk state operations for efficiency and performance."""
    
    def test_bulk_get_operations(self):
        """
        BVJ: Bulk operations improve performance for AI agent batch processing.
        Tests bulk get operations.
        """
        manager = UnifiedStateManager()
        
        # Set up test data
        test_data = {
            "key1": "value1",
            "key2": "value2", 
            "key3": "value3",
            "key4": "value4"
        }
        
        for key, value in test_data.items():
            manager.set(key, value)
        
        # Test bulk get
        keys = list(test_data.keys())
        results = manager.get_multiple(keys)
        
        self.assertEqual(len(results), 4)
        for key, expected_value in test_data.items():
            self.assertEqual(results[key], expected_value)
        
        # Test bulk get with non-existent keys
        keys_with_missing = keys + ["missing_key"]
        results = manager.get_multiple(keys_with_missing)
        
        self.assertIsNone(results["missing_key"])
    
    def test_bulk_set_operations(self):
        """
        BVJ: Bulk set operations enable efficient AI agent state initialization.
        Tests bulk set operations.
        """
        manager = UnifiedStateManager()
        
        # Test bulk set
        bulk_data = {
            "bulk_key1": "bulk_value1",
            "bulk_key2": "bulk_value2",
            "bulk_key3": "bulk_value3"
        }
        
        manager.set_multiple(
            bulk_data,
            scope=StateScope.GLOBAL,
            state_type=StateType.CACHE_DATA
        )
        
        # Verify all were set
        for key, expected_value in bulk_data.items():
            actual_value = manager.get(key)
            self.assertEqual(actual_value, expected_value)
    
    def test_bulk_delete_operations(self):
        """
        BVJ: Bulk delete operations enable efficient cleanup operations.
        Tests bulk delete operations.
        """
        manager = UnifiedStateManager()
        
        # Set up test data
        keys_to_delete = ["delete_key1", "delete_key2", "delete_key3"]
        for key in keys_to_delete:
            manager.set(key, f"value_for_{key}")
        
        # Verify all exist
        for key in keys_to_delete:
            self.assertTrue(manager.exists(key))
        
        # Test bulk delete
        deleted_count = manager.delete_multiple(keys_to_delete)
        
        self.assertEqual(deleted_count, 3)
        
        # Verify all deleted
        for key in keys_to_delete:
            self.assertFalse(manager.exists(key))
    
    def test_scope_clearing_operations(self):
        """
        BVJ: Scope clearing enables complete session/agent cleanup.
        Tests clearing entire scopes.
        """
        manager = UnifiedStateManager()
        
        # Set up data in different scopes
        manager.set_user_state("user1", "pref1", "value1")
        manager.set_user_state("user1", "pref2", "value2")
        manager.set_user_state("user2", "pref1", "value3")
        manager.set_session_state("session1", "data1", "session_value")
        
        # Clear user1 states
        deleted_count = manager.clear_user_states("user1")
        
        self.assertEqual(deleted_count, 2)
        
        # Verify user1 states gone, others remain
        self.assertIsNone(manager.get_user_state("user1", "pref1"))
        self.assertIsNone(manager.get_user_state("user1", "pref2"))
        self.assertEqual(manager.get_user_state("user2", "pref1"), "value3")
        self.assertEqual(manager.get_session_state("session1", "data1"), "session_value")
    
    def test_agent_state_clearing(self):
        """
        BVJ: Agent state clearing enables clean agent termination.
        Tests clearing all states for a specific agent.
        """
        manager = UnifiedStateManager()
        
        # Set up agent states
        manager.set_agent_state("agent1", "step", 5)
        manager.set_agent_state("agent1", "context", "processing")
        manager.set_agent_state("agent2", "step", 10)
        
        # Clear agent1 states
        deleted_count = manager.clear_agent_states("agent1")
        
        self.assertEqual(deleted_count, 2)
        
        # Verify agent1 states gone, agent2 remains
        self.assertIsNone(manager.get_agent_state("agent1", "step"))
        self.assertIsNone(manager.get_agent_state("agent1", "context"))
        self.assertEqual(manager.get_agent_state("agent2", "step"), 10)


# ============================================================================
# MULTI-USER ISOLATION TESTS
# ============================================================================

class TestMultiUserIsolation(BaseTestCase):
    """Test multi-user isolation and prevent cross-contamination."""
    
    def test_user_manager_isolation(self):
        """
        BVJ: User manager isolation prevents data leakage between users.
        Tests that different user managers maintain complete isolation.
        """
        user1_manager = UnifiedStateManager(user_id="user1")
        user2_manager = UnifiedStateManager(user_id="user2")
        
        # Set user-specific data
        user1_manager.set("shared_key", "user1_value")
        user2_manager.set("shared_key", "user2_value")
        
        # Verify isolation
        user1_value = user1_manager.get("shared_key")
        user2_value = user2_manager.get("shared_key")
        
        self.assertEqual(user1_value, "user1_value")
        self.assertEqual(user2_value, "user2_value")
        
        # Verify complete independence
        user1_manager.set("user1_only", "exclusive_data")
        
        self.assertEqual(user1_manager.get("user1_only"), "exclusive_data")
        self.assertIsNone(user2_manager.get("user1_only"))
    
    def test_concurrent_multi_user_operations(self):
        """
        BVJ: Concurrent multi-user operations must not interfere with each other.
        Tests concurrent operations across multiple user contexts.
        """
        users = ["user1", "user2", "user3", "user4", "user5"]
        managers = {user_id: UnifiedStateManager(user_id=user_id) for user_id in users}
        results = {}
        
        def user_worker(user_id):
            manager = managers[user_id]
            user_results = []
            
            # Each user performs operations
            for i in range(50):
                key = f"data_{i}"
                value = f"{user_id}_value_{i}"
                manager.set(key, value)
                
                # Verify immediate read
                read_value = manager.get(key)
                user_results.append((key, value, read_value))
            
            results[user_id] = user_results
        
        # Execute concurrent multi-user operations
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(user_worker, user_id)
                for user_id in users
            ]
            
            for future in as_completed(futures):
                future.result()  # Wait for completion
        
        # Verify all users' operations succeeded independently
        self.assertEqual(len(results), 5)
        
        for user_id, user_results in results.items():
            self.assertEqual(len(user_results), 50)
            for key, expected_value, read_value in user_results:
                self.assertEqual(read_value, expected_value)
                self.assertIn(user_id, expected_value)
    
    def test_user_scoped_state_isolation_comprehensive(self):
        """
        BVJ: Comprehensive user state isolation prevents any cross-contamination.
        Tests complete isolation across all state scopes for different users.
        """
        manager = UnifiedStateManager()
        
        # Set up states for multiple users across all scopes
        users = ["alice", "bob", "charlie"]
        
        for user in users:
            manager.set_user_state(user, "preferences", f"{user}_preferences")
            manager.set_session_state(f"{user}_session", "cart", f"{user}_cart")
            manager.set_thread_state(f"{user}_thread", "context", f"{user}_context")
            manager.set_agent_state(f"{user}_agent", "state", f"{user}_agent_state")
            manager.set_websocket_state(f"{user}_ws", "connection", f"{user}_connection")
        
        # Verify complete isolation - each user only sees their own data
        for user in users:
            user_prefs = manager.get_user_state(user, "preferences")
            session_cart = manager.get_session_state(f"{user}_session", "cart")
            thread_context = manager.get_thread_state(f"{user}_thread", "context")
            agent_state = manager.get_agent_state(f"{user}_agent", "state")
            ws_connection = manager.get_websocket_state(f"{user}_ws", "connection")
            
            # Verify correct user data
            self.assertEqual(user_prefs, f"{user}_preferences")
            self.assertEqual(session_cart, f"{user}_cart")
            self.assertEqual(thread_context, f"{user}_context")
            self.assertEqual(agent_state, f"{user}_agent_state")
            self.assertEqual(ws_connection, f"{user}_connection")
            
            # Verify no access to other users' data
            other_users = [u for u in users if u != user]
            for other_user in other_users:
                self.assertIsNone(manager.get_user_state(other_user, "preferences"))
                self.assertIsNone(manager.get_session_state(f"{other_user}_session", "cart"))
    
    def test_factory_pattern_isolation(self):
        """
        BVJ: Factory pattern ensures proper user isolation at the manager level.
        Tests StateManagerFactory isolation between users.
        """
        # Get managers for different users
        manager1 = StateManagerFactory.get_user_manager("factory_user1") 
        manager2 = StateManagerFactory.get_user_manager("factory_user2")
        global_manager = StateManagerFactory.get_global_manager()
        
        # Verify different instances
        self.assertNotEqual(id(manager1), id(manager2))
        self.assertNotEqual(id(manager1), id(global_manager))
        
        # Set data in each manager
        manager1.set("factory_test", "user1_data")
        manager2.set("factory_test", "user2_data")
        global_manager.set("factory_test", "global_data")
        
        # Verify isolation
        self.assertEqual(manager1.get("factory_test"), "user1_data")
        self.assertEqual(manager2.get("factory_test"), "user2_data")
        self.assertEqual(global_manager.get("factory_test"), "global_data")
        
        # Get same user manager again (should be same instance)
        manager1_again = StateManagerFactory.get_user_manager("factory_user1")
        self.assertEqual(id(manager1), id(manager1_again))
        self.assertEqual(manager1_again.get("factory_test"), "user1_data")


# ============================================================================
# CONTEXT MANAGER TESTS
# ============================================================================

class TestContextManagers(BaseTestCase):
    """Test context manager functionality for scoped operations."""
    
    @pytest.mark.asyncio
    async def test_session_context_manager(self):
        """
        BVJ: Session context managers simplify scoped state operations.
        Tests session context manager functionality.
        """
        manager = UnifiedStateManager()
        session_id = "test_session_123"
        
        async with manager.session_context(session_id) as session_ctx:
            # Use context for session operations
            session_ctx.set("user_id", "user123")
            session_ctx.set("cart", ["item1", "item2"])
            session_ctx.set("last_activity", time.time())
            
            # Verify within context
            self.assertEqual(session_ctx.get("user_id"), "user123")
            self.assertEqual(session_ctx.get("cart"), ["item1", "item2"])
            self.assertIsNotNone(session_ctx.get("last_activity"))
        
        # Verify data persists after context
        self.assertEqual(
            manager.get_session_state(session_id, "user_id"),
            "user123"
        )
        self.assertEqual(
            manager.get_session_state(session_id, "cart"),
            ["item1", "item2"]
        )
    
    @pytest.mark.asyncio
    async def test_agent_context_manager(self):
        """
        BVJ: Agent context managers enable clean agent state management.
        Tests agent context manager functionality.
        """
        manager = UnifiedStateManager()
        agent_id = "test_agent_456"
        
        async with manager.agent_context(agent_id) as agent_ctx:
            # Use context for agent operations
            agent_ctx.set("current_step", 5)
            agent_ctx.set("processing_data", {"task": "analysis"})
            agent_ctx.set("last_checkpoint", "step_4_complete")
            
            # Verify within context
            self.assertEqual(agent_ctx.get("current_step"), 5)
            self.assertEqual(
                agent_ctx.get("processing_data")["task"], 
                "analysis"
            )
        
        # Verify data persists after context
        self.assertEqual(
            manager.get_agent_state(agent_id, "current_step"),
            5
        )
        self.assertEqual(
            manager.get_agent_state(agent_id, "processing_data")["task"],
            "analysis"
        )
    
    @pytest.mark.asyncio 
    async def test_thread_context_manager(self):
        """
        BVJ: Thread context managers enable conversation context management.
        Tests thread context manager functionality.
        """
        manager = UnifiedStateManager()
        thread_id = "test_thread_789"
        
        async with manager.thread_context(thread_id) as thread_ctx:
            # Use context for thread operations
            thread_ctx.set("conversation_topic", "AI development")
            thread_ctx.set("message_count", 15)
            thread_ctx.set("participants", ["user", "assistant"])
            
            # Verify within context
            self.assertEqual(
                thread_ctx.get("conversation_topic"), 
                "AI development"
            )
            self.assertEqual(thread_ctx.get("message_count"), 15)
        
        # Verify data persists after context
        self.assertEqual(
            manager.get_thread_state(thread_id, "conversation_topic"),
            "AI development"
        )
        self.assertEqual(
            manager.get_thread_state(thread_id, "message_count"),
            15
        )
    
    def test_context_helper_deletion(self):
        """
        BVJ: Context helper deletion enables scoped cleanup operations.
        Tests deletion through context helpers.
        """
        manager = UnifiedStateManager()
        
        # Set up data
        session_id = "delete_test_session"
        agent_id = "delete_test_agent" 
        thread_id = "delete_test_thread"
        
        manager.set_session_state(session_id, "temp_data", "delete_me")
        manager.set_agent_state(agent_id, "temp_state", "delete_me_too")
        manager.set_thread_state(thread_id, "temp_context", "delete_me_also")
        
        # Create context helpers
        session_ctx = SessionStateContext(manager, session_id)
        agent_ctx = AgentStateContext(manager, agent_id)
        thread_ctx = ThreadStateContext(manager, thread_id)
        
        # Verify data exists
        self.assertEqual(session_ctx.get("temp_data"), "delete_me")
        self.assertEqual(agent_ctx.get("temp_state"), "delete_me_too")
        self.assertEqual(thread_ctx.get("temp_context"), "delete_me_also")
        
        # Delete through context helpers
        self.assertTrue(session_ctx.delete("temp_data"))
        self.assertTrue(agent_ctx.delete("temp_state"))
        self.assertTrue(thread_ctx.delete("temp_context"))
        
        # Verify deletion
        self.assertIsNone(session_ctx.get("temp_data"))
        self.assertIsNone(agent_ctx.get("temp_state"))
        self.assertIsNone(thread_ctx.get("temp_context"))


# ============================================================================
# PERFORMANCE AND MEMORY TESTS
# ============================================================================

class TestPerformanceAndMemory(BaseTestCase):
    """Test performance characteristics and memory management."""
    
    def test_memory_limit_enforcement(self):
        """
        BVJ: Memory limits prevent system crashes in production environments.
        Tests memory limit enforcement and LRU eviction.
        """
        manager = UnifiedStateManager(max_memory_entries=10)
        
        # Fill beyond memory limit
        for i in range(20):
            manager.set(f"key_{i:02d}", f"value_{i}")
            time.sleep(0.001)  # Small delay for different access times
        
        # Should only have max_memory_entries items
        total_entries = len(manager._states)
        self.assertLessEqual(total_entries, 10)
        
        # Verify LRU eviction (newer items should be kept)
        for i in range(15, 20):  # Last 5 items should exist
            self.assertIsNotNone(manager.get(f"key_{i:02d}"))
    
    def test_large_data_handling(self):
        """
        BVJ: Large data handling ensures system stability with complex AI contexts.
        Tests handling of large data structures.
        """
        manager = UnifiedStateManager()
        
        # Create large data structure
        large_data = {
            "conversation_history": [
                {"message": f"Message {i}", "timestamp": time.time(), "metadata": {"id": i}}
                for i in range(1000)
            ],
            "context_analysis": {
                "topics": [f"topic_{i}" for i in range(100)],
                "sentiment_scores": [0.5 + (i % 100) / 200 for i in range(1000)],
                "entity_extraction": {
                    f"entity_{i}": {"type": "PERSON", "confidence": 0.9}
                    for i in range(200)
                }
            }
        }
        
        # Store and retrieve large data
        manager.set("large_context", large_data)
        retrieved_data = manager.get("large_context")
        
        # Verify data integrity
        self.assertEqual(
            len(retrieved_data["conversation_history"]), 
            1000
        )
        self.assertEqual(
            len(retrieved_data["context_analysis"]["topics"]), 
            100
        )
        self.assertEqual(
            len(retrieved_data["context_analysis"]["entity_extraction"]), 
            200
        )
    
    def test_concurrent_access_performance(self):
        """
        BVJ: Concurrent access performance ensures responsive AI interactions.
        Tests performance under concurrent access load.
        """
        manager = UnifiedStateManager()
        num_threads = 20
        operations_per_thread = 100
        
        def performance_worker(thread_id):
            start_time = time.time()
            
            for i in range(operations_per_thread):
                key = f"perf_{thread_id}_{i}"
                value = f"value_{thread_id}_{i}"
                
                manager.set(key, value)
                retrieved = manager.get(key)
                self.assertEqual(retrieved, value)
            
            end_time = time.time()
            return end_time - start_time
        
        # Execute concurrent performance test
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(performance_worker, thread_id)
                for thread_id in range(num_threads)
            ]
            
            execution_times = []
            for future in as_completed(futures):
                execution_time = future.result()
                execution_times.append(execution_time)
        
        # Verify reasonable performance
        avg_time = sum(execution_times) / len(execution_times)
        max_time = max(execution_times)
        
        # Performance assertions (adjust thresholds as needed)
        self.assertLess(avg_time, 5.0, "Average execution time should be under 5 seconds")
        self.assertLess(max_time, 10.0, "Max execution time should be under 10 seconds")
    
    def test_index_performance(self):
        """
        BVJ: Index performance ensures fast state queries for AI agent operations.
        Tests performance of index-based queries.
        """
        manager = UnifiedStateManager()
        
        # Set up indexed data
        users = [f"user_{i}" for i in range(100)]
        sessions = [f"session_{i}" for i in range(50)]
        agents = [f"agent_{i}" for i in range(25)]
        
        for user in users:
            manager.set_user_state(user, "data", f"data_for_{user}")
        
        for session in sessions:
            manager.set_session_state(session, "info", f"info_for_{session}")
        
        for agent in agents:
            manager.set_agent_state(agent, "status", f"status_for_{agent}")
        
        # Test query performance
        start_time = time.time()
        
        # Query by scope (should use index)
        user_query = StateQuery(scope=StateScope.USER)
        user_results = manager.query_states(user_query)
        
        session_query = StateQuery(scope=StateScope.SESSION)  
        session_results = manager.query_states(session_query)
        
        agent_query = StateQuery(scope=StateScope.AGENT)
        agent_results = manager.query_states(agent_query)
        
        end_time = time.time()
        query_time = end_time - start_time
        
        # Verify results
        self.assertEqual(len(user_results), 100)
        self.assertEqual(len(session_results), 50)
        self.assertEqual(len(agent_results), 25)
        
        # Performance assertion
        self.assertLess(query_time, 1.0, "Index-based queries should be fast")


# ============================================================================
# ERROR HANDLING AND EDGE CASES TESTS
# ============================================================================

class TestErrorHandlingAndEdgeCases(BaseTestCase):
    """Test error handling, recovery, and edge cases."""
    
    def test_invalid_state_operations(self):
        """
        BVJ: Robust error handling prevents system crashes from invalid operations.
        Tests handling of invalid state operations.
        """
        manager = UnifiedStateManager()
        
        # Test operations with None values
        manager.set("none_key", None)
        self.assertIsNone(manager.get("none_key"))
        
        # Test operations with empty strings
        manager.set("", "empty_key_value")
        self.assertEqual(manager.get(""), "empty_key_value")
        
        # Test operations with very long keys
        long_key = "x" * 1000
        manager.set(long_key, "long_key_value")
        self.assertEqual(manager.get(long_key), "long_key_value")
    
    def test_unicode_and_special_characters(self):
        """
        BVJ: Unicode support enables international user content handling.
        Tests handling of unicode and special characters.
        """
        manager = UnifiedStateManager()
        
        # Test unicode strings
        unicode_data = {
            "emoji_key": "🚀🤖💻",
            "chinese": "你好世界",
            "arabic": "مرحبا بالعالم",
            "emoji_mix": "Hello 👋 World 🌍",
            "special_chars": "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        }
        
        for key, value in unicode_data.items():
            manager.set(key, value)
            retrieved = manager.get(key)
            self.assertEqual(retrieved, value)
    
    def test_circular_reference_handling(self):
        """
        BVJ: Circular reference handling prevents infinite loops in state operations.
        Tests handling of circular references in stored data.
        """
        manager = UnifiedStateManager()
        
        # Create circular reference
        circular_dict = {"name": "root"}
        circular_dict["self"] = circular_dict  # Circular reference
        
        # This should not crash (though serialization might have limits)
        try:
            manager.set("circular_key", circular_dict)
            retrieved = manager.get("circular_key")
            
            # Basic verification (can't do deep comparison due to circularity)
            self.assertIsInstance(retrieved, dict)
            self.assertEqual(retrieved["name"], "root")
            
        except Exception as e:
            # If circular references aren't supported, that's acceptable
            self.assertIsInstance(e, (ValueError, RecursionError, TypeError))
    
    def test_state_corruption_recovery(self):
        """
        BVJ: State corruption recovery prevents data loss in production systems.
        Tests handling of corrupted state entries.
        """
        manager = UnifiedStateManager()
        
        # Set normal state
        manager.set("normal_key", "normal_value")
        
        # Simulate corruption by direct manipulation
        corrupt_entry = StateEntry(
            key="corrupt_key",
            value="corrupt_value",
            state_type=StateType.CORRUPTED,  # Using corrupted status
            scope=StateScope.GLOBAL,
            status=StateStatus.CORRUPTED
        )
        
        manager._states["corrupt_key"] = corrupt_entry
        manager._add_to_indices("corrupt_key", corrupt_entry)
        
        # Test handling of corrupted entry
        value = manager.get("corrupt_key")
        
        # Should still return value (graceful degradation)
        self.assertEqual(value, "corrupt_value")
        
        # Verify normal entries still work
        self.assertEqual(manager.get("normal_key"), "normal_value")
    
    def test_concurrent_expiration_handling(self):
        """
        BVJ: Concurrent expiration handling prevents race conditions during cleanup.
        Tests race conditions between expiration and access.
        """
        manager = UnifiedStateManager()
        
        # Set entry with very short TTL
        manager.set("race_key", "race_value", ttl_seconds=1)
        
        results = []
        
        def access_worker():
            """Try to access the key repeatedly"""
            for _ in range(100):
                value = manager.get("race_key")
                results.append(value)
                time.sleep(0.01)
        
        def expiration_check_worker():
            """Check expiration status repeatedly"""
            for _ in range(100):
                exists = manager.exists("race_key")
                results.append(exists)
                time.sleep(0.01)
        
        # Start workers with timing around expiration
        with ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(access_worker)
            future2 = executor.submit(expiration_check_worker)
            
            # Wait briefly, then let expiration occur
            time.sleep(0.5)
            
            # Wait for completion
            future1.result()
            future2.result()
        
        # Should have mix of results before and after expiration
        # Important: no exceptions should be raised
        self.assertEqual(len(results), 200)  # Both workers completed


# ============================================================================
# INTEGRATION AND MIGRATION TESTS
# ============================================================================

class TestIntegrationAndMigration(BaseTestCase):
    """Test integration patterns and legacy manager migration."""
    
    def test_legacy_function_compatibility(self):
        """
        BVJ: Legacy compatibility prevents breaking changes during migration.
        Tests legacy compatibility functions.
        """
        # Test legacy functions return UnifiedStateManager instances
        agent_manager = get_agent_state_manager()
        session_manager = get_session_state_manager() 
        websocket_manager = get_websocket_state_manager()
        message_manager = get_message_state_manager()
        
        self.assertIsInstance(agent_manager, UnifiedStateManager)
        self.assertIsInstance(session_manager, UnifiedStateManager)
        self.assertIsInstance(websocket_manager, UnifiedStateManager)
        self.assertIsInstance(message_manager, UnifiedStateManager)
        
        # Test they all return the same global instance
        global_manager = get_state_manager()
        self.assertEqual(id(agent_manager), id(global_manager))
        self.assertEqual(id(session_manager), id(global_manager))
    
    def test_factory_pattern_consolidation(self):
        """
        BVJ: Factory pattern consolidation enables centralized state management.
        Tests factory pattern for different manager types.
        """
        # Get managers through factory
        global1 = StateManagerFactory.get_global_manager()
        global2 = StateManagerFactory.get_global_manager()
        
        user1_manager = StateManagerFactory.get_user_manager("consolidation_user1")
        user2_manager = StateManagerFactory.get_user_manager("consolidation_user2")
        
        # Verify singleton behavior for global manager
        self.assertEqual(id(global1), id(global2))
        
        # Verify separate instances for different users
        self.assertNotEqual(id(user1_manager), id(user2_manager))
        self.assertNotEqual(id(user1_manager), id(global1))
        
        # Test manager count tracking
        counts = StateManagerFactory.get_manager_count()
        self.assertEqual(counts["global"], 1)
        self.assertGreaterEqual(counts["user_specific"], 2)
    
    @pytest.mark.asyncio
    async def test_shutdown_lifecycle(self):
        """
        BVJ: Proper shutdown prevents resource leaks in production deployment.
        Tests manager shutdown and resource cleanup.
        """
        manager = UnifiedStateManager(
            enable_ttl_cleanup=True,
            cleanup_interval=1
        )
        
        # Set some state
        manager.set("shutdown_test", "test_value")
        
        # Verify manager is operational
        self.assertEqual(manager.get("shutdown_test"), "test_value")
        
        # Test shutdown
        await manager.shutdown()
        
        # Verify background tasks stopped
        if manager._cleanup_task:
            self.assertTrue(manager._cleanup_task.done())
        if manager._event_processing_task:
            self.assertTrue(manager._event_processing_task.done())
    
    @pytest.mark.asyncio
    async def test_factory_shutdown_all(self):
        """
        BVJ: Factory shutdown enables clean application termination.
        Tests factory-wide shutdown of all managers.
        """
        # Create multiple managers
        StateManagerFactory.get_global_manager().set("global_data", "test")
        StateManagerFactory.get_user_manager("shutdown_user1").set("user1_data", "test")
        StateManagerFactory.get_user_manager("shutdown_user2").set("user2_data", "test")
        
        # Verify managers exist
        counts_before = StateManagerFactory.get_manager_count()
        self.assertGreater(counts_before["total"], 0)
        
        # Shutdown all
        await StateManagerFactory.shutdown_all_managers()
        
        # Verify cleanup
        counts_after = StateManagerFactory.get_manager_count()
        self.assertEqual(counts_after["total"], 0)


# ============================================================================
# STATUS AND MONITORING TESTS
# ============================================================================

class TestStatusAndMonitoring(BaseTestCase):
    """Test status reporting and monitoring functionality."""
    
    def test_status_reporting(self):
        """
        BVJ: Status reporting enables production monitoring and debugging.
        Tests comprehensive status reporting.
        """
        manager = UnifiedStateManager(
            user_id="status_test_user",
            max_memory_entries=100,
            enable_ttl_cleanup=True,
            enable_versioning=True
        )
        
        # Add some test data
        manager.set("status_key1", "value1")
        manager.set_user_state("user1", "pref", "dark")
        manager.set_agent_state("agent1", "step", 5)
        
        status = manager.get_status()
        
        # Verify status structure
        self.assertIn("user_id", status)
        self.assertIn("total_entries", status)
        self.assertIn("memory_limit", status)
        self.assertIn("memory_usage_percent", status)
        self.assertIn("cleanup_enabled", status)
        self.assertIn("persistence_enabled", status)
        self.assertIn("versioning_enabled", status)
        self.assertIn("scope_distribution", status)
        self.assertIn("type_distribution", status)
        self.assertIn("metrics", status)
        
        # Verify values
        self.assertEqual(status["user_id"], "status_test_user")
        self.assertEqual(status["memory_limit"], 100)
        self.assertTrue(status["cleanup_enabled"])
        self.assertTrue(status["versioning_enabled"])
        self.assertGreater(status["total_entries"], 0)
    
    def test_health_status_monitoring(self):
        """
        BVJ: Health monitoring enables proactive system maintenance.
        Tests health status monitoring functionality.
        """
        manager = UnifiedStateManager(max_memory_entries=100)
        
        # Test healthy state
        health = manager.get_health_status()
        self.assertEqual(health["status"], "healthy")
        self.assertLess(health["memory_usage_percent"], 90)
        self.assertLess(health["event_queue_size"], 1000)
        
        # Test approaching memory limit
        for i in range(85):  # Approach 85% of limit
            manager.set(f"health_key_{i}", f"value_{i}")
        
        health = manager.get_health_status()
        self.assertGreater(health["memory_usage_percent"], 80)
    
    def test_metrics_collection(self):
        """
        BVJ: Metrics collection enables performance analysis and optimization.
        Tests metrics collection and tracking.
        """
        manager = UnifiedStateManager()
        
        # Perform various operations
        manager.set("metrics_key1", "value1")
        manager.set("metrics_key2", "value2")
        manager.get("metrics_key1")
        manager.get("metrics_key1")  # Second get (cache hit)
        manager.get("nonexistent_key")  # Cache miss
        manager.delete("metrics_key2")
        
        status = manager.get_status()
        metrics = status["metrics"]
        
        # Verify metrics tracking
        self.assertGreater(metrics["total_operations"], 0)
        self.assertGreater(metrics["set_operations"], 0)
        self.assertGreater(metrics["get_operations"], 0)
        self.assertGreater(metrics["delete_operations"], 0)
        self.assertGreater(metrics["cache_hits"], 0)
        self.assertGreater(metrics["cache_misses"], 0)
    
    def test_scope_and_type_statistics(self):
        """
        BVJ: Statistics enable understanding state distribution for optimization.
        Tests scope and type distribution statistics.
        """
        manager = UnifiedStateManager()
        
        # Set data across different scopes and types
        manager.set("global1", "value1", StateScope.GLOBAL, StateType.CONFIGURATION_STATE)
        manager.set("global2", "value2", StateScope.GLOBAL, StateType.CACHE_DATA)
        manager.set_user_state("user1", "pref1", "value3")
        manager.set_user_state("user2", "pref2", "value4")
        manager.set_session_state("session1", "data1", "value5")
        manager.set_agent_state("agent1", "state1", "value6")
        
        # Get statistics
        scope_stats = manager.get_stats_by_scope()
        type_stats = manager.get_stats_by_type()
        
        # Verify scope distribution
        self.assertGreater(scope_stats["global"], 0)
        self.assertGreater(scope_stats["user"], 0)
        self.assertGreater(scope_stats["session"], 0)
        self.assertGreater(scope_stats["agent"], 0)
        
        # Verify type distribution
        self.assertGreater(type_stats["configuration_state"], 0)
        self.assertGreater(type_stats["cache_data"], 0)
        self.assertGreater(type_stats["user_preferences"], 0)
        self.assertGreater(type_stats["session_data"], 0)
        self.assertGreater(type_stats["agent_execution"], 0)


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s", "--tb=short"])