"""Demo session management handlers."""
from typing import Dict, Any

from app.services.demo_service import DemoService


async def handle_session_status(
    session_id: str, demo_service: DemoService
) -> Dict[str, Any]:
    """Get demo session status."""
    try:
        return await demo_service.get_session_status(session_id)
    except ValueError as e:
        from app.routes.demo_handlers_utils import raise_not_found_error
        raise_not_found_error(str(e))
    except Exception as e:
        from app.routes.demo_handlers_utils import log_and_raise_error
        log_and_raise_error("Failed to get session status", e)


async def handle_session_feedback(
    session_id: str, feedback: Dict[str, Any], demo_service: DemoService
) -> Dict[str, str]:
    """Submit demo session feedback."""
    try:
        await demo_service.submit_feedback(session_id, feedback)
        from app.routes.demo_handlers_utils import build_feedback_success_response
        return build_feedback_success_response()
    except Exception as e:
        from app.routes.demo_handlers_utils import log_and_raise_error
        log_and_raise_error("Failed to submit feedback", e)