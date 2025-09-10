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

BACKWARD COMPATIBILITY: UnifiedLifecycleManager is aliased to SystemLifecycle during migration.
"""

from .unified_lifecycle_manager import SystemLifecycle
from .unified_configuration_manager import UnifiedConfigurationManager
from .unified_state_manager import UnifiedStateManager

# PHASE 2: Maintain backward compatibility during migration
UnifiedLifecycleManager = SystemLifecycle

__all__ = [
    "UnifiedLifecycleManager",  # Legacy name - maintained for backward compatibility
    "SystemLifecycle",          # New business-focused name
    "UnifiedConfigurationManager", 
    "UnifiedStateManager"
]