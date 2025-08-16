# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-14T00:00:00.000000+00:00
# Agent: Claude Sonnet 4 claude-sonnet-4-20250514
# Context: Refactor admin_tool_dispatcher.py - Extract tool handler functions
# Git: anthony-aug-13-2 | Refactoring for modularity
# Change: Create | Scope: Module | Risk: Low
# Session: admin-tool-refactor | Seq: 2
# Review: Pending | Score: 95
# ================================
"""
Admin Tool Handler Functions

This module contains individual tool handler functions split from the original
dispatcher to comply with function size limits (≤8 lines each).
"""
from typing import Dict, Any, Optional, Callable
from sqlalchemy.orm import Session
from app.db.models_postgres import User
from app.logging_config import central_logger

logger = central_logger


async def execute_corpus_manager(action: str, 
                                user: User, 
                                db: Session, 
                                **kwargs) -> Dict[str, Any]:
    """Execute corpus manager actions via corpus service"""
    action_handlers = get_corpus_action_handlers()
    handler = action_handlers.get(action)
    if handler:
        return await handler(user, db, **kwargs)
    return {"error": f"Unknown corpus action: {action}"}


def get_corpus_action_handlers() -> Dict[str, Callable]:
    """Get mapping of corpus actions to handlers."""
    return {
        'create': handle_corpus_create,
        'list': lambda user, db, **kwargs: handle_corpus_list(db),
        'validate': lambda user, db, **kwargs: handle_corpus_validate(**kwargs)
    }


async def handle_corpus_create(user: User, 
                              db: Session, 
                              **kwargs) -> Dict[str, Any]:
    """Handle corpus creation"""
    from app.services import corpus_service
    from .tool_handler_helpers import create_corpus_success_response
    params = extract_corpus_create_params(kwargs, user)
    result = await corpus_service.create_corpus(**params, db=db)
    return create_corpus_success_response(result)


def extract_corpus_create_params(kwargs: Dict[str, Any], user: User) -> Dict[str, Any]:
    """Extract parameters for corpus creation."""
    from .tool_handler_helpers import build_corpus_create_params_base, add_corpus_description
    params = build_corpus_create_params_base(kwargs, user)
    add_corpus_description(params, kwargs)
    return params


async def handle_corpus_list(db: Session) -> Dict[str, Any]:
    """Handle corpus listing"""
    from app.services import corpus_service
    from .tool_handler_helpers import create_corpus_list_response
    corpora = await corpus_service.list_corpora(db)
    return create_corpus_list_response(corpora)


async def handle_corpus_validate(**kwargs) -> Dict[str, Any]:
    """Handle corpus validation"""
    from .tool_handler_helpers import check_corpus_id_required, create_corpus_validation_response
    corpus_id = kwargs.get('corpus_id')
    check_corpus_id_required(corpus_id)
    return create_corpus_validation_response(corpus_id)


async def execute_synthetic_generator(action: str, 
                                     user: User, 
                                     db: Session, 
                                     **kwargs) -> Dict[str, Any]:
    """Execute synthetic data generator actions"""
    action_handlers = get_synthetic_action_handlers()
    handler = action_handlers.get(action)
    if handler:
        return await handler(user, db, **kwargs)
    return {"error": f"Unknown synthetic generator action: {action}"}


def get_synthetic_action_handlers() -> Dict[str, Callable]:
    """Get mapping of synthetic actions to handlers."""
    return {
        'generate': handle_synthetic_generate,
        'list_presets': lambda user, db, **kwargs: handle_synthetic_list_presets(db)
    }


async def handle_synthetic_generate(user: User, 
                                   db: Session, 
                                   **kwargs) -> Dict[str, Any]:
    """Handle synthetic data generation"""
    from app.services.synthetic_data_service import SyntheticDataService
    from .tool_handler_helpers import create_synthetic_success_response
    synthetic_service = SyntheticDataService(db)
    params = extract_synthetic_params(kwargs, user)
    result = await synthetic_service.generate_synthetic_data(**params)
    return create_synthetic_success_response(result)


def extract_synthetic_params(kwargs: Dict[str, Any], user: User) -> Dict[str, Any]:
    """Extract parameters for synthetic data generation."""
    from .tool_handler_helpers import extract_corpus_service_params, add_user_id_to_params
    params = extract_corpus_service_params(kwargs)
    add_user_id_to_params(params, user)
    return params


async def handle_synthetic_list_presets(db: Session) -> Dict[str, Any]:
    """Handle listing synthetic data presets"""
    from app.services.synthetic_data_service import SyntheticDataService
    from .tool_handler_helpers import create_presets_list_response
    synthetic_service = SyntheticDataService(db)
    presets = await synthetic_service.list_presets()
    return create_presets_list_response(presets)


async def execute_user_admin(action: str, 
                            user: User, 
                            db: Session, 
                            **kwargs) -> Dict[str, Any]:
    """Execute user admin actions via user service"""
    action_handlers = get_user_admin_handlers()
    handler = action_handlers.get(action)
    if handler:
        return await handler(db, **kwargs)
    return {"error": f"Unknown user admin action: {action}"}


def get_user_admin_handlers() -> Dict[str, Callable]:
    """Get mapping of user admin actions to handlers."""
    return {
        'create_user': lambda user, db, **kwargs: handle_user_create(db, **kwargs),
        'grant_permission': lambda user, db, **kwargs: handle_user_grant_permission(db, **kwargs)
    }


async def handle_user_create(db: Session, **kwargs) -> Dict[str, Any]:
    """Handle user creation"""
    from app.services import user_service
    from .tool_handler_helpers import check_email_required, build_user_create_params, create_user_success_response
    email = kwargs.get('email')
    check_email_required(email)
    params = build_user_create_params(kwargs)
    params["db"] = db
    result = await user_service.create_user(**params)
    return create_user_success_response(result)


async def handle_user_grant_permission(db: Session, **kwargs) -> Dict[str, Any]:
    """Handle granting user permissions"""
    from app.services.permission_service import PermissionService
    from .tool_handler_helpers import check_user_permission_params, create_permission_grant_response
    user_email = kwargs.get('user_email')
    permission = kwargs.get('permission')
    check_user_permission_params(user_email, permission)
    success = await PermissionService.grant_permission(user_email, permission, db)
    return create_permission_grant_response(success)


async def execute_system_configurator(action: str, 
                                     user: User, 
                                     db: Session, 
                                     **kwargs) -> Dict[str, Any]:
    """Execute system configurator actions"""
    if action == 'update_setting':
        return await handle_system_update_setting(**kwargs)
    else:
        return {"error": f"Unknown system configurator action: {action}"}


async def handle_system_update_setting(**kwargs) -> Dict[str, Any]:
    """Handle system setting update"""
    from .tool_handler_helpers import check_setting_name_required, create_setting_update_result
    setting_name = kwargs.get('setting_name')
    value = kwargs.get('value')
    check_setting_name_required(setting_name)
    return create_setting_update_result(setting_name, value)


async def execute_log_analyzer(action: str, 
                              user: User, 
                              db: Session, 
                              **kwargs) -> Dict[str, Any]:
    """Execute log analyzer actions via debug service"""
    if action == 'analyze':
        return await handle_log_analyze(user, db, **kwargs)
    else:
        return {"error": f"Unknown log analyzer action: {action}"}


async def handle_log_analyze(user: User, 
                            db: Session, 
                            **kwargs) -> Dict[str, Any]:
    """Handle log analysis"""
    from app.services.debug_service import DebugService
    from .tool_handler_helpers import extract_log_analysis_params, build_debug_service_params, create_log_analysis_result
    query, time_range = extract_log_analysis_params(kwargs)
    debug_service = DebugService(db)
    service_params = build_debug_service_params(user)
    result = await debug_service.get_debug_info(**service_params)
    return create_log_analysis_result(query, time_range, result)


def extract_log_params(kwargs: Dict[str, Any]) -> tuple:
    """Extract log analysis parameters."""
    from .tool_handler_helpers import extract_log_analysis_params
    return extract_log_analysis_params(kwargs)


def build_log_analysis_response(query: str, time_range: str, result: dict) -> Dict[str, Any]:
    """Build log analysis response."""
    from .tool_handler_helpers import create_log_analysis_result
    return create_log_analysis_result(query, time_range, result)


def get_tool_executor(tool_name: str) -> Optional[Callable]:
    """Get the appropriate executor function for a tool"""
    executor_map = {
        'corpus_manager': execute_corpus_manager,
        'synthetic_generator': execute_synthetic_generator,
        'user_admin': execute_user_admin,
        'system_configurator': execute_system_configurator,
        'log_analyzer': execute_log_analyzer
    }
    return executor_map.get(tool_name)


async def execute_admin_tool(tool_name: str, 
                            user: User, 
                            db: Session, 
                            action: str, 
                            **kwargs) -> Dict[str, Any]:
    """Execute admin tool with appropriate handler"""
    from .tool_handler_helpers import check_tool_executor_exists
    executor = get_tool_executor(tool_name)
    check_tool_executor_exists(executor)
    return await executor(action, user, db, **kwargs)