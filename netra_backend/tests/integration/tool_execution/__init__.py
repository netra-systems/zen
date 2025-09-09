"""
Tool Execution & Dispatching Integration Test Suite

This module contains comprehensive integration tests for the Tool Execution & Dispatching 
swimlane following CLAUDE.md requirements and TEST_CREATION_GUIDE.md patterns.

Business Value:
- Validates core tool execution functionality that delivers AI optimization insights
- Ensures multi-user security and isolation required for enterprise deployment  
- Tests real-time WebSocket events that enable responsive user experience
- Validates complex orchestration flows that differentiate the platform

Test Categories:
- Tool Registration and Discovery (test_tool_registration_discovery.py)
- Tool Execution Timeout and Error Handling (test_tool_execution_timeout_handling.py)
- Tool Security Sandboxing (test_tool_security_sandboxing.py)
- Tool Dispatcher Factory and Context Isolation (test_tool_dispatcher_factory_isolation.py)
- Multi-Tool Orchestration Flows (test_multi_tool_orchestration_flows.py)
- WebSocket Tool Execution Integration (test_websocket_tool_execution_integration.py)

CRITICAL: All tests use REAL services only (PostgreSQL, Redis, WebSocket connections)
NO MOCKS ALLOWED except for business logic simulation within test tools
"""

__version__ = "1.0.0"
__author__ = "Netra Apex Development Team"
__test_suite__ = "Tool Execution & Dispatching Integration Tests"