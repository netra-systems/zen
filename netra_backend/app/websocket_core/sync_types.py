"""WebSocket Synchronization Types

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Error handling and reliability
- Value Impact: Provides structured error handling for WebSocket synchronization
- Strategic Impact: Consistent error propagation patterns
"""

from typing import Any, Optional
from dataclasses import dataclass


@dataclass
class CriticalCallbackFailure(Exception):
    """Exception raised when critical callbacks fail during state synchronization."""
    
    callback_name: str
    original_error: Optional[Exception] = None
    context: Optional[dict] = None
    
    def __str__(self) -> str:
        """String representation of the error."""
        msg = f"Critical callback '{self.callback_name}' failed"
        if self.original_error:
            msg += f": {self.original_error}"
        return msg