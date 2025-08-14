# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-14T00:00:00.000000+00:00
# Agent: Claude Sonnet 4 claude-sonnet-4-20250514
# Context: Refactor admin_tool_dispatcher.py - Extract validation functions
# Git: anthony-aug-13-2 | Refactoring for modularity
# Change: Create | Scope: Module | Risk: Low
# Session: admin-tool-refactor | Seq: 3
# Review: Pending | Score: 95
# ================================
"""
Admin Tool Validation Module

This module contains permission validation and access control functions
extracted from the original dispatcher to comply with size limits.
"""
from typing import List, Optional
from app.db.models_postgres import User
from app.services.permission_service import PermissionService


def get_available_admin_tools(user: Optional[User]) -> List[str]:
    """Get list of available admin tools for current user"""
    if not user:
        return []
    
    tools = []
    tools.extend(get_corpus_tools_if_permitted(user))
    tools.extend(get_synthetic_tools_if_permitted(user))
    tools.extend(get_user_admin_tools_if_permitted(user))
    tools.extend(get_system_admin_tools_if_permitted(user))
    
    return tools


def get_corpus_tools_if_permitted(user: User) -> List[str]:
    """Get corpus tools if user has corpus permissions"""
    if PermissionService.has_permission(user, "corpus_write"):
        return ["corpus_manager"]
    return []


def get_synthetic_tools_if_permitted(user: User) -> List[str]:
    """Get synthetic data tools if user has synthetic permissions"""
    if PermissionService.has_permission(user, "synthetic_generate"):
        return ["synthetic_generator"]
    return []


def get_user_admin_tools_if_permitted(user: User) -> List[str]:
    """Get user admin tools if user has user management permissions"""
    if PermissionService.has_permission(user, "user_management"):
        return ["user_admin"]
    return []


def get_system_admin_tools_if_permitted(user: User) -> List[str]:
    """Get system admin tools if user has system admin permissions"""
    if PermissionService.has_permission(user, "system_admin"):
        return ["system_configurator", "log_analyzer"]
    return []


def validate_admin_tool_access(user: Optional[User], tool_name: str) -> bool:
    """Validate if user has access to specific admin tool"""
    if not user:
        return False
    
    permission_map = get_permission_map()
    required_permission = permission_map.get(tool_name)
    
    if not required_permission:
        return False
    
    return PermissionService.has_permission(user, required_permission)


def get_permission_map() -> dict[str, str]:
    """Get mapping of tool names to required permissions"""
    return {
        "corpus_manager": "corpus_write",
        "synthetic_generator": "synthetic_generate", 
        "user_admin": "user_management",
        "system_configurator": "system_admin",
        "log_analyzer": "system_admin"
    }


def get_required_permissions(tool_name: str) -> List[str]:
    """Get required permissions for a tool"""
    permission_map = {
        "corpus_manager": ["corpus_write"],
        "synthetic_generator": ["synthetic_generate"],
        "user_admin": ["user_management"],
        "system_configurator": ["system_admin"],
        "log_analyzer": ["system_admin"]
    }
    return permission_map.get(tool_name, [])


def check_admin_tools_enabled(user: Optional[User]) -> bool:
    """Check if admin tools should be enabled for user"""
    if not user:
        return False
    return PermissionService.is_developer_or_higher(user)


def validate_tool_input(tool_name: str, **kwargs) -> Optional[str]:
    """Validate tool input parameters and return error if invalid"""
    validators = get_tool_validators()
    validator = validators.get(tool_name)
    
    if validator:
        return validator(**kwargs)
    
    return None


def get_tool_validators() -> dict:
    """Get mapping of tool names to their validators"""
    return {
        "corpus_manager": validate_corpus_manager_input,
        "synthetic_generator": validate_synthetic_generator_input,
        "user_admin": validate_user_admin_input,
        "system_configurator": validate_system_configurator_input,
        "log_analyzer": validate_log_analyzer_input
    }


def validate_corpus_manager_input(**kwargs) -> Optional[str]:
    """Validate corpus manager input parameters"""
    action = kwargs.get('action', 'default')
    
    if action == 'create':
        return validate_corpus_create_input(**kwargs)
    elif action == 'validate':
        return validate_corpus_validate_input(**kwargs)
    
    return None


def validate_corpus_create_input(**kwargs) -> Optional[str]:
    """Validate corpus creation input"""
    name = kwargs.get('name')
    if name and len(name) > 255:
        return "Corpus name too long (max 255 characters)"
    return None


def validate_corpus_validate_input(**kwargs) -> Optional[str]:
    """Validate corpus validation input"""
    corpus_id = kwargs.get('corpus_id')
    if not corpus_id:
        return "corpus_id is required for validation"
    return None


def validate_synthetic_generator_input(**kwargs) -> Optional[str]:
    """Validate synthetic generator input parameters"""
    action = kwargs.get('action', 'default')
    
    if action == 'generate':
        return validate_synthetic_generate_input(**kwargs)
    
    return None


def validate_synthetic_generate_input(**kwargs) -> Optional[str]:
    """Validate synthetic data generation input"""
    count = kwargs.get('count', 10)
    if count and (count < 1 or count > 1000):
        return "Count must be between 1 and 1000"
    return None


def validate_user_admin_input(**kwargs) -> Optional[str]:
    """Validate user admin input parameters"""
    action = kwargs.get('action', 'default')
    
    if action == 'create_user':
        return validate_user_create_input(**kwargs)
    elif action == 'grant_permission':
        return validate_user_grant_permission_input(**kwargs)
    
    return None


def validate_user_create_input(**kwargs) -> Optional[str]:
    """Validate user creation input"""
    email = kwargs.get('email')
    if not email or '@' not in email:
        return "Valid email is required"
    return None


def validate_user_grant_permission_input(**kwargs) -> Optional[str]:
    """Validate user permission grant input"""
    user_email = kwargs.get('user_email')
    permission = kwargs.get('permission')
    
    if not user_email or not permission:
        return "user_email and permission are required"
    
    return None


def validate_system_configurator_input(**kwargs) -> Optional[str]:
    """Validate system configurator input parameters"""
    action = kwargs.get('action', 'default')
    
    if action == 'update_setting':
        return validate_system_update_setting_input(**kwargs)
    
    return None


def validate_system_update_setting_input(**kwargs) -> Optional[str]:
    """Validate system setting update input"""
    setting_name = kwargs.get('setting_name')
    if not setting_name:
        return "setting_name is required"
    return None


def validate_log_analyzer_input(**kwargs) -> Optional[str]:
    """Validate log analyzer input parameters"""
    # No specific validation needed for current log analyzer actions
    return None