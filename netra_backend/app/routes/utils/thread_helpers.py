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
    handle_send_message_request,
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