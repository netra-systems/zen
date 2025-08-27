"""Error logging type definitions.

This module defines types and enums for error logging functionality.
"""

from enum import Enum
from typing import Any, Dict, Optional
from dataclasses import dataclass


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