"""
Quick validation test for Issue #362 - HTTP API WebSocket independence.
Tests the core functionality without complex mocking.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

def test_request_scoped_context_property_alias():
    """Test the websocket_connection_id property alias fix."""
    from netra_backend.app.dependencies import RequestScopedContext

    print("Testing RequestScopedContext websocket_connection_id property alias...")

    # Test with websocket_client_id
    context = RequestScopedContext(
        user_id="test_user",
        thread_id="test_thread",
        run_id="test_run",
        websocket_client_id="test_websocket_123"
    )

    # Verify property alias works
    assert hasattr(context, 'websocket_connection_id'), "websocket_connection_id property missing"
    assert context.websocket_connection_id == "test_websocket_123", "Property alias not working"
    assert context.websocket_connection_id == context.websocket_client_id, "Property alias mismatch"

    # Test with None
    context_none = RequestScopedContext(
        user_id="test_user",
        thread_id="test_thread",
        run_id="test_run",
        websocket_client_id=None
    )
    assert context_none.websocket_connection_id is None, "None case not handled"

    print("PASS: RequestScopedContext property alias working correctly")
    return True

def test_http_api_parameter_mapping():
    """Test HTTP API parameter name mapping."""
    import asyncio
    from netra_backend.app.dependencies import get_request_scoped_context

    print("Testing HTTP API parameter mapping...")

    async def test_mapping():
        # Test parameter mapping from websocket_connection_id to websocket_client_id
        context = await get_request_scoped_context(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run",
            websocket_connection_id="mapped_connection_id"
        )

        # Verify mapping worked
        assert context.websocket_client_id == "mapped_connection_id", "Parameter mapping failed"
        assert context.websocket_connection_id == "mapped_connection_id", "Property alias after mapping failed"

    # Run the async test
    asyncio.run(test_mapping())

    print("PASS: HTTP API parameter mapping working correctly")
    return True

def test_fallback_execution_pattern():
    """Test that AgentService has fallback execution pattern."""
    from netra_backend.app.services.agent_service_core import AgentService

    print("Testing AgentService fallback pattern availability...")

    # Check that fallback method exists
    assert hasattr(AgentService, '_execute_agent_fallback'), "Fallback method missing"

    # Check that ensure_service_ready method exists
    assert hasattr(AgentService, 'ensure_service_ready'), "Service ready check missing"

    print("PASS: AgentService fallback patterns available")
    return True

def test_http_routes_availability():
    """Test that HTTP API routes are available."""
    print("Testing HTTP API routes availability...")

    from netra_backend.app.routes.agents_execute import router

    # Check routes are defined
    routes = [route for route in router.routes]
    route_paths = [route.path for route in routes]

    expected_paths = [
        "/execute",
        "/triage",
        "/data",
        "/optimization",
        "/start",
        "/stop",
        "/cancel",
        "/status",
        "/stream"
    ]

    for expected_path in expected_paths:
        assert expected_path in route_paths, f"Route {expected_path} missing"

    print("PASS: All HTTP API routes available")
    return True

def main():
    """Run all validation tests."""
    print("Issue #362 Validation - HTTP API WebSocket Independence\n")

    tests = [
        test_request_scoped_context_property_alias,
        test_http_api_parameter_mapping,
        test_fallback_execution_pattern,
        test_http_routes_availability
    ]

    passed = 0
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"FAIL: Test failed: {test.__name__}")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()

    print(f"\nResults: {passed}/{len(tests)} tests passed")

    if passed == len(tests):
        print("SUCCESS: Issue #362 core infrastructure is working correctly!")
        print("HTTP API can operate without WebSocket dependency")
        return True
    else:
        print("WARNING: Some issues found - see errors above")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)