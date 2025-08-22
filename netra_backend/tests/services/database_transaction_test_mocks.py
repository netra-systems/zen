"""
Mock classes for database transaction tests.
All functions ≤8 lines per requirements.
"""

import asyncio
from typing import Dict, List, Optional

from sqlalchemy.exc import (
    DisconnectionError,
    IntegrityError,
    OperationalError,
    SQLAlchemyError,
)
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.services.database.base_repository import BaseRepository
from netra_backend.tests.database_transaction_test_helpers import MockDatabaseModel


class MockRepository(BaseRepository[MockDatabaseModel]):
    """Mock repository for testing transaction behavior"""
    
    def __init__(self):
        super().__init__(MockDatabaseModel)
        self.operation_log = []  # Track operations for testing
    
    async def create(self, db: Optional[AsyncSession] = None, **kwargs) -> Optional[MockDatabaseModel]:
        """Override create to log operations"""
        self.operation_log.append(('create', kwargs))
        
        if not db:
            return None
        
        return await self._perform_create_operation(db, kwargs)
    
    async def _perform_create_operation(self, db: AsyncSession, kwargs: dict) -> Optional[MockDatabaseModel]:
        """Perform create operation with error handling and deadlock recovery"""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                entity = MockDatabaseModel(**kwargs)
                db.add(entity)
                await db.flush()  # Use flush instead of commit to match BaseRepository
                return entity
            except DisconnectionError:
                raise  # Let DisconnectionError propagate
            except OperationalError as e:
                # Handle deadlock and timeout scenarios
                retry_count += 1
                await self._handle_deadlock_recovery(db, e, retry_count, max_retries)
                if retry_count >= max_retries:
                    return None
                continue
            except (IntegrityError, SQLAlchemyError):
                await self._handle_create_error(db)
                return None
    
    async def _handle_deadlock_recovery(self, db: AsyncSession, error: OperationalError, 
                                        retry_count: int, max_retries: int) -> None:
        """Handle deadlock recovery with exponential backoff"""
        # Log the deadlock attempt
        self.operation_log.append(('deadlock_recovery', retry_count, str(error)))
        
        # Perform rollback to clear the transaction state
        await db.rollback()
        
        # Exponential backoff: wait progressively longer between retries
        wait_time = 0.001 * (2 ** (retry_count - 1))  # 1ms, 2ms, 4ms...
        await asyncio.sleep(wait_time)
    
    async def _handle_create_error(self, db: AsyncSession) -> None:
        """Handle create operation errors"""
        try:
            await db.rollback()
        except asyncio.TimeoutError:
            raise
        except Exception:
            await db.rollback()
    
    async def update(self, db: AsyncSession, entity_id: str, **kwargs) -> Optional[MockDatabaseModel]:
        """Override update to log operations"""
        self.operation_log.append(('update', entity_id, kwargs))
        return await super().update(db, entity_id, **kwargs)
    
    async def delete(self, db: AsyncSession, entity_id: str) -> bool:
        """Override delete to log operations"""
        self.operation_log.append(('delete', entity_id))
        return await super().delete(db, entity_id)
    
    async def find_by_user(self, db: AsyncSession, user_id: str) -> List[MockDatabaseModel]:
        """Implementation of abstract method find_by_user"""
        self.operation_log.append(('find_by_user', user_id))
        # Return empty list for testing purposes
        return []
    
    def clear_log(self) -> None:
        """Clear operation log"""
        self.operation_log.clear()


class TransactionTestManager:
    """Manages transaction test scenarios"""
    
    def __init__(self):
        self.transaction_states = {}  # transaction_id -> state
        self._init_counters()
        
    def _init_counters(self) -> None:
        """Initialize transaction counters"""
        self.rollback_counts = 0
        self.commit_counts = 0
        self.deadlock_simulations = 0
    
    def simulate_deadlock(self, session: AsyncSession) -> None:
        """Simulate database deadlock"""
        self.deadlock_simulations += 1
        # Configure session to raise deadlock error when used
        session.flush.side_effect = SQLAlchemyError("deadlock detected")
    
    def simulate_connection_loss(self, session: AsyncSession) -> None:
        """Simulate connection loss"""
        raise DisconnectionError("connection lost", None, None)
    
    def track_transaction_state(self, transaction_id: str, state: str) -> None:
        """Track transaction state changes"""
        self.transaction_states[transaction_id] = state
    
    def increment_rollback(self) -> None:
        """Track rollback operations"""
        self.rollback_counts += 1
    
    def increment_commit(self) -> None:
        """Track commit operations"""
        self.commit_counts += 1
    
    def get_transaction_stats(self) -> Dict[str, int]:
        """Get transaction statistics"""
        return {
            'rollbacks': self.rollback_counts,
            'commits': self.commit_counts,
            'deadlocks': self.deadlock_simulations,
            'active_states': len(self.transaction_states)
        }
    
    def reset_counters(self) -> None:
        """Reset all counters"""
        self._init_counters()
        self.transaction_states.clear()