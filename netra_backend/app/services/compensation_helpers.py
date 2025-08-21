"""Compensation base helper functions for function decomposition.

Decomposes large compensation functions into 25-line focused helpers.
"""

from typing import Dict, Any, List
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.compensation_models import CompensationAction, CompensationState

logger = central_logger.get_logger(__name__)


def validate_required_keys(compensation_data: Dict[str, Any], required_keys: List[str]) -> bool:
    """Validate compensation data contains required keys."""
    for key in required_keys:
        if key not in compensation_data:
            logger.error(f"Missing required compensation data key: {key}")
            return False
    return True


def update_action_state_executing(action: CompensationAction) -> None:
    """Update action state to executing."""
    action.state = CompensationState.EXECUTING


def update_action_state_completed(action: CompensationAction, action_id: str) -> None:
    """Update action state to completed."""
    action.state = CompensationState.COMPLETED
    logger.info(f"Compensation completed: {action_id}")


def update_action_state_failed(action: CompensationAction, action_id: str, error_msg: str) -> None:
    """Update action state to failed."""
    action.state = CompensationState.FAILED
    action.error_message = error_msg
    logger.error(f"Compensation failed: {action_id}")


def log_preparation_failure(action_id: str) -> None:
    """Log preparation failure."""
    logger.error(f"Compensation preparation failed: {action_id}")


def log_execution_failure(action_id: str) -> None:
    """Log execution failure."""
    logger.error(f"Compensation failed: {action_id}")


def log_compensation_error(action_id: str, error: Exception) -> None:
    """Log compensation error."""
    logger.error(f"Compensation error for {action_id}: {error}")


def log_cleanup_error(cleanup_error: Exception) -> None:
    """Log post-compensation cleanup error."""
    logger.error(f"Post-compensation cleanup failed: {cleanup_error}")


def build_error_context_dict(action: CompensationAction, error: Exception, handler_type: str) -> Dict[str, Any]:
    """Build error context dictionary."""
    return {
        'action_id': action.action_id,
        'operation_id': action.operation_id,
        'action_type': action.action_type,
        'handler_type': handler_type,
        'error_type': type(error).__name__,
        'error_message': str(error),
        'compensation_data_keys': list(action.compensation_data.keys()),
        'retry_count': action.retry_count
    }


def get_non_retryable_errors() -> List[str]:
    """Get list of non-retryable error types."""
    return [
        'ValidationError',
        'PermissionError',
        'AuthenticationError'
    ]


def check_max_retries_exceeded(retry_count: int, max_retries: int = 3) -> bool:
    """Check if max retry attempts exceeded."""
    return retry_count >= max_retries


def is_non_retryable_error(error: Exception) -> bool:
    """Check if error type is non-retryable."""
    non_retryable_errors = get_non_retryable_errors()
    return type(error).__name__ in non_retryable_errors


def should_skip_retry(action: CompensationAction, error: Exception) -> bool:
    """Check if retry should be skipped based on conditions."""
    max_retries = 3
    if check_max_retries_exceeded(action.retry_count, max_retries):
        return True
    if is_non_retryable_error(error):
        return True
    return False