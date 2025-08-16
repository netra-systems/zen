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
from app.logging_config import central_logger
from app.redis_manager import redis_manager
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
        self._memory_store: Dict[str, Any] = {}
        self._redis = redis_manager
        self._transactions: Dict[str, StateTransaction] = {}
        self._change_listeners: Dict[str, List[Callable]] = {}
        self._snapshots: List[StateSnapshot] = []
        self._operation_count = 0
        self._lock = asyncio.Lock()
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get state value"""
        if self.storage == StateStorage.MEMORY:
            return self._memory_store.get(key, default)
        
        elif self.storage == StateStorage.REDIS:
            value = await self._redis.get(f"state:{key}")
            return json.loads(value) if value else default
        
        elif self.storage == StateStorage.HYBRID:
            value = self._memory_store.get(key)
            if value is None:
                redis_value = await self._redis.get(f"state:{key}")
                if redis_value:
                    value = json.loads(redis_value)
                    self._memory_store[key] = value
            return value if value is not None else default
        
        return default
    
    async def set(self, key: str, value: Any, transaction_id: Optional[str] = None) -> None:
        """Set state value"""
        async with self._lock:
            if transaction_id:
                if transaction_id not in self._transactions:
                    raise ValueError(f"Transaction {transaction_id} not found")
                
                self._transactions[transaction_id].add_operation("set", key, value)
            else:
                await self._apply_change(key, value)
    
    async def delete(self, key: str, transaction_id: Optional[str] = None) -> None:
        """Delete state value"""
        async with self._lock:
            if transaction_id:
                if transaction_id not in self._transactions:
                    raise ValueError(f"Transaction {transaction_id} not found")
                
                self._transactions[transaction_id].add_operation("delete", key, None)
            else:
                await self._apply_delete(key)
    
    async def update(self, key: str, updater: Callable[[Any], Any], transaction_id: Optional[str] = None) -> None:
        """Update state value using a function"""
        current = await self.get(key)
        new_value = updater(current)
        await self.set(key, new_value, transaction_id)
    
    @asynccontextmanager
    async def transaction(self):
        """Create a state transaction context"""
        transaction_id = f"txn_{datetime.now(timezone.utc).timestamp()}"
        transaction = StateTransaction(id=transaction_id)
        
        self._transactions[transaction_id] = transaction
        
        snapshot = await self._create_snapshot()
        transaction.snapshots.append(snapshot)
        
        try:
            yield transaction_id
            await self._commit_transaction(transaction_id)
        except Exception as e:
            await self._rollback_transaction(transaction_id)
            raise e
        finally:
            del self._transactions[transaction_id]
    
    async def _commit_transaction(self, transaction_id: str) -> None:
        """Commit a transaction"""
        transaction = self._transactions.get(transaction_id)
        if not transaction:
            return
        
        logger.info(f"Committing transaction {transaction_id} with {len(transaction.operations)} operations")
        
        for op in transaction.operations:
            if op["operation"] == "set":
                await self._apply_change(op["key"], op["value"])
            elif op["operation"] == "delete":
                await self._apply_delete(op["key"])
        
        transaction.status = TransactionStatus.COMMITTED
        
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
        
        snapshot = transaction.snapshots[0]
        await self._restore_snapshot(snapshot)
        
        transaction.status = TransactionStatus.ROLLED_BACK
    
    async def _apply_change(self, key: str, value: Any) -> None:
        """Apply a state change"""
        old_value = await self.get(key)
        
        if self.storage in [StateStorage.MEMORY, StateStorage.HYBRID]:
            self._memory_store[key] = value
        
        if self.storage in [StateStorage.REDIS, StateStorage.HYBRID]:
            await self._redis.set(f"state:{key}", json.dumps(value), ex=3600)
        
        await self._notify_listeners(key, old_value, value)
    
    async def _apply_delete(self, key: str) -> None:
        """Apply a state deletion"""
        old_value = await self.get(key)
        
        if self.storage in [StateStorage.MEMORY, StateStorage.HYBRID]:
            self._memory_store.pop(key, None)
        
        if self.storage in [StateStorage.REDIS, StateStorage.HYBRID]:
            await self._redis.delete(f"state:{key}")
        
        await self._notify_listeners(key, old_value, None)
    
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
            try:
                if asyncio.iscoroutinefunction(listener):
                    await listener(key, old_value, new_value)
                else:
                    listener(key, old_value, new_value)
            except Exception as e:
                logger.error(f"Error notifying listener for key {key}: {e}")
    
    async def _create_snapshot(self) -> StateSnapshot:
        """Create a state snapshot"""
        snapshot_id = f"snapshot_{datetime.now(timezone.utc).timestamp()}"
        
        if self.storage in [StateStorage.MEMORY, StateStorage.HYBRID]:
            data = dict(self._memory_store)
        else:
            data = {}
            keys = await self._redis.keys("state:*")
            for key in keys:
                value = await self._redis.get(key)
                if value:
                    clean_key = key.replace("state:", "")
                    data[clean_key] = json.loads(value)
        
        snapshot = StateSnapshot(
            id=snapshot_id,
            timestamp=datetime.now(timezone.utc),
            data=data,
            metadata={
                "storage": self.storage.value,
                "size": len(data)
            }
        )
        
        return snapshot
    
    async def _restore_snapshot(self, snapshot: StateSnapshot) -> None:
        """Restore from a snapshot"""
        logger.info(f"Restoring snapshot {snapshot.id}")
        
        if self.storage in [StateStorage.MEMORY, StateStorage.HYBRID]:
            self._memory_store = dict(snapshot.data)
        
        if self.storage in [StateStorage.REDIS, StateStorage.HYBRID]:
            pipe = self._redis.pipeline()
            
            keys = await self._redis.keys("state:*")
            for key in keys:
                pipe.delete(key)
            
            for key, value in snapshot.data.items():
                pipe.set(f"state:{key}", json.dumps(value), ex=3600)
            
            await pipe.execute()
    
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
            data = {}
            keys = await self._redis.keys("state:*")
            for key in keys:
                value = await self._redis.get(key)
                if value:
                    clean_key = key.replace("state:", "")
                    data[clean_key] = json.loads(value)
            return data
        
        return {}
    
    async def clear(self) -> None:
        """Clear all state"""
        async with self._lock:
            if self.storage in [StateStorage.MEMORY, StateStorage.HYBRID]:
                self._memory_store.clear()
            
            if self.storage in [StateStorage.REDIS, StateStorage.HYBRID]:
                keys = await self._redis.keys("state:*")
                if keys:
                    await self._redis.delete(*keys)
            
            logger.info("Cleared all state")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get state manager statistics"""
        return {
            "storage": self.storage.value,
            "keys": len(self._memory_store) if self.storage != StateStorage.REDIS else 0,
            "transactions": len(self._transactions),
            "snapshots": len(self._snapshots),
            "listeners": sum(len(listeners) for listeners in self._change_listeners.values()),
            "operation_count": self._operation_count
        }