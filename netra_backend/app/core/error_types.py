"""Core error types module.

Defines resource-related exception classes following SSOT principles.
"""

from typing import Any, Dict, Optional

from netra_backend.app.core.error_codes import ErrorCode, ErrorSeverity
from netra_backend.app.core.exceptions_base import NetraException


class ResourceError(NetraException):
    """Exception raised when resource-related operations fail."""
    
    def __init__(self, message: str = None, resource_type: str = None, 
                 details: Optional[Dict[str, Any]] = None, **kwargs):
        """Initialize ResourceError with resource-specific context."""
        self.resource_type = resource_type
        
        # Build details dictionary with resource context
        if details is None:
            details = {}
        if resource_type:
            details["resource_type"] = resource_type
            
        super().__init__(
            message=message or "Resource operation failed",
            code=ErrorCode.INTERNAL_ERROR,
            severity=ErrorSeverity.HIGH,
            details=details,
            user_message="A system resource error occurred. Please try again later.",
            **kwargs
        )


class MemoryError(ResourceError):
    """Exception raised when memory-related operations fail."""
    
    def __init__(self, message: str = None, memory_usage: int = None, **kwargs):
        """Initialize MemoryError with memory-specific context."""
        details = kwargs.get('details', {})
        if memory_usage is not None:
            details["memory_usage_mb"] = memory_usage
            
        super().__init__(
            message=message or "Memory resource error",
            resource_type="memory",
            details=details,
            **kwargs
        )


class CPUError(ResourceError):
    """Exception raised when CPU-related operations fail."""
    
    def __init__(self, message: str = None, cpu_usage: float = None, **kwargs):
        """Initialize CPUError with CPU-specific context."""
        details = kwargs.get('details', {})
        if cpu_usage is not None:
            details["cpu_usage_percent"] = cpu_usage
            
        super().__init__(
            message=message or "CPU resource error",
            resource_type="cpu",
            details=details,
            **kwargs
        )