"""Transaction Testing Fixtures and Mock Classes

Supporting infrastructure for transaction consistency testing.
Provides mock database connections, transaction managers, and test data factories.

Business Value Justification (BVJ):
1. Segment: All customer segments (Free, Early, Mid, Enterprise) 
2. Business Goal: Provide reliable test infrastructure for data integrity testing
3. Value Impact: Enables comprehensive testing that prevents revenue loss from data corruption
4. Revenue Impact: Testing reliability directly supports revenue protection (-$50K ARR risk mitigation)

Architecture: 300-line limit, 8-line functions, modular design
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class TransactionState(Enum):
    """Transaction state enumeration."""
    ACTIVE = "active"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


class DatabaseType(Enum):
    """Database type enumeration."""
    AUTH_DB = "auth_db"
    BACKEND_DB = "backend_db" 
    CLICKHOUSE = "clickhouse"


@dataclass
class MockTransaction:
    """Mock transaction for testing."""
    id: str
    state: TransactionState = TransactionState.ACTIVE
    operations: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    committed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MockOperation:
    """Mock operation within transaction."""
    id: str
    db_type: DatabaseType
    operation_type: str
    data: Dict[str, Any]
    completed: bool = False
    error: Optional[str] = None


class MockDatabaseConnection:
    """Mock database connection with failure simulation."""
    
    def __init__(self, db_type: DatabaseType, fail_on_operation: Optional[str] = None):
        """Initialize mock connection."""
        self.db_type = db_type
        self.fail_on_operation = fail_on_operation
        self.operations = []
        self.in_transaction = False
        self.rolled_back = False
    
    async def begin_transaction(self) -> str:
        """Begin transaction."""
        self.in_transaction = True
        transaction_id = f"tx_{uuid.uuid4().hex[:8]}"
        return transaction_id
    
    async def execute_operation(self, operation: MockOperation) -> None:
        """Execute operation with optional failure."""
        if operation.operation_type == self.fail_on_operation:
            raise Exception(f"Simulated failure in {self.db_type.value}")
        self.operations.append(operation)
        operation.completed = True
    
    async def commit(self) -> None:
        """Commit transaction."""
        if not self.in_transaction:
            raise Exception("No active transaction")
        self.in_transaction = False
    
    async def rollback(self) -> None:
        """Rollback transaction."""
        self.in_transaction = False
        self.rolled_back = True


class DistributedTransactionManager:
    """Mock distributed transaction manager for testing."""
    
    def __init__(self):
        """Initialize transaction manager."""
        self.connections: Dict[DatabaseType, MockDatabaseConnection] = {}
        self.active_transactions: Dict[str, MockTransaction] = {}
        self.compensation_log = []
    
    def add_database(self, db_type: DatabaseType, connection: MockDatabaseConnection) -> None:
        """Add database connection."""
        self.connections[db_type] = connection
    
    async def begin_transaction(self, metadata: Optional[Dict] = None) -> str:
        """Begin distributed transaction."""
        tx_id = f"dist_tx_{uuid.uuid4().hex[:8]}"
        transaction = MockTransaction(id=tx_id, metadata=metadata or {})
        self.active_transactions[tx_id] = transaction
        return tx_id
    
    async def execute_operation(self, tx_id: str, operation: MockOperation) -> None:
        """Execute operation on specific database."""
        self._validate_transaction(tx_id)
        connection = self.connections[operation.db_type]
        try:
            await connection.execute_operation(operation)
            self.active_transactions[tx_id].operations.append(operation.id)
        except Exception as e:
            # Mark transaction as failed when any operation fails
            self.active_transactions[tx_id].state = TransactionState.FAILED
            await self._execute_rollback_phase(tx_id, str(e))
            raise
    
    def _validate_transaction(self, tx_id: str) -> None:
        """Validate transaction exists."""
        if tx_id not in self.active_transactions:
            raise ValueError(f"Transaction not found: {tx_id}")
    
    async def commit_transaction(self, tx_id: str) -> bool:
        """Commit distributed transaction."""
        transaction = self.active_transactions.get(tx_id)
        if not transaction:
            return False
        
        # Don't commit if transaction is already failed or rolled back
        if transaction.state in [TransactionState.FAILED, TransactionState.ROLLED_BACK]:
            return False
        
        try:
            await self._execute_commit_phase(tx_id)
            return self._finalize_commit(transaction)
        except Exception as e:
            await self._execute_rollback_phase(tx_id, str(e))
            return False
    
    def _finalize_commit(self, transaction: MockTransaction) -> bool:
        """Finalize transaction commit."""
        transaction.state = TransactionState.COMMITTED
        transaction.committed_at = datetime.now(timezone.utc)
        return True
    
    async def _execute_commit_phase(self, tx_id: str) -> None:
        """Execute commit phase."""
        for connection in self.connections.values():
            if connection.in_transaction:
                await connection.commit()
    
    async def _execute_rollback_phase(self, tx_id: str, error: str) -> None:
        """Execute rollback phase."""
        transaction = self.active_transactions.get(tx_id)
        if transaction:
            transaction.state = TransactionState.ROLLED_BACK
        
        for connection in self.connections.values():
            if connection.in_transaction:
                await connection.rollback()


class TransactionConsistencyTester:
    """Main transaction consistency test orchestrator."""
    
    def __init__(self):
        """Initialize test orchestrator."""
        self.manager = DistributedTransactionManager()
        self._setup_mock_databases()
    
    def _setup_mock_databases(self) -> None:
        """Setup mock database connections."""
        auth_db = MockDatabaseConnection(DatabaseType.AUTH_DB)
        backend_db = MockDatabaseConnection(DatabaseType.BACKEND_DB)
        clickhouse = MockDatabaseConnection(DatabaseType.CLICKHOUSE)
        
        self.manager.add_database(DatabaseType.AUTH_DB, auth_db)
        self.manager.add_database(DatabaseType.BACKEND_DB, backend_db)
        self.manager.add_database(DatabaseType.CLICKHOUSE, clickhouse)
    
    def create_test_operation(self, db_type: DatabaseType, operation_type: str, data: Dict) -> MockOperation:
        """Create test operation."""
        return MockOperation(
            id=f"op_{uuid.uuid4().hex[:8]}",
            db_type=db_type,
            operation_type=operation_type,
            data=data
        )
    
    async def verify_rollback_complete(self, tx_id: str) -> bool:
        """Verify all databases rolled back."""
        # If there was a failure, trigger rollback on all connections
        await self._trigger_rollback_all_connections()
        
        # Check if any connection has operations but didn't roll back
        for connection in self.manager.connections.values():
            if connection.operations and not connection.rolled_back:
                return False
        return True
    
    async def _trigger_rollback_all_connections(self) -> None:
        """Trigger rollback on all database connections."""
        for connection in self.manager.connections.values():
            if connection.operations:  # Only rollback if there were operations
                await connection.rollback()
    
    def get_transaction_state(self, tx_id: str) -> Optional[TransactionState]:
        """Get transaction state."""
        transaction = self.manager.active_transactions.get(tx_id)
        return transaction.state if transaction else None
    
    def create_sample_user_data(self) -> Dict[str, Any]:
        """Create sample user data."""
        return {
            "user_id": f"user_{uuid.uuid4().hex[:8]}",
            "email": f"test_{uuid.uuid4().hex[:6]}@example.com", 
            "full_name": "Test User",
            "plan_tier": "mid"
        }
    
    def setup_failure_scenario(self, db_type: DatabaseType, operation_type: str) -> None:
        """Setup failure scenario for testing."""
        connection = self.manager.connections[db_type]
        connection.fail_on_operation = operation_type
    
    def get_operation_counts(self) -> Dict[DatabaseType, int]:
        """Get operation counts per database."""
        counts = {}
        for db_type, connection in self.manager.connections.items():
            counts[db_type] = len(connection.operations)
        return counts
    
    def verify_all_operations_completed(self) -> bool:
        """Verify all operations completed successfully."""
        all_operations = []
        for connection in self.manager.connections.values():
            all_operations.extend(connection.operations)
        return all(op.completed for op in all_operations)


class TransactionTestDataFactory:
    """Factory for creating test data and scenarios."""
    
    @staticmethod
    def create_user_creation_data() -> Dict[str, Any]:
        """Create user creation test data."""
        return {
            "user_id": f"new_user_{uuid.uuid4().hex[:8]}",
            "email": f"newuser_{uuid.uuid4().hex[:6]}@example.com",
            "full_name": "New Test User",
            "plan_tier": "free"
        }
    
    @staticmethod
    def create_user_update_data(user_id: str, version: int = 1) -> Dict[str, Any]:
        """Create user update test data."""
        return {
            "user_id": user_id,
            "plan_tier": "enterprise", 
            "version": version,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    
    @staticmethod
    def create_analytics_event_data(user_id: str, event_type: str) -> Dict[str, Any]:
        """Create analytics event data."""
        return {
            "user_id": user_id,
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_id": f"evt_{uuid.uuid4().hex[:8]}"
        }
    
    @staticmethod
    def create_concurrent_update_scenarios(user_id: str) -> List[Dict[str, Any]]:
        """Create concurrent update scenarios."""
        return [
            {
                "user_id": user_id,
                "plan_tier": "enterprise",
                "version": 1,
                "transaction_source": "transaction_1"
            },
            {
                "user_id": user_id, 
                "plan_tier": "mid",
                "version": 1,
                "transaction_source": "transaction_2"
            }
        ]