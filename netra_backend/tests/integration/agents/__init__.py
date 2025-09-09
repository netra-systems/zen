"""
Agent Integration Tests Module

This module contains comprehensive integration tests for agent execution flows,
validating the complete agent lifecycle and business value delivery.

Test Categories:
1. Agent Startup Tests (7 tests) - Initialization, WebSocket events, user isolation
2. Agent Running State Tests (7 tests) - Execution flow, context preservation, error handling  
3. Agent Completion Tests (6 tests) - Results validation, cleanup, performance
4. ExecutionEngine Tests (5 tests) - Factory patterns, resource management, monitoring

All tests follow CLAUDE.md requirements:
- NO MOCKS (except external LLM APIs)
- Real service integration with in-memory databases
- Comprehensive WebSocket event validation
- Multi-user isolation testing
- Performance and error scenario coverage
"""

__all__ = [
    "TestAgentExecutionComprehensive"
]