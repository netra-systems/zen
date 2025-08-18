# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-15T12:00:00.000000+00:00
# Agent: Claude Sonnet 4 claude-sonnet-4-20250514
# Context: Architecture compliance fix - modularized demo agents
# Git: pr-10-anthony-branch | Current | Clean
# Change: Refactor | Scope: Module | Risk: Low
# Session: Architecture Compliance Fix
# Review: Pending | Score: TBD
# ================================
"""
Demo agent backward compatibility module.

DEPRECATED: This file provides backward compatibility imports.
All classes have been moved to the demo_agent/ module directory
for better organization and compliance with the 300-line limit.

New imports should use:
from app.agents.demo_agent import DemoAgent, DemoTriageAgent, etc.
"""

# Backward compatibility imports
from app.agents.demo_agent.core import DemoAgent
from app.agents.demo_agent.triage import DemoTriageAgent
from app.agents.demo_agent.optimization import DemoOptimizationAgent
from app.agents.demo_agent.reporting import DemoReportingAgent

# Export for backward compatibility
__all__ = [
    "DemoAgent",
    "DemoTriageAgent", 
    "DemoOptimizationAgent",
    "DemoReportingAgent"
]