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
Demo service backward compatibility module.

DEPRECATED: This file provides backward compatibility imports.
All classes have been moved to the demo_service/ module directory
for better organization and compliance with the 450-line limit.

New imports should use:
from netra_backend.app.agents.demo_service import DemoService, DemoTriageService, etc.
"""

# Backward compatibility imports
from netra_backend.app.agents.demo_service.core import DemoService
from netra_backend.app.agents.demo_service.optimization import DemoOptimizationService
from netra_backend.app.agents.demo_service.reporting import DemoReportingService
from netra_backend.app.agents.demo_service.triage import DemoTriageService

# Legacy class aliases for backward compatibility
DemoAgent = DemoService
DemoTriageAgent = DemoTriageService
DemoOptimizationAgent = DemoOptimizationService
DemoReportingAgent = DemoReportingService

# Export for backward compatibility
__all__ = [
    "DemoService",
    "DemoTriageService", 
    "DemoOptimizationService",
    "DemoReportingService",
    # Legacy aliases
    "DemoAgent",
    "DemoTriageAgent",
    "DemoOptimizationAgent",
    "DemoReportingAgent"
]