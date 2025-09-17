"""
Netra Orchestrator Client

A standalone service for orchestrating multiple Claude Code instances.
"""

__version__ = "1.0.0"
__author__ = "Netra Systems"

from .claude_instance_orchestrator import ClaudeInstanceOrchestrator, InstanceConfig, InstanceStatus

__all__ = ["ClaudeInstanceOrchestrator", "InstanceConfig", "InstanceStatus"]