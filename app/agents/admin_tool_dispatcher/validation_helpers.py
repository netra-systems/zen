# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-18T00:00:00.000000+00:00
# Agent: Claude Sonnet 4 claude-sonnet-4-20250514
# Context: Split validation helpers to maintain 300-line limit
# Git: 8-18-25-AM | Agent architecture modernization
# Change: Create | Scope: Module | Risk: Low
# Session: admin-tool-modernization | Seq: 6b
# Review: Pending | Score: 100
# ================================
"""
Validation Helper Functions Module

Input validation functions extracted to maintain 300-line limit per module.
Provides specific validation logic for each admin tool type.

Business Value: Modular validation ensures scalable admin tool validation.
"""
from typing import Optional


class ValidationHelpers:
    """Helper class for specific input validation logic."""
    
    def validate_corpus_input(self, **kwargs) -> Optional[str]:
        """Validate corpus manager input parameters."""
        action = kwargs.get('action', 'default')
        if action == 'create':
            return self._validate_corpus_create(**kwargs)
        if action == 'validate':
            return self._validate_corpus_validate(**kwargs)
        return None
    
    def _validate_corpus_create(self, **kwargs) -> Optional[str]:
        """Validate corpus creation parameters."""
        name = kwargs.get('name')
        return "Name too long" if name and len(name) > 255 else None
    
    def _validate_corpus_validate(self, **kwargs) -> Optional[str]:
        """Validate corpus validation parameters."""
        corpus_id = kwargs.get('corpus_id')
        return "corpus_id required" if not corpus_id else None
    
    def validate_synthetic_input(self, **kwargs) -> Optional[str]:
        """Validate synthetic generator input parameters."""
        count = kwargs.get('count', 10)
        if count and (count < 1 or count > 1000):
            return "Count must be 1-1000"
        return None
    
    def validate_user_admin_input(self, **kwargs) -> Optional[str]:
        """Validate user admin input parameters."""
        action = kwargs.get('action', 'default')
        if action == 'create_user':
            return self._validate_user_create(**kwargs)
        if action == 'grant_permission':
            return self._validate_permission_grant(**kwargs)
        return None
    
    def _validate_user_create(self, **kwargs) -> Optional[str]:
        """Validate user creation parameters."""
        email = kwargs.get('email')
        return "Valid email required" if not email or '@' not in email else None
    
    def _validate_permission_grant(self, **kwargs) -> Optional[str]:
        """Validate permission grant parameters."""
        user_email = kwargs.get('user_email')
        permission = kwargs.get('permission')
        return "user_email and permission required" if not user_email or not permission else None
    
    def validate_system_input(self, **kwargs) -> Optional[str]:
        """Validate system configurator input parameters."""
        setting_name = kwargs.get('setting_name')
        return "setting_name required" if not setting_name else None
    
    def validate_log_analyzer_input(self, **kwargs) -> Optional[str]:
        """Validate log analyzer input parameters."""
        return None  # No validation needed currently


class PermissionHelpers:
    """Helper class for permission checking logic."""
    
    def get_tool_permission_mapping(self) -> dict[str, str]:
        """Get mapping of tools to required permissions."""
        return {
            "corpus_manager": "corpus_write",
            "synthetic_generator": "synthetic_generate",
            "user_admin": "user_management",
            "system_configurator": "system_admin",
            "log_analyzer": "system_admin"
        }
    
    def build_validator_mapping(self, helpers: ValidationHelpers) -> dict[str, callable]:
        """Build mapping of tools to validator functions."""
        return {
            "corpus_manager": helpers.validate_corpus_input,
            "synthetic_generator": helpers.validate_synthetic_input,
            "user_admin": helpers.validate_user_admin_input,
            "system_configurator": helpers.validate_system_input,
            "log_analyzer": helpers.validate_log_analyzer_input
        }