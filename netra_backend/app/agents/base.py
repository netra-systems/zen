"""Base agent class and interfaces.

Simplified interface that imports from modular components for backward compatibility.
"""

# Re-export the main class from the new modular structure
from netra_backend.app.agents.base_agent import BaseSubAgent

# Maintain backward compatibility by re-exporting all the original functionality
__all__ = ['BaseSubAgent']