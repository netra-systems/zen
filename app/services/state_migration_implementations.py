"""Concrete state migration implementations.

This module contains the specific migration classes for each version transition.
"""

from typing import Dict, Any, Optional
from app.services.state_migration_core import StateMigration


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
        self._add_execution_context(migrated)
        self._enhance_metadata_structure(migrated)
        self._set_schema_version(migrated, "1.1")
        return migrated
    
    def _add_execution_context(self, migrated: Dict[str, Any]) -> None:
        """Add execution context if missing."""
        if 'execution_context' not in migrated:
            migrated['execution_context'] = {}
    
    def _enhance_metadata_structure(self, migrated: Dict[str, Any]) -> None:
        """Enhance metadata structure."""
        if 'metadata' in migrated and isinstance(migrated['metadata'], dict):
            metadata = migrated['metadata']
            self._ensure_metadata_fields(metadata)
    
    def _ensure_metadata_fields(self, metadata: Dict[str, Any]) -> None:
        """Ensure required metadata fields exist."""
        if 'custom_fields' not in metadata:
            metadata['custom_fields'] = {}
        if 'execution_context' not in metadata:
            metadata['execution_context'] = {}
    
    def _set_schema_version(self, migrated: Dict[str, Any], version: str) -> None:
        """Set schema version."""
        migrated['_schema_version'] = version
    
    def validate_migration(self, original: Dict[str, Any], 
                          migrated: Dict[str, Any]) -> bool:
        """Validate migration to version 1.1."""
        if not self._validate_preserved_fields(original, migrated):
            return False
        return self._validate_new_fields_v11(migrated)
    
    def _validate_preserved_fields(self, original: Dict[str, Any], 
                                  migrated: Dict[str, Any]) -> bool:
        """Validate required fields are preserved."""
        required_fields = ['user_request', 'step_count']
        for field in required_fields:
            if field in original and original[field] != migrated.get(field):
                return False
        return True
    
    def _validate_new_fields_v11(self, migrated: Dict[str, Any]) -> bool:
        """Validate new fields were added for v1.1."""
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
        self._add_agent_phase(migrated)
        self._add_phase_history(migrated)
        self._add_checkpoint_metadata(migrated)
        migrated['_schema_version'] = "1.2"
        return migrated
    
    def _add_agent_phase(self, migrated: Dict[str, Any]) -> None:
        """Add agent phase if missing."""
        if 'agent_phase' not in migrated:
            migrated['agent_phase'] = self._infer_agent_phase(migrated)
    
    def _add_phase_history(self, migrated: Dict[str, Any]) -> None:
        """Add phase transition history."""
        if 'phase_history' not in migrated:
            migrated['phase_history'] = []
    
    def _add_checkpoint_metadata(self, migrated: Dict[str, Any]) -> None:
        """Add checkpoint metadata."""
        if 'checkpoint_metadata' not in migrated:
            migrated['checkpoint_metadata'] = {
                'last_checkpoint': None,
                'recovery_points': []
            }
    
    def validate_migration(self, original: Dict[str, Any], 
                          migrated: Dict[str, Any]) -> bool:
        """Validate migration to version 1.2."""
        if not self._validate_required_fields_v12(migrated):
            return False
        return self._validate_version_v12(migrated)
    
    def _validate_required_fields_v12(self, migrated: Dict[str, Any]) -> bool:
        """Validate required fields for v1.2."""
        required_new_fields = ['agent_phase', 'phase_history', 'checkpoint_metadata']
        for field in required_new_fields:
            if field not in migrated:
                return False
        return True
    
    def _validate_version_v12(self, migrated: Dict[str, Any]) -> bool:
        """Validate version was updated to 1.2."""
        return migrated.get('_schema_version') == "1.2"
    
    def _infer_agent_phase(self, state_data: Dict[str, Any]) -> str:
        """Infer current agent phase from state data."""
        completion_phase = self._check_completion_phases(state_data)
        if completion_phase:
            return completion_phase
        return self._check_analysis_phases(state_data)
    
    def _check_completion_phases(self, state_data: Dict[str, Any]) -> Optional[str]:
        """Check completion and reporting phases."""
        if state_data.get('final_report'):
            return "completion"
        elif state_data.get('report_result'):
            return "reporting"
        elif state_data.get('action_plan_result'):
            return "action_planning"
        return None
    
    def _check_analysis_phases(self, state_data: Dict[str, Any]) -> str:
        """Check analysis and processing phases."""
        if state_data.get('optimizations_result'):
            return "optimization"
        elif state_data.get('data_result'):
            return "data_analysis"
        elif state_data.get('triage_result'):
            return "triage"
        return "initialization"