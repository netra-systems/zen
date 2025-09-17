"""
Agent Interface Module for Zen Orchestrator

This module provides extensible support for multiple coding agents,
allowing zen to orchestrate various AI coding assistants beyond Claude Code.
"""

from .base_agent import (
    BaseCodingAgent,
    ClaudeCodeAgent,
    ContinueAgent,
    AgentConfig,
    AgentStatus,
    AgentUsageMetrics,
    AgentFactory
)

__all__ = [
    'BaseCodingAgent',
    'ClaudeCodeAgent',
    'ContinueAgent',
    'AgentConfig',
    'AgentStatus',
    'AgentUsageMetrics',
    'AgentFactory'
]