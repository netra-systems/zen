#!/usr/bin/env python3
"""
Status Analysis Module - Main Aggregator
Aggregates status analysis from specialized analyzers.
Complies with 450-line and 25-line function limits.
"""

# Import all analyzer classes for easy access
try:
    from .status_agent_analyzer import (
        AgentSystemAnalyzer,
        HealthScoreCalculator,
        TestCoverageAnalyzer,
    )
    from scripts.status_integration_analyzer import IntegrationAnalyzer
except ImportError:
    from status_agent_analyzer import (
        AgentSystemAnalyzer,
        HealthScoreCalculator,
        TestCoverageAnalyzer,
    )
    from status_integration_analyzer import IntegrationAnalyzer

# Re-export classes for backward compatibility
__all__ = [
    'IntegrationAnalyzer',
    'AgentSystemAnalyzer', 
    'TestCoverageAnalyzer',
    'HealthScoreCalculator'
]