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
- DEPRECATED: from netra_backend.app.core.managers.execution_engine_factory import ExecutionEngineFactory
- RECOMMENDED: from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
"""

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

# Re-export all execution engine factory components from the canonical supervisor location
try:
    from netra_backend.app.agents.supervisor.execution_engine_factory import (
        ExecutionEngineFactory,
        RequestScopedExecutionEngineFactory,
        # Export any other classes/functions that may be needed
    )
    
    logger.debug("COMPATIBILITY: Execution engine factory components imported from supervisor package")
    
    # Also try to export the factory creation function if it exists
    try:
        from netra_backend.app.agents.supervisor.execution_engine_factory import create_execution_engine_factory
        __all__ = ['ExecutionEngineFactory', 'RequestScopedExecutionEngineFactory', 'create_execution_engine_factory']
    except ImportError:
        __all__ = ['ExecutionEngineFactory', 'RequestScopedExecutionEngineFactory']
        
except ImportError as e:
    logger.warning(f"Could not import execution engine factory from supervisor package: {e}")
    
    # Provide minimal fallback implementations for test compatibility
    class ExecutionEngineFactory:
        """Fallback execution engine factory for compatibility."""
        
        def __init__(self, *args, **kwargs):
            logger.warning("Using fallback ExecutionEngineFactory - please update imports")
            
        def create_execution_engine(self, *args, **kwargs):
            """Create execution engine - fallback implementation."""
            raise NotImplementedError("ExecutionEngineFactory fallback - please use supervisor package")
    
    class RequestScopedExecutionEngineFactory(ExecutionEngineFactory):
        """Fallback request-scoped execution engine factory for compatibility."""
        pass
    
    def create_execution_engine_factory(*args, **kwargs):
        """Create execution engine factory - fallback implementation."""
        logger.warning("Using fallback create_execution_engine_factory - please update imports")
        return ExecutionEngineFactory(*args, **kwargs)
    
    __all__ = ['ExecutionEngineFactory', 'RequestScopedExecutionEngineFactory', 'create_execution_engine_factory']


# Compatibility function for backward compatibility
def get_execution_engine_factory(*args, **kwargs):
    """
    Get execution engine factory - Compatibility wrapper.
    
    COMPATIBILITY: This function provides backward compatibility for tests
    that expect factory creation in the managers module.
    
    Returns:
        ExecutionEngineFactory instance
    """
    logger.debug("COMPATIBILITY: Creating execution engine factory via managers module wrapper")
    
    if 'create_execution_engine_factory' in globals():
        return create_execution_engine_factory(*args, **kwargs)
    else:
        return ExecutionEngineFactory(*args, **kwargs)


# Add get_execution_engine_factory to exports
__all__.append('get_execution_engine_factory')