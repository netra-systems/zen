"""Error logging type definitions.

This module defines types and enums for error logging functionality.
"""

from datetime import datetime
from collections import defaultdict
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field


class LogLevel(str, Enum):
    """Logging levels for error messages."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ErrorCategory(str, Enum):
    """Categories of errors for classification."""
    SYSTEM = "SYSTEM"
    APPLICATION = "APPLICATION"
    VALIDATION = "VALIDATION"
    NETWORK = "NETWORK"
    DATABASE = "DATABASE"
    AUTHENTICATION = "AUTHENTICATION"
    AUTHORIZATION = "AUTHORIZATION"
    CONFIGURATION = "CONFIGURATION"
    EXTERNAL_SERVICE = "EXTERNAL_SERVICE"


class ErrorSeverity(str, Enum):
    """Severity levels for errors."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class DetailedErrorContext:
    """Detailed context information for error logging."""
    category: ErrorCategory
    severity: ErrorSeverity
    operation: str
    details: Dict[str, Any]
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    component: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ErrorAggregation:
    """Aggregated error information for tracking patterns."""
    error_signature: str
    count: int = 0
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    affected_components: Set[str] = field(default_factory=set)
    affected_users: Set[str] = field(default_factory=set)
    severity_distribution: Dict[str, int] = field(default_factory=dict)
    recent_occurrences: List[Dict[str, Any]] = field(default_factory=list)