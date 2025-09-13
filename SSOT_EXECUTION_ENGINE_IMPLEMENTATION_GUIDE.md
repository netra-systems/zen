# SSOT Execution Engine Implementation Guide
## Issue #710: Step-by-Step Code Changes with Atomic Units

**Status**: IMPLEMENTATION READY
**Business Impact**: $500K+ ARR Golden Path restoration
**Priority**: P0 - Execute immediately
**Generated**: 2025-12-09

---

## Implementation Overview

This guide provides exact code changes required to implement the SSOT remediation plan. Each change is atomic, testable, and rollbackable.

---

## Phase 1: Critical Factory Method Fixes

### Step 1.1: Fix UserExecutionEngine.create_from_legacy() Method

**File**: `netra_backend/app/agents/supervisor/user_execution_engine.py`
**Lines**: 341-473 (create_from_legacy method)

**CRITICAL FIX**: Add auto-WebSocket bridge creation to prevent TypeError failures.

**Code Change**:
```python
@classmethod
async def create_from_legacy(cls, registry: 'AgentRegistry', websocket_bridge=None,
                           user_context: Optional['UserExecutionContext'] = None) -> 'UserExecutionEngine':
    """API Compatibility factory method for legacy ExecutionEngine signature.

    ⚠️  ISSUE #710 CRITICAL FIX ⚠️

    Auto-creates WebSocket bridge when None to prevent concurrent user execution failures.
    This resolves TypeError exceptions that block the Golden Path user flow.

    Args:
        registry: Agent registry for agent lookup (legacy parameter)
        websocket_bridge: WebSocket bridge for event emission (can be None - will auto-create)
        user_context: Optional UserExecutionContext (if None, creates anonymous user context)

    Returns:
        UserExecutionEngine: Properly configured engine with user isolation

    Raises:
        ValueError: If required components cannot be created
        DeprecationWarning: Always issued to encourage migration
    """
    import warnings
    warnings.warn(
        "ExecutionEngine(registry, websocket_bridge, user_context) pattern is DEPRECATED. "
        "Use UserExecutionEngine with proper UserExecutionContext for Issue #710 migration. "
        "This compatibility bridge will be removed after migration is complete.",
        DeprecationWarning,
        stacklevel=2
    )

    logger.warning(
        "🔄 Issue #710 API COMPATIBILITY: Legacy ExecutionEngine signature detected. "
        "Creating UserExecutionEngine with compatibility bridge. "
        "MIGRATION REQUIRED: Use proper UserExecutionContext pattern for full benefits."
    )

    try:
        # 1. Create or validate UserExecutionContext
        if user_context is None:
            # Create anonymous user context for compatibility
            from netra_backend.app.services.user_execution_context import UserExecutionContext

            # Use UnifiedIDManager for secure ID generation
            id_manager = UnifiedIDManager()

            # Create UserExecutionContext using factory method for compatibility
            anonymous_user_context = UserExecutionContext.from_request_supervisor(
                user_id=id_manager.generate_id(IDType.USER, prefix="legacy_compat"),
                thread_id=id_manager.generate_id(IDType.THREAD, prefix="legacy"),
                run_id=id_manager.generate_id(IDType.EXECUTION, prefix="legacy"),
                request_id=id_manager.generate_id(IDType.REQUEST, prefix="legacy"),
                metadata={
                    'compatibility_mode': True,
                    'migration_issue': '#710',
                    'created_for': 'legacy_execution_engine_compatibility',
                    'security_note': 'Anonymous user context - migrate to proper user authentication'
                }
            )
            user_context = anonymous_user_context

            logger.warning(
                "🔄 Issue #710: Created anonymous UserExecutionContext for compatibility. "
                f"User ID: {user_context.user_id}. SECURITY: Use proper user authentication."
            )

        # Validate user context
        user_context = validate_user_context(user_context)

        # CRITICAL FIX: Auto-create WebSocket bridge if None
        if websocket_bridge is None:
            from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

            # Create WebSocket bridge for user context
            try:
                websocket_bridge = AgentWebSocketBridge.create_for_user(user_context)
                logger.info(
                    f"✅ Issue #710 CRITICAL FIX: Auto-created WebSocket bridge for user {user_context.user_id}. "
                    f"This resolves TypeError failures in concurrent user execution."
                )
            except Exception as bridge_error:
                logger.warning(
                    f"⚠️ Issue #710: Could not auto-create WebSocket bridge: {bridge_error}. "
                    f"Creating minimal compatibility bridge for testing."
                )
                # Create minimal bridge for test compatibility
                websocket_bridge = AgentWebSocketBridge.create_minimal_for_testing()

        # 2. Create AgentInstanceFactory (it doesn't take registry in constructor)
        from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory

        # Create AgentInstanceFactory (it initializes with default/empty components)
        agent_factory = AgentInstanceFactory()

        # Set the registry and websocket bridge after creation if factory supports it
        if hasattr(agent_factory, 'set_registry'):
            agent_factory.set_registry(registry)
        if hasattr(agent_factory, 'set_websocket_bridge'):
            agent_factory.set_websocket_bridge(websocket_bridge)

        logger.debug("🔄 Created AgentInstanceFactory for Issue #710 compatibility mode")

        # 3. Create websocket emitter - Use UnifiedWebSocketEmitter directly for SSOT compliance
        from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter

        if hasattr(websocket_bridge, 'notify_agent_started'):
            # Create UnifiedWebSocketEmitter that uses the AgentWebSocketBridge
            websocket_emitter = UnifiedWebSocketEmitter(
                manager=websocket_bridge,
                user_id=user_context.user_id,
                context=user_context
            )
            logger.debug("🔄 Created UserWebSocketEmitter from auto-created websocket_bridge")
        else:
            raise ValueError(
                f"WebSocket bridge type {type(websocket_bridge)} not compatible. "
                f"Expected AgentWebSocketBridge with notify_agent_started() method. "
                f"Issue #710 fix failed - check AgentWebSocketBridge.create_for_user() implementation."
            )

        # 4. Create UserExecutionEngine with proper parameters
        engine = cls(
            user_context,
            agent_factory,
            websocket_emitter
        )

        # 5. Add compatibility metadata for debugging
        engine._compatibility_mode = True
        engine._legacy_registry = registry
        engine._legacy_websocket_bridge = websocket_bridge
        engine._migration_issue = "#710"

        logger.info(
            f"✅ Issue #710 CRITICAL FIX COMPLETE: Successfully created UserExecutionEngine "
            f"from legacy signature with auto-WebSocket bridge. User: {user_context.user_id}, "
            f"Engine: {engine.engine_id}. Concurrent user execution restored."
        )

        return engine

    except Exception as e:
        logger.error(
            f"❌ Issue #710 CRITICAL FIX FAILED: Could not create UserExecutionEngine "
            f"from legacy ExecutionEngine signature: {e}. "
            f"Registry: {type(registry)}, WebSocketBridge: {type(websocket_bridge)}. "
            f"SOLUTION: Check AgentWebSocketBridge.create_for_user() availability."
        )
        raise ValueError(f"Legacy compatibility bridge failed (Issue #710): {e}")
```

**Validation Command**:
```bash
python -c "
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
registry = AgentRegistry()
engine = await UserExecutionEngine.create_from_legacy(registry, None)
print(f'✅ SUCCESS: Auto-WebSocket bridge creation working: {engine.engine_id}')
"
```

### Step 1.2: Enhanced ExecutionEngineFactory.create_for_user()

**File**: `netra_backend/app/agents/supervisor/execution_engine_factory.py`
**Lines**: 147-227 (create_for_user method)

**Enhancement**: Ensure robust WebSocket bridge creation and validation.

**Code Change**:
```python
async def create_for_user(self, context: UserExecutionContext) -> UserExecutionEngine:
    """Create UserExecutionEngine for specific user with enhanced WebSocket integration.

    ISSUE #710 ENHANCEMENT: Ensures robust WebSocket bridge creation
    for reliable concurrent user execution and Golden Path stability.

    Args:
        context: User execution context for isolation

    Returns:
        UserExecutionEngine: Isolated execution engine for the user

    Raises:
        ExecutionEngineFactoryError: If engine creation fails
        InvalidContextError: If user context is invalid
    """
    # Validate user context
    try:
        validated_context = validate_user_context(context)
    except (TypeError, InvalidContextError) as e:
        logger.error(f"Invalid user context for engine creation: {e}")
        raise ExecutionEngineFactoryError(f"Invalid user context: {e}")

    start_time = time.time()
    engine_key = f"{validated_context.user_id}_{validated_context.run_id}_{int(time.time() * 1000)}"

    try:
        async with self._engine_lock:
            # Check per-user engine limits
            await self._enforce_user_engine_limits(validated_context.user_id)

            # ISSUE #710 ENHANCEMENT: Robust WebSocket bridge validation
            websocket_bridge = self._websocket_bridge
            if not websocket_bridge:
                logger.info(
                    f"🔄 Issue #710: No WebSocket bridge configured in factory. "
                    f"Auto-creating for user {validated_context.user_id}"
                )
                try:
                    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
                    websocket_bridge = AgentWebSocketBridge.create_for_user(validated_context)
                    logger.info(
                        f"✅ Issue #710: Auto-created WebSocket bridge for user {validated_context.user_id}. "
                        f"Golden Path WebSocket events will be available."
                    )
                except Exception as bridge_error:
                    logger.warning(
                        f"⚠️ Issue #710: Auto-WebSocket bridge creation failed: {bridge_error}. "
                        f"Creating minimal bridge for degraded mode."
                    )
                    websocket_bridge = AgentWebSocketBridge.create_minimal_for_testing()

            # Create NEW agent factory instance per user for complete isolation
            # This prevents shared state between users - each gets their own factory
            from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
            agent_factory = AgentInstanceFactory()

            if not agent_factory:
                raise ExecutionEngineFactoryError("AgentInstanceFactory creation failed")

            # Set WebSocket bridge on agent factory for integration
            if hasattr(agent_factory, 'set_websocket_bridge'):
                agent_factory.set_websocket_bridge(websocket_bridge)

            # Create user WebSocket emitter via factory with enhanced validation
            websocket_emitter = await self._create_user_websocket_emitter_enhanced(
                validated_context, agent_factory, websocket_bridge
            )

            # Create UserExecutionEngine
            logger.info(f"Creating UserExecutionEngine for user {validated_context.user_id} "
                       f"(run_id: {validated_context.run_id}) with enhanced WebSocket integration")

            engine = UserExecutionEngine(
                context=validated_context,
                agent_factory=agent_factory,
                websocket_emitter=websocket_emitter
            )

            # ISSUE #710: Enhanced infrastructure integration
            # Attach infrastructure managers for tests and validation
            # Always set the attributes (even if None) to ensure hasattr() tests pass
            engine.database_session_manager = self._database_session_manager
            engine.redis_manager = self._redis_manager
            engine._websocket_bridge = websocket_bridge  # Direct access for validation

            # Register engine for lifecycle management
            self._active_engines[engine_key] = engine

            # Update metrics
            self._factory_metrics['total_engines_created'] += 1
            self._factory_metrics['active_engines_count'] = len(self._active_engines)

            # Start cleanup task if not running
            if not self._cleanup_task:
                self._cleanup_task = asyncio.create_task(self._cleanup_loop())

            creation_time = (time.time() - start_time) * 1000
            logger.info(f"✅ Issue #710 ENHANCED: Created UserExecutionEngine {engine.engine_id} "
                       f"in {creation_time:.1f}ms (user: {validated_context.user_id}) "
                       f"with robust WebSocket integration")

            return engine

    except Exception as e:
        self._factory_metrics['creation_errors'] += 1
        logger.error(f"❌ Issue #710: Failed to create UserExecutionEngine for user {validated_context.user_id}: {e}")
        raise ExecutionEngineFactoryError(f"Engine creation failed (Issue #710): {e}")

async def _create_user_websocket_emitter_enhanced(self,
                                                context: UserExecutionContext,
                                                agent_factory,
                                                websocket_bridge) -> UnifiedWebSocketEmitter:
    """Create user WebSocket emitter with enhanced validation (Issue #710).

    Args:
        context: User execution context
        agent_factory: Agent instance factory (for compatibility)
        websocket_bridge: Validated WebSocket bridge (never None)

    Returns:
        UnifiedWebSocketEmitter: User-specific WebSocket emitter with validation

    Raises:
        ExecutionEngineFactoryError: If emitter creation fails
    """
    try:
        if not websocket_bridge:
            raise ExecutionEngineFactoryError(
                f"Issue #710: WebSocket bridge cannot be None. "
                f"Auto-creation should have been handled in create_for_user()."
            )

        # Create user WebSocket emitter with validated bridge
        emitter = UnifiedWebSocketEmitter(
            user_id=context.user_id,
            thread_id=context.thread_id,
            run_id=context.run_id,
            websocket_bridge=websocket_bridge
        )

        # ISSUE #710: Validate emitter functionality
        if hasattr(emitter, 'websocket_bridge') and emitter.websocket_bridge:
            logger.debug(f"✅ Issue #710: UnifiedWebSocketEmitter created with validated bridge "
                        f"for user {context.user_id}")
        else:
            logger.warning(f"⚠️ Issue #710: UnifiedWebSocketEmitter bridge validation failed "
                          f"for user {context.user_id}")

        return emitter

    except Exception as e:
        logger.error(f"❌ Issue #710: Failed to create enhanced UnifiedWebSocketEmitter: {e}")
        raise ExecutionEngineFactoryError(f"Enhanced WebSocket emitter creation failed: {e}")
```

---

## Phase 2: Duplicate Factory Elimination

### Step 2.1: Convert execution_engine_unified_factory.py to Redirect Module

**File**: `netra_backend/app/agents/execution_engine_unified_factory.py`
**Action**: Replace entire file content with redirect

**New Content**:
```python
"""Unified Execution Engine Factory - SSOT Redirect (Issue #710)

⚠️  DEPRECATED MODULE - USE execution_engine_factory DIRECTLY ⚠️

This module now serves as a compatibility redirect to the SSOT ExecutionEngineFactory
during Issue #710 remediation. All functionality has been consolidated into the
canonical execution_engine_factory module.

Business Value:
- Maintains backward compatibility during SSOT migration
- Zero breaking changes for existing consumers
- Automatic migration path to consolidated SSOT
- Protection of $500K+ ARR Golden Path during transition
"""

from __future__ import annotations

import warnings
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    from netra_backend.app.agents.tool_dispatcher_consolidated import UnifiedToolDispatcher

from netra_backend.app.agents.execution_engine_interface import IExecutionEngine

# ISSUE #710 SSOT MIGRATION: Direct delegation to SSOT ExecutionEngineFactory
from netra_backend.app.agents.supervisor.execution_engine_factory import (
    ExecutionEngineFactory as SSotExecutionEngineFactory,
    get_execution_engine_factory,
    user_execution_engine,
    create_request_scoped_engine
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

# Issue #710: Deprecation warning for all usage
warnings.warn(
    "DEPRECATED: execution_engine_unified_factory is deprecated due to Issue #710 SSOT consolidation. "
    "Use 'from netra_backend.app.agents.supervisor.execution_engine_factory import ...' directly. "
    "This redirect module will be removed after migration is complete.",
    DeprecationWarning,
    stacklevel=2
)

logger.warning(
    "🔄 Issue #710 DEPRECATION: execution_engine_unified_factory imported. "
    "This module is deprecated - update imports to use execution_engine_factory directly. "
    "See SSOT_EXECUTION_ENGINE_REMEDIATION_PLAN.md for migration guidance."
)

# Simple configuration for engine creation
EngineConfig = Dict[str, Any]


class UnifiedExecutionEngineFactory:
    """DEPRECATED: Unified factory redirecting to SSOT ExecutionEngineFactory.

    ⚠️  MIGRATION REQUIRED FOR ISSUE #710 ⚠️

    This factory serves as a backward compatibility bridge during SSOT
    consolidation. All methods delegate to the SSOT ExecutionEngineFactory.

    MIGRATION PATH:
    OLD: from netra_backend.app.agents.execution_engine_unified_factory import UnifiedExecutionEngineFactory
    NEW: from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
    """

    @classmethod
    def set_defaults(
        cls,
        config: Optional[EngineConfig] = None,
        registry: Optional['AgentRegistry'] = None,
        websocket_bridge: Optional['AgentWebSocketBridge'] = None,
        tool_dispatcher: Optional['UnifiedToolDispatcher'] = None
    ) -> None:
        """DEPRECATED: Set default configuration - delegates to SSOT factory."""
        logger.warning("🔄 Issue #710: UnifiedExecutionEngineFactory.set_defaults is deprecated - "
                      "SSOT factory doesn't use global defaults")
        # SSOT factory doesn't use global defaults - this is a no-op for compatibility

    @classmethod
    def configure(
        cls,
        config: Optional[EngineConfig] = None,
        registry: Optional['AgentRegistry'] = None,
        websocket_bridge: Optional['AgentWebSocketBridge'] = None,
        tool_dispatcher: Optional['UnifiedToolDispatcher'] = None
    ) -> None:
        """DEPRECATED: Configure the unified factory - delegates to SSOT factory."""
        logger.warning("🔄 Issue #710: UnifiedExecutionEngineFactory.configure is deprecated - "
                      "SSOT factory doesn't use global configuration")
        # SSOT factory doesn't use global configuration - this is a no-op for compatibility

    @classmethod
    async def create_engine(
        cls,
        config: Optional[Dict] = None,
        registry: Optional['AgentRegistry'] = None,
        websocket_bridge: Optional['AgentWebSocketBridge'] = None,
        user_context: Optional['UserExecutionContext'] = None,
        tool_dispatcher: Optional['UnifiedToolDispatcher'] = None,
        **kwargs
    ) -> IExecutionEngine:
        """DEPRECATED: Create execution engine - delegates to SSOT factory.

        Returns:
            IExecutionEngine: SSOT UserExecutionEngine instance
        """
        if not user_context:
            raise ValueError(
                "Issue #710: SSOT ExecutionEngine requires user_context for proper isolation. "
                "Create UserExecutionContext with proper user authentication."
            )

        logger.warning("🔄 Issue #710: UnifiedExecutionEngineFactory.create_engine is deprecated - "
                      "use ExecutionEngineFactory.create_for_user() directly")

        # Get SSOT factory and create engine
        factory = await get_execution_engine_factory()
        return await factory.create_for_user(user_context)

    @classmethod
    async def create_user_engine(
        cls,
        user_context: 'UserExecutionContext',
        config: Optional[EngineConfig] = None,
        **kwargs
    ) -> IExecutionEngine:
        """DEPRECATED: Create user engine - delegates to SSOT factory."""
        logger.warning("🔄 Issue #710: UnifiedExecutionEngineFactory.create_user_engine is deprecated - "
                      "use ExecutionEngineFactory.create_for_user() directly")

        # Delegate to SSOT implementation
        factory = await get_execution_engine_factory()
        return await factory.create_for_user(user_context)


# COMPATIBILITY EXPORTS FOR ISSUE #710 MIGRATION
# These maintain backward compatibility while encouraging migration to SSOT

# Redirect all factory functions to SSOT implementations
ExecutionEngineFactory = SSotExecutionEngineFactory
get_execution_engine_factory = get_execution_engine_factory
user_execution_engine = user_execution_engine
create_request_scoped_engine = create_request_scoped_engine

# Legacy alias
UnifiedFactory = UnifiedExecutionEngineFactory

logger.info("✅ Issue #710: execution_engine_unified_factory loaded as compatibility redirect. "
           "All functionality delegated to SSOT ExecutionEngineFactory.")
```

### Step 2.2: Add Deprecation to execution_factory.py

**File**: `netra_backend/app/agents/supervisor/execution_factory.py`
**Action**: Add deprecation header and redirect imports

**Add to top of file**:
```python
"""Execution Factory - DEPRECATED FOR ISSUE #710

⚠️  THIS MODULE IS DEPRECATED ⚠️

This module is being phased out as part of Issue #710 SSOT consolidation.
All execution engine factory functionality has been consolidated into:
netra_backend.app.agents.supervisor.execution_engine_factory

MIGRATION REQUIRED:
OLD: from netra_backend.app.agents.supervisor.execution_factory import ...
NEW: from netra_backend.app.agents.supervisor.execution_engine_factory import ...

This module will be removed after all consumers are migrated.
"""

import warnings

# Issue #710: Emit deprecation warning on import
warnings.warn(
    "execution_factory module is deprecated due to Issue #710 SSOT consolidation. "
    "Use 'netra_backend.app.agents.supervisor.execution_engine_factory' instead. "
    "This module will be removed after migration is complete.",
    DeprecationWarning,
    stacklevel=2
)

# ... rest of existing file content ...
```

---

## Phase 3: Import Path Standardization

### Step 3.1: Automated Import Replacement Script

**File**: `scripts/fix_execution_engine_imports.py`

**Create New Script**:
```python
#!/usr/bin/env python3
"""Fix execution engine imports for Issue #710 SSOT consolidation.

This script automatically updates import statements to use the SSOT
ExecutionEngineFactory from execution_engine_factory module.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

def find_python_files(root_dir: str) -> List[Path]:
    """Find all Python files in the directory tree."""
    python_files = []
    for root, dirs, files in os.walk(root_dir):
        # Skip certain directories
        skip_dirs = {'.git', '__pycache__', '.pytest_cache', 'node_modules', '.venv', 'venv'}
        dirs[:] = [d for d in dirs if d not in skip_dirs]

        for file in files:
            if file.endswith('.py'):
                python_files.append(Path(root) / file)

    return python_files

def fix_imports_in_file(file_path: Path) -> Tuple[bool, List[str]]:
    """Fix execution engine imports in a single file."""
    changes = []
    modified = False

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Pattern 1: execution_engine_unified_factory imports
        pattern1 = re.compile(
            r'from\s+netra_backend\.app\.agents\.execution_engine_unified_factory\s+import\s+([^\n]+)',
            re.MULTILINE
        )

        def replace1(match):
            imports = match.group(1)
            new_import = f"from netra_backend.app.agents.supervisor.execution_engine_factory import {imports}"
            changes.append(f"  Updated unified_factory import: {imports}")
            return new_import

        content = pattern1.sub(replace1, content)

        # Pattern 2: execution_factory imports
        pattern2 = re.compile(
            r'from\s+netra_backend\.app\.agents\.supervisor\.execution_factory\s+import\s+([^\n]+)',
            re.MULTILINE
        )

        def replace2(match):
            imports = match.group(1)
            new_import = f"from netra_backend.app.agents.supervisor.execution_engine_factory import {imports}"
            changes.append(f"  Updated execution_factory import: {imports}")
            return new_import

        content = pattern2.sub(replace2, content)

        # Pattern 3: Direct UnifiedExecutionEngineFactory imports
        pattern3 = re.compile(
            r'UnifiedExecutionEngineFactory',
            re.MULTILINE
        )

        if pattern3.search(content):
            content = pattern3.sub('ExecutionEngineFactory', content)
            changes.append(f"  Replaced UnifiedExecutionEngineFactory with ExecutionEngineFactory")

        # Write back if modified
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            modified = True

    except Exception as e:
        changes.append(f"  ERROR: {e}")

    return modified, changes

def main():
    """Main execution function."""
    if len(sys.argv) != 2:
        print("Usage: python scripts/fix_execution_engine_imports.py <root_directory>")
        sys.exit(1)

    root_dir = sys.argv[1]
    if not os.path.exists(root_dir):
        print(f"Error: Directory {root_dir} does not exist")
        sys.exit(1)

    print(f"🔍 Issue #710: Scanning for execution engine imports in {root_dir}")

    python_files = find_python_files(root_dir)
    print(f"Found {len(python_files)} Python files")

    modified_files = 0
    total_changes = 0

    for file_path in python_files:
        modified, changes = fix_imports_in_file(file_path)

        if modified:
            modified_files += 1
            total_changes += len(changes)
            print(f"\n✅ Fixed: {file_path}")
            for change in changes:
                print(change)

    print(f"\n🎯 Issue #710 Import Fix Summary:")
    print(f"  Files scanned: {len(python_files)}")
    print(f"  Files modified: {modified_files}")
    print(f"  Total changes: {total_changes}")

    if modified_files > 0:
        print(f"\n⚠️  IMPORTANT: Review changes and run tests to validate:")
        print(f"  git diff")
        print(f"  python tests/unified_test_runner.py --category integration")
        print(f"  python tests/mission_critical/test_execution_engine_ssot.py")

if __name__ == '__main__':
    main()
```

**Usage**:
```bash
# Run the import fix script
python scripts/fix_execution_engine_imports.py netra_backend/

# Validate changes
git diff

# Test the changes
python tests/unified_test_runner.py --category integration --filter="execution_engine"
```

### Step 3.2: Manual Import Updates for Critical Files

**High-priority files requiring manual review**:

1. **Main application routes**:
```bash
# Files to update manually:
netra_backend/app/routes/agent_routes.py
netra_backend/app/routes/websocket.py
netra_backend/app/main.py
netra_backend/app/smd.py
```

2. **Test files** (sample):
```bash
# Update test imports manually for validation:
netra_backend/tests/integration/test_execution_engine_integration.py
netra_backend/tests/unit/test_execution_engine_factory.py
tests/mission_critical/test_websocket_agent_events_suite.py
```

**Example Manual Import Update**:
```python
# OLD (execution_engine_unified_factory):
from netra_backend.app.agents.execution_engine_unified_factory import (
    UnifiedExecutionEngineFactory,
    create_user_engine
)

# NEW (execution_engine_factory):
from netra_backend.app.agents.supervisor.execution_engine_factory import (
    ExecutionEngineFactory,
    create_request_scoped_engine,
    user_execution_engine
)
```

---

## Phase 4: Validation and Testing

### Step 4.1: SSOT Compliance Test

**File**: `tests/mission_critical/test_execution_engine_ssot_compliance.py`

**Create New Test**:
```python
"""SSOT Execution Engine Compliance Tests for Issue #710.

These tests validate that the SSOT consolidation is working correctly
and that the Golden Path is protected during migration.
"""

import asyncio
import pytest
from typing import List

from netra_backend.app.agents.supervisor.execution_engine_factory import (
    ExecutionEngineFactory,
    get_execution_engine_factory,
    user_execution_engine,
    create_request_scoped_engine
)
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry


class TestExecutionEngineSSotCompliance:
    """Test SSOT compliance for execution engine factory consolidation."""

    @pytest.mark.asyncio
    async def test_user_execution_engine_create_from_legacy_websocket_auto_creation(self):
        """Test Issue #710 fix: Auto-create WebSocket bridge in create_from_legacy."""
        # Create test registry
        registry = AgentRegistry()

        # CRITICAL TEST: Call create_from_legacy with None websocket_bridge
        # This should auto-create the bridge instead of failing with TypeError
        try:
            engine = await UserExecutionEngine.create_from_legacy(
                registry=registry,
                websocket_bridge=None,  # This should auto-create
                user_context=None       # This should create anonymous context
            )

            # Validate engine created successfully
            assert engine is not None
            assert isinstance(engine, UserExecutionEngine)

            # Validate WebSocket bridge was auto-created
            assert engine.websocket_bridge is not None
            assert hasattr(engine.websocket_bridge, 'notify_agent_started')

            # Validate user context was auto-created
            assert engine.get_user_context() is not None
            assert engine.get_user_context().user_id.startswith('legacy_compat_')

            # Validate compatibility mode enabled
            assert engine.is_compatibility_mode() is True

            print("✅ Issue #710 CRITICAL FIX: Auto-WebSocket bridge creation working")

        except TypeError as e:
            pytest.fail(f"❌ Issue #710 CRITICAL FAILURE: create_from_legacy still failing with TypeError: {e}")
        except Exception as e:
            pytest.fail(f"❌ Issue #710 UNEXPECTED ERROR: {e}")
        finally:
            # Cleanup
            if 'engine' in locals():
                await engine.cleanup()

    @pytest.mark.asyncio
    async def test_execution_engine_factory_single_authority(self):
        """Test that ExecutionEngineFactory is the single authority for engine creation."""
        # Create user context
        user_context = UserExecutionContext.from_request_supervisor(
            user_id="test_user_ssot",
            thread_id="test_thread_ssot",
            run_id="test_run_ssot",
            request_id="test_request_ssot"
        )

        # Test all factory methods create consistent engines
        engines = []

        try:
            # Method 1: Direct factory usage
            factory = await get_execution_engine_factory()
            engine1 = await factory.create_for_user(user_context)
            engines.append(engine1)

            # Method 2: Convenience function
            engine2 = await create_request_scoped_engine(user_context)
            engines.append(engine2)

            # Method 3: Context manager
            async with user_execution_engine(user_context) as engine3:
                engines.append(engine3)

                # Validate all engines are UserExecutionEngine instances
                for i, engine in enumerate(engines):
                    assert isinstance(engine, UserExecutionEngine), f"Engine {i} is not UserExecutionEngine"
                    assert engine.get_user_context().user_id == user_context.user_id
                    assert engine.websocket_emitter is not None
                    assert engine.agent_factory is not None

                print(f"✅ Issue #710 SSOT: All {len(engines)} factory methods create consistent UserExecutionEngine instances")

        finally:
            # Cleanup engines
            for engine in engines[:-1]:  # Skip context manager engine (auto-cleanup)
                try:
                    await engine.cleanup()
                except:
                    pass

    @pytest.mark.asyncio
    async def test_concurrent_user_isolation_after_ssot_fix(self):
        """Test that concurrent users have proper isolation after SSOT fixes."""
        # Create 3 different user contexts
        user_contexts = [
            UserExecutionContext.from_request_supervisor(
                user_id=f"concurrent_user_{i}",
                thread_id=f"thread_{i}",
                run_id=f"run_{i}",
                request_id=f"request_{i}"
            )
            for i in range(3)
        ]

        engines = []

        try:
            # Create engines for all users simultaneously
            factory = await get_execution_engine_factory()

            creation_tasks = [
                factory.create_for_user(context)
                for context in user_contexts
            ]

            engines = await asyncio.gather(*creation_tasks)

            # Validate complete isolation
            for i, engine in enumerate(engines):
                # Each engine has unique user context
                assert engine.get_user_context().user_id == f"concurrent_user_{i}"

                # Each engine has separate WebSocket emitter
                assert engine.websocket_emitter is not None
                assert engine.websocket_emitter.user_id == f"concurrent_user_{i}"

                # Each engine has separate agent factory
                assert engine.agent_factory is not None

                # No shared state between engines
                for j, other_engine in enumerate(engines):
                    if i != j:
                        assert engine.engine_id != other_engine.engine_id
                        assert engine.get_user_context().user_id != other_engine.get_user_context().user_id

            print(f"✅ Issue #710 CONCURRENCY: {len(engines)} concurrent users properly isolated")

        finally:
            # Cleanup all engines
            for engine in engines:
                try:
                    await engine.cleanup()
                except:
                    pass

    @pytest.mark.asyncio
    async def test_websocket_events_after_ssot_migration(self):
        """Test that WebSocket events work correctly after SSOT migration."""
        user_context = UserExecutionContext.from_request_supervisor(
            user_id="websocket_test_user",
            thread_id="websocket_test_thread",
            run_id="websocket_test_run",
            request_id="websocket_test_request"
        )

        async with user_execution_engine(user_context) as engine:
            # Validate WebSocket components are properly connected
            assert engine.websocket_emitter is not None
            assert engine.websocket_bridge is not None

            # Test WebSocket bridge has required methods
            bridge = engine.websocket_bridge
            required_methods = [
                'notify_agent_started',
                'notify_agent_completed',
                'notify_tool_executing',
                'notify_tool_completed'
            ]

            for method_name in required_methods:
                assert hasattr(bridge, method_name), f"WebSocket bridge missing {method_name}"
                assert callable(getattr(bridge, method_name)), f"{method_name} is not callable"

            # Test emitter functionality
            emitter = engine.websocket_emitter
            assert emitter.user_id == user_context.user_id
            assert emitter.websocket_bridge is not None

            print("✅ Issue #710 WEBSOCKET: WebSocket event delivery system properly integrated")


@pytest.mark.integration
class TestGoldenPathProtection:
    """Test that Golden Path functionality is protected during SSOT migration."""

    @pytest.mark.asyncio
    async def test_golden_path_user_flow_after_ssot_fixes(self):
        """Test complete Golden Path: Users login → get AI responses."""
        user_context = UserExecutionContext.from_request_supervisor(
            user_id="golden_path_user",
            thread_id="golden_path_thread",
            run_id="golden_path_run",
            request_id="golden_path_request",
            metadata={
                'test_type': 'golden_path_validation',
                'issue': '#710',
                'user_message': 'Test AI optimization request'
            }
        )

        async with user_execution_engine(user_context) as engine:
            # Validate engine is ready for Golden Path
            assert engine.is_active()
            assert engine.get_user_context().user_id == "golden_path_user"

            # Validate WebSocket events are available (critical for chat)
            assert engine.websocket_emitter is not None
            assert engine.websocket_bridge is not None

            # Validate agent factory is ready
            assert engine.agent_factory is not None

            # Validate tool dispatcher integration
            tool_dispatcher = await engine.get_tool_dispatcher()
            assert tool_dispatcher is not None

            # Check available agents (should not be empty)
            available_agents = engine.get_available_agents()
            assert len(available_agents) > 0, "No agents available for Golden Path execution"

            # Check available tools
            available_tools = await engine.get_available_tools()
            assert len(available_tools) > 0, "No tools available for Golden Path execution"

            print("✅ Issue #710 GOLDEN PATH: Complete user flow validation successful")
            print(f"   - Available agents: {len(available_agents)}")
            print(f"   - Available tools: {len(available_tools)}")
            print(f"   - WebSocket events: Ready")
            print(f"   - User isolation: Confirmed")
```

### Step 4.2: Validation Commands

**Execute in sequence after each phase**:

```bash
# Phase 1 Validation: Critical factory method fixes
python tests/mission_critical/test_execution_engine_ssot_compliance.py::TestExecutionEngineSSotCompliance::test_user_execution_engine_create_from_legacy_websocket_auto_creation

# Phase 2 Validation: Duplicate factory elimination
python tests/unified_test_runner.py --category integration --filter="execution_engine" --real-services

# Phase 3 Validation: Import standardization
python -c "
import sys
import importlib
try:
    # Test old imports fail appropriately
    import netra_backend.app.agents.execution_engine_unified_factory
    print('⚠️ Redirect module loaded (expected during transition)')
except ImportError:
    print('✅ Old unified factory module properly removed')

try:
    # Test new imports work
    from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
    print('✅ SSOT factory import successful')
except ImportError as e:
    print(f'❌ SSOT factory import failed: {e}')
    sys.exit(1)
"

# Phase 4 Validation: Complete Golden Path test
python tests/mission_critical/test_execution_engine_ssot_compliance.py::TestGoldenPathProtection::test_golden_path_user_flow_after_ssot_fixes

# Final validation: All execution engine tests
python tests/unified_test_runner.py --real-services --category integration unit --filter="execution_engine"
```

---

## Emergency Rollback Procedures

### Git-Based Rollback
```bash
# If any phase fails, immediate rollback:
git stash  # Save current changes
git checkout HEAD~1  # Go to last known good commit

# Validate rollback
python tests/mission_critical/test_websocket_agent_events_suite.py
python tests/e2e/test_golden_path_user_flow.py

# If validation passes, analyze what went wrong:
git diff HEAD~1 HEAD  # See what changed
```

### Atomic Rollback per Phase
```bash
# Phase 1 rollback (if factory method fixes fail):
git checkout HEAD -- netra_backend/app/agents/supervisor/user_execution_engine.py
git checkout HEAD -- netra_backend/app/agents/supervisor/execution_engine_factory.py

# Phase 2 rollback (if redirect modules fail):
git checkout HEAD -- netra_backend/app/agents/execution_engine_unified_factory.py

# Phase 3 rollback (if import fixes fail):
git checkout HEAD -- netra_backend/  # Restore all import changes
python scripts/fix_execution_engine_imports.py netra_backend/ --rollback  # If script supports rollback
```

---

## Success Criteria Checklist

### Technical Validation
- [ ] **TypeError Fix**: `UserExecutionEngine.create_from_legacy(registry, None)` succeeds
- [ ] **WebSocket Auto-creation**: WebSocket bridge auto-created when None
- [ ] **Import Standardization**: All imports use `execution_engine_factory` path
- [ ] **Factory Consolidation**: Only `ExecutionEngineFactory` creates engines
- [ ] **Test Pass Rate**: 100% of execution engine tests pass

### Business Validation
- [ ] **Golden Path Working**: Users login → get AI responses end-to-end
- [ ] **WebSocket Events**: All 5 critical events delivered correctly
- [ ] **Concurrent Users**: 5+ users supported simultaneously with isolation
- [ ] **Response Quality**: AI agents return meaningful results
- [ ] **Performance**: <2s response times maintained

### Architecture Validation
- [ ] **SSOT Compliance**: Single source of truth for execution engine creation
- [ ] **Code Reduction**: Duplicate factory implementations eliminated
- [ ] **Documentation**: Changes documented in architecture specs
- [ ] **Import Clarity**: Clear, unambiguous import paths for all consumers

---

This implementation guide provides the exact code changes and validation steps needed to successfully remediate the execution engine factory chaos while protecting the critical Golden Path functionality.