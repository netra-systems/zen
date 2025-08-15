"""WebSocket error types and data structures.

Defines error severity levels and error data structures for WebSocket operations.
"""

import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


# Import ErrorSeverity from single source of truth
from app.core.error_codes import ErrorSeverity


@dataclass
class WebSocketErrorInfo:
    """Represents WebSocket error information with context data (not an exception)."""
    error_id: str = field(default_factory=lambda: f"err_{int(time.time() * 1000)}")
    connection_id: Optional[str] = None
    user_id: Optional[str] = None
    error_type: str = "unknown"
    message: str = ""
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    context: Dict[str, Any] = field(default_factory=dict)
    recoverable: bool = True
    retry_count: int = 0
    max_retries: int = 3