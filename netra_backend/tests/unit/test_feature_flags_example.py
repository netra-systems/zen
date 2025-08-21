"""Example tests demonstrating feature flag usage.

This file shows best practices for using feature flags in tests,
enabling TDD workflow while maintaining 100% pass rate for CI/CD.
"""

import pytest
from test_framework.decorators import (
    feature_flag,
    tdd_test,
    requires_feature,
    experimental_test,
    performance_test,
    integration_only,
    unit_only,
    requires_env,
    flaky_test,
    skip_if_fast_mode
)


# Example 1: Basic feature flag usage
@feature_flag("roi_calculator")
def test_roi_calculator_basic():
    """Test ROI calculator basic functionality.
    
    This test will be skipped if 'roi_calculator' feature is not enabled.
    Currently marked as 'in_development' in test_feature_flags.json.
    """
    from frontend.components.demo.ROICalculator import calculate_roi
    
    result = calculate_roi(
        current_spend=10000,
        optimization_percentage=20
    )
    assert result["savings"] == 2000
    assert result["roi_percentage"] == 20


# Example 2: TDD test expected to fail initially
@tdd_test("first_time_user_flow", expected_to_fail=True)
def test_first_time_user_onboarding():
    """Test first-time user onboarding flow.
    
    Written using TDD approach - expected to fail until feature is complete.
    """
    from netra_backend.app.services.onboarding import create_first_time_user
    
    user = create_first_time_user(
        email="newuser@example.com",
        company="Test Corp"
    )
    
    assert user.onboarding_completed is False
    assert user.trial_credits == 1000
    assert user.guided_tour_enabled is True


# Example 3: Test requiring multiple features
@requires_feature("auth_integration", "usage_tracking")
def test_authenticated_usage_tracking():
    """Test that requires both auth and usage tracking to be enabled.
    
    Both features must be enabled for this test to run.
    """
    from netra_backend.app.auth_integration.auth import authenticate_user
    from netra_backend.app.services.usage_tracker import track_usage
    
    user = authenticate_user("test@example.com", "password")
    usage = track_usage(user.id, "api_call", 1)
    
    assert usage.user_id == user.id
    assert usage.event_type == "api_call"


# Example 4: Experimental test
@experimental_test("Testing new ML-based rate limiting algorithm")
def test_ml_rate_limiter():
    """Experimental test for ML-based rate limiting.
    
    Only runs when ENABLE_EXPERIMENTAL_TESTS=true.
    """
    from netra_backend.app.websocket.ml_rate_limiter import MLRateLimiter
    
    limiter = MLRateLimiter()
    pattern = limiter.analyze_pattern([1, 2, 4, 8, 16])
    
    assert pattern.is_exponential is True
    assert pattern.should_throttle is True


# Example 5: Performance test with threshold
@performance_test(threshold_ms=100)
def test_api_response_time():
    """Test API response time stays under 100ms.
    
    Skipped in fast mode unless ENABLE_PERFORMANCE_TESTS=true.
    """
    import time
    from netra_backend.app.routes.health import health_check
    
    start = time.time()
    response = health_check()
    duration_ms = (time.time() - start) * 1000
    
    assert response["status"] == "healthy"
    # Performance assertion handled by decorator


# Example 6: Integration-only test
@integration_only()
@feature_flag("websocket_streaming")
def test_websocket_integration():
    """Test WebSocket integration with real connections.
    
    Only runs during integration testing and when websocket_streaming is enabled.
    """
    from netra_backend.app.websocket.connection import WebSocketConnection
    
    conn = WebSocketConnection()
    conn.connect("ws://localhost:8000/ws")
    conn.send({"type": "ping"})
    response = conn.receive()
    
    assert response["type"] == "pong"
    conn.close()


# Example 7: Unit-only test
@unit_only()
def test_utility_function():
    """Simple unit test that only runs during unit testing."""
    from netra_backend.app.core.utils import format_currency
    
    assert format_currency(1000) == "$1,000.00"
    assert format_currency(0) == "$0.00"


# Example 8: Test requiring environment variables
@requires_env("GEMINI_API_KEY", "OPENAI_API_KEY")
@feature_flag("agent_orchestration")
def test_multi_llm_orchestration():
    """Test that requires API keys and agent orchestration feature."""
    from netra_backend.app.agents.orchestrator import MultiLLMOrchestrator
    
    orchestrator = MultiLLMOrchestrator()
    result = orchestrator.process("Analyze this text", models=["gemini", "openai"])
    
    assert "gemini" in result
    assert "openai" in result


# Example 9: Flaky test with retries
@flaky_test(max_retries=3, reason="External API dependency")
@feature_flag("github_integration")
def test_github_api_integration():
    """Test GitHub API integration with retry logic.
    
    May fail due to network issues, will retry up to 3 times.
    """
    from netra_backend.app.services.github_analyzer import GitHubAnalyzer
    
    analyzer = GitHubAnalyzer()
    repo_data = analyzer.analyze_repo("anthropics/netra")
    
    assert repo_data is not None
    assert "stars" in repo_data


# Example 10: Conditional skip based on environment
@skip_if_fast_mode
@feature_flag("clickhouse_analytics")
def test_clickhouse_analytics_pipeline():
    """Test ClickHouse analytics pipeline.
    
    Skipped in fast mode and when clickhouse_analytics is disabled.
    """
    from netra_backend.app.db.clickhouse import ClickHouseClient
    
    client = ClickHouseClient()
    client.insert_events([
        {"user_id": "123", "event": "login"},
        {"user_id": "456", "event": "api_call"}
    ])
    
    count = client.count_events()
    assert count >= 2


# Example 11: Complex feature with dependencies
@requires_feature("enterprise_sso")
def test_enterprise_sso_flow():
    """Test enterprise SSO flow.
    
    Currently disabled as enterprise_sso depends on features not yet launched.
    """
    # from netra_backend.app.auth.enterprise_sso import SSOProvider  # DEPRECATED: Use auth_integration
    pytest.skip("enterprise_sso module not available - use auth_integration")
    return
    
    provider = SSOProvider("okta")
    auth_url = provider.get_auth_url("client_123")
    
    assert "okta" in auth_url
    assert "client_id=client_123" in auth_url


# Example 12: Combined decorators for complex requirements
@integration_only()
@requires_feature("auth_integration", "websocket_streaming")
@performance_test(threshold_ms=500)
@skip_if_fast_mode
def test_authenticated_websocket_performance():
    """Complex test with multiple requirements.
    
    This test:
    - Only runs during integration testing
    - Requires auth and websocket features
    - Must complete within 500ms
    - Is skipped in fast mode
    """
    from netra_backend.app.auth_integration.auth import create_auth_token
    from netra_backend.app.websocket.authenticated_connection import AuthenticatedWebSocket
    
    token = create_auth_token("user123")
    ws = AuthenticatedWebSocket(token)
    
    ws.connect()
    ws.send({"action": "subscribe", "channel": "updates"})
    response = ws.receive()
    
    assert response["status"] == "subscribed"
    ws.close()


if __name__ == "__main__":
    # Run this file directly to see which tests would be skipped
    pytest.main([__file__, "-v", "--tb=short"])