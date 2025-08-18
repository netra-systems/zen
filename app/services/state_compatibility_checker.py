"""State compatibility checking functionality.

This module provides compatibility checking for state data across versions.
"""

from typing import Dict, Any, List, Tuple
from app.services.state_migration_core import StateVersionManager


class StateCompatibilityChecker:
    """Checks state compatibility across versions."""
    
    def __init__(self, version_manager: StateVersionManager):
        self.version_manager = version_manager
    
    def check_compatibility(self, state_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Check if state data is compatible with current version."""
        issues = []
        self._check_version_compatibility(state_data, issues)
        self._check_deprecated_fields(state_data, issues)
        self._check_required_fields(state_data, issues)
        is_compatible = len(issues) == 0
        return is_compatible, issues
    
    def _check_version_compatibility(self, state_data: Dict[str, Any], 
                                    issues: List[str]) -> None:
        """Check version compatibility."""
        current_version = self.version_manager.get_current_version()
        state_version = state_data.get('_schema_version', '1.0')
        if state_version != current_version:
            self._add_version_issue(state_version, current_version, issues)
    
    def _add_version_issue(self, state_version: str, current_version: str, 
                          issues: List[str]) -> None:
        """Add version compatibility issue."""
        if self.version_manager.is_migration_needed(state_version, current_version):
            issues.append(f"Migration needed from {state_version} to {current_version}")
        else:
            issues.append(f"No migration path available from {state_version}")
    
    def _check_deprecated_fields(self, state_data: Dict[str, Any], 
                                issues: List[str]) -> None:
        """Check for deprecated fields."""
        state_version = state_data.get('_schema_version', '1.0')
        deprecated_fields = self._get_deprecated_fields(state_version)
        for field in deprecated_fields:
            if field in state_data:
                issues.append(f"Deprecated field '{field}' found")
    
    def _check_required_fields(self, state_data: Dict[str, Any], 
                              issues: List[str]) -> None:
        """Check for missing required fields."""
        current_version = self.version_manager.get_current_version()
        required_fields = self._get_required_fields(current_version)
        for field in required_fields:
            if field not in state_data:
                issues.append(f"Missing required field '{field}'")
    
    def _get_deprecated_fields(self, version: str) -> List[str]:
        """Get list of deprecated fields for version."""
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