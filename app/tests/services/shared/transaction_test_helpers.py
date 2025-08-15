"""
Shared test helpers for database repository transaction testing
Mock classes and test managers for transaction behavior testing
"""

import pytest
import asyncio
import uuid
from datetime import datetime, UTC
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch, call
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError, DisconnectionError
from sqlalchemy import select, text

from app.services.database.base_repository import BaseRepository
from app.services.database.unit_of_work import UnitOfWork
from app.core.exceptions_base import NetraException


class MockDatabaseModel:
    """Mock database model for testing"""
    
    def __init__(self, id: str = None, name: str = None, **kwargs):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.created_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)
        
        # Set other attributes
        for key, value in kwargs.items():
            setattr(self, key, value)


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
            
        try:
            # Create mock entity directly without calling super()
            entity = MockDatabaseModel(**kwargs)
            db.add(entity)
            await db.flush()  # Use flush instead of commit to match BaseRepository
            return entity
        except (IntegrityError, SQLAlchemyError):
            await db.rollback()
            return None
        except asyncio.TimeoutError:
            raise
        except Exception:
            await db.rollback()
            return None
    
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
    
    def clear_log(self):
        """Clear operation log"""
        self.operation_log.clear()


class TransactionTestManager:
    """Manages transaction test scenarios"""
    
    def __init__(self):
        self.transaction_states = {}  # transaction_id -> state
        self.rollback_counts = 0
        self.commit_counts = 0
        self.deadlock_simulations = 0
        
    def simulate_deadlock(self, session: AsyncSession):
        """Simulate database deadlock"""
        self.deadlock_simulations += 1
        raise SQLAlchemyError("deadlock detected")
    
    def simulate_connection_loss(self, session: AsyncSession):
        """Simulate connection loss"""
        raise DisconnectionError("connection lost", None, None)
    
    def track_transaction_state(self, transaction_id: str, state: str):
        """Track transaction state changes"""
        self.transaction_states[transaction_id] = state
    
    def increment_rollback(self):
        """Track rollback operations"""
        self.rollback_counts += 1
    
    def increment_commit(self):
        """Track commit operations"""
        self.commit_counts += 1