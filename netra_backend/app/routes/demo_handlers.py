"""Demo route handlers - Main exports."""

# Import all functions from focused modules
from netra_backend.app.routes.demo_handlers_chat import (
    handle_demo_chat, execute_demo_chat_flow, get_or_create_session_id,
    execute_demo_chat_service, process_chat_request, create_chat_tracking_data,
    add_chat_tracking_task, track_chat_interaction, create_chat_response
)
from netra_backend.app.routes.demo_handlers_roi import (
    handle_roi_calculation, execute_roi_calculation_flow, execute_roi_calculation,
    calculate_roi_metrics, create_roi_tracking_data, add_roi_tracking_task,
    track_roi_calculation
)
from netra_backend.app.routes.demo_handlers_templates import (
    handle_industry_templates, generate_metrics_from_service,
    handle_synthetic_metrics, build_demo_metrics_response
)
from netra_backend.app.routes.demo_handlers_export import (
    handle_export_report, execute_export_flow, execute_report_generation,
    build_report_params, generate_demo_report, create_export_tracking_data,
    add_export_tracking_task, track_report_export, create_export_response
)
from netra_backend.app.routes.demo_handlers_session import (
    handle_session_status, handle_session_feedback
)
from netra_backend.app.routes.demo_handlers_analytics import (
    handle_demo_analytics, get_analytics_from_service
)
from netra_backend.app.routes.demo_handlers_utils import (
    log_and_raise_error, raise_not_found_error, validate_admin_access,
    build_feedback_success_response, build_tracking_params
)

# Export all functions for backward compatibility
__all__ = [
    # Chat handlers
    'handle_demo_chat', 'execute_demo_chat_flow', 'get_or_create_session_id',
    'execute_demo_chat_service', 'process_chat_request', 'create_chat_tracking_data',
    'add_chat_tracking_task', 'track_chat_interaction', 'create_chat_response',
    
    # ROI handlers
    'handle_roi_calculation', 'execute_roi_calculation_flow', 'execute_roi_calculation',
    'calculate_roi_metrics', 'create_roi_tracking_data', 'add_roi_tracking_task',
    'track_roi_calculation',
    
    # Templates and metrics
    'handle_industry_templates', 'generate_metrics_from_service',
    'handle_synthetic_metrics', 'build_demo_metrics_response',
    
    # Export handlers
    'handle_export_report', 'execute_export_flow', 'execute_report_generation',
    'build_report_params', 'generate_demo_report', 'create_export_tracking_data',
    'add_export_tracking_task', 'track_report_export', 'create_export_response',
    
    # Session handlers
    'handle_session_status', 'handle_session_feedback',
    
    # Analytics handlers
    'handle_demo_analytics', 'get_analytics_from_service',
    
    # Utilities
    'log_and_raise_error', 'raise_not_found_error', 'validate_admin_access',
    'build_feedback_success_response', 'build_tracking_params'
]


# Legacy function aliases for backward compatibility
def _get_or_create_session_id(session_id):
    """Legacy alias."""
    return get_or_create_session_id(session_id)


def _execute_demo_chat_flow(request, background_tasks, demo_service, current_user):
    """Legacy alias."""
    return execute_demo_chat_flow(request, background_tasks, demo_service, current_user)


def _execute_demo_chat_service(request, session_id, demo_service, current_user):
    """Legacy alias."""
    return execute_demo_chat_service(request, session_id, demo_service, current_user)


def _process_chat_request(request, session_id, demo_service, current_user):
    """Legacy alias."""
    return process_chat_request(request, session_id, demo_service, current_user)


def _create_chat_tracking_data(request):
    """Legacy alias."""
    return create_chat_tracking_data(request)


def _add_chat_tracking_task(background_tasks, demo_service, session_id, data):
    """Legacy alias."""
    return add_chat_tracking_task(background_tasks, demo_service, session_id, data)


def _track_chat_interaction(background_tasks, demo_service, session_id, request):
    """Legacy alias."""
    return track_chat_interaction(background_tasks, demo_service, session_id, request)


def _create_chat_response(result, session_id):
    """Legacy alias."""
    return create_chat_response(result, session_id)


def _execute_roi_calculation_flow(request, background_tasks, demo_service):
    """Legacy alias."""
    return execute_roi_calculation_flow(request, background_tasks, demo_service)


def _execute_roi_calculation(request, demo_service):
    """Legacy alias."""
    return execute_roi_calculation(request, demo_service)


def _calculate_roi_metrics(request, demo_service):
    """Legacy alias."""
    return calculate_roi_metrics(request, demo_service)


def _log_and_raise_error(message, error):
    """Legacy alias."""
    return log_and_raise_error(message, error)


def _raise_not_found_error(message):
    """Legacy alias."""
    return raise_not_found_error(message)


def _validate_admin_access(current_user):
    """Legacy alias."""
    return validate_admin_access(current_user)


def _generate_metrics_from_service(scenario, duration_hours, demo_service):
    """Legacy alias."""
    return generate_metrics_from_service(scenario, duration_hours, demo_service)


async def _build_demo_metrics_response(metrics):
    """Legacy alias."""
    # The actual function is async, so we need to await it
    import asyncio
    if asyncio.iscoroutinefunction(build_demo_metrics_response):
        return await build_demo_metrics_response(metrics)
    return build_demo_metrics_response(metrics)


def _get_analytics_from_service(demo_service, days):
    """Legacy alias."""
    return get_analytics_from_service(demo_service, days)