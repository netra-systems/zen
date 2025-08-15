#!/usr/bin/env python3
"""
Status Analysis Module - Main Aggregator
Aggregates status analysis from specialized analyzers.
Complies with 300-line and 8-line function limits.
"""

# Import all analyzer classes for easy access
try:
    from .status_integration_analyzer import IntegrationAnalyzer
    from .status_agent_analyzer import (
        AgentSystemAnalyzer, TestCoverageAnalyzer, HealthScoreCalculator
    )
except ImportError:
    from status_integration_analyzer import IntegrationAnalyzer
    from status_agent_analyzer import (
        AgentSystemAnalyzer, TestCoverageAnalyzer, HealthScoreCalculator
    )

# Re-export classes for backward compatibility
__all__ = [
    'IntegrationAnalyzer',
    'AgentSystemAnalyzer', 
    'TestCoverageAnalyzer',
    'HealthScoreCalculator'
]