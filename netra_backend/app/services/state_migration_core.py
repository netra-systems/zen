"""Core state versioning and migration system classes.

This module provides the foundational classes for state version management.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from netra_backend.app.core.exceptions import NetraException
from netra_backend.app.logging_config import central_logger

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
        target_version = to_version or self.get_current_version()
        if from_version == target_version:
            return state_data
        
        migration_path = self._validate_migration_path(from_version, target_version)
        return self._execute_migration_chain(state_data, from_version, migration_path)
    
    def _validate_migration_path(self, from_version: str, to_version: str) -> List[str]:
        """Validate and return migration path."""
        migration_path = self._find_migration_path(from_version, to_version)
        if not migration_path:
            self._raise_no_migration_path_error(from_version, to_version)
        return migration_path
    
    def _raise_no_migration_path_error(self, from_version: str, to_version: str) -> None:
        """Raise error for missing migration path."""
        raise NetraException(f"No migration path from {from_version} to {to_version}")
    
    def _execute_migration_chain(self, state_data: Dict[str, Any], 
                                from_version: str, migration_path: List[str]) -> Dict[str, Any]:
        """Execute chain of migrations."""
        current_data = state_data.copy()
        current_version = from_version
        current_data, current_version = self._apply_migration_steps(
            current_data, current_version, migration_path)
        return current_data
    
    def _apply_migration_steps(self, current_data: Dict[str, Any],
                              current_version: str, migration_path: List[str]) -> Tuple[Dict[str, Any], str]:
        """Apply each migration step in sequence."""
        for next_version in migration_path:
            current_data = self._execute_single_migration(
                current_data, current_version, next_version)
            current_version = next_version
        return current_data, current_version
    
    def _execute_single_migration(self, current_data: Dict[str, Any], 
                                 current_version: str, next_version: str) -> Dict[str, Any]:
        """Execute single migration step."""
        migration_key = f"{current_version}:{next_version}"
        migration = self._get_migration(migration_key)
        original_data = current_data.copy()
        migrated_data = self._perform_migration_with_validation(
            migration, current_data, original_data, migration_key, current_version, next_version)
        return migrated_data
    
    def _perform_migration_with_validation(self, migration: StateMigration, current_data: Dict[str, Any],
                                          original_data: Dict[str, Any], migration_key: str,
                                          current_version: str, next_version: str) -> Dict[str, Any]:
        """Perform migration and validate result."""
        migrated_data = migration.migrate(current_data)
        self._validate_migration_result(migration, original_data, migrated_data, migration_key)
        self._log_migration_success(current_version, next_version)
        return migrated_data
    
    def _log_migration_success(self, current_version: str, next_version: str) -> None:
        """Log successful migration."""
        logger.debug(f"Migrated state from {current_version} to {next_version}")
    
    def _get_migration(self, migration_key: str) -> StateMigration:
        """Get migration by key."""
        migration = self.migrations.get(migration_key)
        if not migration:
            raise NetraException(f"Missing migration {migration_key}")
        return migration
    
    def _validate_migration_result(self, migration: StateMigration, 
                                  original: Dict[str, Any], migrated: Dict[str, Any],
                                  migration_key: str) -> None:
        """Validate migration result."""
        if not migration.validate_migration(original, migrated):
            raise NetraException(f"Migration validation failed: {migration_key}")
    
    def _register_default_versions(self) -> None:
        """Register default state versions."""
        self._register_version_1_0()
        self._register_version_1_1()
        self._register_version_1_2()
    
    def _register_version_1_0(self) -> None:
        """Register version 1.0."""
        version = StateVersion(
            version="1.0",
            description="Initial state schema",
            release_date=datetime(2025, 1, 1)
        )
        self.register_version(version)
    
    def _register_version_1_1(self) -> None:
        """Register version 1.1."""
        version = StateVersion(
            version="1.1", 
            description="Added execution context and metadata",
            release_date=datetime(2025, 1, 15)
        )
        self.register_version(version)
    
    def _register_version_1_2(self) -> None:
        """Register version 1.2."""
        version = StateVersion(
            version="1.2",
            description="Enhanced agent phase tracking",
            release_date=datetime(2025, 2, 1)
        )
        self.register_version(version)
    
    def _has_migration_path(self, from_version: str, to_version: str) -> bool:
        """Check if migration path exists between versions."""
        return from_version in self.migration_paths and \
               to_version in self.migration_paths[from_version]
    
    def _find_migration_path(self, from_version: str, to_version: str) -> Optional[List[str]]:
        """Find migration path between versions using BFS."""
        if from_version == to_version:
            return []
        
        queue = [(from_version, [])]
        visited = {from_version}
        return self._bfs_migration_path(queue, visited, to_version)
    
    def _bfs_migration_path(self, queue: List[Tuple[str, List[str]]], 
                           visited: set, to_version: str) -> Optional[List[str]]:
        """BFS algorithm for finding migration path."""
        while queue:
            current_version, path = queue.pop(0)
            result = self._process_migration_candidates(
                current_version, path, visited, to_version, queue)
            if result is not None:
                return result
        return None
    
    def _process_migration_candidates(self, current_version: str, path: List[str],
                                     visited: set, to_version: str, 
                                     queue: List[Tuple[str, List[str]]]) -> Optional[List[str]]:
        """Process migration candidates from current version."""
        for migration_key, migration in self.migrations.items():
            migration_from, migration_to = migration_key.split(':')
            result = self._try_migration_candidate(
                migration_from, migration_to, current_version, path, 
                visited, to_version, queue)
            if result is not None:
                return result
        return None
    
    def _try_migration_candidate(self, migration_from: str, migration_to: str,
                                current_version: str, path: List[str], visited: set,
                                to_version: str, queue: List[Tuple[str, List[str]]]) -> Optional[List[str]]:
        """Try single migration candidate."""
        if self._should_explore_migration(migration_from, migration_to, 
                                         current_version, visited):
            return self._explore_migration_path(
                migration_to, path, to_version, queue, visited)
        return None
    
    def _should_explore_migration(self, migration_from: str, migration_to: str,
                                 current_version: str, visited: set) -> bool:
        """Check if migration should be explored."""
        return (migration_from == current_version and 
                migration_to not in visited)
    
    def _explore_migration_path(self, migration_to: str, path: List[str], 
                               to_version: str, queue: List[Tuple[str, List[str]]],
                               visited: set) -> Optional[List[str]]:
        """Explore migration path option."""
        new_path = path + [migration_to]
        if migration_to == to_version:
            return new_path
        self._add_to_search_queue(migration_to, new_path, queue, visited)
        return None
    
    def _add_to_search_queue(self, migration_to: str, new_path: List[str],
                            queue: List[Tuple[str, List[str]]], visited: set) -> None:
        """Add migration target to search queue."""
        queue.append((migration_to, new_path))
        visited.add(migration_to)
    
    def _rebuild_migration_paths(self) -> None:
        """Rebuild migration paths after registering new migrations."""
        self.migration_paths.clear()
        for from_version in self.versions:
            reachable_versions = self._find_reachable_versions(from_version)
            self.migration_paths[from_version] = list(reachable_versions)
    
    def _find_reachable_versions(self, from_version: str) -> set:
        """Find all reachable versions from given version."""
        reachable = set()
        queue = [from_version]
        visited = {from_version}
        self._explore_reachable_versions(queue, visited, reachable)
        return reachable
    
    def _explore_reachable_versions(self, queue: List[str], 
                                   visited: set, reachable: set) -> None:
        """Explore reachable versions using BFS."""
        while queue:
            current = queue.pop(0)
            self._process_migration_targets(current, visited, reachable, queue)
    
    def _process_migration_targets(self, current: str, visited: set, 
                                  reachable: set, queue: List[str]) -> None:
        """Process migration targets from current version."""
        for migration_key in self.migrations:
            migration_from, migration_to = migration_key.split(':')
            self._check_and_add_reachable_version(
                migration_from, migration_to, current, visited, reachable, queue)
    
    def _check_and_add_reachable_version(self, migration_from: str, migration_to: str,
                                        current: str, visited: set, reachable: set, 
                                        queue: List[str]) -> None:
        """Check and add reachable version to collections."""
        if self._can_reach_version(migration_from, migration_to, current, visited):
            self._add_reachable_version(migration_to, visited, reachable, queue)
    
    def _add_reachable_version(self, migration_to: str, visited: set, reachable: set, queue: List[str]) -> None:
        """Add reachable version to collections."""
        reachable.add(migration_to)
        queue.append(migration_to)
        visited.add(migration_to)
    
    def _can_reach_version(self, migration_from: str, migration_to: str,
                          current: str, visited: set) -> bool:
        """Check if version can be reached."""
        return (migration_from == current and migration_to not in visited)