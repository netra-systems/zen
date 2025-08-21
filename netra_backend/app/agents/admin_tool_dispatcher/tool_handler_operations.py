# AI AGENT MODIFICATION METADATA - AGT-003
# ===============================================
# Timestamp: 2025-08-18T12:16:00.000000+00:00
# Agent: Claude Sonnet 4 claude-sonnet-4-20250514  
# Context: Extract tool handler operations into separate module
# Git: 8-18-25-AM | Admin tool dispatcher modernization
# Change: Modernize | Scope: Module | Risk: Low
# Session: admin-tool-modernization | Seq: 003
# Review: Pending | Score: 98
# ===============================================
"""
Tool Handler Operations Module

Helper functions and operations for admin tool handlers.
Contains all business logic operations extracted from main handlers.

Business Value: Modular operations for improved maintainability.
Target Segments: Growth & Enterprise (improved admin operations).
"""
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models_postgres import User


# Core utility functions for tool handlers
def extract_corpus_create_params(kwargs: Dict[str, Any], user: User) -> Dict[str, Any]:
    """Extract parameters for corpus creation."""
    from .tool_handler_helpers import build_corpus_create_params_base, add_corpus_description
    params = build_corpus_create_params_base(kwargs, user)
    add_corpus_description(params, kwargs)
    return params


def extract_synthetic_params(kwargs: Dict[str, Any], user: User) -> Dict[str, Any]:
    """Extract parameters for synthetic data generation."""
    from .tool_handler_helpers import extract_corpus_service_params, add_user_id_to_params
    params = extract_corpus_service_params(kwargs)
    add_user_id_to_params(params, user)
    return params


# Helper functions for corpus operations
async def _execute_corpus_creation(params: Dict[str, Any], db: AsyncSession) -> Any:
    """Execute corpus creation with service"""
    from app.services import corpus_service
    return await corpus_service.create_corpus(**params, db=db)


def _create_corpus_response(result: Any) -> Dict[str, Any]:
    """Create corpus success response"""
    from .tool_handler_helpers import create_corpus_success_response
    return create_corpus_success_response(result)


# Helper functions for synthetic operations
def _create_synthetic_service(db: AsyncSession):
    """Create synthetic data service instance"""
    from app.services.synthetic_data_service import SyntheticDataService
    return SyntheticDataService(db)


def _create_synthetic_response(result: Any) -> Dict[str, Any]:
    """Create synthetic success response"""
    from .tool_handler_helpers import create_synthetic_success_response
    return create_synthetic_success_response(result)


# Helper functions for user operations
def _prepare_user_create_params(kwargs: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
    """Prepare user creation parameters"""
    from .tool_handler_helpers import build_user_create_params
    params = build_user_create_params(kwargs)
    params["db"] = db
    return params


async def _execute_user_creation(params: Dict[str, Any]) -> Any:
    """Execute user creation with service"""
    from app.services import user_service
    return await user_service.create_user(**params)


def _create_user_response(result: Any) -> Dict[str, Any]:
    """Create user success response"""
    from .tool_handler_helpers import create_user_success_response
    return create_user_success_response(result)


# Helper functions for permission operations
def _extract_permission_params(kwargs: Dict[str, Any]) -> tuple:
    """Extract permission parameters"""
    user_email = kwargs.get('user_email')
    permission = kwargs.get('permission')
    return user_email, permission


async def _grant_user_permission(user_email: str, permission: str, db: AsyncSession) -> bool:
    """Grant user permission via service"""
    from app.services.permission_service import PermissionService
    return await PermissionService.grant_permission(user_email, permission, db)


def _create_permission_response(success: bool) -> Dict[str, Any]:
    """Create permission grant response"""
    from .tool_handler_helpers import create_permission_grant_response
    return create_permission_grant_response(success)


# Helper functions for log analysis operations
async def _execute_debug_analysis(db: AsyncSession, user: User) -> dict:
    """Execute debug analysis with service"""
    from app.services.debug_service import DebugService
    from .tool_handler_helpers import build_debug_service_params
    service = DebugService(db)
    service_params = build_debug_service_params(user)
    return await service.get_debug_info(**service_params)


def _create_log_analysis_response(query: str, time_range: str, result: dict) -> Dict[str, Any]:
    """Create log analysis response"""
    from .tool_handler_helpers import create_log_analysis_result
    return create_log_analysis_result(query, time_range, result)