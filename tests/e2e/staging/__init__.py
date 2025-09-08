"""
E2E Staging Tests Package

This package contains comprehensive End-to-End tests designed for staging environment
with mandatory authentication and real service integration.

All tests in this package follow CLAUDE.md requirements:
- Mandatory authentication (JWT/OAuth) except auth validation tests  
- Real services integration (Docker stack + real LLM)
- WebSocket event validation (all 5 critical events)
- Business value focus (complete user journeys)
- Multi-user isolation and concurrent execution testing

Test Categories:
1. Agent Execution Journeys (8 tests) - test_agent_optimization_complete_flow.py
2. Multi-User Scenarios (6 tests) - test_multi_user_concurrent_sessions.py
3. WebSocket & Real-Time (5 tests) - test_websocket_realtime_updates.py
4. Authentication & Authorization (3 tests) - test_authentication_authorization_flow.py
5. Data Pipeline Validation (3 tests) - test_data_pipeline_persistence.py

Total: 25+ comprehensive E2E tests with mandatory authentication.
"""

__all__ = [
    "TestAgentOptimizationCompleteFlow",
    "TestMultiUserConcurrentSessions", 
    "TestWebSocketRealTimeUpdates",
    "TestAuthenticationAuthorizationFlow",
    "TestDataPipelinePersistence"
]