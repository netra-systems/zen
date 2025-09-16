"""Execution Engine Factory - SSOT Compatibility Module

CRITICAL GOLDEN PATH COMPATIBILITY: This module provides compatibility imports
for Golden Path integration tests that expect execution engine factory in the
managers directory.

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise) - Golden Path Infrastructure 
- Business Goal: Enable Golden Path integration testing (protects $500K+ ARR)
- Value Impact: Maintains import compatibility during SSOT refactoring
- Revenue Impact: Ensures execution engine testing works reliably

COMPLIANCE NOTES:
- This is a COMPATIBILITY MODULE only - new code should import from supervisor package
- Maintains backward compatibility for existing Golden Path tests
- Follows SSOT principles by re-exporting from the canonical location
- Provides proper execution engine factory functionality

IMPORT GUIDANCE:
- DEPRECATED: from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
- RECOMMENDED: from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
"""

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

# SSOT CONSOLIDATION: Re-export UserExecutionEngineFactory as the canonical implementation
# Phase 2B: Direct SSOT redirect with proper error handling
try:
    from netra_backend.app.agents.supervisor.execution_engine_factory import (
        ExecutionEngineFactory as UserExecutionEngineFactory,
        get_execution_engine_factory,
        configure_execution_engine_factory,
        user_execution_engine
    )

    logger.debug("SSOT CONSOLIDATION: UserExecutionEngineFactory imported from supervisor package")

    # Provide backward compatible aliases for existing consumers
    ExecutionEngineFactory = UserExecutionEngineFactory
    RequestScopedExecutionEngineFactory = UserExecutionEngineFactory  # Legacy alias
    create_execution_engine_factory = configure_execution_engine_factory  # Function alias

    __all__ = [
        'ExecutionEngineFactory',
        'UserExecutionEngineFactory',
        'RequestScopedExecutionEngineFactory',
        'get_execution_engine_factory',
        'configure_execution_engine_factory',
        'create_execution_engine_factory',
        'user_execution_engine'
    ]

except ImportError as e:
    logger.error(f"CRITICAL: Could not import UserExecutionEngineFactory from supervisor package: {e}")

    # SSOT ENFORCING: Raise ImportError instead of creating alternative class
    def ExecutionEngineFactory(*args, **kwargs):
        """Error fallback - SSOT factory not available."""
        raise ImportError(
            "SSOT UserExecutionEngineFactory not available. "
            "Check netra_backend.app.agents.supervisor.execution_engine_factory import."
        )

    def RequestScopedExecutionEngineFactory(*args, **kwargs):
        """Error fallback for legacy request-scoped factory."""
        raise ImportError(
            "SSOT UserExecutionEngineFactory not available. "
            "Check netra_backend.app.agents.supervisor.execution_engine_factory import."
        )

    UserExecutionEngineFactory = ExecutionEngineFactory

    def get_execution_engine_factory(*args, **kwargs):
        """Error fallback for factory getter."""
        raise ImportError("SSOT UserExecutionEngineFactory not available")

    def configure_execution_engine_factory(*args, **kwargs):
        """Error fallback for factory configuration."""
        raise ImportError("SSOT UserExecutionEngineFactory not available")

    def create_execution_engine_factory(*args, **kwargs):
        """Error fallback for legacy factory creation."""
        raise ImportError("SSOT UserExecutionEngineFactory not available")

    def user_execution_engine(*args, **kwargs):
        """Error fallback for user execution context manager."""
        raise ImportError("SSOT UserExecutionEngineFactory not available")

    __all__ = [
        'ExecutionEngineFactory',
        'UserExecutionEngineFactory',
        'RequestScopedExecutionEngineFactory',
        'get_execution_engine_factory',
        'configure_execution_engine_factory',
        'create_execution_engine_factory',
        'user_execution_engine'
    ]


# NOTE: All necessary functions are already exported in the __all__ list above
# No need for additional compatibility functions - the SSOT redirect handles everything