"""Thread route specific utilities - Main exports."""

import time

# Import classes that tests need to patch
from netra_backend.app.services.database.thread_repository import ThreadRepository
from netra_backend.app.services.database.message_repository import MessageRepository
from netra_backend.app.llm.llm_manager import LLMManager

# Import all functions from focused modules
from netra_backend.app.routes.utils.thread_builders import (
    build_messages_metadata,
    build_thread_messages_response,
    build_thread_response,
    convert_threads_to_responses,
    extract_thread_title,
    extract_thread_updated_at,
    format_messages_list,
    format_single_message,
)
from netra_backend.app.routes.utils.thread_creators import (
    create_thread_record,
    create_thread_repositories,
    generate_thread_id,
    get_user_threads,
    prepare_thread_metadata,
)
from netra_backend.app.routes.utils.thread_error_handling import (
    apply_thread_pattern_mappings,
    check_thread_pattern,
    clean_thread_specific_context,
    get_context_mappings,
    get_thread_pattern_mappings,
    handle_route_with_error_logging,
    resolve_clean_context,
    should_log_exc_info,
)
from netra_backend.app.routes.utils.thread_handlers import (
    handle_auto_rename_request,
    handle_create_thread_request,
    handle_delete_thread_request,
    handle_get_messages_request,
    handle_get_thread_request,
    handle_list_threads_request,
    handle_update_thread_request,
    update_thread_metadata_fields,
)
from netra_backend.app.routes.utils.thread_title_generator import (
    build_title_generation_prompt,
    clean_generated_title,
    create_final_thread_response,
    generate_title_with_llm,
    get_fallback_title,
    get_first_user_message_safely,
    send_thread_rename_notification,
    update_thread_with_title,
)
from netra_backend.app.routes.utils.thread_validators import (
    archive_thread_safely,
    get_thread_with_validation,
    validate_thread_access,
    validate_thread_exists,
)

# Maintain backward compatibility by re-exporting all functions
__all__ = [
    # Validators
    'validate_thread_exists', 'validate_thread_access', 
    'get_thread_with_validation', 'archive_thread_safely',
    
    # Builders
    'extract_thread_title', 'extract_thread_updated_at', 'build_thread_response',
    'convert_threads_to_responses', 'format_single_message', 'format_messages_list',
    'build_messages_metadata', 'build_thread_messages_response',
    
    # Creators
    'generate_thread_id', 'prepare_thread_metadata', 'create_thread_record',
    'create_thread_repositories', 'get_user_threads',
    
    # Title generation
    'get_first_user_message_safely', 'build_title_generation_prompt',
    'clean_generated_title', 'get_fallback_title', 'generate_title_with_llm',
    'update_thread_with_title', 'send_thread_rename_notification',
    'create_final_thread_response',
    
    # Handlers
    'handle_list_threads_request', 'handle_create_thread_request',
    'handle_get_thread_request', 'update_thread_metadata_fields',
    'handle_update_thread_request', 'handle_delete_thread_request',
    'handle_get_messages_request', 'handle_auto_rename_request',
    
    # Error handling
    'get_context_mappings', 'check_thread_pattern', 'get_thread_pattern_mappings',
    'apply_thread_pattern_mappings', 'clean_thread_specific_context',
    'resolve_clean_context', 'should_log_exc_info', 'handle_route_with_error_logging'
]


# Legacy function aliases for backward compatibility
def _extract_thread_title(thread, title=None):
    """Legacy alias for extract_thread_title."""
    return extract_thread_title(thread, title)


def _extract_thread_updated_at(thread):
    """Legacy alias for extract_thread_updated_at."""
    return extract_thread_updated_at(thread)


def _format_single_message(msg):
    """Legacy alias for format_single_message."""
    return format_single_message(msg)


def _format_messages_list(messages):
    """Legacy alias for format_messages_list."""
    return format_messages_list(messages)


def _build_messages_metadata(thread_id, total, limit, offset):
    """Legacy alias for build_messages_metadata."""
    return build_messages_metadata(thread_id, total, limit, offset)


def _build_title_generation_prompt(content):
    """Legacy alias for build_title_generation_prompt."""
    return build_title_generation_prompt(content)


def _clean_generated_title(generated_title):
    """Legacy alias for clean_generated_title."""
    return clean_generated_title(generated_title)


def _get_fallback_title():
    """Legacy alias for get_fallback_title."""
    return get_fallback_title()


def _get_context_mappings():
    """Legacy alias for get_context_mappings."""
    return get_context_mappings()


def _check_thread_pattern(clean_context, pattern, replacement):
    """Legacy alias for check_thread_pattern."""
    return check_thread_pattern(clean_context, pattern, replacement)


def _get_thread_pattern_mappings():
    """Legacy alias for get_thread_pattern_mappings."""
    return get_thread_pattern_mappings()


def _apply_thread_pattern_mappings(clean_context):
    """Legacy alias for apply_thread_pattern_mappings."""
    return apply_thread_pattern_mappings(clean_context)


def _clean_thread_specific_context(clean_context):
    """Legacy alias for clean_thread_specific_context."""
    return clean_thread_specific_context(clean_context)


def _resolve_clean_context(error_context):
    """Legacy alias for resolve_clean_context."""
    return resolve_clean_context(error_context)


def _should_log_exc_info(error_context):
    """Legacy alias for should_log_exc_info."""
    return should_log_exc_info(error_context)