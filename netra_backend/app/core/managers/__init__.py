"""
Core Managers Package

SSOT (Single Source of Truth) manager implementations consolidating 808+ legacy managers.
These unified managers serve as the central integration points for platform-wide operations.

Manager Hierarchy:
- SystemLifecycle (formerly UnifiedLifecycleManager): All lifecycle operations (startup, shutdown, health monitoring)  
- UnifiedConfigurationManager: All configuration management across services
- UnifiedStateManager: All state management operations

Business Value: Reduces operational complexity from 808 managers to 3 SSOT managers.
Strategic Impact: Eliminates manager sprawl and provides consistent interfaces.

MIGRATION STATUS: 
- UnifiedLifecycleManager  ->  SystemLifecycle (COMPLETED)
- LifecycleManagerFactory  ->  SystemLifecycleFactory (COMPLETED)
- Backward compatibility maintained with deprecation warnings

BUSINESS NAMING CONVENTION: Classes now use business-focused names that clearly indicate their purpose.
"""

from .unified_lifecycle_manager import (
    SystemLifecycle, 
    SystemLifecycleFactory,
    get_lifecycle_manager,
    setup_application_lifecycle
)
from .unified_configuration_manager import UnifiedConfigurationManager
from .unified_state_manager import UnifiedStateManager

# PHASE 2 & 3: Maintain backward compatibility during migration
import warnings

def _deprecation_warning(old_name: str, new_name: str) -> None:
    """Emit deprecation warning for old naming conventions."""
    warnings.warn(
        f"{old_name} is deprecated and will be removed in a future version. "
        f"Please use {new_name} instead for business-focused naming compliance.",
        DeprecationWarning,
        stacklevel=3
    )

class _DeprecatedUnifiedLifecycleManager:
    """Deprecated wrapper for UnifiedLifecycleManager  ->  SystemLifecycle migration."""
    def __new__(cls, *args, **kwargs):
        _deprecation_warning("UnifiedLifecycleManager", "SystemLifecycle")
        return SystemLifecycle(*args, **kwargs)

class _DeprecatedLifecycleManagerFactory:
    """Deprecated wrapper for LifecycleManagerFactory  ->  SystemLifecycleFactory migration."""
    def __getattr__(self, name):
        _deprecation_warning("LifecycleManagerFactory", "SystemLifecycleFactory")
        return getattr(SystemLifecycleFactory, name)

# Backward compatibility aliases with deprecation warnings
UnifiedLifecycleManager = _DeprecatedUnifiedLifecycleManager
LifecycleManagerFactory = _DeprecatedLifecycleManagerFactory()

__all__ = [
    "UnifiedLifecycleManager",   # Legacy name - maintained for backward compatibility
    "SystemLifecycle",           # New business-focused name
    "LifecycleManagerFactory",   # Legacy factory name - maintained for backward compatibility
    "SystemLifecycleFactory",    # New business-focused factory name
    "get_lifecycle_manager",     # Convenience function
    "setup_application_lifecycle",  # Convenience function
    "UnifiedConfigurationManager", 
    "UnifiedStateManager"
]