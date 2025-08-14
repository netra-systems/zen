"""
Startup Checks - Legacy Compatibility Module

This module maintains backward compatibility while delegating to the new
modular startup_checks package. All functionality has been moved to focused
modules under 300 lines each.
"""

# Import from modular implementation
from .startup_checks import (
    StartupCheckResult,
    StartupChecker,
    run_startup_checks
)

# Maintain backward compatibility - all legacy code removed
# All classes and functions now imported from startup_checks module

__all__ = [
    "StartupCheckResult",
    "StartupChecker", 
    "run_startup_checks"
]