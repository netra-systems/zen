"""
ZEN - Multi-Instance Claude Orchestrator

A service for orchestrating multiple Claude Code instances in parallel.
"""

__version__ = "1.0.0"
__author__ = "Netra Systems"

from .zen_orchestrator import ClaudeInstanceOrchestrator, InstanceConfig, InstanceStatus

__all__ = ["ClaudeInstanceOrchestrator", "InstanceConfig", "InstanceStatus"]