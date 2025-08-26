"""Supervisor Agent - Compatibility Module

This module provides compatibility imports for tests that expect
SupervisorAgent in this specific module path. The actual implementation
is in supervisor_agent_modern.py.
"""

# Import the actual SupervisorAgent implementation
from netra_backend.app.agents.supervisor_agent_modern import SupervisorAgent

# Re-export for compatibility
__all__ = ['SupervisorAgent']