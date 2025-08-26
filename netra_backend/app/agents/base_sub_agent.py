"""Base Sub Agent - Compatibility Module

This module provides compatibility imports for tests that expect
BaseSubAgent in this specific module path. The actual implementation
is in base_agent.py.
"""

# Import the actual BaseSubAgent implementation
from netra_backend.app.agents.base_agent import BaseSubAgent

# Re-export for compatibility
__all__ = ['BaseSubAgent']