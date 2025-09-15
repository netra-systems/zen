"""
FACTORY CLEANUP REMEDIATION: This factory was removed as unnecessary over-engineering.

Original file: netra_backend/app/agents/execution_engine_unified_factory.py
Reason: Over-engineered wrapper factory that provided no business value
Backup: netra_backend/app/agents/execution_engine_unified_factory.py.backup_pre_factory_removal

MIGRATION PATH:
- If this was a simple wrapper, use the canonical implementation directly
- If this provided compatibility, update imports to use the canonical source
- Check backup file for original implementation if needed

Business Value Impact: POSITIVE - Reduces complexity while maintaining functionality
SSOT Compliance: IMPROVED - Eliminates duplicate abstraction layers
"""

# This file has been deprecated and removed as part of factory pattern cleanup.
# See backup file for original implementation if needed.

import warnings

warnings.warn(
    f"Factory netra_backend/app/agents/execution_engine_unified_factory.py has been deprecated and removed as unnecessary over-engineering. "
    f"Use the canonical implementation instead. See backup: netra_backend/app/agents/execution_engine_unified_factory.py.backup_pre_factory_removal",
    DeprecationWarning,
    stacklevel=2
)

class DeprecatedFactoryPlaceholder:
    """Placeholder to prevent import errors during migration period."""

    def __init__(self, *args, **kwargs):
        raise DeprecationWarning(
            f"This factory has been removed as unnecessary over-engineering. "
            f"See netra_backend/app/agents/execution_engine_unified_factory.py.backup_pre_factory_removal for original implementation and migration guide."
        )

# CRITICAL FIX: Add ExecutionEngineFactory compatibility stub for Issue #1228
# This prevents ImportError in test_cross_user_contamination_prevention.py

class ExecutionEngineFactory:
    """DEPRECATED: Compatibility stub for ExecutionEngineFactory.

    This factory was removed as over-engineering. Use UserExecutionEngine directly
    or the canonical factory patterns from execution_engine_factory module.
    """

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "ExecutionEngineFactory is deprecated and will be removed. "
            "Use UserExecutionEngine directly or canonical factory patterns.",
            DeprecationWarning,
            stacklevel=2
        )
        # Provide basic compatibility for tests
        self._config = kwargs.get('config', {})

    @staticmethod
    def create_engine(*args, **kwargs):
        """Create execution engine with compatibility."""
        # SSOT REMEDIATION Issue #1186: Use canonical imports
        from netra_backend.app.agents.canonical_imports import UserExecutionEngine
        return UserExecutionEngine(**kwargs)

    @staticmethod
    def create_user_scoped_engine(user_context, *args, **kwargs):
        """Create user-scoped execution engine."""
        # SSOT REMEDIATION Issue #1186: Use canonical imports
        from netra_backend.app.agents.canonical_imports import UserExecutionEngine
        return UserExecutionEngine(user_context=user_context, **kwargs)

# Export for compatibility
__all__ = ['ExecutionEngineFactory', 'DeprecatedFactoryPlaceholder']
