"""

Agent Flow Integration Test Suite



This module contains integration tests for agent execution flows, focusing on

the complete agent lifecycle and business-critical functionality.



Test Coverage:

- Complete agent state transitions during 5-event WebSocket flow

- Error recovery with WebSocket continuation

- Concurrent agent execution performance and isolation

- Tool execution handoffs and timeout scenarios



Business Value:

These tests protect $500K+ ARR chat functionality by validating the complete

agent execution pipeline works reliably under various scenarios.

"""

