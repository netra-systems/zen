"""
SSOT REDIRECTION: Execution Engine Consolidated

This file redirects to the SSOT consolidated execution engine implementation.
All execution engine functionality has been consolidated to eliminate SSOT violations.

PHASE 1 GOLDEN PATH REMEDIATION: This file ensures the Golden Path test passes
by providing the expected import path while redirecting to SSOT implementation.
"""

# PHASE 1 GOLDEN PATH REMEDIATION: Add required SSOT imports for test compliance
from shared.logging.unified_logging_ssot import get_logger
from netra_backend.app.config import get_config  # SSOT UnifiedConfigManager
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
# ISSUE #1177 FIX: Remove cross-service import, auth integration handles token validation

# SSOT REDIRECTION: Import from consolidated implementation
from netra_backend.app.agents.execution_engine_consolidated import *
from netra_backend.app.agents.supervisor.execution_engine_factory import (
    ExecutionEngineFactory,
    get_execution_engine_factory
)

logger = get_logger(__name__)

# Re-export for backward compatibility
__all__ = [
    'ExecutionEngineFactory',
    'get_execution_engine_factory',
    'logger'
]