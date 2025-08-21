"""State versioning and migration system for backward compatibility.

This module provides version management and migration capabilities
for agent state data structures. All implementations are now modularized
for maintainability and adherence to the 450-line limit.
"""

# Re-export core classes for backward compatibility
# Import compatibility checker
from netra_backend.app.services.state_compatibility_checker import (
    StateCompatibilityChecker,
)
from netra_backend.app.services.state_migration_core import (
    StateMigration,
    StateVersion,
    StateVersionManager,
)

# Import migration implementations
from netra_backend.app.services.state_migration_implementations import (
    Migration_1_0_to_1_1,
    Migration_1_1_to_1_2,
)

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