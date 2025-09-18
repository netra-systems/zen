"""
Test 2: Staging WebSocket Agent Events - Modern API Implementation

CRITICAL: Test WebSocket agent communication flow in staging environment.
This validates the mission-critical WebSocket events that enable chat value delivery.

FIXES IMPLEMENTED:
- Uses canonical staging.netrasystems.ai URLs (CLAUDE.md compliance)
- Modern WebSocket API without deprecated timeout parameter (Issue #605)
- Service availability checks before connection attempts
- Proper asyncio timeout patterns and error handling

Business Value: Free/Early/Mid/Enterprise - Chat is King (90% value delivery)
WebSocket events enable real-time AI interactions, the core of our business value.
"""

import pytest
import asyncio
import json
import time
import uuid
from typing import Dict, List, Any, Optional
from shared.isolated_environment import IsolatedEnvironment
from tests.staging.staging_config import StagingConfig
from tests.clients.staging_websocket_client import StagingWebSocketTester

# Required WebSocket Events for Chat Value
REQUIRED_EVENTS = [
    "agent_started",
    "agent_thinking", 
    "tool_executing",
    "tool_completed",
    "agent_completed"
]


@pytest.mark.asyncio
@pytest.mark.staging  
async def test_staging_websocket_agent_events():
    """
    Main test entry point for WebSocket agent events using modern API.
    
    CRITICAL FIXES:
    - Uses canonical staging.netrasystems.ai URLs
    - Modern WebSocket API without deprecated timeout parameter
    - Service availability checks before connection attempts
    - Proper error handling and timeout patterns
    """
    tester = StagingWebSocketTester()
    results = await tester.run_comprehensive_test()
    
    # Log results for debugging
    print(f"[WebSocket Test Results] {results['summary']}")
    if not results['summary']['all_tests_passed']:
        print(f"[FAILURE DETAILS] {results}")
    
    # Assert critical conditions with detailed error messages
    assert results["summary"]["connectivity_success"], (
        f"WebSocket connectivity failed: {results['basic_connectivity']}"
    )
    
    assert results["summary"]["agent_events_success"], (
        f"Agent events test failed: {results['agent_execution']}"
    )
    
    assert not results["summary"]["critical_chat_issue"], (
        f"Missing critical WebSocket events for chat: {results['agent_execution'].get('missing_events', [])}"
    )


@pytest.mark.asyncio
@pytest.mark.staging  
async def test_staging_websocket_basic_connectivity():
    """Test basic WebSocket connectivity to staging environment."""
    tester = StagingWebSocketTester()
    result = await tester.test_basic_connectivity()
    
    assert result["success"], f"Basic WebSocket connectivity failed: {result}"
    assert result["connection_time"] is not None, "Connection time not recorded"
    assert result["connection_time"] < 10.0, f"Connection took too long: {result['connection_time']}s"


@pytest.mark.asyncio
@pytest.mark.staging
async def test_staging_service_availability():
    """Test that all staging services are available before WebSocket tests."""
    from tests.clients.staging_websocket_client import StagingWebSocketClient
    
    client = StagingWebSocketClient()
    
    # Test each required service
    services_to_check = ["auth", "websocket", "netra_backend"]
    results = {}
    
    for service in services_to_check:
        result = await client.check_service_availability(service)
        results[service] = result
        
        assert result["available"], (
            f"Staging service {service} not available: {result}"
        )
    
    print(f"All staging services available: {results}")


if __name__ == "__main__":
    async def main():
        tester = StagingWebSocketTester()
        results = await tester.run_comprehensive_test()
        
        print(f"\n=== STAGING WEBSOCKET TEST RESULTS ===")
        print(f"All tests passed: {results['summary']['all_tests_passed']}")
        print(f"Connectivity: {results['summary']['connectivity_success']}")
        print(f"Agent events: {results['summary']['agent_events_success']}")
        print(f"Connection time: {results['summary'].get('connection_time', 'N/A')}s")
        
        if not results["summary"]["all_tests_passed"]:
            print(f"\n=== FAILURE DETAILS ===")
            for test_name, test_result in results.items():
                if test_name != "summary" and isinstance(test_result, dict) and not test_result.get("success", True):
                    print(f"{test_name}: {test_result}")
            exit(1)
        else:
            print("\nCHECK All staging WebSocket tests PASSED!")
            
    asyncio.run(main())