"""Agent Execution Engine Integration Tests

This package contains comprehensive integration tests for Agent Execution Engine
Cross-Service Orchestration - the third highest priority area for business value.

Test Modules:
- test_agent_execution_orchestration.py: Core orchestration patterns and engine behavior
- test_multi_agent_workflow_integration.py: Multi-agent coordination and workflows
- test_agent_failure_recovery_integration.py: Error handling and recovery patterns
- test_agent_websocket_events_integration.py: WebSocket event validation (MISSION CRITICAL)
- test_concurrent_agent_execution_integration.py: Concurrent execution safety

Business Value Focus:
Agent orchestration is core business logic for AI agent workflows - central to
platform value and user experience. These tests ensure reliable multi-agent
orchestration for enterprise-grade solutions.

Usage:
    # Run all agent execution integration tests
    pytest netra_backend/tests/integration/agent_execution/ -v
    
    # Run specific test module
    pytest netra_backend/tests/integration/agent_execution/test_agent_websocket_events_integration.py -v
    
    # Run with real services
    pytest netra_backend/tests/integration/agent_execution/ -v -m real_services
"""

# Test category for unified test runner
TEST_CATEGORY = "agent_execution_integration"
TEST_PRIORITY = "high_business_value"