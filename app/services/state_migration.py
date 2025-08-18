"""State versioning and migration system for backward compatibility.

This module provides version management and migration capabilities
for agent state data structures. All implementations are now modularized
for maintainability and adherence to the 300-line limit.
"""

# Re-export core classes for backward compatibility
from app.services.state_migration_core import (
    StateVersion,
    StateMigration, 
    StateVersionManager
)

# Import migration implementations
from app.services.state_migration_implementations import (
    Migration_1_0_to_1_1,
    Migration_1_1_to_1_2
)

# Import compatibility checker
from app.services.state_compatibility_checker import StateCompatibilityChecker

# Global instances for backward compatibility
state_version_manager = StateVersionManager()
state_compatibility_checker = StateCompatibilityChecker(state_version_manager)

# Register default migrations
state_version_manager.register_migration(Migration_1_0_to_1_1())
state_version_manager.register_migration(Migration_1_1_to_1_2())

# Export commonly used items
__all__ = [
    'StateVersion',
    'StateMigration',
    'StateVersionManager', 
    'Migration_1_0_to_1_1',
    'Migration_1_1_to_1_2',
    'StateCompatibilityChecker',
    'state_version_manager',
    'state_compatibility_checker'
]