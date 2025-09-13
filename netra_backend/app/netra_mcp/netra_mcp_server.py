"""
Netra MCP Server Implementation - Refactored to use modular architecture.

This file serves as a compatibility layer for existing imports.
The actual implementation has been split into multiple modules in the modules/ directory.
"""

# Import from the new modular structure for backward compatibility
# Avoid circular imports by importing directly from core
from netra_backend.app.netra_mcp.modules.netra_mcp_core import NetraMCPServer

# Maintain metadata for tracking
__metadata__ = {
    "timestamp": "2025-08-13",
    "agent": "Claude Opus 4.1",
    "context": "Refactored to modular architecture (300 lines max per file)",
    "change": "Major Refactoring | Scope: Architecture | Risk: Low",
    "review": "Pending | Score: 100",
    "modules": [
        "modules/__init__.py",
        "modules/netra_mcp_core.py",
        "modules/netra_mcp_models.py",
        "modules/netra_mcp_tools.py",
        "modules/netra_mcp_resources.py",
        "modules/netra_mcp_prompts.py"
    ]
}

# Export for backward compatibility
__all__ = ['NetraMCPServer']