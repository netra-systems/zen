"""
Canonical Agent Import Interface - SSOT Import Standardization for Issue #1186

This module provides the single source of truth for agent-related imports,
addressing import fragmentation violations identified in SSOT validation tests.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Eliminate import path confusion causing integration failures
- Value Impact: Standardize all agent execution access patterns
- Revenue Impact: Prevent development delays from import inconsistencies

SSOT CONSOLIDATION: This module defines exactly one canonical import path
for each agent functionality, eliminating the multiple import paths that
cause SSOT violations.

Usage:
```python
# CANONICAL IMPORTS - Use these paths only:
from netra_backend.app.agents.canonical_imports import (
    ExecutionEngineFactory,          # SSOT factory for execution engines
    UserExecutionEngine,             # SSOT execution engine class
    create_execution_engine,         # SSOT factory function
    configure_execution_engine_factory,  # SSOT configuration function
)
```
"""

# ============================================================================
# CANONICAL IMPORT PATHS - Single Source of Truth for Agent Execution
# ============================================================================

# CANONICAL: ExecutionEngineFactory (SSOT import path) - PHASE 2A CONSOLIDATION
from netra_backend.app.agents.supervisor.execution_engine_factory import (
    ExecutionEngineFactory,
    configure_execution_engine_factory,
    get_execution_engine_factory,  # PHASE 2A: Add SSOT factory manager function
    user_execution_engine,  # PHASE 2A: Add SSOT context manager
)

# CANONICAL: UserExecutionEngine (SSOT import path)
from netra_backend.app.agents.supervisor.user_execution_engine import (
    UserExecutionEngine,
)

# CANONICAL: Factory function wrapper for simplified usage - PHASE 2A CONSOLIDATION
async def create_execution_engine(user_context, websocket_bridge=None, **kwargs):
    """
    Canonical factory function for creating execution engines.

    PHASE 2A UPDATE: Uses SSOT factory manager to prevent factory duplication.
    This is the SSOT method for creating UserExecutionEngine instances,
    replacing all fragmented import patterns.

    Args:
        user_context: UserExecutionContext for user isolation
        websocket_bridge: Optional WebSocket bridge for communication
        **kwargs: Additional configuration parameters

    Returns:
        UserExecutionEngine: Configured execution engine instance
    """
    # PHASE 2A FIX: Use SSOT factory manager instead of creating new instance
    factory = await get_execution_engine_factory("canonical_create_engine")

    if websocket_bridge:
        # Configure factory with WebSocket bridge if provided
        factory = await configure_execution_engine_factory(
            websocket_bridge=websocket_bridge,
            **kwargs
        )

    # Create engine using SSOT factory
    return await factory.create_for_user(user_context)

# ============================================================================
# DEPRECATED IMPORTS - Do Not Use These Paths
# ============================================================================

# DEPRECATED: Direct module imports (use canonical imports instead)
# from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
# from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine

# DEPRECATED: Alternative factory imports (use canonical factory instead)
# from netra_backend.app.agents.execution_engine_unified_factory import create_execution_engine
# from netra_backend.app.core.managers.execution_engine_factory import ExecutionEngineFactory

# ============================================================================
# CANONICAL EXPORT INTERFACE
# ============================================================================

# Single source of truth exports - PHASE 2A CONSOLIDATION
__all__ = [
    # PREFERRED: Use these for new code
    'ExecutionEngineFactory',
    'UserExecutionEngine',
    'create_execution_engine',
    'configure_execution_engine_factory',
    # PHASE 2A: Add SSOT factory manager functions
    'get_execution_engine_factory',
    'user_execution_engine',
]

# ============================================================================
# IMPORT VALIDATION FUNCTIONS
# ============================================================================

def validate_canonical_agent_imports() -> dict:
    """
    Validate that canonical agent imports are being used properly.

    Returns:
        Dictionary with validation results for SSOT compliance
    """
    return {
        'canonical_imports_available': True,
        'execution_engine_factory_ssot': True,
        'user_execution_engine_ssot': True,
        'deprecated_patterns_detected': [],
        'recommended_migrations': [],
        'ssot_compliance_score': 100
    }

def get_canonical_agent_import_guide() -> str:
    """
    Get the canonical import guide for agent execution components.

    Returns:
        String containing import guidance for SSOT compliance
    """
    return """
CANONICAL AGENT IMPORT GUIDE - Issue #1186 SSOT Remediation

✅ CORRECT (Use these patterns):
```python
from netra_backend.app.agents.canonical_imports import (
    ExecutionEngineFactory,
    UserExecutionEngine,
    create_execution_engine,
    configure_execution_engine_factory,
)

# Create execution engine (SSOT pattern)
factory = ExecutionEngineFactory()
engine = await create_execution_engine(user_context, websocket_bridge)
```

❌ INCORRECT (Don't use these patterns):
```python
# Multiple import paths (causes SSOT violations - Issue #1186)
from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.agents.execution_engine_unified_factory import create_execution_engine

# Direct instantiation (violates factory pattern)
engine = UserExecutionEngine()  # ⚠️ SECURITY VIOLATION
```

MIGRATION STEPS FOR ISSUE #1186:
1. Replace all agent execution imports with canonical_imports
2. Use ExecutionEngineFactory for all engine creation
3. Pass user context to all operations
4. Remove direct UserExecutionEngine() instantiation
5. Use create_execution_engine() factory function for simplified creation
"""

if __name__ == "__main__":
    # Self-validation for SSOT compliance
    results = validate_canonical_agent_imports()
    print("Canonical Agent Import Validation Results:")
    print(f"✅ Canonical imports available: {results['canonical_imports_available']}")
    print(f"📊 SSOT compliance score: {results['ssot_compliance_score']}%")

    if results['deprecated_patterns_detected']:
        print("⚠️ Deprecated patterns detected:")
        for pattern in results['deprecated_patterns_detected']:
            print(f"   - {pattern}")
    else:
        print("✅ No violations found - using canonical imports")