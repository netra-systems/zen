"""Demo handlers utilities."""
from fastapi import HTTPException
from typing import Dict, Any
from app.logging_config import central_logger


def log_and_raise_error(message: str, error: Exception) -> None:
    """Log error and raise HTTP exception."""
    logger = central_logger.get_logger(__name__)
    logger.error(f"{message}: {str(error)}")
    raise HTTPException(status_code=500, detail=message)


def raise_not_found_error(message: str) -> None:
    """Raise 404 HTTP exception."""
    raise HTTPException(status_code=404, detail=message)


def validate_admin_access(current_user: Dict) -> None:
    """Validate user has admin access."""
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")


def build_feedback_success_response() -> Dict[str, str]:
    """Build feedback submission success response."""
    return {"status": "success", "message": "Feedback received"}


def build_tracking_params(session_id: str, interaction_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Build tracking parameters for service call."""
    return {"session_id": session_id, "interaction_type": interaction_type, "data": data}