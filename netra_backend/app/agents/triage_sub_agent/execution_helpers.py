"""Triage Execution Helper Functions

Helper functions for triage execution to maintain 450-line module limit.
Contains utility functions for result processing, state management, and messaging.
"""

import time
from typing import Any, Dict

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TriageExecutionHelpers:
    """Helper functions for triage execution operations."""
    
    def ensure_triage_result_type(self, result):
        """Ensure result is proper TriageResult object."""
        from netra_backend.app.agents.triage_sub_agent.models import TriageResult
        if isinstance(result, TriageResult):
            return result
        elif isinstance(result, dict):
            return self._convert_dict_to_triage_result(result)
        else:
            return self._create_default_triage_result()
    
    def _convert_dict_to_triage_result(self, result_dict: dict):
        """Convert dictionary to TriageResult with error handling."""
        from netra_backend.app.agents.triage_sub_agent.models import TriageResult
        try:
            return TriageResult(**result_dict)
        except Exception as e:
            logger.warning(f"Failed to convert dict to TriageResult: {e}")
            return self._create_default_triage_result()
    
    def _create_default_triage_result(self):
        """Create default TriageResult for error cases."""
        from netra_backend.app.agents.triage_sub_agent.models import TriageMetadata, TriageResult
        return TriageResult(
            category="unknown", 
            confidence_score=0.5,
            metadata=TriageMetadata(triage_duration_ms=0, fallback_used=True)
        )
    
    def create_error_result(self, error_message: str):
        """Create result object for error cases."""
        from netra_backend.app.agents.triage_sub_agent.models import TriageMetadata, TriageResult
        error_metadata = self._create_error_metadata(error_message)
        params = self._build_error_result_params(error_metadata)
        return TriageResult(**params)
    
    def _create_error_metadata(self, error_message: str):
        """Create metadata for error result."""
        from netra_backend.app.agents.triage_sub_agent.models import TriageMetadata
        return TriageMetadata(
            triage_duration_ms=0,
            error_details=error_message,
            fallback_used=True
        )
    
    def _build_error_result_params(self, metadata) -> dict:
        """Build parameters for error result."""
        return {
            "category": "Error",
            "confidence_score": 0.0,
            "metadata": metadata
        }
    
    def create_emergency_fallback_result(self):
        """Create basic emergency fallback response."""
        from netra_backend.app.agents.triage_sub_agent.models import Priority, TriageMetadata, TriageResult
        metadata = self._create_emergency_metadata()
        params = self._build_emergency_fallback_params(metadata)
        return TriageResult(**params)
    
    def _create_emergency_metadata(self):
        """Create metadata for emergency fallback."""
        from netra_backend.app.agents.triage_sub_agent.models import TriageMetadata
        return TriageMetadata(
            triage_duration_ms=0,
            fallback_used=True,
            error_details="emergency fallback"
        )
    
    def _build_emergency_fallback_params(self, metadata) -> dict:
        """Build parameters for emergency fallback result."""
        from netra_backend.app.agents.triage_sub_agent.models import Priority
        return {
            "category": "General Inquiry",
            "confidence_score": 0.3,
            "priority": Priority.MEDIUM,
            "metadata": metadata
        }
    
    def extract_result_data(self, result) -> tuple:
        """Extract result dictionary and category from result object."""
        if hasattr(result, 'model_dump'):
            result_dict = result.model_dump()
            category = result.category if hasattr(result, 'category') else 'Unknown'
        else:
            result_dict = result if isinstance(result, dict) else {}
            category = result_dict.get('category', 'Unknown')
        return result_dict, category
    
    def determine_completion_status(self, result_dict: dict) -> str:
        """Determine completion status based on result metadata."""
        metadata = result_dict.get("metadata", {}) or {}
        fallback_used = metadata.get("fallback_used", False)
        return "completed_with_fallback" if fallback_used else "completed"
    
    def create_validation_error_result(self, validation):
        """Create validation error result."""
        from netra_backend.app.agents.triage_sub_agent.models import TriageMetadata, TriageResult
        validation_metadata = TriageMetadata(triage_duration_ms=0, fallback_used=True)
        params = self._build_validation_error_params(validation, validation_metadata)
        return TriageResult(**params)
    
    def _build_validation_error_params(self, validation, metadata) -> dict:
        """Build parameters for validation error result."""
        return {
            "category": "Validation Error",
            "confidence_score": 0.0,
            "validation_status": validation,
            "metadata": metadata
        }
    
    def build_completion_message(self, status: str, category: str, 
                               result_dict: dict) -> dict:
        """Build completion message dictionary."""
        return {
            "status": status,
            "message": f"Request categorized as: {category}",
            "result": result_dict
        }
    
    def build_emergency_message(self, result_dict: dict) -> dict:
        """Build emergency fallback message."""
        return {
            "status": "completed_with_emergency_fallback",
            "message": "Triage completed using emergency fallback",
            "result": result_dict
        }


class TriageValidationHelpers:
    """Helper functions for triage validation operations."""
    
    def process_validation_result(self, validation, state: DeepAgentState, run_id: str) -> bool:
        """Process validation result and handle errors."""
        if not validation.is_valid:
            self._handle_validation_error(state, run_id, validation)
            return False
        return True
    
    def _handle_validation_error(self, state: DeepAgentState, run_id: str, validation) -> None:
        """Handle validation error by creating error result."""
        logger.error(f"Invalid request for run_id {run_id}: {validation.validation_errors}")
        helpers = TriageExecutionHelpers()
        error_result = helpers.create_validation_error_result(validation)
        state.triage_result = error_result
        state.step_count += 1