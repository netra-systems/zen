"""
SSOT Re-export of UserExecutionContext.
Maintains backward compatibility while following Single Source of Truth principles.
"""

# SSOT import from the actual implementation
from netra_backend.app.services.user_execution_context import UserExecutionContext

# Re-export for backward compatibility
__all__ = [
    "UserExecutionContext",
]