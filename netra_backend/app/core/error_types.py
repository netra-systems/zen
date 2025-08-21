"""Error types, enums, and data classes for error logging.

Provides core data structures for error classification and context management.
"""

import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from collections import deque

from netra_backend.app.core.error_codes import ErrorCode, ErrorSeverity
from netra_backend.app.core.error_recovery import OperationType


class LogLevel(Enum):
    """Enhanced log levels for error logging."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    SECURITY = "security"
    BUSINESS = "business"


class ErrorCategory(Enum):
    """Categories for error classification."""
    SYSTEM = "system"
    APPLICATION = "application"
    SECURITY = "security"
    BUSINESS = "business"
    INFRASTRUCTURE = "infrastructure"
    INTEGRATION = "integration"
    USER = "user"


@dataclass
class DetailedErrorContext:
    """Rich context information for error logging with extensive metadata."""
    # Core identifiers
    error_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: Optional[str] = None
    trace_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # Temporal information
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Error classification
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    category: ErrorCategory = ErrorCategory.APPLICATION
    error_code: Optional[ErrorCode] = None
    
    # Operational context
    operation_type: Optional[OperationType] = None
    operation_id: Optional[str] = None
    agent_type: Optional[str] = None
    component: Optional[str] = None
    
    # User and request context
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    
    # Technical context
    stack_trace: Optional[str] = None
    environment: str = "development"
    version: Optional[str] = None
    
    # Business context
    business_impact: Optional[str] = None
    affected_users: int = 0
    financial_impact: float = 0.0
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        data = asdict(self)
        data = self._convert_enums(data)
        data = self._convert_datetime(data)
        return data
    
    def _convert_enums(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert enum fields to values."""
        enum_fields = ['severity', 'category', 'error_code', 'operation_type']
        for field_name in enum_fields:
            value = data.get(field_name)
            if hasattr(value, 'value'):
                data[field_name] = value.value
        return data
    
    def _convert_datetime(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert datetime to ISO string."""
        if isinstance(data.get('timestamp'), datetime):
            data['timestamp'] = data['timestamp'].isoformat()
        return data


@dataclass
class ErrorAggregation:
    """Aggregated error information for pattern analysis."""
    error_signature: str
    count: int = 0
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    affected_components: Set[str] = field(default_factory=set)
    affected_users: Set[str] = field(default_factory=set)
    severity_distribution: Dict[str, int] = field(default_factory=dict)
    recent_occurrences: deque = field(default_factory=lambda: deque(maxlen=100))