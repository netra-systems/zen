"""
Comprehensive unit tests for UnifiedStateManager SSOT class.

This test suite covers all public methods and key scenarios for the 
UnifiedStateManager with proper mocking of external dependencies.
Tests are designed to fail initially to identify gaps in implementation.
"""

import asyncio
import pytest
import threading
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List
from unittest.mock import Mock, patch, AsyncMock, MagicMock

# Import classes to test
from netra_backend.app.core.managers.unified_state_manager import (
    UnifiedStateManager,
    StateScope,
    StateType,
    StateStatus,
    StateEntry,
    StateChangeEvent,
    StateQuery,
    StateManagerFactory,
    SessionStateContext,
    AgentStateContext,
    ThreadStateContext,
    get_state_manager
)


class TestStateEntry:
    """Tests for StateEntry class."""
    
    def test_state_entry_creation_with_defaults(self):
        """Test StateEntry creation with default values."""
        entry = StateEntry(
            key="test_key",
            value="test_value",
            state_type=StateType.CACHE_DATA,
            scope=StateScope.GLOBAL
        )
        
        assert entry.key == "test_key"
        assert entry.value == "test_value"
        assert entry.state_type == StateType.CACHE_DATA
        assert entry.scope == StateScope.GLOBAL
        assert entry.status == StateStatus.ACTIVE
        assert entry.version == 1
        assert entry.expires_at is None
        assert entry.ttl_seconds is None
        
    def test_state_entry_creation_with_ttl_sets_expiry(self):
        """Test StateEntry with TTL automatically sets expires_at."""
        entry = StateEntry(
            key="test_key",
            value="test_value",
            state_type=StateType.CACHE_DATA,
            scope=StateScope.GLOBAL,
            ttl_seconds=60
        )
        
        assert entry.ttl_seconds == 60
        assert entry.expires_at is not None
        assert entry.expires_at > time.time()
        assert entry.expires_at <= time.time() + 61  # Allow 1 second variance
        
    def test_state_entry_is_expired_returns_false_when_not_expired(self):
        """Test is_expired returns False for non-expired entries."""
        entry = StateEntry(
            key="test_key",
            value="test_value",
            state_type=StateType.CACHE_DATA,
            scope=StateScope.GLOBAL,
            ttl_seconds=60
        )
        
        assert not entry.is_expired()
        
    def test_state_entry_is_expired_returns_true_when_expired(self):
        """Test is_expired returns True for expired entries."""
        entry = StateEntry(
            key="test_key",
            value="test_value",
            state_type=StateType.CACHE_DATA,
            scope=StateScope.GLOBAL,
            expires_at=time.time() - 10  # 10 seconds ago
        )
        
        assert entry.is_expired()
        
    def test_state_entry_is_expired_returns_false_when_no_expiry(self):
        """Test is_expired returns False when no expiry is set."""
        entry = StateEntry(
            key="test_key",
            value="test_value",
            state_type=StateType.CACHE_DATA,
            scope=StateScope.GLOBAL
        )
        
        assert not entry.is_expired()
        
    def test_state_entry_refresh_access_updates_timestamp(self):
        """Test refresh_access updates accessed_at timestamp."""
        entry = StateEntry(
            key="test_key",
            value="test_value",
            state_type=StateType.CACHE_DATA,
            scope=StateScope.GLOBAL
        )
        
        original_time = entry.accessed_at
        time.sleep(0.01)  # Small delay
        entry.refresh_access()
        
        assert entry.accessed_at > original_time
        
    def test_state_entry_update_value_increments_version(self):
        """Test update_value increments version and updates timestamps."""
        entry = StateEntry(
            key="test_key",
            value="test_value",
            state_type=StateType.CACHE_DATA,
            scope=StateScope.GLOBAL
        )
        
        original_version = entry.version
        original_updated_at = entry.updated_at
        
        time.sleep(0.01)  # Small delay
        entry.update_value("new_value")
        
        assert entry.value == "new_value"
        assert entry.version == original_version + 1
        assert entry.updated_at > original_updated_at
        assert entry.accessed_at > original_updated_at
        
    def test_state_entry_extend_ttl_with_existing_expiry(self):
        """Test extend_ttl with existing expires_at."""
        entry = StateEntry(
            key="test_key",
            value="test_value",
            state_type=StateType.CACHE_DATA,
            scope=StateScope.GLOBAL,
            ttl_seconds=60
        )
        
        original_expiry = entry.expires_at
        entry.extend_ttl(30)
        
        assert entry.expires_at == original_expiry + 30
        
    def test_state_entry_extend_ttl_without_existing_expiry_but_with_ttl(self):
        """Test extend_ttl without expires_at but with ttl_seconds."""
        entry = StateEntry(
            key="test_key",
            value="test_value",
            state_type=StateType.CACHE_DATA,
            scope=StateScope.GLOBAL,
            ttl_seconds=60
        )
        
        # Clear expires_at but keep ttl_seconds
        entry.expires_at = None
        entry.extend_ttl(30)
        
        assert entry.expires_at is not None
        assert entry.expires_at <= time.time() + 31  # Allow variance
        
    def test_state_entry_to_dict_contains_all_fields(self):
        """Test to_dict contains all expected fields."""
        entry = StateEntry(
            key="test_key",
            value="test_value",
            state_type=StateType.CACHE_DATA,
            scope=StateScope.GLOBAL,
            ttl_seconds=60,
            user_id="user123",
            session_id="session123",
            thread_id="thread123",
            agent_id="agent123",
            metadata={"custom": "value"}
        )
        
        result = entry.to_dict()
        
        expected_keys = {
            "key", "value", "state_type", "scope", "created_at", "updated_at",
            "accessed_at", "expires_at", "ttl_seconds", "status", "user_id",
            "session_id", "thread_id", "agent_id", "metadata", "version"
        }
        
        assert set(result.keys()) == expected_keys
        assert result["key"] == "test_key"
        assert result["value"] == "test_value"
        assert result["state_type"] == StateType.CACHE_DATA.value
        assert result["scope"] == StateScope.GLOBAL.value


class TestUnifiedStateManagerInitialization:
    """Tests for UnifiedStateManager initialization."""
    
    @patch('netra_backend.app.core.managers.unified_state_manager.IsolatedEnvironment')
    def test_init_with_default_parameters_succeeds(self, mock_env):
        """Test UnifiedStateManager initialization with defaults."""
        mock_env_instance = Mock()
        # Mock environment to return defaults that don't override constructor params
        mock_env_instance.get.side_effect = lambda key, default: {
            'STATE_CLEANUP_INTERVAL': '60',
            'STATE_MAX_MEMORY_ENTRIES': '10000', 
            'STATE_ENABLE_PERSISTENCE': 'true'
        }.get(key, default)
        mock_env.return_value = mock_env_instance
        
        manager = UnifiedStateManager()
        
        assert manager.user_id is None
        assert manager.enable_persistence is True
        assert manager.enable_ttl_cleanup is True
        assert manager.cleanup_interval == 60
        assert manager.max_memory_entries == 10000
        assert manager.enable_versioning is True
        assert len(manager._states) == 0
        
    @patch('netra_backend.app.core.managers.unified_state_manager.IsolatedEnvironment')
    def test_init_with_custom_parameters_sets_values(self, mock_env):
        """Test UnifiedStateManager initialization with custom parameters."""
        mock_env_instance = Mock()
        # Mock environment to not override constructor params
        mock_env_instance.get.side_effect = lambda key, default: {
            'STATE_CLEANUP_INTERVAL': '30',  # Should be overridden by constructor
            'STATE_MAX_MEMORY_ENTRIES': '5000',  # Should be overridden by constructor  
            'STATE_ENABLE_PERSISTENCE': 'false'  # Should be overridden by constructor
        }.get(key, default)
        mock_env.return_value = mock_env_instance
        
        manager = UnifiedStateManager(
            user_id="test_user",
            enable_persistence=False,
            enable_ttl_cleanup=False,
            cleanup_interval=30,
            max_memory_entries=5000,
            enable_versioning=False
        )
        
        assert manager.user_id == "test_user"
        assert manager.enable_persistence is False
        assert manager.enable_ttl_cleanup is False
        assert manager.cleanup_interval == 30
        assert manager.max_memory_entries == 5000
        assert manager.enable_versioning is False
        
    @patch('netra_backend.app.core.managers.unified_state_manager.IsolatedEnvironment')
    def test_load_environment_config_reads_env_vars(self, mock_env):
        """Test environment configuration loading from environment variables."""
        mock_env_instance = Mock()
        mock_env_instance.get.side_effect = lambda key, default: {
            'STATE_CLEANUP_INTERVAL': '120',
            'STATE_MAX_MEMORY_ENTRIES': '20000',
            'STATE_ENABLE_PERSISTENCE': 'false'
        }.get(key, default)
        mock_env.return_value = mock_env_instance
        
        manager = UnifiedStateManager()
        
        assert manager.cleanup_interval == 120
        assert manager.max_memory_entries == 20000
        assert manager.enable_persistence is False
        
    @patch('netra_backend.app.core.managers.unified_state_manager.IsolatedEnvironment')
    def test_load_environment_config_handles_invalid_values(self, mock_env):
        """Test environment configuration handles invalid values gracefully."""
        mock_env_instance = Mock()
        mock_env_instance.get.side_effect = lambda key, default: {
            'STATE_CLEANUP_INTERVAL': 'invalid',
            'STATE_MAX_MEMORY_ENTRIES': 'not_a_number'
        }.get(key, default)
        mock_env.return_value = mock_env_instance
        
        # Should not raise exception, should use defaults
        manager = UnifiedStateManager()
        
        # Should still have default values since invalid config was provided
        assert isinstance(manager.cleanup_interval, int)
        assert isinstance(manager.max_memory_entries, int)


class TestUnifiedStateManagerCoreOperations:
    """Tests for core state operations (get, set, delete, etc.)."""
    
    def setup_method(self, method):
        """Set up test manager for each test."""
        mock_env = Mock()
        mock_env.get.side_effect = lambda key, default: default
        with patch('netra_backend.app.core.managers.unified_state_manager.IsolatedEnvironment', return_value=mock_env):
            self.manager = UnifiedStateManager()
    
    def test_get_nonexistent_key_returns_default(self):
        """Test get returns default value for nonexistent key."""
        result = self.manager.get("nonexistent_key", "default_value")
        assert result == "default_value"
        
    def test_get_nonexistent_key_returns_none_when_no_default(self):
        """Test get returns None when no default provided for nonexistent key."""
        result = self.manager.get("nonexistent_key")
        assert result is None
        
    def test_set_and_get_value_succeeds(self):
        """Test setting and getting a value works correctly."""
        self.manager.set("test_key", "test_value")
        result = self.manager.get("test_key")
        assert result == "test_value"
        
    def test_set_overwrites_existing_value(self):
        """Test setting overwrites existing value."""
        self.manager.set("test_key", "old_value")
        self.manager.set("test_key", "new_value")
        result = self.manager.get("test_key")
        assert result == "new_value"
        
    def test_set_with_scope_and_type_validation(self):
        """Test set with specific scope and type, then validate on get."""
        self.manager.set(
            "test_key", 
            "test_value",
            scope=StateScope.USER,
            state_type=StateType.USER_PREFERENCES
        )
        
        # Get with matching scope and type should succeed
        result = self.manager.get(
            "test_key", 
            scope=StateScope.USER,
            state_type=StateType.USER_PREFERENCES
        )
        assert result == "test_value"
        
        # Get with mismatched scope should return default
        result = self.manager.get(
            "test_key",
            default="default",
            scope=StateScope.SESSION,
            state_type=StateType.USER_PREFERENCES
        )
        assert result == "default"
        
    def test_set_with_ttl_expires_entry(self):
        """Test entry with TTL expires after specified time."""
        self.manager.set("test_key", "test_value", ttl_seconds=1)
        
        # Should be available immediately
        result = self.manager.get("test_key")
        assert result == "test_value"
        
        # Wait for expiry
        time.sleep(1.1)
        
        # Should return default after expiry
        result = self.manager.get("test_key", "default")
        assert result == "default"
        
    def test_set_with_metadata_stores_correctly(self):
        """Test set with metadata stores metadata correctly."""
        metadata = {"source": "test", "priority": 1}
        self.manager.set("test_key", "test_value", metadata=metadata)
        
        # Check internal entry has metadata
        entry = self.manager._states["test_key"]
        assert entry.metadata == metadata
        
    def test_delete_existing_key_returns_true(self):
        """Test delete returns True for existing key."""
        self.manager.set("test_key", "test_value")
        result = self.manager.delete("test_key")
        assert result is True
        
        # Verify key is gone
        assert self.manager.get("test_key") is None
        
    def test_delete_nonexistent_key_returns_false(self):
        """Test delete returns False for nonexistent key."""
        result = self.manager.delete("nonexistent_key")
        assert result is False
        
    def test_exists_returns_true_for_existing_key(self):
        """Test exists returns True for existing non-expired key."""
        self.manager.set("test_key", "test_value")
        assert self.manager.exists("test_key") is True
        
    def test_exists_returns_false_for_nonexistent_key(self):
        """Test exists returns False for nonexistent key."""
        assert self.manager.exists("nonexistent_key") is False
        
    def test_exists_returns_false_for_expired_key(self):
        """Test exists returns False for expired key and removes it."""
        self.manager.set("test_key", "test_value", ttl_seconds=1)
        time.sleep(1.1)
        assert self.manager.exists("test_key") is False
        
        # Key should be removed from internal storage
        assert "test_key" not in self.manager._states
        
    def test_keys_returns_all_non_expired_keys(self):
        """Test keys returns all non-expired keys."""
        self.manager.set("key1", "value1")
        self.manager.set("key2", "value2")
        self.manager.set("expired_key", "value", ttl_seconds=1)
        
        time.sleep(1.1)  # Wait for expiry
        
        keys = self.manager.keys()
        assert sorted(keys) == ["key1", "key2"]
        
    def test_keys_with_pattern_filters_correctly(self):
        """Test keys with pattern filters keys correctly."""
        self.manager.set("user_123", "value1")
        self.manager.set("user_456", "value2")
        self.manager.set("session_123", "value3")
        
        keys = self.manager.keys(pattern="user_.*")
        assert sorted(keys) == ["user_123", "user_456"]
        
    def test_update_with_existing_key_modifies_value(self):
        """Test update modifies existing value using updater function."""
        self.manager.set("counter", 5)
        
        result = self.manager.update("counter", lambda x: x + 1)
        
        assert result == 6
        assert self.manager.get("counter") == 6
        
    def test_update_with_nonexistent_key_uses_default(self):
        """Test update with nonexistent key uses default value."""
        result = self.manager.update("new_counter", lambda x: x + 1, default=0)
        
        assert result == 1
        assert self.manager.get("new_counter") == 1
        
    def test_get_refreshes_access_timestamp(self):
        """Test get operation refreshes access timestamp."""
        self.manager.set("test_key", "test_value")
        entry = self.manager._states["test_key"]
        original_access_time = entry.accessed_at
        
        time.sleep(0.01)
        self.manager.get("test_key")
        
        assert entry.accessed_at > original_access_time


class TestUnifiedStateManagerScopedOperations:
    """Tests for scoped state operations (user, session, thread, agent, websocket)."""
    
    def setup_method(self, method):
        """Set up test manager for each test."""
        mock_env = Mock()
        mock_env.get.side_effect = lambda key, default: default
        with patch('netra_backend.app.core.managers.unified_state_manager.IsolatedEnvironment', return_value=mock_env):
            self.manager = UnifiedStateManager()
    
    def test_user_state_operations_with_correct_prefix(self):
        """Test user state operations use correct key prefix."""
        user_id = "user123"
        key = "preference"
        value = "dark_theme"
        
        self.manager.set_user_state(user_id, key, value)
        result = self.manager.get_user_state(user_id, key)
        
        assert result == value
        
        # Check internal key format
        full_key = f"user:{user_id}:{key}"
        assert full_key in self.manager._states
        
    def test_user_state_isolation_between_users(self):
        """Test user state is isolated between different users."""
        self.manager.set_user_state("user1", "key", "value1")
        self.manager.set_user_state("user2", "key", "value2")
        
        assert self.manager.get_user_state("user1", "key") == "value1"
        assert self.manager.get_user_state("user2", "key") == "value2"
        
    def test_session_state_operations_with_correct_prefix(self):
        """Test session state operations use correct key prefix."""
        session_id = "session123"
        key = "cart_items"
        value = ["item1", "item2"]
        
        self.manager.set_session_state(session_id, key, value)
        result = self.manager.get_session_state(session_id, key)
        
        assert result == value
        
        # Check internal key format
        full_key = f"session:{session_id}:{key}"
        assert full_key in self.manager._states
        
    def test_session_state_isolation_between_sessions(self):
        """Test session state is isolated between different sessions."""
        self.manager.set_session_state("session1", "key", "value1")
        self.manager.set_session_state("session2", "key", "value2")
        
        assert self.manager.get_session_state("session1", "key") == "value1"
        assert self.manager.get_session_state("session2", "key") == "value2"
        
    def test_thread_state_operations_with_correct_prefix(self):
        """Test thread state operations use correct key prefix."""
        thread_id = "thread123"
        key = "conversation_history"
        value = ["msg1", "msg2"]
        
        self.manager.set_thread_state(thread_id, key, value)
        result = self.manager.get_thread_state(thread_id, key)
        
        assert result == value
        
        # Check internal key format
        full_key = f"thread:{thread_id}:{key}"
        assert full_key in self.manager._states
        
    def test_thread_state_isolation_between_threads(self):
        """Test thread state is isolated between different threads."""
        self.manager.set_thread_state("thread1", "key", "value1")
        self.manager.set_thread_state("thread2", "key", "value2")
        
        assert self.manager.get_thread_state("thread1", "key") == "value1"
        assert self.manager.get_thread_state("thread2", "key") == "value2"
        
    def test_agent_state_operations_with_default_ttl(self):
        """Test agent state operations use default TTL."""
        agent_id = "agent123"
        key = "execution_status"
        value = "running"
        
        self.manager.set_agent_state(agent_id, key, value)
        result = self.manager.get_agent_state(agent_id, key)
        
        assert result == value
        
        # Check internal entry has TTL
        full_key = f"agent:{agent_id}:{key}"
        entry = self.manager._states[full_key]
        assert entry.ttl_seconds == 3600  # 1 hour default
        assert entry.expires_at is not None
        
    def test_agent_state_isolation_between_agents(self):
        """Test agent state is isolated between different agents."""
        self.manager.set_agent_state("agent1", "key", "value1")
        self.manager.set_agent_state("agent2", "key", "value2")
        
        assert self.manager.get_agent_state("agent1", "key") == "value1"
        assert self.manager.get_agent_state("agent2", "key") == "value2"
        
    def test_websocket_state_operations_with_default_ttl(self):
        """Test websocket state operations use default TTL."""
        connection_id = "conn123"
        key = "connection_info"
        value = {"ip": "192.168.1.1", "user_agent": "test"}
        
        self.manager.set_websocket_state(connection_id, key, value)
        result = self.manager.get_websocket_state(connection_id, key)
        
        assert result == value
        
        # Check internal entry has TTL
        full_key = f"websocket:{connection_id}:{key}"
        entry = self.manager._states[full_key]
        assert entry.ttl_seconds == 1800  # 30 minutes default
        assert entry.expires_at is not None
        
    def test_websocket_state_isolation_between_connections(self):
        """Test websocket state is isolated between different connections."""
        self.manager.set_websocket_state("conn1", "key", "value1")
        self.manager.set_websocket_state("conn2", "key", "value2")
        
        assert self.manager.get_websocket_state("conn1", "key") == "value1"
        assert self.manager.get_websocket_state("conn2", "key") == "value2"


class TestUnifiedStateManagerBulkOperations:
    """Tests for bulk state operations."""
    
    def setup_method(self, method):
        """Set up test manager for each test."""
        mock_env = Mock()
        mock_env.get.side_effect = lambda key, default: default
        with patch('netra_backend.app.core.managers.unified_state_manager.IsolatedEnvironment', return_value=mock_env):
            self.manager = UnifiedStateManager()
    
    def test_get_multiple_returns_dict_with_all_keys(self):
        """Test get_multiple returns dictionary with all requested keys."""
        self.manager.set("key1", "value1")
        self.manager.set("key2", "value2")
        self.manager.set("key3", "value3")
        
        result = self.manager.get_multiple(["key1", "key2", "nonexistent"])
        
        assert result == {
            "key1": "value1",
            "key2": "value2",
            "nonexistent": None
        }
        
    def test_set_multiple_sets_all_values(self):
        """Test set_multiple sets all provided key-value pairs."""
        states = {
            "key1": "value1",
            "key2": "value2",
            "key3": "value3"
        }
        
        self.manager.set_multiple(states, scope=StateScope.USER)
        
        for key, expected_value in states.items():
            assert self.manager.get(key) == expected_value
            # Check scope was applied
            entry = self.manager._states[key]
            assert entry.scope == StateScope.USER
            
    def test_delete_multiple_deletes_existing_keys(self):
        """Test delete_multiple deletes existing keys and returns count."""
        self.manager.set("key1", "value1")
        self.manager.set("key2", "value2")
        self.manager.set("key3", "value3")
        
        deleted_count = self.manager.delete_multiple(["key1", "key3", "nonexistent"])
        
        assert deleted_count == 2
        assert self.manager.get("key1") is None
        assert self.manager.get("key2") == "value2"
        assert self.manager.get("key3") is None
        
    def test_clear_scope_removes_all_entries_for_scope(self):
        """Test clear_scope removes all entries for specified scope."""
        # Set up entries with different scopes
        self.manager.set("global1", "value", scope=StateScope.GLOBAL)
        self.manager.set("global2", "value", scope=StateScope.GLOBAL)
        self.manager.set("user1", "value", scope=StateScope.USER, user_id="user123")
        self.manager.set("user2", "value", scope=StateScope.USER, user_id="user123")
        self.manager.set("session1", "value", scope=StateScope.SESSION)
        
        deleted_count = self.manager.clear_scope(StateScope.GLOBAL)
        
        assert deleted_count == 2
        assert self.manager.get("global1") is None
        assert self.manager.get("global2") is None
        assert self.manager.get("user1") == "value"
        assert self.manager.get("session1") == "value"
        
    def test_clear_user_states_removes_only_user_entries(self):
        """Test clear_user_states removes only entries for specific user."""
        self.manager.set_user_state("user123", "key1", "value1")
        self.manager.set_user_state("user123", "key2", "value2")
        self.manager.set_user_state("user456", "key1", "value3")
        
        deleted_count = self.manager.clear_user_states("user123")
        
        assert deleted_count == 2
        assert self.manager.get_user_state("user123", "key1") is None
        assert self.manager.get_user_state("user123", "key2") is None
        assert self.manager.get_user_state("user456", "key1") == "value3"
        
    def test_clear_session_states_removes_only_session_entries(self):
        """Test clear_session_states removes only entries for specific session."""
        self.manager.set_session_state("session123", "key1", "value1")
        self.manager.set_session_state("session123", "key2", "value2")
        self.manager.set_session_state("session456", "key1", "value3")
        
        deleted_count = self.manager.clear_session_states("session123")
        
        assert deleted_count == 2
        assert self.manager.get_session_state("session123", "key1") is None
        assert self.manager.get_session_state("session123", "key2") is None
        assert self.manager.get_session_state("session456", "key1") == "value3"
        
    def test_clear_agent_states_removes_only_agent_entries(self):
        """Test clear_agent_states removes only entries for specific agent."""
        self.manager.set_agent_state("agent123", "key1", "value1")
        self.manager.set_agent_state("agent123", "key2", "value2")
        self.manager.set_agent_state("agent456", "key1", "value3")
        
        deleted_count = self.manager.clear_agent_states("agent123")
        
        assert deleted_count == 2
        assert self.manager.get_agent_state("agent123", "key1") is None
        assert self.manager.get_agent_state("agent123", "key2") is None
        assert self.manager.get_agent_state("agent456", "key1") == "value3"


class TestUnifiedStateManagerQuerying:
    """Tests for state querying and filtering capabilities."""
    
    def setup_method(self, method):
        """Set up test manager with sample data for each test."""
        mock_env = Mock()
        mock_env.get.side_effect = lambda key, default: default
        with patch('netra_backend.app.core.managers.unified_state_manager.IsolatedEnvironment', return_value=mock_env):
            self.manager = UnifiedStateManager()
            
        # Set up sample data using scoped methods
        self.manager.set_user_state("user1", "key", "value1")
        self.manager.set_user_state("user2", "key", "value2")
        self.manager.set_session_state("session1", "key", "value3")
        self.manager.set("global_key", "value4", scope=StateScope.GLOBAL, state_type=StateType.CACHE_DATA)
        
    def test_query_states_by_scope_filters_correctly(self):
        """Test query_states filters by scope correctly."""
        query = StateQuery(scope=StateScope.USER)
        results = self.manager.query_states(query)
        
        assert len(results) == 2
        scopes = {entry.scope for entry in results}
        assert scopes == {StateScope.USER}
        
    def test_query_states_by_user_id_filters_correctly(self):
        """Test query_states filters by user_id correctly."""
        query = StateQuery(user_id="user1")
        results = self.manager.query_states(query)
        
        assert len(results) == 1
        assert results[0].user_id == "user1"
        
    def test_query_states_by_session_id_filters_correctly(self):
        """Test query_states filters by session_id correctly."""
        query = StateQuery(session_id="session1")
        results = self.manager.query_states(query)
        
        assert len(results) == 1
        assert results[0].session_id == "session1"
        
    def test_query_states_by_state_type_filters_correctly(self):
        """Test query_states filters by state_type correctly."""
        query = StateQuery(state_type=StateType.CACHE_DATA)
        results = self.manager.query_states(query)
        
        assert len(results) == 1
        assert results[0].state_type == StateType.CACHE_DATA
        
    def test_query_states_with_multiple_filters_combines_correctly(self):
        """Test query_states combines multiple filters with AND logic."""
        query = StateQuery(
            scope=StateScope.USER,
            user_id="user1"
        )
        results = self.manager.query_states(query)
        
        assert len(results) == 1
        assert results[0].scope == StateScope.USER
        assert results[0].user_id == "user1"
        
    def test_query_states_by_created_after_filters_correctly(self):
        """Test query_states filters by created_after correctly."""
        # Add entry with known timestamp
        current_time = time.time()
        self.manager.set("recent_key", "value")
        
        query = StateQuery(created_after=current_time - 1)
        results = self.manager.query_states(query)
        
        # Should include at least the recent entry
        recent_keys = [r.key for r in results if r.key == "recent_key"]
        assert len(recent_keys) == 1
        
    def test_query_states_by_key_pattern_filters_correctly(self):
        """Test query_states filters by key pattern correctly."""
        query = StateQuery(key_pattern="user:.*")
        results = self.manager.query_states(query)
        
        assert len(results) == 2
        keys = {entry.key for entry in results}
        assert keys == {"user:user1:key", "user:user2:key"}
        
    def test_query_states_with_limit_restricts_results(self):
        """Test query_states respects limit parameter."""
        query = StateQuery(limit=2)
        results = self.manager.query_states(query)
        
        assert len(results) == 2
        
    def test_query_states_excludes_expired_by_default(self):
        """Test query_states excludes expired entries by default."""
        # Add expired entry
        self.manager.set("expired_key", "value", ttl_seconds=1)
        time.sleep(1.1)
        
        query = StateQuery()
        results = self.manager.query_states(query)
        
        expired_keys = [r.key for r in results if r.key == "expired_key"]
        assert len(expired_keys) == 0
        
    def test_query_states_includes_expired_when_requested(self):
        """Test query_states includes expired entries when include_expired=True."""
        # Add expired entry
        self.manager.set("expired_key", "value", ttl_seconds=1)
        time.sleep(1.1)
        
        query = StateQuery(include_expired=True)
        results = self.manager.query_states(query)
        
        expired_keys = [r.key for r in results if r.key == "expired_key"]
        assert len(expired_keys) == 1
        
    def test_get_stats_by_scope_returns_correct_counts(self):
        """Test get_stats_by_scope returns correct counts."""
        stats = self.manager.get_stats_by_scope()
        
        assert stats[StateScope.USER.value] == 2
        assert stats[StateScope.SESSION.value] == 1
        assert stats[StateScope.GLOBAL.value] == 1
        
    def test_get_stats_by_type_returns_correct_counts(self):
        """Test get_stats_by_type returns correct counts."""
        stats = self.manager.get_stats_by_type()
        
        # Most entries use default cache data type
        assert stats[StateType.CACHE_DATA.value] >= 1
        assert stats[StateType.USER_PREFERENCES.value] >= 2  # From user entries
        assert stats[StateType.SESSION_DATA.value] >= 1  # From session entry


class TestUnifiedStateManagerThreadSafety:
    """Tests for thread-safe operations and concurrency."""
    
    def setup_method(self, method):
        """Set up test manager for each test."""
        mock_env = Mock()
        mock_env.get.side_effect = lambda key, default: default
        with patch('netra_backend.app.core.managers.unified_state_manager.IsolatedEnvironment', return_value=mock_env):
            self.manager = UnifiedStateManager()
    
    def test_concurrent_set_operations_thread_safe(self):
        """Test concurrent set operations are thread safe."""
        results = {}
        errors = []
        
        def set_value(thread_id):
            try:
                key = f"thread_{thread_id}"
                value = f"value_{thread_id}"
                self.manager.set(key, value)
                results[thread_id] = self.manager.get(key)
            except Exception as e:
                errors.append(e)
        
        threads = []
        for i in range(10):
            thread = threading.Thread(target=set_value, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert len(errors) == 0
        assert len(results) == 10
        for i in range(10):
            assert results[i] == f"value_{i}"
            
    def test_concurrent_get_operations_thread_safe(self):
        """Test concurrent get operations are thread safe."""
        # Set up initial data
        for i in range(10):
            self.manager.set(f"key_{i}", f"value_{i}")
        
        results = {}
        errors = []
        
        def get_value(thread_id):
            try:
                key = f"key_{thread_id}"
                results[thread_id] = self.manager.get(key)
            except Exception as e:
                errors.append(e)
        
        threads = []
        for i in range(10):
            thread = threading.Thread(target=get_value, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert len(errors) == 0
        assert len(results) == 10
        for i in range(10):
            assert results[i] == f"value_{i}"
            
    def test_concurrent_update_operations_thread_safe(self):
        """Test concurrent update operations are thread safe."""
        self.manager.set("counter", 0)
        
        errors = []
        
        def increment_counter():
            try:
                self.manager.update("counter", lambda x: x + 1)
            except Exception as e:
                errors.append(e)
        
        threads = []
        for i in range(10):
            thread = threading.Thread(target=increment_counter)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert len(errors) == 0
        final_value = self.manager.get("counter")
        assert final_value == 10
        
    def test_concurrent_delete_operations_thread_safe(self):
        """Test concurrent delete operations are thread safe."""
        # Set up initial data
        for i in range(10):
            self.manager.set(f"key_{i}", f"value_{i}")
        
        results = {}
        errors = []
        
        def delete_value(thread_id):
            try:
                key = f"key_{thread_id}"
                results[thread_id] = self.manager.delete(key)
            except Exception as e:
                errors.append(e)
        
        threads = []
        for i in range(10):
            thread = threading.Thread(target=delete_value, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert len(errors) == 0
        # All deletes should succeed
        for i in range(10):
            assert results[i] is True
            assert self.manager.get(f"key_{i}") is None


class TestUnifiedStateManagerMemoryManagement:
    """Tests for memory limits and cleanup procedures."""
    
    def setup_method(self, method):
        """Set up test manager with small memory limit."""
        mock_env = Mock()
        mock_env.get.side_effect = lambda key, default: default
        with patch('netra_backend.app.core.managers.unified_state_manager.IsolatedEnvironment', return_value=mock_env):
            self.manager = UnifiedStateManager(max_memory_entries=5)
    
    def test_memory_limit_enforcement_evicts_lru_entries(self):
        """Test memory limit enforcement evicts least recently used entries."""
        import time
        
        # Fill up to limit
        for i in range(5):
            self.manager.set(f"key_{i}", f"value_{i}")
            time.sleep(0.001)  # Ensure different creation times
        
        # Small delay to ensure access time is distinguishable
        time.sleep(0.01)
        
        # Access key_0 to make it recently used
        self.manager.get("key_0")
        
        # Add one more entry to trigger eviction
        self.manager.set("key_5", "value_5")
        
        # key_0 should still exist (recently used)
        assert self.manager.get("key_0") == "value_0"
        # key_1 should be evicted (least recently used)
        assert self.manager.get("key_1") is None
        # Newest entry should exist
        assert self.manager.get("key_5") == "value_5"
        
    def test_memory_limit_enforcement_maintains_limit(self):
        """Test memory limit enforcement maintains max entries limit."""
        # Add more entries than limit
        for i in range(10):
            self.manager.set(f"key_{i}", f"value_{i}")
        
        # Should not exceed limit
        assert len(self.manager._states) <= self.manager.max_memory_entries
        
    def test_memory_usage_calculation_in_status(self):
        """Test memory usage percentage calculation in status."""
        # Add entries
        for i in range(3):
            self.manager.set(f"key_{i}", f"value_{i}")
        
        status = self.manager.get_status()
        
        assert status["total_entries"] == 3
        assert status["memory_limit"] == 5
        assert status["memory_usage_percent"] == 60.0  # 3/5 * 100
        
    def test_enforce_memory_limits_removes_oldest_accessed(self):
        """Test _enforce_memory_limits removes entries by access time."""
        import time
        
        # Fill to limit
        for i in range(5):
            self.manager.set(f"key_{i}", f"value_{i}")
            time.sleep(0.001)  # Ensure different timestamps
        
        # Small delay before access operations
        time.sleep(0.01)
        
        # Access some entries to update access times
        self.manager.get("key_2")
        self.manager.get("key_4")
        
        # Force memory limit enforcement
        self.manager.set("key_5", "value_5")
        
        # Recently accessed entries should remain
        assert self.manager.get("key_2") == "value_2"
        assert self.manager.get("key_4") == "value_4"
        assert self.manager.get("key_5") == "value_5"
        
        # Verify only 5 entries remain (at the memory limit)
        total_entries = len(self.manager._states)
        assert total_entries == 5
        
        # At least one of the oldest accessed entries should be removed
        oldest_keys_removed = 0
        for key in ["key_0", "key_1", "key_3"]:
            if self.manager.get(key) is None:
                oldest_keys_removed += 1
        
        # At least one oldest key should have been removed to make space
        assert oldest_keys_removed >= 1


class TestUnifiedStateManagerWebSocketIntegration:
    """Tests for WebSocket integration and real-time notifications."""
    
    def setup_method(self, method):
        """Set up test manager with mocked WebSocket manager."""
        mock_env = Mock()
        mock_env.get.side_effect = lambda key, default: default
        with patch('netra_backend.app.core.managers.unified_state_manager.IsolatedEnvironment', return_value=mock_env):
            self.manager = UnifiedStateManager()
            
        self.mock_websocket_manager = Mock()
        self.mock_websocket_manager.broadcast_system_message = AsyncMock()
        self.manager.set_websocket_manager(self.mock_websocket_manager)
        
    def test_set_websocket_manager_stores_reference(self):
        """Test set_websocket_manager stores manager reference."""
        mock_manager = Mock()
        self.manager.set_websocket_manager(mock_manager)
        
        assert self.manager._websocket_manager is mock_manager
        
    def test_enable_websocket_events_controls_emission(self):
        """Test enable_websocket_events controls event emission."""
        self.manager.enable_websocket_events(False)
        assert self.manager._enable_websocket_events is False
        
        self.manager.enable_websocket_events(True)
        assert self.manager._enable_websocket_events is True
        
    @pytest.mark.asyncio
    async def test_emit_websocket_event_sends_message_when_enabled(self):
        """Test _emit_websocket_event sends message when enabled."""
        self.manager.enable_websocket_events(True)
        
        test_data = {"key": "test_key", "value": "test_value"}
        await self.manager._emit_websocket_event("test_event", test_data)
        
        self.mock_websocket_manager.broadcast_system_message.assert_called_once()
        call_args = self.mock_websocket_manager.broadcast_system_message.call_args[0][0]
        assert call_args["type"] == "state_test_event"
        assert call_args["data"] == test_data
        
    @pytest.mark.asyncio
    async def test_emit_websocket_event_skips_when_disabled(self):
        """Test _emit_websocket_event skips when disabled."""
        self.manager.enable_websocket_events(False)
        
        test_data = {"key": "test_key", "value": "test_value"}
        await self.manager._emit_websocket_event("test_event", test_data)
        
        self.mock_websocket_manager.broadcast_system_message.assert_not_called()
        
    @pytest.mark.asyncio
    async def test_emit_websocket_event_handles_missing_manager(self):
        """Test _emit_websocket_event handles missing manager gracefully."""
        self.manager.set_websocket_manager(None)
        self.manager.enable_websocket_events(True)
        
        test_data = {"key": "test_key", "value": "test_value"}
        # Should not raise exception
        await self.manager._emit_websocket_event("test_event", test_data)
        
    @pytest.mark.asyncio
    async def test_emit_websocket_event_handles_broadcast_exception(self):
        """Test _emit_websocket_event handles broadcast exceptions gracefully."""
        self.mock_websocket_manager.broadcast_system_message.side_effect = Exception("Network error")
        
        test_data = {"key": "test_key", "value": "test_value"}
        # Should not raise exception
        await self.manager._emit_websocket_event("test_event", test_data)


class TestUnifiedStateManagerContextManagers:
    """Tests for context managers (session, agent, thread)."""
    
    def setup_method(self, method):
        """Set up test manager for each test."""
        mock_env = Mock()
        mock_env.get.side_effect = lambda key, default: default
        with patch('netra_backend.app.core.managers.unified_state_manager.IsolatedEnvironment', return_value=mock_env):
            self.manager = UnifiedStateManager()
    
    @pytest.mark.asyncio
    async def test_session_context_provides_scoped_operations(self):
        """Test session context provides session-scoped operations."""
        session_id = "session123"
        
        async with self.manager.session_context(session_id) as session_ctx:
            session_ctx.set("key", "value")
            result = session_ctx.get("key")
            assert result == "value"
            
            # Check internal storage uses correct key format
            full_key = f"session:{session_id}:key"
            assert full_key in self.manager._states
            
    @pytest.mark.asyncio
    async def test_session_context_delete_removes_scoped_key(self):
        """Test session context delete removes session-scoped key."""
        session_id = "session123"
        
        async with self.manager.session_context(session_id) as session_ctx:
            session_ctx.set("key", "value")
            result = session_ctx.delete("key")
            assert result is True
            
            full_key = f"session:{session_id}:key"
            assert full_key not in self.manager._states
            
    @pytest.mark.asyncio
    async def test_agent_context_provides_scoped_operations(self):
        """Test agent context provides agent-scoped operations."""
        agent_id = "agent123"
        
        async with self.manager.agent_context(agent_id) as agent_ctx:
            agent_ctx.set("status", "running")
            result = agent_ctx.get("status")
            assert result == "running"
            
            # Check internal storage uses correct key format
            full_key = f"agent:{agent_id}:status"
            assert full_key in self.manager._states
            
    @pytest.mark.asyncio
    async def test_agent_context_uses_default_ttl(self):
        """Test agent context uses default TTL for entries."""
        agent_id = "agent123"
        
        async with self.manager.agent_context(agent_id) as agent_ctx:
            agent_ctx.set("status", "running")
            
            full_key = f"agent:{agent_id}:status"
            entry = self.manager._states[full_key]
            assert entry.ttl_seconds == 3600  # Default agent TTL
            
    @pytest.mark.asyncio
    async def test_thread_context_provides_scoped_operations(self):
        """Test thread context provides thread-scoped operations."""
        thread_id = "thread123"
        
        async with self.manager.thread_context(thread_id) as thread_ctx:
            thread_ctx.set("history", ["msg1", "msg2"])
            result = thread_ctx.get("history")
            assert result == ["msg1", "msg2"]
            
            # Check internal storage uses correct key format
            full_key = f"thread:{thread_id}:history"
            assert full_key in self.manager._states
            
    @pytest.mark.asyncio
    async def test_context_managers_isolate_between_instances(self):
        """Test context managers isolate state between different instances."""
        async with self.manager.session_context("session1") as ctx1:
            async with self.manager.session_context("session2") as ctx2:
                ctx1.set("key", "value1")
                ctx2.set("key", "value2")
                
                assert ctx1.get("key") == "value1"
                assert ctx2.get("key") == "value2"


class TestUnifiedStateManagerEventSystem:
    """Tests for state change event system and listeners."""
    
    def setup_method(self, method):
        """Set up test manager for each test."""
        mock_env = Mock()
        mock_env.get.side_effect = lambda key, default: default
        with patch('netra_backend.app.core.managers.unified_state_manager.IsolatedEnvironment', return_value=mock_env):
            self.manager = UnifiedStateManager()
        
        self.received_events = []
        
        def test_listener(event):
            self.received_events.append(event)
        
        self.test_listener = test_listener
        
    def test_add_change_listener_adds_listener(self):
        """Test add_change_listener adds listener to list."""
        self.manager.add_change_listener(self.test_listener)
        
        assert self.test_listener in self.manager._change_listeners
        
    def test_remove_change_listener_removes_listener(self):
        """Test remove_change_listener removes listener from list."""
        self.manager.add_change_listener(self.test_listener)
        self.manager.remove_change_listener(self.test_listener)
        
        assert self.test_listener not in self.manager._change_listeners
        
    def test_remove_change_listener_handles_missing_listener(self):
        """Test remove_change_listener handles missing listener gracefully."""
        # Should not raise exception
        self.manager.remove_change_listener(self.test_listener)
        
    @pytest.mark.asyncio
    async def test_queue_change_event_adds_to_queue(self):
        """Test _queue_change_event adds event to processing queue."""
        event = StateChangeEvent(
            key="test_key",
            old_value=None,
            new_value="test_value",
            change_type="create",
            scope=StateScope.GLOBAL,
            state_type=StateType.CACHE_DATA
        )
        
        await self.manager._queue_change_event(event)
        
        # Queue should have the event
        assert self.manager._event_queue.qsize() == 1
        
    @pytest.mark.asyncio
    async def test_process_state_change_event_notifies_listeners(self):
        """Test _process_state_change_event notifies all listeners."""
        self.manager.add_change_listener(self.test_listener)
        
        event = StateChangeEvent(
            key="test_key",
            old_value=None,
            new_value="test_value",
            change_type="create",
            scope=StateScope.GLOBAL,
            state_type=StateType.CACHE_DATA
        )
        
        await self.manager._process_state_change_event(event)
        
        assert len(self.received_events) == 1
        assert self.received_events[0] == event
        
    @pytest.mark.asyncio
    async def test_process_state_change_event_handles_listener_exceptions(self):
        """Test _process_state_change_event handles listener exceptions gracefully."""
        def failing_listener(event):
            raise Exception("Listener error")
        
        self.manager.add_change_listener(failing_listener)
        self.manager.add_change_listener(self.test_listener)
        
        event = StateChangeEvent(
            key="test_key",
            old_value=None,
            new_value="test_value",
            change_type="create",
            scope=StateScope.GLOBAL,
            state_type=StateType.CACHE_DATA
        )
        
        # Should not raise exception and should still notify other listeners
        await self.manager._process_state_change_event(event)
        
        assert len(self.received_events) == 1


class TestUnifiedStateManagerStatusMonitoring:
    """Tests for status reporting and health monitoring."""
    
    def setup_method(self, method):
        """Set up test manager for each test."""
        mock_env = Mock()
        mock_env.get.side_effect = lambda key, default: default
        with patch('netra_backend.app.core.managers.unified_state_manager.IsolatedEnvironment', return_value=mock_env):
            self.manager = UnifiedStateManager(max_memory_entries=100)
    
    def test_get_status_returns_comprehensive_info(self):
        """Test get_status returns comprehensive manager information."""
        # Add some data
        self.manager.set("key1", "value1", scope=StateScope.USER)
        self.manager.set("key2", "value2", scope=StateScope.SESSION)
        
        status = self.manager.get_status()
        
        required_keys = {
            "user_id", "total_entries", "memory_limit", "memory_usage_percent",
            "cleanup_enabled", "persistence_enabled", "versioning_enabled",
            "scope_distribution", "type_distribution", "metrics", "active_locks",
            "change_listeners", "event_queue_size", "background_tasks"
        }
        
        assert set(status.keys()).issuperset(required_keys)
        assert status["total_entries"] == 2
        assert status["memory_limit"] == 100
        assert status["memory_usage_percent"] == 2.0
        
    def test_get_health_status_returns_health_info(self):
        """Test get_health_status returns health status."""
        health = self.manager.get_health_status()
        
        required_keys = {
            "status", "total_entries", "memory_usage_percent", "event_queue_size"
        }
        
        assert set(health.keys()) == required_keys
        assert health["status"] in ["healthy", "unhealthy"]
        
    def test_get_health_status_reports_healthy_when_normal(self):
        """Test get_health_status reports healthy under normal conditions."""
        health = self.manager.get_health_status()
        
        assert health["status"] == "healthy"
        assert health["memory_usage_percent"] < 90
        assert health["event_queue_size"] < 1000
        
    def test_get_health_status_reports_unhealthy_when_memory_high(self):
        """Test get_health_status reports unhealthy when memory usage is high."""
        # Fill up memory to trigger unhealthy status
        for i in range(95):  # 95% of 100 limit
            self.manager.set(f"key_{i}", f"value_{i}")
        
        health = self.manager.get_health_status()
        
        assert health["status"] == "unhealthy"
        assert health["memory_usage_percent"] >= 90
        
    def test_metrics_track_operations_correctly(self):
        """Test operation metrics are tracked correctly."""
        # Perform various operations
        self.manager.set("key1", "value1")
        self.manager.get("key1")
        self.manager.get("nonexistent", "default")
        self.manager.delete("key1")
        
        status = self.manager.get_status()
        metrics = status["metrics"]
        
        assert metrics["set_operations"] == 1
        assert metrics["get_operations"] == 2
        assert metrics["delete_operations"] == 1
        assert metrics["total_operations"] == 4
        assert metrics["cache_hits"] == 1
        assert metrics["cache_misses"] == 1
        
    @pytest.mark.asyncio
    async def test_shutdown_cancels_background_tasks(self):
        """Test shutdown cancels running background tasks."""
        # Start background tasks
        if not self.manager._cleanup_task:
            self.manager._cleanup_task = asyncio.create_task(asyncio.sleep(10))
        if not self.manager._event_processing_task:
            self.manager._event_processing_task = asyncio.create_task(asyncio.sleep(10))
        
        await self.manager.shutdown()
        
        assert self.manager._cleanup_task.cancelled()
        assert self.manager._event_processing_task.cancelled()


class TestStateManagerFactory:
    """Tests for StateManagerFactory and user isolation."""
    
    def test_get_global_manager_returns_singleton(self):
        """Test get_global_manager returns same instance on multiple calls."""
        # Clear factory state first
        StateManagerFactory._global_manager = None
        
        manager1 = StateManagerFactory.get_global_manager()
        manager2 = StateManagerFactory.get_global_manager()
        
        assert manager1 is manager2
        assert manager1.user_id is None
        
    def test_get_user_manager_returns_user_specific_instance(self):
        """Test get_user_manager returns user-specific instances."""
        # Clear factory state first
        StateManagerFactory._user_managers.clear()
        
        manager1 = StateManagerFactory.get_user_manager("user1")
        manager2 = StateManagerFactory.get_user_manager("user2")
        manager1_again = StateManagerFactory.get_user_manager("user1")
        
        assert manager1 is not manager2
        assert manager1 is manager1_again
        assert manager1.user_id == "user1"
        assert manager2.user_id == "user2"
        
    def test_user_managers_provide_state_isolation(self):
        """Test user managers provide complete state isolation."""
        manager1 = StateManagerFactory.get_user_manager("user1")
        manager2 = StateManagerFactory.get_user_manager("user2")
        
        manager1.set("shared_key", "value1")
        manager2.set("shared_key", "value2")
        
        assert manager1.get("shared_key") == "value1"
        assert manager2.get("shared_key") == "value2"
        
    @pytest.mark.asyncio
    async def test_shutdown_all_managers_shuts_down_all_instances(self):
        """Test shutdown_all_managers shuts down all manager instances."""
        # Create some managers
        global_manager = StateManagerFactory.get_global_manager()
        user_manager1 = StateManagerFactory.get_user_manager("user1")
        user_manager2 = StateManagerFactory.get_user_manager("user2")
        
        # Mock shutdown methods
        global_manager.shutdown = AsyncMock()
        user_manager1.shutdown = AsyncMock()
        user_manager2.shutdown = AsyncMock()
        
        await StateManagerFactory.shutdown_all_managers()
        
        global_manager.shutdown.assert_called_once()
        user_manager1.shutdown.assert_called_once()
        user_manager2.shutdown.assert_called_once()
        
        # References should be cleared
        assert StateManagerFactory._global_manager is None
        assert len(StateManagerFactory._user_managers) == 0
        
    def test_get_manager_count_returns_correct_counts(self):
        """Test get_manager_count returns correct counts."""
        # Clear and set up known state
        StateManagerFactory._global_manager = None
        StateManagerFactory._user_managers.clear()
        
        counts = StateManagerFactory.get_manager_count()
        assert counts["global"] == 0
        assert counts["user_specific"] == 0
        assert counts["total"] == 0
        
        # Create managers
        StateManagerFactory.get_global_manager()
        StateManagerFactory.get_user_manager("user1")
        StateManagerFactory.get_user_manager("user2")
        
        counts = StateManagerFactory.get_manager_count()
        assert counts["global"] == 1
        assert counts["user_specific"] == 2
        assert counts["total"] == 3


class TestConvenienceFunctions:
    """Tests for convenience functions and legacy compatibility."""
    
    def test_get_state_manager_returns_global_when_no_user(self):
        """Test get_state_manager returns global manager when no user_id."""
        manager = get_state_manager()
        
        assert manager.user_id is None
        assert manager is StateManagerFactory.get_global_manager()
        
    def test_get_state_manager_returns_user_manager_when_user_provided(self):
        """Test get_state_manager returns user manager when user_id provided."""
        user_id = "test_user"
        manager = get_state_manager(user_id)
        
        assert manager.user_id == user_id
        assert manager is StateManagerFactory.get_user_manager(user_id)
        
    def test_legacy_compatibility_functions_return_global_manager(self):
        """Test legacy compatibility functions return global manager."""
        from netra_backend.app.core.managers.unified_state_manager import (
            get_agent_state_manager,
            get_session_state_manager,
            get_websocket_state_manager,
            get_message_state_manager
        )
        
        agent_manager = get_agent_state_manager()
        session_manager = get_session_state_manager()
        websocket_manager = get_websocket_state_manager()
        message_manager = get_message_state_manager()
        
        # All should return the same global manager
        global_manager = StateManagerFactory.get_global_manager()
        assert agent_manager is global_manager
        assert session_manager is global_manager
        assert websocket_manager is global_manager
        assert message_manager is global_manager


class TestAsyncCleanupOperations:
    """Tests for asynchronous cleanup operations and TTL management."""
    
    def setup_method(self, method):
        """Set up test manager for each test."""
        mock_env = Mock()
        mock_env.get.side_effect = lambda key, default: default
        with patch('netra_backend.app.core.managers.unified_state_manager.IsolatedEnvironment', return_value=mock_env):
            self.manager = UnifiedStateManager(cleanup_interval=1)
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_entries_removes_expired(self):
        """Test _cleanup_expired_entries removes expired entries."""
        # Add entries with different TTLs
        self.manager.set("short_ttl", "value1", ttl_seconds=1)
        self.manager.set("long_ttl", "value2", ttl_seconds=10)
        self.manager.set("no_ttl", "value3")
        
        # Wait for short TTL to expire
        await asyncio.sleep(1.1)
        
        # Run cleanup
        await self.manager._cleanup_expired_entries()
        
        # Check results
        assert self.manager.get("short_ttl") is None
        assert self.manager.get("long_ttl") == "value2"
        assert self.manager.get("no_ttl") == "value3"
        
    @pytest.mark.asyncio
    async def test_cleanup_expired_entries_updates_metrics(self):
        """Test _cleanup_expired_entries updates cleanup metrics."""
        initial_count = self.manager._metrics["expired_cleanups"]
        
        # Add expired entry
        self.manager.set("expired", "value", ttl_seconds=1)
        await asyncio.sleep(1.1)
        
        # Run cleanup
        await self.manager._cleanup_expired_entries()
        
        # Check metrics updated
        assert self.manager._metrics["expired_cleanups"] == initial_count + 1
        
    @pytest.mark.asyncio
    async def test_cleanup_expired_entries_removes_from_indices(self):
        """Test _cleanup_expired_entries removes entries from indices."""
        # Add entry with specific attributes for indexing
        self.manager.set(
            "test_key",
            "test_value",
            ttl_seconds=1,
            scope=StateScope.USER,
            user_id="test_user"
        )
        
        # Verify entry is in indices
        assert "test_key" in self.manager._scope_index[StateScope.USER]
        assert "test_key" in self.manager._user_index["test_user"]
        
        # Wait for expiry and cleanup
        await asyncio.sleep(1.1)
        await self.manager._cleanup_expired_entries()
        
        # Verify entry removed from indices
        assert "test_key" not in self.manager._scope_index[StateScope.USER]
        assert "test_key" not in self.manager._user_index["test_user"]


class TestStateChangeEvents:
    """Tests for StateChangeEvent creation and handling."""
    
    def test_state_change_event_creation_with_all_fields(self):
        """Test StateChangeEvent creation with all fields."""
        event = StateChangeEvent(
            key="test_key",
            old_value="old_value",
            new_value="new_value",
            change_type="update",
            scope=StateScope.USER,
            state_type=StateType.USER_PREFERENCES,
            user_id="user123",
            session_id="session123",
            thread_id="thread123",
            agent_id="agent123"
        )
        
        assert event.key == "test_key"
        assert event.old_value == "old_value"
        assert event.new_value == "new_value"
        assert event.change_type == "update"
        assert event.scope == StateScope.USER
        assert event.state_type == StateType.USER_PREFERENCES
        assert event.user_id == "user123"
        assert event.session_id == "session123"
        assert event.thread_id == "thread123"
        assert event.agent_id == "agent123"
        assert isinstance(event.timestamp, float)


class TestStateQueryFiltering:
    """Tests for StateQuery creation and filtering logic."""
    
    def test_state_query_creation_with_all_filters(self):
        """Test StateQuery creation with all possible filters."""
        current_time = time.time()
        
        query = StateQuery(
            scope=StateScope.USER,
            state_type=StateType.USER_PREFERENCES,
            user_id="user123",
            session_id="session123",
            thread_id="thread123",
            agent_id="agent123",
            status=StateStatus.ACTIVE,
            created_after=current_time - 3600,
            created_before=current_time,
            updated_after=current_time - 1800,
            updated_before=current_time,
            include_expired=True,
            key_pattern="user_.*",
            limit=10
        )
        
        assert query.scope == StateScope.USER
        assert query.state_type == StateType.USER_PREFERENCES
        assert query.user_id == "user123"
        assert query.session_id == "session123"
        assert query.thread_id == "thread123"
        assert query.agent_id == "agent123"
        assert query.status == StateStatus.ACTIVE
        assert query.created_after == current_time - 3600
        assert query.created_before == current_time
        assert query.updated_after == current_time - 1800
        assert query.updated_before == current_time
        assert query.include_expired is True
        assert query.key_pattern == "user_.*"
        assert query.limit == 10


class TestContextHelperClasses:
    """Tests for context helper classes (SessionStateContext, etc.)."""
    
    def setup_method(self, method):
        """Set up test manager for each test."""
        mock_env = Mock()
        mock_env.get.side_effect = lambda key, default: default
        with patch('netra_backend.app.core.managers.unified_state_manager.IsolatedEnvironment', return_value=mock_env):
            self.manager = UnifiedStateManager()
    
    def test_session_state_context_operations(self):
        """Test SessionStateContext provides correct operations."""
        session_id = "session123"
        context = SessionStateContext(self.manager, session_id)
        
        # Test set and get
        context.set("key", "value")
        result = context.get("key")
        assert result == "value"
        
        # Test delete
        deleted = context.delete("key")
        assert deleted is True
        assert context.get("key") is None
        
    def test_agent_state_context_operations(self):
        """Test AgentStateContext provides correct operations."""
        agent_id = "agent123"
        context = AgentStateContext(self.manager, agent_id)
        
        # Test set and get
        context.set("status", "running")
        result = context.get("status")
        assert result == "running"
        
        # Test delete
        deleted = context.delete("status")
        assert deleted is True
        assert context.get("status") is None
        
    def test_thread_state_context_operations(self):
        """Test ThreadStateContext provides correct operations."""
        thread_id = "thread123"
        context = ThreadStateContext(self.manager, thread_id)
        
        # Test set and get
        context.set("history", ["msg1"])
        result = context.get("history")
        assert result == ["msg1"]
        
        # Test delete
        deleted = context.delete("history")
        assert deleted is True
        assert context.get("history") is None
        
    def test_context_classes_use_correct_key_format(self):
        """Test context classes generate correct internal keys."""
        session_context = SessionStateContext(self.manager, "session123")
        agent_context = AgentStateContext(self.manager, "agent123")
        thread_context = ThreadStateContext(self.manager, "thread123")
        
        session_context.set("key", "session_value")
        agent_context.set("key", "agent_value")
        thread_context.set("key", "thread_value")
        
        # Check internal keys
        assert "session:session123:key" in self.manager._states
        assert "agent:agent123:key" in self.manager._states
        assert "thread:thread123:key" in self.manager._states


# Performance and Edge Case Tests

class TestPerformanceAndLimits:
    """Tests for performance characteristics and edge cases."""
    
    def setup_method(self, method):
        """Set up test manager for performance tests."""
        mock_env = Mock()
        mock_env.get.side_effect = lambda key, default: default
        with patch('netra_backend.app.core.managers.unified_state_manager.IsolatedEnvironment', return_value=mock_env):
            self.manager = UnifiedStateManager(max_memory_entries=1000)
    
    def test_large_number_of_entries_performance(self):
        """Test performance with large number of entries."""
        # This should not timeout with reasonable performance
        start_time = time.time()
        
        for i in range(500):
            self.manager.set(f"key_{i}", f"value_{i}")
        
        elapsed = time.time() - start_time
        assert elapsed < 5.0  # Should complete in reasonable time
        
        # Query should also be reasonably fast
        start_time = time.time()
        keys = self.manager.keys()
        elapsed = time.time() - start_time
        
        assert len(keys) == 500
        assert elapsed < 1.0  # Query should be fast
        
    def test_concurrent_access_with_many_operations(self):
        """Test concurrent access with many operations doesn't deadlock."""
        def worker(worker_id):
            for i in range(50):
                key = f"worker_{worker_id}_key_{i}"
                self.manager.set(key, f"value_{i}")
                result = self.manager.get(key)
                assert result == f"value_{i}"
        
        threads = []
        for worker_id in range(10):
            thread = threading.Thread(target=worker, args=(worker_id,))
            threads.append(thread)
            thread.start()
        
        # Should complete without deadlock
        for thread in threads:
            thread.join(timeout=10.0)  # 10 second timeout
            assert not thread.is_alive()
        
        # All entries should exist
        total_entries = len(self.manager._states)
        assert total_entries == 500  # 10 workers * 50 entries each
        
    def test_memory_cleanup_with_rapid_changes(self):
        """Test memory cleanup handles rapid state changes."""
        # Rapidly add and remove entries to test cleanup robustness
        for cycle in range(5):
            # Add many entries
            for i in range(100):
                self.manager.set(f"cycle_{cycle}_key_{i}", f"value_{i}")
            
            # Remove half of them
            for i in range(0, 100, 2):
                self.manager.delete(f"cycle_{cycle}_key_{i}")
        
        # Should maintain reasonable memory usage
        total_entries = len(self.manager._states)
        assert total_entries <= self.manager.max_memory_entries
        
    def test_index_consistency_after_many_operations(self):
        """Test internal indices remain consistent after many operations."""
        # Perform many mixed operations
        for i in range(100):
            # Add entries with different scopes and types
            self.manager.set(f"user_key_{i}", f"value_{i}", 
                           scope=StateScope.USER, user_id=f"user_{i % 10}")
            self.manager.set(f"session_key_{i}", f"value_{i}", 
                           scope=StateScope.SESSION, session_id=f"session_{i % 5}")
            
            # Update some entries
            if i % 3 == 0:
                self.manager.update(f"user_key_{i}", lambda x: x + "_updated")
            
            # Delete some entries
            if i % 5 == 0 and i > 0:
                self.manager.delete(f"user_key_{i-1}")
        
        # Verify index consistency
        for scope, keys in self.manager._scope_index.items():
            for key in keys:
                if key in self.manager._states:
                    entry = self.manager._states[key]
                    assert entry.scope == scope
        
        for user_id, keys in self.manager._user_index.items():
            for key in keys:
                if key in self.manager._states:
                    entry = self.manager._states[key]
                    assert entry.user_id == user_id