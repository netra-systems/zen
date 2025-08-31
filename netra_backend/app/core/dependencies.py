"""Dependencies Compatibility Shim Module

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Enable test execution and prevent import errors
- Value Impact: Ensures test suite can import dependency-related code
- Strategic Impact: Maintains backward compatibility during code refactoring

This module provides a compatibility layer for code that expects app.core.dependencies imports.
All actual dependency injection logic is handled in the main dependencies module.
"""

# Compatibility shim for tests expecting a Dependencies class
# The actual dependency injection logic is in netra_backend.app.dependencies
# This is just for backward compatibility

import warnings
warnings.warn(
    "netra_backend.app.core.dependencies is deprecated. Use 'from netra_backend.app.dependencies import' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Import all dependency functions from the actual module for compatibility
from netra_backend.app.dependencies import *

# Create a minimal Dependencies class for backward compatibility with tests
class Dependencies:
    """Compatibility class for legacy tests expecting a Dependencies class.
    
    Note: This is deprecated. New code should use dependency injection functions
    from netra_backend.app.dependencies directly.
    """
    
    def __init__(self):
        """Initialize Dependencies compatibility wrapper."""
        pass
    
    def get_database(self):
        """Compatibility method for database access."""
        from netra_backend.app.database import get_db
        return get_db()
    
    def process(self):
        """Generic process method for test compatibility."""
        return {"status": "initialized", "dependencies": "loaded"}

# Export compatibility class
__all__ = ["Dependencies"]