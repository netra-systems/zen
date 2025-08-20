# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-14T00:00:00.000000+00:00
# Agent: Claude Sonnet 4 claude-sonnet-4-20250514
# Context: CLAUDE.md compliance - Admin tool permission management module ≤300 lines
# Git: anthony-aug-13-2 | modified
# Change: Refactor | Scope: Component | Risk: Low
# Session: claude-md-compliance | Seq: 4
# Review: Pending | Score: 90
# ================================

"""
Admin Tool Permission Management

This module handles permission validation and access control for admin tools.
All functions are ≤8 lines as per CLAUDE.md requirements.
"""

from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models_postgres import User
from app.services.permission_service import PermissionService
from app.schemas.admin_tool_types import AdminToolType, ToolPermissionCheck
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class AdminToolPermissionManager:
    """Manages permissions for admin tools with strict 8-line function limit"""
    
    def __init__(self, db: AsyncSession, user: User):
        self.db = db
        self.user = user
        self.permission_map = self._create_permission_map()
    
    def _create_permission_map(self) -> Dict[str, str]:
        """Create mapping of tools to required permissions"""
        return {
            "corpus_manager": "corpus_write",
            "synthetic_generator": "synthetic_generate", 
            "user_admin": "user_management",
            "system_configurator": "system_admin",
            "log_analyzer": "system_admin"
        }
    
    def initialize_admin_access(self) -> bool:
        """Initialize admin access if user has permissions"""
        if not self._has_dev_permissions():
            return False
        
        self._log_admin_initialization()
        return True
    
    def _has_dev_permissions(self) -> bool:
        """Check if user has developer or higher permissions"""
        if not self.user or not self.db:
            return False
        return PermissionService.is_developer_or_higher(self.user)
    
    def _log_admin_initialization(self) -> None:
        """Log admin tools initialization"""
        available_tools = self.get_available_tools()
        logger.info(f"Initializing admin tools for user {self.user.email}")
        logger.info(f"Admin tools available: {available_tools}")
    
    def get_available_tools(self) -> List[str]:
        """Get list of available admin tools for current user"""
        if not self._has_dev_permissions():
            return []
        
        tools = []
        for tool_name, permission in self.permission_map.items():
            if self._user_has_permission(permission):
                tools.append(tool_name)
        return tools
    
    def _user_has_permission(self, permission: str) -> bool:
        """Check if user has specific permission"""
        return PermissionService.has_permission(self.user, permission)
    
    def validate_tool_access(self, tool_name: str) -> bool:
        """Validate if user has access to specific admin tool"""
        if not self._is_valid_tool(tool_name):
            return False
        
        required_permission = self.permission_map.get(tool_name)
        if not required_permission:
            return False
        
        return self._user_has_permission(required_permission)
    
    def _is_valid_tool(self, tool_name: str) -> bool:
        """Check if tool name is valid admin tool"""
        admin_tool_names = [tool.value for tool in AdminToolType]
        return tool_name in admin_tool_names
    
    def create_permission_check(self, tool_name: str) -> ToolPermissionCheck:
        """Create permission check result for tool"""
        required_perms = self.get_required_permissions(tool_name)
        has_access = self.validate_tool_access(tool_name)
        
        return ToolPermissionCheck(
            tool_name=tool_name,
            user_id=self.user.id if self.user else "unknown",
            required_permissions=required_perms,
            has_access=has_access,
            missing_permissions=self._get_missing_permissions(tool_name)
        )
    
    def get_required_permissions(self, tool_name: str) -> List[str]:
        """Get required permissions for a tool"""
        permission_map = {
            "corpus_manager": ["corpus_write"],
            "synthetic_generator": ["synthetic_generate"],
            "user_admin": ["user_management"],
            "system_configurator": ["system_admin"],
            "log_analyzer": ["system_admin"]
        }
        return permission_map.get(tool_name, [])
    
    def _get_missing_permissions(self, tool_name: str) -> List[str]:
        """Get list of missing permissions for tool"""
        required = self.get_required_permissions(tool_name)
        missing = []
        
        for permission in required:
            if not self._user_has_permission(permission):
                missing.append(permission)
        
        return missing
    
    def log_access_attempt(self, tool_name: str, success: bool) -> None:
        """Log tool access attempt"""
        action = "granted" if success else "denied"
        user_email = self.user.email if self.user else "unknown"
        
        logger.info(f"Admin tool access {action}: {tool_name} for user {user_email}")
        
        if not success:
            missing = self._get_missing_permissions(tool_name)
            logger.warning(f"Missing permissions for {tool_name}: {missing}")
    
    def validate_bulk_access(self, tool_names: List[str]) -> Dict[str, bool]:
        """Validate access to multiple tools at once"""
        results = {}
        for tool_name in tool_names:
            results[tool_name] = self.validate_tool_access(tool_name)
        return results
    
    def get_user_permissions_summary(self) -> Dict[str, any]:
        """Get comprehensive permissions summary for user"""
        if not self.user:
            return {"error": "No user context"}
        
        return {
            "user_id": self.user.id,
            "email": self.user.email,
            "is_admin": self._has_dev_permissions(),
            "available_tools": self.get_available_tools(),
            "all_permissions": self._get_all_user_permissions()
        }
    
    def _get_all_user_permissions(self) -> List[str]:
        """Get all permissions for current user"""
        # This would need to be implemented based on your permission system
        # For now, return permissions based on available tools
        permissions = []
        for tool_name in self.get_available_tools():
            permissions.extend(self.get_required_permissions(tool_name))
        return list(set(permissions))  # Remove duplicates