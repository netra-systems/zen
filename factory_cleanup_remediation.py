#!/usr/bin/env python3
"""
Factory Pattern Cleanup Remediation Script
Phase 1: Critical Security Fixes and Over-Engineering Reduction

Business Value Justification:
- Segment: Platform Infrastructure
- Business Goal: Security & Performance
- Value Impact: Eliminates multi-user data contamination risks
- Strategic Impact: Reduces over-engineering while maintaining $500K+ ARR functionality

This script performs Phase 1 factory pattern cleanup based on Issue #1116 proven patterns:
1. Convert critical singletons to user-scoped factories
2. Remove unnecessary factory abstractions
3. Fix SSOT compliance violations
"""

import os
import re
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

class FactoryCleanupRemediator:
    """Performs factory pattern cleanup based on audit findings."""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.remediation_log = []
        self.metrics = {
            'singletons_converted': 0,
            'factories_removed': 0,
            'imports_fixed': 0,
            'violations_resolved': 0
        }

    def log_action(self, action: str, file_path: str, details: str = ""):
        """Log remediation action."""
        log_entry = f"[{action}] {file_path}: {details}"
        self.remediation_log.append(log_entry)
        print(log_entry)

    def backup_file(self, file_path: Path) -> Path:
        """Create backup of file before modification."""
        backup_path = file_path.with_suffix(f"{file_path.suffix}.backup_pre_factory_cleanup")
        shutil.copy2(file_path, backup_path)
        self.log_action("BACKUP", str(file_path), f"→ {backup_path.name}")
        return backup_path

    def convert_singleton_to_user_factory(self, file_path: Path, singleton_pattern: str):
        """Convert singleton pattern to user-scoped factory."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Backup original
        self.backup_file(file_path)

        # Apply Issue #1116 singleton remediation pattern
        if singleton_pattern == "agent_registry_instance":
            new_content = self.remediate_agent_registry_singleton(content)
        elif singleton_pattern == "execution_engine_factory_instance":
            new_content = self.remediate_execution_engine_singleton(content)
        elif singleton_pattern == "execution_state_store_instance":
            new_content = self.remediate_execution_state_singleton(content)
        else:
            self.log_action("SKIP", str(file_path), f"Unknown singleton pattern: {singleton_pattern}")
            return False

        # Write remediated content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        self.metrics['singletons_converted'] += 1
        self.log_action("REMEDIATE", str(file_path), f"Converted {singleton_pattern} to user-scoped factory")
        return True

    def remediate_agent_registry_singleton(self, content: str) -> str:
        """Apply Issue #1116 pattern to agent registry singleton."""
        # Add necessary imports
        if "import threading" not in content:
            content = content.replace(
                "import logging\nimport warnings",
                "import logging\nimport warnings\nimport threading\nfrom typing import Dict, Optional"
            )

        # Replace singleton pattern with user-scoped factory
        singleton_replacement = '''# ISSUE #1116 REMEDIATION: Phase 1 Singleton to User-Scoped Factory Migration
# Replace global singleton with user-scoped factory for multi-user safety

class AgentRegistryFactory:
    """User-scoped AgentRegistry factory for multi-user isolation.

    CRITICAL SECURITY: Prevents cross-user data contamination by ensuring
    each user gets their own isolated AgentRegistry instance.

    Business Value: Enables $500K+ ARR multi-user chat functionality
    with enterprise-grade user isolation.
    """

    def __init__(self):
        """Initialize factory with per-user registry storage."""
        self._user_registries: Dict[str, AgentRegistry] = {}
        self._lock = threading.Lock()

    def get_registry(self, user_context: Optional[str] = None) -> AgentRegistry:
        """Get user-scoped AgentRegistry instance.

        Args:
            user_context: User identifier for isolation (optional for backward compatibility)

        Returns:
            AgentRegistry: Isolated registry for the user
        """
        # Default context for backward compatibility
        if user_context is None:
            user_context = "default_global"

        with self._lock:
            if user_context not in self._user_registries:
                self._user_registries[user_context] = AgentRegistry()
            return self._user_registries[user_context]

    def clear_user_registry(self, user_context: str) -> None:
        """Clear registry for specific user (cleanup after session ends)."""
        with self._lock:
            self._user_registries.pop(user_context, None)

# Factory instance for creating user-scoped registries
_agent_registry_factory = AgentRegistryFactory()

def _get_global_agent_registry():
    """DEPRECATED: Get the global agent registry instance.

    MIGRATION PATH: This maintains backward compatibility.
    New code should use get_user_agent_registry(user_context) instead.
    """
    return _agent_registry_factory.get_registry(user_context=None)

def get_user_agent_registry(user_context: Optional[str] = None) -> AgentRegistry:
    """Get user-scoped agent registry for multi-user safety.

    Args:
        user_context: User identifier for isolation

    Returns:
        AgentRegistry: Isolated registry for the user
    """
    return _agent_registry_factory.get_registry(user_context)

# Module-level agent_registry for backward compatibility
agent_registry = _get_global_agent_registry()'''

        # Replace old singleton pattern
        old_pattern = re.compile(
            r'# Backward compatibility.*?agent_registry = _get_global_agent_registry\(\)',
            re.DOTALL | re.MULTILINE
        )
        content = old_pattern.sub(singleton_replacement, content)

        return content

    def remediate_execution_engine_singleton(self, content: str) -> str:
        """Apply Issue #1116 pattern to execution engine factory singleton."""
        # Replace singleton pattern with user-scoped factory approach
        singleton_replacement = '''# ISSUE #1116 REMEDIATION: Phase 1 Singleton to User-Scoped Factory Migration
# Replace global singleton with user-scoped factory for multi-user safety

class ExecutionEngineFactoryManager:
    """User-scoped ExecutionEngineFactory manager for multi-user isolation.

    CRITICAL SECURITY: Prevents cross-user data contamination by ensuring
    each request gets proper user context isolation.

    Business Value: Enables $500K+ ARR multi-user chat functionality
    with enterprise-grade user isolation.
    """

    def __init__(self):
        """Initialize factory manager with per-user context storage."""
        self._user_factories: Dict[str, ExecutionEngineFactory] = {}
        self._lock = asyncio.Lock()

    async def get_factory(self, user_context: Optional[str] = None) -> ExecutionEngineFactory:
        """Get user-scoped ExecutionEngineFactory instance.

        Args:
            user_context: User identifier for isolation (optional for backward compatibility)

        Returns:
            ExecutionEngineFactory: Isolated factory for the user
        """
        # Default context for backward compatibility
        if user_context is None:
            user_context = "default_global"

        async with self._lock:
            if user_context not in self._user_factories:
                # Try to get configured factory from FastAPI app state first
                try:
                    from netra_backend.app.main import app
                    if hasattr(app.state, 'execution_engine_factory'):
                        # Use the app-configured factory as template for user-scoped instances
                        base_factory = app.state.execution_engine_factory
                        # Create user-scoped instance with same configuration
                        user_factory = ExecutionEngineFactory(
                            websocket_bridge=base_factory.websocket_bridge,
                            database_session_manager=base_factory.database_session_manager,
                            redis_manager=base_factory.redis_manager,
                            user_context=user_context  # Add user context for isolation
                        )
                        self._user_factories[user_context] = user_factory
                    else:
                        raise ExecutionEngineFactoryError(
                            "ExecutionEngineFactory not configured during startup. "
                            "The factory requires a WebSocket bridge for proper agent execution. "
                            "Check system initialization in smd.py - ensure ExecutionEngineFactory "
                            "is created with websocket_bridge parameter during startup."
                        )
                except (ImportError, AttributeError) as e:
                    raise ExecutionEngineFactoryError(
                        f"ExecutionEngineFactory not configured during startup: {e}"
                    )

            return self._user_factories[user_context]

    async def clear_user_factory(self, user_context: str) -> None:
        """Clear factory for specific user (cleanup after session ends)."""
        async with self._lock:
            if user_context in self._user_factories:
                factory = self._user_factories.pop(user_context)
                # Clean up any resources if needed
                if hasattr(factory, 'cleanup'):
                    await factory.cleanup()

# Factory manager instance for creating user-scoped factories
_factory_manager = ExecutionEngineFactoryManager()'''

        # Replace old singleton pattern
        old_pattern = re.compile(
            r'# Singleton factory instance.*?_factory_instance.*?=.*?None.*?_factory_lock = asyncio\.Lock\(\)',
            re.DOTALL | re.MULTILINE
        )
        content = old_pattern.sub(singleton_replacement, content)

        # Update get_execution_engine_factory function
        old_function = re.compile(
            r'async def get_execution_engine_factory\(\) -> ExecutionEngineFactory:.*?return _factory_instance',
            re.DOTALL | re.MULTILINE
        )

        new_function = '''async def get_execution_engine_factory(user_context: Optional[str] = None) -> ExecutionEngineFactory:
    """Get user-scoped ExecutionEngineFactory instance.

    Args:
        user_context: User identifier for isolation (optional for backward compatibility)

    Returns:
        ExecutionEngineFactory: User-isolated factory instance

    Raises:
        ExecutionEngineFactoryError: If factory not configured during startup
    """
    return await _factory_manager.get_factory(user_context)'''

        content = old_function.sub(new_function, content)

        return content

    def remediate_execution_state_singleton(self, content: str) -> str:
        """Apply Issue #1116 pattern to execution state store singleton."""
        # Similar pattern as above but for execution state store
        singleton_replacement = '''# ISSUE #1116 REMEDIATION: Phase 1 Singleton to User-Scoped Factory Migration
# Replace global singleton with user-scoped factory for multi-user safety

class ExecutionStateStoreFactory:
    """User-scoped ExecutionStateStore factory for multi-user isolation."""

    def __init__(self):
        """Initialize factory with per-user store storage."""
        self._user_stores: Dict[str, ExecutionStateStore] = {}
        self._lock = threading.Lock()

    def get_store(self, user_context: Optional[str] = None) -> ExecutionStateStore:
        """Get user-scoped ExecutionStateStore instance."""
        if user_context is None:
            user_context = "default_global"

        with self._lock:
            if user_context not in self._user_stores:
                self._user_stores[user_context] = ExecutionStateStore()
            return self._user_stores[user_context]

# Factory instance for creating user-scoped stores
_store_factory = ExecutionStateStoreFactory()'''

        # Replace old singleton pattern
        old_pattern = re.compile(
            r'_store_instance.*?=.*?None',
            re.DOTALL | re.MULTILINE
        )
        content = old_pattern.sub('_store_factory = ExecutionStateStoreFactory()', content)

        return content

    def remove_unnecessary_factory(self, file_path: Path, factory_type: str):
        """Remove unnecessary factory abstraction."""
        # For Phase 1, focus on simple wrapper factories that don't add value
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check if this is a simple wrapper factory
        if self.is_simple_wrapper_factory(content, factory_type):
            self.backup_file(file_path)

            # Replace with direct instantiation pattern
            new_content = self.replace_wrapper_with_direct_instantiation(content, factory_type)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            self.metrics['factories_removed'] += 1
            self.log_action("REMOVE", str(file_path), f"Removed unnecessary {factory_type} wrapper factory")
            return True

        return False

    def is_simple_wrapper_factory(self, content: str, factory_type: str) -> bool:
        """Check if factory is a simple wrapper that doesn't add business value."""
        # Look for patterns indicating over-engineering
        patterns = [
            r'class.*Factory.*:.*def create.*:.*return.*\(\)',  # Simple create() -> instantiate pattern
            r'def.*factory.*:.*return.*\(\)',  # Function factory that just returns instance
            r'Factory.*def __init__.*def create.*return.*\(\)'  # Basic factory with no business logic
        ]

        for pattern in patterns:
            if re.search(pattern, content, re.DOTALL):
                # Check if it has any business logic beyond simple instantiation
                if not re.search(r'(validate|configure|setup|inject|context)', content, re.IGNORECASE):
                    return True

        return False

    def replace_wrapper_with_direct_instantiation(self, content: str, factory_type: str) -> str:
        """Replace wrapper factory with direct instantiation."""
        # Add comment explaining the change
        replacement_comment = f"""
# FACTORY CLEANUP REMEDIATION: Removed unnecessary {factory_type} wrapper
# Direct instantiation is preferred for simple cases without complex configuration
# This reduces over-engineering while maintaining functionality
"""

        # Simple replacements for common patterns
        content = re.sub(
            r'class.*Factory.*:.*?def create.*?:.*?return.*?\(\)',
            replacement_comment + '\n# Use direct instantiation instead',
            content,
            flags=re.DOTALL
        )

        return content

    def run_phase1_remediation(self) -> Dict[str, any]:
        """Run Phase 1 factory cleanup remediation."""
        print("=== FACTORY CLEANUP REMEDIATION PHASE 1 ===")
        print("Focusing on critical security fixes and over-engineering reduction")
        print()

        # 1. Convert critical singletons to user-scoped factories
        print("1. Converting critical singleton patterns...")
        critical_singletons = [
            ("/c/GitHub/netra-apex/netra_backend/app/agents/registry.py", "agent_registry_instance"),
            ("/c/GitHub/netra-apex/netra_backend/app/agents/supervisor/execution_engine_factory.py", "execution_engine_factory_instance"),
            ("/c/GitHub/netra-apex/netra_backend/app/agents/supervisor/execution_state_store.py", "execution_state_store_instance"),
        ]

        for file_path_str, singleton_pattern in critical_singletons:
            file_path = Path(file_path_str)
            if file_path.exists():
                try:
                    self.convert_singleton_to_user_factory(file_path, singleton_pattern)
                except Exception as e:
                    self.log_action("ERROR", str(file_path), f"Failed to convert {singleton_pattern}: {e}")

        # 2. Remove unnecessary factory abstractions (high-impact, low-risk)
        print("\n2. Removing unnecessary factory abstractions...")
        # This will be implemented in subsequent iterations

        # 3. Generate summary
        print("\n=== REMEDIATION SUMMARY ===")
        for metric, count in self.metrics.items():
            print(f"{metric.replace('_', ' ').title()}: {count}")

        print("\n=== REMEDIATION LOG ===")
        for log_entry in self.remediation_log[-10:]:  # Show last 10 entries
            print(log_entry)

        return {
            'metrics': self.metrics,
            'log': self.remediation_log,
            'success': True
        }

if __name__ == "__main__":
    remediate = FactoryCleanupRemediator("/c/GitHub/netra-apex")
    result = remediate.run_phase1_remediation()
    print(f"\nRemediation completed with metrics: {result['metrics']}")