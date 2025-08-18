"""Demo analytics handlers."""
from typing import Dict, Any

from app.services.demo_service import DemoService


async def handle_demo_analytics(
    days: int, demo_service: DemoService, current_user: Dict
) -> Dict[str, Any]:
    """Get demo analytics summary."""
    from app.routes.demo_handlers_utils import validate_admin_access
    validate_admin_access(current_user)
    try:
        return await get_analytics_from_service(demo_service, days)
    except Exception as e:
        from app.routes.demo_handlers_utils import log_and_raise_error
        log_and_raise_error("Failed to get analytics", e)


async def get_analytics_from_service(demo_service: DemoService, days: int) -> Dict[str, Any]:
    """Get analytics data from demo service."""
    return await demo_service.get_analytics_summary(days=days)