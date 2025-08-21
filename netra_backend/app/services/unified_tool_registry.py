"""
Unified Tool Registry - Refactored to use modular architecture

This file serves as a compatibility layer for existing imports.
The actual implementation has been split into multiple modules in the unified_tool_registry/ directory.
"""

# Import from the new modular structure for backward compatibility
from netra_backend.app.services.unified_tool_registry import (
    ToolExecutionResult,
    UnifiedTool,
    UnifiedToolRegistry,
)

# Maintain metadata for tracking
__metadata__ = {
    "timestamp": "2025-08-13",
    "agent": "Claude Sonnet 4",
    "context": "Refactored to modular architecture (300 lines max per file)",
    "change": "Major Refactoring | Scope: Architecture | Risk: Low",
    "review": "Pending | Score: 100",
    "modules": [
        "unified_tool_registry/__init__.py",
        "unified_tool_registry/models.py",
        "unified_tool_registry/registry.py",
        "unified_tool_registry/tool_registrations.py",
        "unified_tool_registry/tool_handlers.py",
        "unified_tool_registry/data_management_handlers.py",
        "unified_tool_registry/optimization_handlers.py",
        "unified_tool_registry/system_handlers.py",
        "unified_tool_registry/execution_engine.py"
    ]
}

# Export for backward compatibility
__all__ = [
    'UnifiedTool',
    'ToolExecutionResult',
    'UnifiedToolRegistry'
]