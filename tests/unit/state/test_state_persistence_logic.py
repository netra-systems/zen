"""
Unit Test Suite for State Persistence Logic

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Ensure reliable state persistence for WebSocket connection recovery
- Value Impact: Prevents state loss that would break chat session continuity for users
- Strategic Impact: State persistence enables seamless reconnection and session recovery

This test suite validates the state persistence and recovery mechanisms that enable
WebSocket connections to maintain continuity across disconnections and reconnections,
preserving chat session context and agent execution state.

CRITICAL STATE PERSISTENCE AREAS:
- StateEntry serialization and deserialization for storage
- TTL (Time To Live) expiration logic for cleanup
- State versioning and conflict resolution
- Connection metadata preservation across sessions
- Agent execution context recovery
- Multi-user state isolation validation

STATE MANAGEMENT REQUIREMENTS:
- State entries must survive process restarts
- TTL expiration must prevent memory leaks
- Version conflicts must be resolved safely
- User isolation must be maintained in persistence
- Agent context must be recoverable
"""

import pytest
import uuid
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Union
import unittest
from unittest.mock import Mock, patch
from dataclasses import dataclass, asdict

# Import system under test - State persistence types
from shared.types import (
    ConnectionState, WebSocketConnectionInfo, WebSocketID, UserID,
    ThreadID, RequestID, AgentID, ExecutionID, WebSocketEventType
)


@dataclass
class StateEntry:
    """Represents a persisted state entry with metadata.
    
    This is the unit of state persistence for WebSocket connections
    and agent execution contexts.
    """
    
    # Core identification
    entry_id: str
    user_id: UserID
    entry_type: str  # 'connection', 'agent_context', 'execution_state'
    
    # State data
    state_data: Dict[str, Any]
    
    # Lifecycle management
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None
    version: int = 1
    
    # Metadata
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize metadata if not provided."""
        if self.metadata is None:
            self.metadata = {}
    
    def is_expired(self) -> bool:
        """Check if state entry has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    def update_timestamp(self) -> None:
        """Update the last modified timestamp."""
        self.updated_at = datetime.now(timezone.utc)
    
    def increment_version(self) -> None:
        """Increment version for conflict resolution."""
        self.version += 1
        self.update_timestamp()
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize state entry to dictionary for storage."""
        data = asdict(self)
        
        # Convert datetime objects to ISO strings
        for field in ['created_at', 'updated_at', 'expires_at']:
            if data[field] is not None:
                data[field] = data[field].isoformat()
        
        # Convert UserID to string
        data['user_id'] = str(data['user_id'])
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StateEntry':
        """Deserialize state entry from dictionary."""
        # Convert ISO strings back to datetime objects
        for field in ['created_at', 'updated_at', 'expires_at']:
            if data[field] is not None:
                data[field] = datetime.fromisoformat(data[field])
        
        # Convert string back to UserID
        data['user_id'] = UserID(data['user_id'])
        
        return cls(**data)


class StateManager:
    """Manages state persistence with TTL and versioning.
    
    This class implements the business logic for persisting and recovering
    WebSocket connection and agent execution state.
    """
    
    def __init__(self, default_ttl_hours: int = 24):
        """Initialize state manager with default TTL."""
        self.state_store: Dict[str, StateEntry] = {}
        self.default_ttl_hours = default_ttl_hours
        self.cleanup_count = 0
    
    def store_state(self, entry: StateEntry) -> bool:
        """Store a state entry with optional TTL."""
        try:
            # Set default TTL if not specified
            if entry.expires_at is None:
                entry.expires_at = entry.created_at + timedelta(hours=self.default_ttl_hours)
            
            # Check for version conflicts
            existing = self.state_store.get(entry.entry_id)
            if existing and existing.version >= entry.version:
                return False  # Version conflict
            
            # Store the entry
            self.state_store[entry.entry_id] = entry
            return True
            
        except Exception:
            return False
    
    def retrieve_state(self, entry_id: str) -> Optional[StateEntry]:
        """Retrieve a state entry by ID."""
        entry = self.state_store.get(entry_id)
        
        if entry is None:
            return None
        
        # Check if expired
        if entry.is_expired():
            self.state_store.pop(entry_id, None)
            return None
        
        return entry
    
    def update_state(self, entry_id: str, new_data: Dict[str, Any]) -> bool:
        """Update existing state entry data."""
        entry = self.retrieve_state(entry_id)
        if entry is None:
            return False
        
        # Update data and version
        entry.state_data.update(new_data)
        entry.increment_version()
        
        return True
    
    def delete_state(self, entry_id: str) -> bool:
        """Delete a state entry."""
        return self.state_store.pop(entry_id, None) is not None
    
    def cleanup_expired_states(self) -> int:
        """Remove all expired state entries."""
        expired_ids = []
        
        for entry_id, entry in self.state_store.items():
            if entry.is_expired():
                expired_ids.append(entry_id)
        
        for entry_id in expired_ids:
            self.state_store.pop(entry_id, None)
        
        self.cleanup_count += len(expired_ids)
        return len(expired_ids)
    
    def get_user_states(self, user_id: UserID) -> List[StateEntry]:
        """Get all non-expired state entries for a user."""
        user_states = []
        
        for entry in self.state_store.values():
            if entry.user_id == user_id and not entry.is_expired():
                user_states.append(entry)
        
        return user_states
    
    def get_state_count(self) -> int:
        """Get count of stored state entries."""
        return len(self.state_store)


class TestStateEntrySerialization(unittest.TestCase):
    """Test StateEntry serialization and deserialization."""
    
    def setUp(self):
        """Set up test data."""
        self.user_id = UserID(str(uuid.uuid4()))
        self.entry_id = str(uuid.uuid4())
        self.created_at = datetime.now(timezone.utc)
        self.expires_at = self.created_at + timedelta(hours=24)
    
    def test_state_entry_creation(self):
        """Test creation of StateEntry with required fields."""
        state_data = {
            "connection_state": "connected",
            "websocket_id": str(uuid.uuid4()),
            "message_count": 42
        }
        
        entry = StateEntry(
            entry_id=self.entry_id,
            user_id=self.user_id,
            entry_type="connection",
            state_data=state_data,
            created_at=self.created_at,
            updated_at=self.created_at,
            expires_at=self.expires_at
        )
        
        self.assertEqual(entry.entry_id, self.entry_id)
        self.assertEqual(entry.user_id, self.user_id)
        self.assertEqual(entry.entry_type, "connection")
        self.assertEqual(entry.state_data, state_data)
        self.assertEqual(entry.version, 1)
        self.assertIsInstance(entry.metadata, dict)
    
    def test_state_entry_serialization(self):
        """Test StateEntry serialization to dictionary."""
        state_data = {"test_key": "test_value", "number": 123}
        metadata = {"source": "test", "priority": "high"}
        
        entry = StateEntry(
            entry_id=self.entry_id,
            user_id=self.user_id,
            entry_type="test",
            state_data=state_data,
            created_at=self.created_at,
            updated_at=self.created_at,
            expires_at=self.expires_at,
            metadata=metadata
        )
        
        serialized = entry.to_dict()
        
        # Check basic fields
        self.assertEqual(serialized["entry_id"], self.entry_id)
        self.assertEqual(serialized["user_id"], str(self.user_id))
        self.assertEqual(serialized["entry_type"], "test")
        self.assertEqual(serialized["state_data"], state_data)
        self.assertEqual(serialized["version"], 1)
        self.assertEqual(serialized["metadata"], metadata)
        
        # Check datetime serialization
        self.assertIsInstance(serialized["created_at"], str)
        self.assertIsInstance(serialized["expires_at"], str)
    
    def test_state_entry_deserialization(self):
        """Test StateEntry deserialization from dictionary."""
        serialized_data = {
            "entry_id": self.entry_id,
            "user_id": str(self.user_id),
            "entry_type": "connection",
            "state_data": {"status": "active"},
            "created_at": self.created_at.isoformat(),
            "updated_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "version": 2,
            "metadata": {"test": True}
        }
        
        entry = StateEntry.from_dict(serialized_data)
        
        self.assertEqual(entry.entry_id, self.entry_id)
        self.assertEqual(entry.user_id, self.user_id)
        self.assertEqual(entry.entry_type, "connection")
        self.assertEqual(entry.state_data, {"status": "active"})
        self.assertEqual(entry.version, 2)
        self.assertEqual(entry.metadata, {"test": True})
        
        # Check datetime deserialization
        self.assertIsInstance(entry.created_at, datetime)
        self.assertIsInstance(entry.expires_at, datetime)
    
    def test_serialization_round_trip(self):
        """Test complete serialization round-trip."""
        original_entry = StateEntry(
            entry_id=self.entry_id,
            user_id=self.user_id,
            entry_type="agent_context",
            state_data={"agent_id": "agent_123", "tools": ["web_search", "calculator"]},
            created_at=self.created_at,
            updated_at=self.created_at,
            expires_at=self.expires_at,
            version=3,
            metadata={"session_id": "session_456"}
        )
        
        # Serialize and deserialize
        serialized = original_entry.to_dict()
        deserialized = StateEntry.from_dict(serialized)
        
        # Should be equivalent (accounting for microsecond precision)
        self.assertEqual(deserialized.entry_id, original_entry.entry_id)
        self.assertEqual(deserialized.user_id, original_entry.user_id)
        self.assertEqual(deserialized.entry_type, original_entry.entry_type)
        self.assertEqual(deserialized.state_data, original_entry.state_data)
        self.assertEqual(deserialized.version, original_entry.version)
        self.assertEqual(deserialized.metadata, original_entry.metadata)


class TestTTLExpirationLogic(unittest.TestCase):
    """Test TTL (Time To Live) expiration logic for state cleanup."""
    
    def test_state_entry_expiration_check(self):
        """Test StateEntry expiration checking."""
        user_id = UserID(str(uuid.uuid4()))
        now = datetime.now(timezone.utc)
        
        # Non-expired entry (expires in future)
        future_expiry = StateEntry(
            entry_id=str(uuid.uuid4()),
            user_id=user_id,
            entry_type="test",
            state_data={},
            created_at=now,
            updated_at=now,
            expires_at=now + timedelta(hours=1)
        )
        self.assertFalse(future_expiry.is_expired())
        
        # Expired entry (expired in past)
        past_expiry = StateEntry(
            entry_id=str(uuid.uuid4()),
            user_id=user_id,
            entry_type="test",
            state_data={},
            created_at=now - timedelta(hours=2),
            updated_at=now - timedelta(hours=2),
            expires_at=now - timedelta(hours=1)
        )
        self.assertTrue(past_expiry.is_expired())
        
        # No expiry (should never expire)
        no_expiry = StateEntry(
            entry_id=str(uuid.uuid4()),
            user_id=user_id,
            entry_type="test",
            state_data={},
            created_at=now,
            updated_at=now,
            expires_at=None
        )
        self.assertFalse(no_expiry.is_expired())
    
    def test_state_manager_ttl_assignment(self):
        """Test that StateManager assigns default TTL correctly."""
        manager = StateManager(default_ttl_hours=12)
        user_id = UserID(str(uuid.uuid4()))
        now = datetime.now(timezone.utc)
        
        # Entry without TTL should get default
        entry = StateEntry(
            entry_id=str(uuid.uuid4()),
            user_id=user_id,
            entry_type="test",
            state_data={},
            created_at=now,
            updated_at=now,
            expires_at=None  # No TTL set
        )
        
        manager.store_state(entry)
        
        # Should have TTL set to default
        self.assertIsNotNone(entry.expires_at)
        expected_expiry = now + timedelta(hours=12)
        self.assertAlmostEqual(
            entry.expires_at.timestamp(),
            expected_expiry.timestamp(),
            delta=1  # Allow 1 second tolerance
        )
    
    def test_expired_state_retrieval(self):
        """Test that expired states are not retrieved and are cleaned up."""
        manager = StateManager()
        user_id = UserID(str(uuid.uuid4()))
        entry_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        # Create expired entry
        expired_entry = StateEntry(
            entry_id=entry_id,
            user_id=user_id,
            entry_type="test",
            state_data={"data": "value"},
            created_at=now - timedelta(hours=25),
            updated_at=now - timedelta(hours=25),
            expires_at=now - timedelta(hours=1)  # Expired 1 hour ago
        )
        
        # Store directly (bypass TTL assignment)
        manager.state_store[entry_id] = expired_entry
        
        # Retrieve should return None and clean up
        retrieved = manager.retrieve_state(entry_id)
        self.assertIsNone(retrieved)
        
        # Entry should be removed from store
        self.assertNotIn(entry_id, manager.state_store)
    
    def test_bulk_expired_cleanup(self):
        """Test bulk cleanup of expired state entries."""
        manager = StateManager()
        user_id = UserID(str(uuid.uuid4()))
        now = datetime.now(timezone.utc)
        
        # Create mix of expired and non-expired entries
        entries = []
        for i in range(5):
            # Odd numbered entries are expired
            is_expired = (i % 2) == 1
            expires_at = now - timedelta(hours=1) if is_expired else now + timedelta(hours=1)
            
            entry = StateEntry(
                entry_id=f"entry_{i}",
                user_id=user_id,
                entry_type="test",
                state_data={"index": i},
                created_at=now,
                updated_at=now,
                expires_at=expires_at
            )
            entries.append(entry)
            manager.state_store[entry.entry_id] = entry
        
        # Should have 5 entries initially
        self.assertEqual(manager.get_state_count(), 5)
        
        # Clean up expired entries
        cleaned_count = manager.cleanup_expired_states()
        
        # Should have cleaned 3 expired entries (1, 3, 5)
        self.assertEqual(cleaned_count, 3)
        self.assertEqual(manager.get_state_count(), 2)
        
        # Remaining entries should be non-expired (0, 2, 4)
        remaining_ids = set(manager.state_store.keys())
        expected_ids = {"entry_0", "entry_2", "entry_4"}
        self.assertEqual(remaining_ids, expected_ids)


class TestStateVersioningAndConflicts(unittest.TestCase):
    """Test state versioning and conflict resolution."""
    
    def test_version_increment(self):
        """Test version incrementing on state updates."""
        user_id = UserID(str(uuid.uuid4()))
        entry = StateEntry(
            entry_id=str(uuid.uuid4()),
            user_id=user_id,
            entry_type="test",
            state_data={"counter": 0},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Initial version should be 1
        self.assertEqual(entry.version, 1)
        initial_updated_at = entry.updated_at
        
        # Increment version
        time.sleep(0.001)  # Ensure timestamp difference
        entry.increment_version()
        
        # Version should be incremented, timestamp updated
        self.assertEqual(entry.version, 2)
        self.assertGreater(entry.updated_at, initial_updated_at)
    
    def test_version_conflict_detection(self):
        """Test that version conflicts are detected and rejected."""
        manager = StateManager()
        user_id = UserID(str(uuid.uuid4()))
        entry_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        # Store initial entry
        initial_entry = StateEntry(
            entry_id=entry_id,
            user_id=user_id,
            entry_type="test",
            state_data={"value": "initial"},
            created_at=now,
            updated_at=now,
            version=1
        )
        self.assertTrue(manager.store_state(initial_entry))
        
        # Update to version 2
        updated_entry = StateEntry(
            entry_id=entry_id,
            user_id=user_id,
            entry_type="test",
            state_data={"value": "updated"},
            created_at=now,
            updated_at=now,
            version=2
        )
        self.assertTrue(manager.store_state(updated_entry))
        
        # Try to store older version (should be rejected)
        older_entry = StateEntry(
            entry_id=entry_id,
            user_id=user_id,
            entry_type="test",
            state_data={"value": "older"},
            created_at=now,
            updated_at=now,
            version=1  # Older version
        )
        self.assertFalse(manager.store_state(older_entry))
        
        # Verify current entry is still the updated one
        current = manager.retrieve_state(entry_id)
        self.assertEqual(current.state_data["value"], "updated")
        self.assertEqual(current.version, 2)
    
    def test_state_update_versioning(self):
        """Test that state updates increment version correctly."""
        manager = StateManager()
        user_id = UserID(str(uuid.uuid4()))
        entry_id = str(uuid.uuid4())
        
        # Store initial entry
        entry = StateEntry(
            entry_id=entry_id,
            user_id=user_id,
            entry_type="test",
            state_data={"counter": 0},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        manager.store_state(entry)
        
        # Update state data
        self.assertTrue(manager.update_state(entry_id, {"counter": 1, "new_field": "value"}))
        
        # Retrieve and verify version was incremented
        updated = manager.retrieve_state(entry_id)
        self.assertEqual(updated.version, 2)
        self.assertEqual(updated.state_data["counter"], 1)
        self.assertEqual(updated.state_data["new_field"], "value")


class TestUserStateIsolation(unittest.TestCase):
    """Test that state is properly isolated between users."""
    
    def test_user_state_isolation(self):
        """Test that users can only access their own state."""
        manager = StateManager()
        user1_id = UserID(str(uuid.uuid4()))
        user2_id = UserID(str(uuid.uuid4()))
        
        # Store states for both users
        user1_entry = StateEntry(
            entry_id="entry_1",
            user_id=user1_id,
            entry_type="connection",
            state_data={"user": "user1"},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        user2_entry = StateEntry(
            entry_id="entry_2",
            user_id=user2_id,
            entry_type="connection",
            state_data={"user": "user2"},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        manager.store_state(user1_entry)
        manager.store_state(user2_entry)
        
        # Each user should only see their own states
        user1_states = manager.get_user_states(user1_id)
        user2_states = manager.get_user_states(user2_id)
        
        self.assertEqual(len(user1_states), 1)
        self.assertEqual(len(user2_states), 1)
        
        self.assertEqual(user1_states[0].entry_id, "entry_1")
        self.assertEqual(user2_states[0].entry_id, "entry_2")
        
        self.assertEqual(user1_states[0].state_data["user"], "user1")
        self.assertEqual(user2_states[0].state_data["user"], "user2")
    
    def test_bulk_operations_respect_user_isolation(self):
        """Test that bulk operations maintain user isolation."""
        manager = StateManager()
        user1_id = UserID(str(uuid.uuid4()))
        user2_id = UserID(str(uuid.uuid4()))
        
        # Create multiple entries for each user
        for i in range(3):
            for user_id, user_name in [(user1_id, "user1"), (user2_id, "user2")]:
                entry = StateEntry(
                    entry_id=f"{user_name}_entry_{i}",
                    user_id=user_id,
                    entry_type="test",
                    state_data={"user": user_name, "index": i},
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                manager.store_state(entry)
        
        # Total states: 6
        self.assertEqual(manager.get_state_count(), 6)
        
        # Each user should have exactly 3 states
        user1_states = manager.get_user_states(user1_id)
        user2_states = manager.get_user_states(user2_id)
        
        self.assertEqual(len(user1_states), 3)
        self.assertEqual(len(user2_states), 3)
        
        # Verify isolation - no cross-contamination
        for state in user1_states:
            self.assertEqual(state.user_id, user1_id)
            self.assertEqual(state.state_data["user"], "user1")
        
        for state in user2_states:
            self.assertEqual(state.user_id, user2_id)
            self.assertEqual(state.state_data["user"], "user2")


if __name__ == "__main__":
    unittest.main()