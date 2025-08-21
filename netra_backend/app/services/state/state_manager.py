"""State Management Service

Provides centralized state management with transaction support.
"""

from typing import Dict, Any, Optional, List, Type, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone, UTC
from enum import Enum
import asyncio
import json
from contextlib import asynccontextmanager
from netra_backend.app.logging_config import central_logger
from netra_backend.app.redis_manager import redis_manager
from sqlalchemy.ext.asyncio import AsyncSession

logger = central_logger.get_logger(__name__)

class StateStorage(Enum):
    """State storage backends"""
    MEMORY = "memory"
    REDIS = "redis"
    DATABASE = "database"
    HYBRID = "hybrid"

class TransactionStatus(Enum):
    """Transaction status"""
    PENDING = "pending"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"

@dataclass
class StateSnapshot:
    """Represents a state snapshot"""
    id: str
    timestamp: datetime
    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class StateTransaction:
    """Represents a state transaction"""
    id: str
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    status: TransactionStatus = TransactionStatus.PENDING
    operations: List[Dict[str, Any]] = field(default_factory=list)
    snapshots: List[StateSnapshot] = field(default_factory=list)
    
    def add_operation(self, operation: str, key: str, value: Any) -> None:
        """Add operation to transaction"""
        self.operations.append({
            "operation": operation,
            "key": key,
            "value": value,
            "timestamp": datetime.now(timezone.utc)
        })

class StateManager:
    """Manages application state with transaction support"""
    
    def __init__(self,
                 storage: StateStorage = StateStorage.HYBRID,
                 snapshot_interval: int = 10):
        self.storage = storage
        self.snapshot_interval = snapshot_interval
        self._init_storage_components()
        self._init_state_tracking()
        self._lock = asyncio.Lock()

    def _init_storage_components(self) -> None:
        """Initialize storage-related components"""
        self._memory_store: Dict[str, Any] = {}
        self._redis = redis_manager

    def _init_state_tracking(self) -> None:
        """Initialize state tracking components"""
        self._transactions: Dict[str, StateTransaction] = {}
        self._change_listeners: Dict[str, List[Callable]] = {}
        self._snapshots: List[StateSnapshot] = []
        self._operation_count = 0
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get state value"""
        if self.storage == StateStorage.MEMORY:
            return self._memory_store.get(key, default)
        elif self.storage == StateStorage.REDIS:
            return await self._get_from_redis(key, default)
        elif self.storage == StateStorage.HYBRID:
            return await self._get_from_hybrid(key, default)
        return default

    async def _get_from_redis(self, key: str, default: Any) -> Any:
        """Get value from Redis storage"""
        value = await self._redis.get(f"state:{key}")
        return json.loads(value) if value else default

    async def _get_from_hybrid(self, key: str, default: Any) -> Any:
        """Get value from hybrid storage"""
        value = self._memory_store.get(key)
        if value is None:
            value = await self._check_redis_fallback(key)
        return value if value is not None else default

    async def _check_redis_fallback(self, key: str) -> Any:
        """Check Redis as fallback for hybrid storage"""
        redis_value = await self._redis.get(f"state:{key}")
        if redis_value:
            value = json.loads(redis_value)
            self._memory_store[key] = value
            return value
        return None
    
    async def set(self, key: str, value: Any, transaction_id: Optional[str] = None) -> None:
        """Set state value"""
        async with self._lock:
            if transaction_id:
                await self._handle_transactional_set(transaction_id, key, value)
            else:
                await self._apply_change(key, value)

    async def _handle_transactional_set(self, transaction_id: str, key: str, value: Any):
        """Handle transactional set operation"""
        if transaction_id not in self._transactions:
            raise ValueError(f"Transaction {transaction_id} not found")
        self._transactions[transaction_id].add_operation("set", key, value)
    
    async def delete(self, key: str, transaction_id: Optional[str] = None) -> None:
        """Delete state value"""
        async with self._lock:
            if transaction_id:
                await self._handle_transactional_delete(transaction_id, key)
            else:
                await self._apply_delete(key)

    async def _handle_transactional_delete(self, transaction_id: str, key: str):
        """Handle transactional delete operation"""
        if transaction_id not in self._transactions:
            raise ValueError(f"Transaction {transaction_id} not found")
        self._transactions[transaction_id].add_operation("delete", key, None)
    
    async def update(self, key: str, updater: Callable[[Any], Any], transaction_id: Optional[str] = None) -> None:
        """Update state value using a function"""
        current = await self.get(key)
        new_value = updater(current)
        await self.set(key, new_value, transaction_id)
    
    @asynccontextmanager
    async def transaction(self):
        """Create a state transaction context"""
        transaction_id = f"txn_{datetime.now(timezone.utc).timestamp()}"
        transaction = await self._initialize_transaction(transaction_id)
        try:
            yield transaction_id
            await self._commit_transaction(transaction_id)
        except Exception as e:
            await self._handle_transaction_error(transaction_id, e)
        finally:
            del self._transactions[transaction_id]

    async def _handle_transaction_error(self, transaction_id: str, error: Exception) -> None:
        """Handle transaction error with rollback"""
        await self._rollback_transaction(transaction_id)
        raise error

    async def _initialize_transaction(self, transaction_id: str) -> StateTransaction:
        """Initialize new transaction with snapshot"""
        transaction = StateTransaction(id=transaction_id)
        self._transactions[transaction_id] = transaction
        snapshot = await self._create_snapshot()
        transaction.snapshots.append(snapshot)
        return transaction
    
    async def _commit_transaction(self, transaction_id: str) -> None:
        """Commit a transaction"""
        transaction = self._transactions.get(transaction_id)
        if not transaction:
            return
        await self._process_transaction_commit(transaction_id, transaction)

    async def _process_transaction_commit(self, transaction_id: str, transaction: StateTransaction) -> None:
        """Process transaction commit operations"""
        logger.info(f"Committing transaction {transaction_id} with {len(transaction.operations)} operations")
        await self._execute_transaction_operations(transaction)
        transaction.status = TransactionStatus.COMMITTED
        await self._handle_post_commit_snapshot(transaction)

    async def _execute_transaction_operations(self, transaction: StateTransaction):
        """Execute all operations in transaction"""
        for op in transaction.operations:
            if op["operation"] == "set":
                await self._apply_change(op["key"], op["value"])
            elif op["operation"] == "delete":
                await self._apply_delete(op["key"])

    async def _handle_post_commit_snapshot(self, transaction: StateTransaction):
        """Handle post-commit snapshot creation"""
        self._operation_count += len(transaction.operations)
        if self._operation_count >= self.snapshot_interval:
            await self._auto_snapshot()
            self._operation_count = 0
    
    async def _rollback_transaction(self, transaction_id: str) -> None:
        """Rollback a transaction"""
        transaction = self._transactions.get(transaction_id)
        if not transaction or not transaction.snapshots:
            return
        
        logger.info(f"Rolling back transaction {transaction_id}")
        await self._execute_rollback(transaction)
        transaction.status = TransactionStatus.ROLLED_BACK

    async def _execute_rollback(self, transaction: StateTransaction):
        """Execute transaction rollback"""
        snapshot = transaction.snapshots[0]
        await self._restore_snapshot(snapshot)
    
    async def _apply_change(self, key: str, value: Any) -> None:
        """Apply a state change"""
        old_value = await self.get(key)
        await self._store_value(key, value)
        await self._notify_listeners(key, old_value, value)

    async def _store_value(self, key: str, value: Any):
        """Store value in appropriate storage backend"""
        if self.storage in [StateStorage.MEMORY, StateStorage.HYBRID]:
            self._memory_store[key] = value
        
        if self.storage in [StateStorage.REDIS, StateStorage.HYBRID]:
            await self._redis.set(f"state:{key}", json.dumps(value), ex=3600)
    
    async def _apply_delete(self, key: str) -> None:
        """Apply a state deletion"""
        old_value = await self.get(key)
        await self._remove_value(key)
        await self._notify_listeners(key, old_value, None)

    async def _remove_value(self, key: str):
        """Remove value from storage backends"""
        if self.storage in [StateStorage.MEMORY, StateStorage.HYBRID]:
            self._memory_store.pop(key, None)
        
        if self.storage in [StateStorage.REDIS, StateStorage.HYBRID]:
            await self._redis.delete(f"state:{key}")
    
    def subscribe(self, key: str, listener: Callable) -> None:
        """Subscribe to state changes"""
        if key not in self._change_listeners:
            self._change_listeners[key] = []
        
        self._change_listeners[key].append(listener)
        logger.debug(f"Subscribed listener to key: {key}")
    
    def unsubscribe(self, key: str, listener: Callable) -> None:
        """Unsubscribe from state changes"""
        if key in self._change_listeners:
            self._change_listeners[key].remove(listener)
    
    async def _notify_listeners(self, key: str, old_value: Any, new_value: Any) -> None:
        """Notify change listeners"""
        listeners = self._change_listeners.get(key, [])
        for listener in listeners:
            await self._invoke_listener(listener, key, old_value, new_value)

    async def _invoke_listener(self, listener, key: str, old_value: Any, new_value: Any):
        """Invoke individual listener with error handling"""
        try:
            await self._execute_listener(listener, key, old_value, new_value)
        except Exception as e:
            logger.error(f"Error notifying listener for key {key}: {e}")
    
    async def _execute_listener(self, listener, key: str, old_value: Any, new_value: Any):
        """Execute listener based on its type."""
        if asyncio.iscoroutinefunction(listener):
            await listener(key, old_value, new_value)
        else:
            listener(key, old_value, new_value)
    
    async def _create_snapshot(self) -> StateSnapshot:
        """Create a state snapshot"""
        snapshot_id = f"snapshot_{datetime.now(timezone.utc).timestamp()}"
        data = await self._gather_snapshot_data()
        return self._build_snapshot(snapshot_id, data)

    async def _gather_snapshot_data(self) -> Dict[str, Any]:
        """Gather data for snapshot from storage"""
        if self.storage in [StateStorage.MEMORY, StateStorage.HYBRID]:
            return dict(self._memory_store)
        return await self._gather_redis_data()

    async def _gather_redis_data(self) -> Dict[str, Any]:
        """Gather data from Redis for snapshot"""
        data = {}
        keys = await self._redis.keys("state:*")
        for key in keys:
            await self._add_redis_key_to_data(data, key)
        return data

    async def _add_redis_key_to_data(self, data: Dict, key: str):
        """Add Redis key-value to data dictionary"""
        value = await self._redis.get(key)
        if value:
            clean_key = key.replace("state:", "")
            data[clean_key] = json.loads(value)

    def _build_snapshot(self, snapshot_id: str, data: Dict[str, Any]) -> StateSnapshot:
        """Build snapshot object from data"""
        metadata = self._create_snapshot_metadata(data)
        return StateSnapshot(
            id=snapshot_id,
            timestamp=datetime.now(timezone.utc),
            data=data,
            metadata=metadata
        )
    
    def _create_snapshot_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create snapshot metadata dictionary."""
        return {
            "storage": self.storage.value,
            "size": len(data)
        }
    
    async def _restore_snapshot(self, snapshot: StateSnapshot) -> None:
        """Restore from a snapshot"""
        logger.info(f"Restoring snapshot {snapshot.id}")
        await self._restore_memory_data(snapshot)
        await self._restore_redis_data(snapshot)

    async def _restore_memory_data(self, snapshot: StateSnapshot):
        """Restore memory data from snapshot"""
        if self.storage in [StateStorage.MEMORY, StateStorage.HYBRID]:
            self._memory_store = dict(snapshot.data)

    async def _restore_redis_data(self, snapshot: StateSnapshot):
        """Restore Redis data from snapshot"""
        if self.storage in [StateStorage.REDIS, StateStorage.HYBRID]:
            pipe = self._redis.pipeline()
            await self._clear_redis_keys(pipe)
            await self._set_snapshot_data(pipe, snapshot)
            await pipe.execute()

    async def _clear_redis_keys(self, pipe):
        """Clear existing Redis keys"""
        keys = await self._redis.keys("state:*")
        for key in keys:
            pipe.delete(key)

    async def _set_snapshot_data(self, pipe, snapshot: StateSnapshot):
        """Set snapshot data to Redis pipeline"""
        for key, value in snapshot.data.items():
            pipe.set(f"state:{key}", json.dumps(value), ex=3600)
    
    async def _auto_snapshot(self) -> None:
        """Automatically create a snapshot"""
        snapshot = await self._create_snapshot()
        self._snapshots.append(snapshot)
        
        if len(self._snapshots) > 10:
            self._snapshots.pop(0)
        
        logger.debug(f"Created auto-snapshot {snapshot.id}")
    
    async def get_all(self) -> Dict[str, Any]:
        """Get all state values"""
        if self.storage in [StateStorage.MEMORY, StateStorage.HYBRID]:
            return dict(self._memory_store)
        elif self.storage == StateStorage.REDIS:
            return await self._get_all_from_redis()
        return {}

    async def _get_all_from_redis(self) -> Dict[str, Any]:
        """Get all values from Redis storage"""
        data = {}
        keys = await self._redis.keys("state:*")
        for key in keys:
            await self._add_redis_key_to_data(data, key)
        return data
    
    async def clear(self) -> None:
        """Clear all state"""
        async with self._lock:
            await self._clear_memory_storage()
            await self._clear_redis_storage()
            logger.info("Cleared all state")

    async def _clear_memory_storage(self):
        """Clear memory storage"""
        if self.storage in [StateStorage.MEMORY, StateStorage.HYBRID]:
            self._memory_store.clear()

    async def _clear_redis_storage(self):
        """Clear Redis storage"""
        if self.storage in [StateStorage.REDIS, StateStorage.HYBRID]:
            keys = await self._redis.keys("state:*")
            if keys:
                await self._redis.delete(*keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get state manager statistics"""
        return {
            "storage": self.storage.value,
            "keys": self._count_memory_keys(),
            "transactions": len(self._transactions),
            "snapshots": len(self._snapshots),
            "listeners": self._count_listeners(),
            "operation_count": self._operation_count
        }

    def _count_memory_keys(self) -> int:
        """Count keys in memory storage"""
        return len(self._memory_store) if self.storage != StateStorage.REDIS else 0

    def _count_listeners(self) -> int:
        """Count total listeners across all keys"""
        return sum(len(listeners) for listeners in self._change_listeners.values())