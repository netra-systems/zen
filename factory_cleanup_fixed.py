#!/usr/bin/env python3
"""
Factory Pattern Cleanup Remediation Script - FIXED VERSION
Phase 1: Critical Security Fixes for Issue #1116 Singleton Patterns

This script performs the critical singleton remediation based on the baseline audit.
"""

import os
import re
import shutil
from pathlib import Path

def backup_and_remediate_agent_registry():
    """Remediate the agent registry singleton pattern."""
    file_path = "netra_backend/app/agents/registry.py"

    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return False

    # Backup original
    backup_path = file_path + ".backup_pre_singleton_cleanup"
    shutil.copy2(file_path, backup_path)
    print(f"Backup created: {backup_path}")

    # Read current content
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check if already remediated
    if "AgentRegistryFactory" in content:
        print(f"File already remediated: {file_path}")
        return True

    # Look for the singleton pattern to replace
    if "_agent_registry_instance = None" not in content:
        print(f"Singleton pattern not found in: {file_path}")
        return False

    # Add necessary imports if not present
    if "import threading" not in content and "from typing import Dict, Optional" not in content:
        content = content.replace(
            "import logging\nimport warnings",
            "import logging\nimport warnings\nimport threading\nfrom typing import Dict, Optional"
        )

    # Create the remediation replacement
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

    # Find the pattern to replace - be more precise
    pattern_start = content.find("# Backward compatibility - create a module-level agent_registry")
    if pattern_start == -1:
        print("Could not find backward compatibility section")
        return False

    pattern_end = content.find("agent_registry = _get_global_agent_registry()")
    if pattern_end == -1:
        print("Could not find agent_registry assignment")
        return False

    pattern_end += len("agent_registry = _get_global_agent_registry()")

    # Replace the section
    new_content = (
        content[:pattern_start] +
        singleton_replacement +
        content[pattern_end:]
    )

    # Write the remediated content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"Successfully remediated: {file_path}")
    return True

def backup_and_remediate_execution_engine_factory():
    """Remediate the execution engine factory singleton pattern."""
    file_path = "netra_backend/app/agents/supervisor/execution_engine_factory.py"

    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return False

    # Backup original
    backup_path = file_path + ".backup_pre_singleton_cleanup"
    shutil.copy2(file_path, backup_path)
    print(f"Backup created: {backup_path}")

    # Read current content
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check if already remediated
    if "ExecutionEngineFactoryManager" in content:
        print(f"File already remediated: {file_path}")
        return True

    # Look for the singleton pattern
    if "_factory_instance: Optional[ExecutionEngineFactory] = None" not in content:
        print(f"Singleton pattern not found in: {file_path}")
        return False

    # Replace singleton instance with factory manager pattern
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
            user_context: User identifier for isolation

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
                        # Get base configuration
                        base_factory = app.state.execution_engine_factory
                        # Create user-scoped instance
                        user_factory = ExecutionEngineFactory(
                            websocket_bridge=base_factory.websocket_bridge,
                            database_session_manager=base_factory.database_session_manager,
                            redis_manager=base_factory.redis_manager
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
_factory_manager = ExecutionEngineFactoryManager()
_factory_lock = asyncio.Lock()  # Keep for backward compatibility'''

    # Replace the singleton pattern
    content = content.replace(
        "# Singleton factory instance\n_factory_instance: Optional[ExecutionEngineFactory] = None\n_factory_lock = asyncio.Lock()",
        singleton_replacement
    )

    # Update the get_execution_engine_factory function
    old_function_pattern = re.compile(
        r'async def get_execution_engine_factory\(\) -> ExecutionEngineFactory:.*?return _factory_instance',
        re.DOTALL
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

    content = old_function_pattern.sub(new_function, content)

    # Write the remediated content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"Successfully remediated: {file_path}")
    return True

def run_phase1_remediation():
    """Execute Phase 1 factory cleanup remediation."""
    print("=== FACTORY CLEANUP REMEDIATION PHASE 1 ===")
    print("Converting critical singleton patterns to user-scoped factories")
    print("Based on Issue #1116 proven patterns for multi-user isolation")
    print()

    results = {
        'agent_registry': backup_and_remediate_agent_registry(),
        'execution_engine_factory': backup_and_remediate_execution_engine_factory()
    }

    successful_remediations = sum(results.values())

    print(f"\n=== PHASE 1 REMEDIATION COMPLETE ===")
    print(f"Successful remediations: {successful_remediations}/2")
    print(f"Results: {results}")

    if successful_remediations > 0:
        print("\nNEXT STEPS:")
        print("1. Run tests to validate system stability")
        print("2. Check Golden Path functionality")
        print("3. Proceed to Phase 2 - Remove unnecessary factory abstractions")
        print("4. Validate SSOT compliance improvements")

    return results

if __name__ == "__main__":
    results = run_phase1_remediation()
    print(f"\nRemediation completed with {sum(results.values())} successful conversions")