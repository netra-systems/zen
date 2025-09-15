"""
DEPRECATED: RequestScopedExecutionEngine replaced by UserExecutionEngine SSOT

This module now redirects to UserExecutionEngine for SSOT consolidation.
All functionality has been merged into the canonical implementation.

MIGRATION REQUIRED:
- Use UserExecutionEngine from netra_backend.app.agents.supervisor.user_execution_engine
- This file provides backward compatibility only

SECURITY FIX: Multiple ExecutionEngine implementations caused WebSocket user 
isolation vulnerabilities. UserExecutionEngine is now the SINGLE SOURCE OF TRUTH.
"""

# SSOT Redirect: Import the canonical implementation  
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine

# Create compatibility alias
RequestScopedExecutionEngine = UserExecutionEngine

# Also export factory functions for compatibility
from netra_backend.app.agents.supervisor.execution_engine_factory import (
    create_request_scoped_engine
)

__all__ = ["RequestScopedExecutionEngine", "create_request_scoped_engine"]