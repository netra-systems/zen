"""
Synthetic Data Validation Module

Handles entry condition checks and request validation
for synthetic data sub-agent operations.
"""

from netra_backend.app.schemas.agent_models import DeepAgentState
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class RequestValidator:
    """Validates incoming requests for synthetic data operations"""
    
    @staticmethod
    def check_entry_conditions(state: DeepAgentState, run_id: str) -> bool:
        """Check if conditions are met for synthetic data generation"""
        if RequestValidator._is_admin_request(state):
            return True
        if RequestValidator._is_synthetic_request(state):
            return True
        
        logger.info(f"Synthetic data generation not required for run_id: {run_id}")
        return False
    
    @staticmethod
    def _is_admin_request(state: DeepAgentState) -> bool:
        """Check if request is from admin mode"""
        triage_result = state.triage_result or {}
        if not isinstance(triage_result, dict):
            return False
        
        category = triage_result.get("category", "")
        is_admin = triage_result.get("is_admin_mode", False)
        return "synthetic" in category.lower() or is_admin
    
    @staticmethod
    def _is_synthetic_request(state: DeepAgentState) -> bool:
        """Check if request explicitly mentions synthetic data"""
        if not state.user_request:
            return False
        request_lower = state.user_request.lower()
        return "synthetic" in request_lower or "generate data" in request_lower


class StateValidator:
    """Validates state and results during processing"""
    
    @staticmethod
    def has_valid_result(state: DeepAgentState) -> bool:
        """Check if state has valid synthetic data result."""
        return (hasattr(state, 'synthetic_data_result') and 
                state.synthetic_data_result and 
                isinstance(state.synthetic_data_result, dict))


class MetricsValidator:
    """Validates metrics and logging data"""
    
    @staticmethod
    def log_completion_summary(metadata: dict, status: dict) -> None:
        """Log completion summary with metrics."""
        table_name = metadata.get('table_name')
        records = status.get('records_generated')
        logger.info(
            f"Synthetic data generation completed: "
            f"table={table_name}, records={records}"
        )
    
    @staticmethod
    def log_final_metrics(state: DeepAgentState) -> None:
        """Log final generation metrics."""
        if not StateValidator.has_valid_result(state):
            return
        result = state.synthetic_data_result
        metadata = result.get('metadata', {})
        status = result.get('generation_status', {})
        MetricsValidator.log_completion_summary(metadata, status)