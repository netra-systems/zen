"""
Multi-Agent Coordination Integration Tests Package

BVJ:
- Segment: Platform/Internal (foundation for ALL customer segments)
- Business Goal: Platform Stability - Prevent $35K MRR loss from coordination failures
- Value Impact: Ensures start multiple agents → establish communication → verify message passing
- Revenue Impact: Prevents customer requests from failing due to broken agent coordination

This package contains focused integration tests for:
- Agent Initialization: Multi-agent startup and registration coordination
- Agent Communication: Inter-agent messaging and broadcast functionality
- Coordination Protocols: Workflow execution and protocol compliance

All tests maintain ≤8 lines per test function and ≤300 lines per module.
"""

from netra_backend.tests.shared_fixtures import (
    MockCoordinationAgent,
    MockAgentRegistry,
    MockCoordinationInfrastructure,
    coordination_infrastructure,
    coordination_agents
)

__all__ = [
    "MockCoordinationAgent",
    "MockAgentRegistry", 
    "MockCoordinationInfrastructure",
    "coordination_infrastructure",
    "coordination_agents"
]