"""Supervisor Agent Module

This module provides the main Supervisor implementation that orchestrates sub-agents.
It directly exports the consolidated supervisor for a cleaner architecture.
"""

from app.agents.supervisor_consolidated import SupervisorAgent as Supervisor

# For backward compatibility, also export as SupervisorAgent
SupervisorAgent = Supervisor

__all__ = ['Supervisor', 'SupervisorAgent']