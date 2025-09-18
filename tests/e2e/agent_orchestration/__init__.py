"""
Agent Orchestration E2E Tests Package
=====================================

This package contains comprehensive E2E tests for agent orchestration functionality,
focusing on Supervisor Agent multi-user orchestration patterns.

Test Suites:
- test_supervisor_multi_user_isolation.py: Multi-user agent isolation testing
- test_agent_handoff_chain_validation.py: Agent handoff chain validation
- test_websocket_agent_coordination.py: WebSocket coordination for agents

Business Value:
These tests protect 500K+ ARR by ensuring reliable agent orchestration,
multi-user isolation, and real-time WebSocket coordination for enterprise customers.

Environment: GCP Staging (NO DOCKER)
Coverage: Issue #872 - Supervisor Agent Multi-User Orchestration
"""

# Import test classes for discovery
from .test_supervisor_multi_user_isolation import SupervisorMultiUserIsolationTests
from .test_agent_handoff_chain_validation import AgentHandoffChainValidationTests
from .test_websocket_agent_coordination import WebSocketAgentCoordinationTests

__all__ = [
    "SupervisorMultiUserIsolationTests",
    "AgentHandoffChainValidationTests",
    "WebSocketAgentCoordinationTests"
]