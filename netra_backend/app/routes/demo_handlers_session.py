"""Demo session management handlers."""
from typing import Dict, Any

from netra_backend.app.services.demo_service import DemoService


async def handle_session_status(
    session_id: str, demo_service: DemoService
) -> Dict[str, Any]:
    """Get demo session status."""
    return await execute_session_status_with_error_handling(session_id, demo_service)


async def execute_session_status_with_error_handling(
    session_id: str, demo_service: DemoService
) -> Dict[str, Any]:
    """Execute session status with error handling."""
    return await handle_session_status_logic(session_id, demo_service)


async def handle_session_status_logic(
    session_id: str, demo_service: DemoService
) -> Dict[str, Any]:
    """Handle session status logic with error handling."""
    try:
        return await demo_service.get_session_status(session_id)
    except ValueError as e:
        handle_session_value_error(e)
    except Exception as e:
        handle_session_general_error("Failed to get session status", e)


def handle_session_value_error(e: ValueError) -> None:
    """Handle ValueError in session operations."""
    from netra_backend.app.routes.demo_handlers_utils import raise_not_found_error
    raise_not_found_error(str(e))


def handle_session_general_error(message: str, e: Exception) -> None:
    """Handle general exception in session operations."""
    from netra_backend.app.routes.demo_handlers_utils import log_and_raise_error
    log_and_raise_error(message, e)


async def handle_session_feedback(
    session_id: str, feedback: Dict[str, Any], demo_service: DemoService
) -> Dict[str, str]:
    """Submit demo session feedback."""
    return await execute_feedback_with_error_handling(session_id, feedback, demo_service)


async def execute_feedback_with_error_handling(
    session_id: str, feedback: Dict[str, Any], demo_service: DemoService
) -> Dict[str, str]:
    """Execute feedback submission with error handling."""
    return await handle_feedback_submission(session_id, feedback, demo_service)


async def handle_feedback_submission(
    session_id: str, feedback: Dict[str, Any], demo_service: DemoService
) -> Dict[str, str]:
    """Handle feedback submission with error handling."""
    try:
        await demo_service.submit_feedback(session_id, feedback)
        return build_success_response()
    except Exception as e:
        handle_session_general_error("Failed to submit feedback", e)


def build_success_response() -> Dict[str, str]:
    """Build feedback success response."""
    from netra_backend.app.routes.demo_handlers_utils import build_feedback_success_response
    return build_feedback_success_response()