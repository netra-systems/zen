"""
WebSocket Golden Path Unit Tests Package

This package contains comprehensive unit tests for the most critical WebSocket SSOT classes
that enable the Golden Path user flow: connection  ->  authentication  ->  message routing  ->  agent execution.

Business Value: These tests protect $500K+ ARR chat functionality by validating:
- Connection success rates (WebSocket Manager)
- Message routing accuracy (Message Handlers) 
- User isolation enforcement (Connection Handler)
- Agent execution integration (Agent Handler)
- Authentication security (WebSocket Authentication)

SSOT Compliance: All tests inherit from SSotBaseTestCase and use SSotMockFactory.
"""