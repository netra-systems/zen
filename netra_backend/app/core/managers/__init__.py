"""
Core Managers Package

SSOT (Single Source of Truth) manager implementations consolidating 808+ legacy managers.
These unified managers serve as the central integration points for platform-wide operations.

Manager Hierarchy:
- UnifiedLifecycleManager: All lifecycle operations (startup, shutdown, health monitoring)  
- UnifiedConfigurationManager: All configuration management across services
- UnifiedStateManager: All state management operations

Business Value: Reduces operational complexity from 808 managers to 3 SSOT managers.
Strategic Impact: Eliminates manager sprawl and provides consistent interfaces.
"""

from .unified_lifecycle_manager import UnifiedLifecycleManager
from .unified_configuration_manager import UnifiedConfigurationManager
from .unified_state_manager import UnifiedStateManager

__all__ = [
    "UnifiedLifecycleManager",
    "UnifiedConfigurationManager", 
    "UnifiedStateManager"
]