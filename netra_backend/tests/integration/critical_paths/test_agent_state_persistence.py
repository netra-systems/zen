"""Agent State Persistence L2 Integration Tests

Business Value Justification (BVJ):
- Segment: Mid/Enterprise (reliable AI operations)
- Business Goal: State recovery and reliability
- Value Impact: Protects $10K MRR from state loss incidents
- Strategic Impact: Core reliability feature for long-running agent operations

Critical Path: State capture -> Serialization -> Storage -> Recovery -> Validation
Coverage: Real state serialization, Redis/DB persistence, migration, versioning
"""

import pytest
import asyncio
import time
import json
import logging
from typing import Dict, List, Optional, Any, Union
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

# Real components for L2 testing
from netra_backend.app.services.redis_service import RedisService
from netra_backend.app.core.circuit_breaker import CircuitBreaker
from netra_backend.app.core.database_connection_manager import DatabaseConnectionManager
from netra_backend.app.agents.base import BaseSubAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.state_manager import AgentStateManager

logger = logging.getLogger(__name__)


@dataclass
class AgentExecutionState:
    """Represents agent execution state."""
    agent_id: str
    agent_type: str
    status: str
    current_step: int
    execution_context: Dict[str, Any]
    variables: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    version: str = "1.0.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        data["updated_at"] = self.updated_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentExecutionState":
        """Create from dictionary."""
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        return cls(**data)


class StateSerializer:
    """Serializes and deserializes agent state."""
    
    def __init__(self):
        self.compression_enabled = True
        self.encryption_enabled = False
        
    def serialize(self, state: AgentExecutionState) -> bytes:
        """Serialize state to bytes."""
        try:
            data = state.to_dict()
            json_str = json.dumps(data, ensure_ascii=False)
            
            if self.compression_enabled:
                # Simulate compression
                json_str = f"COMPRESSED:{json_str}"
                
            return json_str.encode('utf-8')
            
        except Exception as e:
            logger.error(f"State serialization failed: {e}")
            raise
    
    def deserialize(self, data: bytes) -> AgentExecutionState:
        """Deserialize state from bytes."""
        try:
            json_str = data.decode('utf-8')
            
            if self.compression_enabled and json_str.startswith("COMPRESSED:"):
                json_str = json_str[11:]  # Remove COMPRESSED: prefix
                
            state_dict = json.loads(json_str)
            return AgentExecutionState.from_dict(state_dict)
            
        except Exception as e:
            logger.error(f"State deserialization failed: {e}")
            raise


class StorageManager:
    """Manages state storage in Redis and database."""
    
    def __init__(self, redis_service: RedisService, db_manager: DatabaseConnectionManager):
        self.redis_service = redis_service
        self.db_manager = db_manager
        self.serializer = StateSerializer()
        
    async def save_state(self, state: AgentExecutionState, persistent: bool = True) -> bool:
        """Save state to storage."""
        try:
            serialized_data = self.serializer.serialize(state)
            
            # Save to Redis for fast access
            redis_key = f"agent_state:{state.agent_id}"
            await self.redis_service.client.setex(
                redis_key, 
                3600,  # 1 hour TTL
                serialized_data
            )
            
            # Save to database for persistence if requested
            if persistent:
                conn = await self.db_manager.get_connection()
                try:
                    await conn.execute("""
                        INSERT INTO agent_states (agent_id, agent_type, state_data, version, created_at, updated_at)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        ON CONFLICT (agent_id) DO UPDATE SET
                            state_data = $3,
                            version = $4,
                            updated_at = $6
                    """, state.agent_id, state.agent_type, serialized_data, 
                        state.version, state.created_at, state.updated_at)
                finally:
                    await self.db_manager.return_connection(conn)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save state for {state.agent_id}: {e}")
            return False
    
    async def load_state(self, agent_id: str, from_persistent: bool = False) -> Optional[AgentExecutionState]:
        """Load state from storage."""
        try:
            if not from_persistent:
                # Try Redis first
                redis_key = f"agent_state:{agent_id}"
                cached_data = await self.redis_service.client.get(redis_key)
                
                if cached_data:
                    return self.serializer.deserialize(cached_data)
            
            # Fallback to database
            conn = await self.db_manager.get_connection()
            try:
                row = await conn.fetchrow(
                    "SELECT state_data FROM agent_states WHERE agent_id = $1 ORDER BY updated_at DESC LIMIT 1",
                    agent_id
                )
                
                if row:
                    return self.serializer.deserialize(row["state_data"])
                    
            finally:
                await self.db_manager.return_connection(conn)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to load state for {agent_id}: {e}")
            return None
    
    async def delete_state(self, agent_id: str) -> bool:
        """Delete state from all storage."""
        try:
            # Delete from Redis
            redis_key = f"agent_state:{agent_id}"
            await self.redis_service.client.delete(redis_key)
            
            # Delete from database
            conn = await self.db_manager.get_connection()
            try:
                await conn.execute("DELETE FROM agent_states WHERE agent_id = $1", agent_id)
            finally:
                await self.db_manager.return_connection(conn)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete state for {agent_id}: {e}")
            return False


class RecoveryHandler:
    """Handles state recovery and validation."""
    
    def __init__(self, storage_manager: StorageManager):
        self.storage_manager = storage_manager
        
    async def recover_agent_state(self, agent_id: str) -> Optional[AgentExecutionState]:
        """Recover agent state with validation."""
        state = await self.storage_manager.load_state(agent_id)
        
        if state:
            # Validate state integrity
            if self.validate_state(state):
                return state
            else:
                logger.warning(f"State validation failed for agent {agent_id}")
                return None
        
        return None
    
    def validate_state(self, state: AgentExecutionState) -> bool:
        """Validate state integrity."""
        try:
            # Basic validation
            if not state.agent_id or not state.agent_type:
                return False
                
            if state.current_step < 0:
                return False
                
            if not isinstance(state.execution_context, dict):
                return False
                
            # Check state age (reject states older than 24 hours)
            if datetime.now() - state.updated_at > timedelta(hours=24):
                logger.warning(f"State for {state.agent_id} is too old")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"State validation error: {e}")
            return False
    
    async def migrate_state_version(self, state: AgentExecutionState, target_version: str) -> AgentExecutionState:
        """Migrate state to new version."""
        if state.version == target_version:
            return state
            
        # Simple migration logic (expand as needed)
        if state.version == "1.0.0" and target_version == "1.1.0":
            # Add new fields for v1.1.0
            state.execution_context["migration_timestamp"] = datetime.now().isoformat()
            state.version = target_version
            
        return state


class AgentStatePersistenceManager:
    """Manages agent state persistence testing."""
    
    def __init__(self):
        self.redis_service = None
        self.db_manager = None
        self.storage_manager = None
        self.recovery_handler = None
        
    async def initialize_services(self):
        """Initialize required services."""
        self.redis_service = RedisService()
        await self.redis_service.initialize()
        
        self.db_manager = DatabaseConnectionManager()
        await self.db_manager.initialize()
        
        self.storage_manager = StorageManager(self.redis_service, self.db_manager)
        self.recovery_handler = RecoveryHandler(self.storage_manager)
        
        # Initialize database schema
        await self.create_test_schema()
        
    async def create_test_schema(self):
        """Create test database schema."""
        conn = await self.db_manager.get_connection()
        try:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_states (
                    agent_id VARCHAR PRIMARY KEY,
                    agent_type VARCHAR NOT NULL,
                    state_data BYTEA NOT NULL,
                    version VARCHAR NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                )
            """)
        finally:
            await self.db_manager.return_connection(conn)
    
    def create_test_state(self, agent_id: str = None) -> AgentExecutionState:
        """Create a test agent state."""
        agent_id = agent_id or f"test_agent_{int(time.time() * 1000)}"
        
        return AgentExecutionState(
            agent_id=agent_id,
            agent_type="test_agent",
            status="running",
            current_step=5,
            execution_context={
                "task_id": "task_123",
                "user_input": "Test input",
                "model_used": "gpt-4",
                "tokens_used": 1500
            },
            variables={
                "temp_var": "temp_value",
                "counter": 42,
                "data_cache": ["item1", "item2", "item3"]
            },
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    async def cleanup(self):
        """Clean up resources."""
        if self.redis_service:
            await self.redis_service.shutdown()
        if self.db_manager:
            await self.db_manager.shutdown()


@pytest.fixture
async def state_persistence_manager():
    """Create state persistence manager for testing."""
    manager = AgentStatePersistenceManager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_basic_state_save_load(state_persistence_manager):
    """Test basic state save and load operations."""
    manager = state_persistence_manager
    
    # Create test state
    original_state = manager.create_test_state("save_load_test")
    
    # Save state
    save_result = await manager.storage_manager.save_state(original_state)
    assert save_result is True
    
    # Load state from Redis
    loaded_state = await manager.storage_manager.load_state(original_state.agent_id)
    
    assert loaded_state is not None
    assert loaded_state.agent_id == original_state.agent_id
    assert loaded_state.agent_type == original_state.agent_type
    assert loaded_state.status == original_state.status
    assert loaded_state.current_step == original_state.current_step
    assert loaded_state.execution_context == original_state.execution_context
    assert loaded_state.variables == original_state.variables


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_persistent_state_storage(state_persistence_manager):
    """Test persistent state storage in database."""
    manager = state_persistence_manager
    
    # Create test state
    test_state = manager.create_test_state("persistent_test")
    
    # Save with persistence enabled
    save_result = await manager.storage_manager.save_state(test_state, persistent=True)
    assert save_result is True
    
    # Load from database (bypass Redis)
    loaded_state = await manager.storage_manager.load_state(test_state.agent_id, from_persistent=True)
    
    assert loaded_state is not None
    assert loaded_state.agent_id == test_state.agent_id
    assert loaded_state.variables == test_state.variables


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_state_serialization_compression(state_persistence_manager):
    """Test state serialization with compression."""
    manager = state_persistence_manager
    
    # Create state with large data
    test_state = manager.create_test_state("compression_test")
    test_state.variables["large_data"] = ["data"] * 1000  # Large dataset
    
    # Test serialization
    serializer = StateSerializer()
    serialized_data = serializer.serialize(test_state)
    
    # Verify compression marker
    assert b"COMPRESSED:" in serialized_data
    
    # Test deserialization
    deserialized_state = serializer.deserialize(serialized_data)
    
    assert deserialized_state.agent_id == test_state.agent_id
    assert deserialized_state.variables["large_data"] == test_state.variables["large_data"]


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_state_recovery_validation(state_persistence_manager):
    """Test state recovery with validation."""
    manager = state_persistence_manager
    
    # Create and save valid state
    valid_state = manager.create_test_state("recovery_test")
    await manager.storage_manager.save_state(valid_state)
    
    # Test successful recovery
    recovered_state = await manager.recovery_handler.recover_agent_state(valid_state.agent_id)
    assert recovered_state is not None
    assert recovered_state.agent_id == valid_state.agent_id
    
    # Test recovery of non-existent state
    missing_state = await manager.recovery_handler.recover_agent_state("non_existent_agent")
    assert missing_state is None


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_state_version_migration(state_persistence_manager):
    """Test state version migration."""
    manager = state_persistence_manager
    
    # Create old version state
    old_state = manager.create_test_state("migration_test")
    old_state.version = "1.0.0"
    
    # Migrate to new version
    migrated_state = await manager.recovery_handler.migrate_state_version(old_state, "1.1.0")
    
    assert migrated_state.version == "1.1.0"
    assert "migration_timestamp" in migrated_state.execution_context


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_state_validation_rules(state_persistence_manager):
    """Test state validation rules."""
    manager = state_persistence_manager
    
    # Test valid state
    valid_state = manager.create_test_state("validation_test")
    assert manager.recovery_handler.validate_state(valid_state) is True
    
    # Test invalid states
    invalid_state1 = manager.create_test_state("invalid_test1")
    invalid_state1.agent_id = ""  # Invalid agent_id
    assert manager.recovery_handler.validate_state(invalid_state1) is False
    
    invalid_state2 = manager.create_test_state("invalid_test2")
    invalid_state2.current_step = -1  # Invalid step
    assert manager.recovery_handler.validate_state(invalid_state2) is False
    
    # Test old state (24+ hours)
    old_state = manager.create_test_state("old_test")
    old_state.updated_at = datetime.now() - timedelta(hours=25)
    assert manager.recovery_handler.validate_state(old_state) is False


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_concurrent_state_operations(state_persistence_manager):
    """Test concurrent state save/load operations."""
    manager = state_persistence_manager
    
    # Create multiple states
    states = [manager.create_test_state(f"concurrent_{i}") for i in range(10)]
    
    # Save states concurrently
    save_tasks = [manager.storage_manager.save_state(state) for state in states]
    save_results = await asyncio.gather(*save_tasks)
    
    assert all(save_results)
    
    # Load states concurrently
    load_tasks = [manager.storage_manager.load_state(state.agent_id) for state in states]
    loaded_states = await asyncio.gather(*load_tasks)
    
    assert len(loaded_states) == 10
    assert all(state is not None for state in loaded_states)


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_state_cleanup_operations(state_persistence_manager):
    """Test state cleanup and deletion."""
    manager = state_persistence_manager
    
    # Create and save test state
    test_state = manager.create_test_state("cleanup_test")
    await manager.storage_manager.save_state(test_state, persistent=True)
    
    # Verify state exists
    loaded_state = await manager.storage_manager.load_state(test_state.agent_id)
    assert loaded_state is not None
    
    # Delete state
    delete_result = await manager.storage_manager.delete_state(test_state.agent_id)
    assert delete_result is True
    
    # Verify state is deleted
    deleted_state = await manager.storage_manager.load_state(test_state.agent_id)
    assert deleted_state is None


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_redis_fallback_to_database(state_persistence_manager):
    """Test fallback from Redis to database storage."""
    manager = state_persistence_manager
    
    # Create and save state persistently
    test_state = manager.create_test_state("fallback_test")
    await manager.storage_manager.save_state(test_state, persistent=True)
    
    # Clear Redis cache
    redis_key = f"agent_state:{test_state.agent_id}"
    await manager.redis_service.client.delete(redis_key)
    
    # Load should fallback to database
    loaded_state = await manager.storage_manager.load_state(test_state.agent_id)
    assert loaded_state is not None
    assert loaded_state.agent_id == test_state.agent_id


@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_state_persistence_performance(state_persistence_manager):
    """Benchmark state persistence performance."""
    manager = state_persistence_manager
    
    # Create states for performance testing
    states = [manager.create_test_state(f"perf_{i}") for i in range(100)]
    
    # Benchmark save operations
    start_time = time.time()
    save_tasks = [manager.storage_manager.save_state(state) for state in states]
    save_results = await asyncio.gather(*save_tasks)
    save_time = time.time() - start_time
    
    assert all(save_results)
    
    # Benchmark load operations
    start_time = time.time()
    load_tasks = [manager.storage_manager.load_state(state.agent_id) for state in states]
    loaded_states = await asyncio.gather(*load_tasks)
    load_time = time.time() - start_time
    
    assert len(loaded_states) == 100
    
    # Performance assertions
    assert save_time < 5.0  # 100 saves in under 5 seconds
    assert load_time < 3.0  # 100 loads in under 3 seconds
    
    avg_save_time = save_time / 100
    avg_load_time = load_time / 100
    
    assert avg_save_time < 0.05  # Average save under 50ms
    assert avg_load_time < 0.03  # Average load under 30ms
    
    logger.info(f"Performance: Save {avg_save_time*1000:.1f}ms, Load {avg_load_time*1000:.1f}ms")