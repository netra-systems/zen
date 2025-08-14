"""State versioning and migration system for backward compatibility.

This module provides version management and migration capabilities
for agent state data structures.
"""

from typing import Dict, Any, List, Optional, Callable, Tuple
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from app.logging_config import central_logger
from app.core.exceptions import NetraException

logger = central_logger.get_logger(__name__)


@dataclass
class StateVersion:
    """State schema version information."""
    version: str
    description: str
    release_date: datetime
    deprecated: bool = False
    migration_required: bool = False


class StateMigration(ABC):
    """Abstract base class for state migrations."""
    
    @property
    @abstractmethod
    def from_version(self) -> str:
        """Source version for migration."""
        pass
    
    @property
    @abstractmethod
    def to_version(self) -> str:
        """Target version for migration."""
        pass
    
    @abstractmethod
    def migrate(self, state_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform state migration from source to target version."""
        pass
    
    @abstractmethod
    def validate_migration(self, original: Dict[str, Any], 
                          migrated: Dict[str, Any]) -> bool:
        """Validate that migration was successful."""
        pass


class StateVersionManager:
    """Manages state versions and migrations."""
    
    def __init__(self):
        self.versions: Dict[str, StateVersion] = {}
        self.migrations: Dict[str, StateMigration] = {}
        self.migration_paths: Dict[str, List[str]] = {}
        self._register_default_versions()
    
    def register_version(self, version: StateVersion) -> None:
        """Register a new state version."""
        self.versions[version.version] = version
        logger.debug(f"Registered state version {version.version}")
    
    def register_migration(self, migration: StateMigration) -> None:
        """Register a migration between versions."""
        migration_key = f"{migration.from_version}:{migration.to_version}"
        self.migrations[migration_key] = migration
        self._rebuild_migration_paths()
        logger.debug(f"Registered migration {migration_key}")
    
    def get_current_version(self) -> str:
        """Get the current state schema version."""
        # Return the latest non-deprecated version
        active_versions = [v for v in self.versions.values() if not v.deprecated]
        if not active_versions:
            return "1.0"
        return max(active_versions, key=lambda v: v.release_date).version
    
    def is_migration_needed(self, from_version: str, 
                           to_version: Optional[str] = None) -> bool:
        """Check if migration is needed between versions."""
        if to_version is None:
            to_version = self.get_current_version()
        
        return from_version != to_version and \
               self._has_migration_path(from_version, to_version)
    
    def migrate_state(self, state_data: Dict[str, Any], 
                     from_version: str, 
                     to_version: Optional[str] = None) -> Dict[str, Any]:
        """Migrate state data between versions."""
        if to_version is None:
            to_version = self.get_current_version()
        
        if from_version == to_version:
            return state_data
        
        migration_path = self._find_migration_path(from_version, to_version)
        if not migration_path:
            raise NetraException(
                f"No migration path from {from_version} to {to_version}")
        
        current_data = state_data.copy()
        current_version = from_version
        
        for next_version in migration_path:
            migration_key = f"{current_version}:{next_version}"
            migration = self.migrations.get(migration_key)
            
            if not migration:
                raise NetraException(f"Missing migration {migration_key}")
            
            original_data = current_data.copy()
            current_data = migration.migrate(current_data)
            
            # Validate migration
            if not migration.validate_migration(original_data, current_data):
                raise NetraException(f"Migration validation failed: {migration_key}")
            
            current_version = next_version
            logger.debug(f"Migrated state from {from_version} to {current_version}")
        
        return current_data
    
    def _register_default_versions(self) -> None:
        """Register default state versions."""
        v1_0 = StateVersion(
            version="1.0",
            description="Initial state schema",
            release_date=datetime(2025, 1, 1)
        )
        
        v1_1 = StateVersion(
            version="1.1", 
            description="Added execution context and metadata",
            release_date=datetime(2025, 1, 15)
        )
        
        v1_2 = StateVersion(
            version="1.2",
            description="Enhanced agent phase tracking",
            release_date=datetime(2025, 2, 1)
        )
        
        self.register_version(v1_0)
        self.register_version(v1_1)
        self.register_version(v1_2)
    
    def _has_migration_path(self, from_version: str, to_version: str) -> bool:
        """Check if migration path exists between versions."""
        return from_version in self.migration_paths and \
               to_version in self.migration_paths[from_version]
    
    def _find_migration_path(self, from_version: str, to_version: str) -> Optional[List[str]]:
        """Find migration path between versions using BFS."""
        if from_version == to_version:
            return []
        
        # Simple BFS to find shortest migration path
        queue = [(from_version, [])]
        visited = {from_version}
        
        while queue:
            current_version, path = queue.pop(0)
            
            # Find all direct migrations from current version
            for migration_key, migration in self.migrations.items():
                migration_from, migration_to = migration_key.split(':')
                
                if migration_from == current_version and migration_to not in visited:
                    new_path = path + [migration_to]
                    
                    if migration_to == to_version:
                        return new_path
                    
                    queue.append((migration_to, new_path))
                    visited.add(migration_to)
        
        return None
    
    def _rebuild_migration_paths(self) -> None:
        """Rebuild migration paths after registering new migrations."""
        self.migration_paths.clear()
        
        for from_version in self.versions:
            reachable = set()
            queue = [from_version]
            visited = {from_version}
            
            while queue:
                current = queue.pop(0)
                
                for migration_key in self.migrations:
                    migration_from, migration_to = migration_key.split(':')
                    
                    if migration_from == current and migration_to not in visited:
                        reachable.add(migration_to)
                        queue.append(migration_to)
                        visited.add(migration_to)
            
            self.migration_paths[from_version] = list(reachable)


class Migration_1_0_to_1_1(StateMigration):
    """Migration from version 1.0 to 1.1."""
    
    @property
    def from_version(self) -> str:
        return "1.0"
    
    @property
    def to_version(self) -> str:
        return "1.1"
    
    def migrate(self, state_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add execution context and enhanced metadata."""
        migrated = state_data.copy()
        
        # Add execution context if missing
        if 'execution_context' not in migrated:
            migrated['execution_context'] = {}
        
        # Enhance metadata structure
        if 'metadata' in migrated and isinstance(migrated['metadata'], dict):
            metadata = migrated['metadata']
            if 'custom_fields' not in metadata:
                metadata['custom_fields'] = {}
            if 'execution_context' not in metadata:
                metadata['execution_context'] = {}
        
        # Add version info
        migrated['_schema_version'] = "1.1"
        
        return migrated
    
    def validate_migration(self, original: Dict[str, Any], 
                          migrated: Dict[str, Any]) -> bool:
        """Validate migration to version 1.1."""
        # Check required fields are preserved
        required_fields = ['user_request', 'step_count']
        for field in required_fields:
            if field in original and original[field] != migrated.get(field):
                return False
        
        # Check new fields were added
        if 'execution_context' not in migrated:
            return False
        
        if migrated.get('_schema_version') != "1.1":
            return False
        
        return True


class Migration_1_1_to_1_2(StateMigration):
    """Migration from version 1.1 to 1.2."""
    
    @property
    def from_version(self) -> str:
        return "1.1"
    
    @property
    def to_version(self) -> str:
        return "1.2"
    
    def migrate(self, state_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add enhanced agent phase tracking."""
        migrated = state_data.copy()
        
        # Add agent phase if missing
        if 'agent_phase' not in migrated:
            # Infer phase from existing state
            migrated['agent_phase'] = self._infer_agent_phase(migrated)
        
        # Add phase transition history
        if 'phase_history' not in migrated:
            migrated['phase_history'] = []
        
        # Add checkpoint metadata
        if 'checkpoint_metadata' not in migrated:
            migrated['checkpoint_metadata'] = {
                'last_checkpoint': None,
                'recovery_points': []
            }
        
        # Update version
        migrated['_schema_version'] = "1.2"
        
        return migrated
    
    def validate_migration(self, original: Dict[str, Any], 
                          migrated: Dict[str, Any]) -> bool:
        """Validate migration to version 1.2."""
        # Check new fields were added
        required_new_fields = ['agent_phase', 'phase_history', 'checkpoint_metadata']
        for field in required_new_fields:
            if field not in migrated:
                return False
        
        # Check version was updated
        if migrated.get('_schema_version') != "1.2":
            return False
        
        return True
    
    def _infer_agent_phase(self, state_data: Dict[str, Any]) -> str:
        """Infer current agent phase from state data."""
        if state_data.get('final_report'):
            return "completion"
        elif state_data.get('report_result'):
            return "reporting"
        elif state_data.get('action_plan_result'):
            return "action_planning"
        elif state_data.get('optimizations_result'):
            return "optimization"
        elif state_data.get('data_result'):
            return "data_analysis"
        elif state_data.get('triage_result'):
            return "triage"
        else:
            return "initialization"


class StateCompatibilityChecker:
    """Checks state compatibility across versions."""
    
    def __init__(self, version_manager: StateVersionManager):
        self.version_manager = version_manager
    
    def check_compatibility(self, state_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Check if state data is compatible with current version."""
        issues = []
        
        # Check version field
        current_version = self.version_manager.get_current_version()
        state_version = state_data.get('_schema_version', '1.0')
        
        if state_version != current_version:
            if self.version_manager.is_migration_needed(state_version, current_version):
                issues.append(f"Migration needed from {state_version} to {current_version}")
            else:
                issues.append(f"No migration path available from {state_version}")
        
        # Check for deprecated fields
        deprecated_fields = self._get_deprecated_fields(state_version)
        for field in deprecated_fields:
            if field in state_data:
                issues.append(f"Deprecated field '{field}' found")
        
        # Check for missing required fields
        required_fields = self._get_required_fields(current_version)
        for field in required_fields:
            if field not in state_data:
                issues.append(f"Missing required field '{field}'")
        
        is_compatible = len(issues) == 0
        return is_compatible, issues
    
    def _get_deprecated_fields(self, version: str) -> List[str]:
        """Get list of deprecated fields for version."""
        # This would be configured based on version
        deprecated_by_version = {
            "1.0": [],
            "1.1": ["legacy_metadata"],
            "1.2": ["legacy_metadata", "old_execution_context"]
        }
        return deprecated_by_version.get(version, [])
    
    def _get_required_fields(self, version: str) -> List[str]:
        """Get list of required fields for version."""
        required_by_version = {
            "1.0": ["user_request", "step_count"],
            "1.1": ["user_request", "step_count", "execution_context"],
            "1.2": ["user_request", "step_count", "execution_context", "agent_phase"]
        }
        return required_by_version.get(version, [])


# Global instances
state_version_manager = StateVersionManager()
state_compatibility_checker = StateCompatibilityChecker(state_version_manager)

# Register default migrations
state_version_manager.register_migration(Migration_1_0_to_1_1())
state_version_manager.register_migration(Migration_1_1_to_1_2())