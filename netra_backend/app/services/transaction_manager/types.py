"""Transaction manager type definitions and enums.

Core types for distributed transaction management.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from netra_backend.app.core.error_recovery import OperationType


class TransactionState(Enum):
    """States of a transaction."""
    PENDING = "pending"
    ACTIVE = "active"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


class OperationState(Enum):
    """States of individual operations within a transaction."""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATED = "compensated"


@dataclass
class Operation:
    """Represents a single operation within a transaction."""
    operation_id: str
    operation_type: OperationType
    state: OperationState = OperationState.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    compensation_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Transaction:
    """Represents a distributed transaction."""
    transaction_id: str
    state: TransactionState = TransactionState.PENDING
    operations: List[Operation] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    timeout: timedelta = field(default_factory=lambda: timedelta(minutes=5))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_expired(self) -> bool:
        """Check if transaction has expired."""
        return datetime.now() - self.created_at > self.timeout
    
    @property
    def completed_operations(self) -> List[Operation]:
        """Get all completed operations."""
        return [op for op in self.operations 
                if op.state == OperationState.COMPLETED]
    
    @property
    def failed_operations(self) -> List[Operation]:
        """Get all failed operations."""
        return [op for op in self.operations 
                if op.state == OperationState.FAILED]