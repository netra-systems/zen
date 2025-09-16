"""
Error recovery pattern validation tests.

Tests critical error recovery patterns across service boundaries to prevent
error propagation that causes user session failures and revenue loss.
"""
import pytest
import asyncio
from shared.isolated_environment import IsolatedEnvironment

from tests.e2e.helpers.core.service_independence_helpers import ServiceCommunicator
from tests.e2e.helpers.resilience import ErrorPropagationTester


@pytest.mark.critical
@pytest.mark.e2e
async def test_service_error_isolation_prevents_cascade():
    """Test errors in one service don't cascade to other services."""
    communicator = ServiceCommunicator()
    
    # Simulate error in auth service
    with patch('tests.e2e.helpers.auth.auth_service_helpers.validate_token') as mock_auth:
        mock_auth.side_effect = Exception("Auth service error")
        
        # Backend should handle auth error gracefully
        result = await communicator.call_backend_with_auth("test_operation")
        
        assert result.status == "degraded", "Must handle auth failure gracefully"
        assert "auth_unavailable" in result.flags, "Must flag auth unavailability"


@pytest.mark.critical
@pytest.mark.e2e
async def test_circuit_breaker_prevents_repeated_failures():
    """Test circuit breaker prevents repeated calls to failing services."""
    error_tester = ErrorPropagationTester()
    
    # Simulate service failures to trip circuit breaker
    for i in range(5):
        with pytest.raises(Exception):
            await error_tester.call_failing_service("unreliable_service")
    
    # Circuit breaker should be open
    circuit_state = await error_tester.get_circuit_state("unreliable_service")
    assert circuit_state == "OPEN", "Circuit breaker must open after failures"
    
    # Subsequent calls should fail fast
    start_time = asyncio.get_event_loop().time()
    with pytest.raises(Exception, match="Circuit breaker"):
        await error_tester.call_failing_service("unreliable_service")
    
    elapsed = asyncio.get_event_loop().time() - start_time
    assert elapsed < 0.1, "Circuit breaker must fail fast"


@pytest.mark.critical
@pytest.mark.e2e
async def test_error_recovery_with_exponential_backoff():
    """Test error recovery uses exponential backoff for retries."""
    error_tester = ErrorPropagationTester()
    
    retry_times = []
    
    def track_retry_time():
        retry_times.append(asyncio.get_event_loop().time())
        if len(retry_times) < 3:
            raise Exception("Service still failing")
        return {"status": "success"}
    
    with patch('tests.e2e.helpers.resilience.call_service_endpoint') as mock_call:
        mock_call.side_effect = track_retry_time
        
        # Call with retry policy
        result = await error_tester.call_with_exponential_backoff("retry_service")
        
        assert result["status"] == "success", "Must eventually succeed"
        assert len(retry_times) == 3, "Must retry correct number of times"
        
        # Verify exponential backoff timing
        if len(retry_times) >= 3:
            interval1 = retry_times[1] - retry_times[0]
            interval2 = retry_times[2] - retry_times[1]
            assert interval2 > interval1 * 1.5, "Must use exponential backoff"


@pytest.mark.critical
@pytest.mark.e2e
async def test_error_context_preservation_across_services():
    """Test error context is preserved when errors cross service boundaries."""
    error_tester = ErrorPropagationTester()
    
    # Simulate error with context in backend
    original_error = Exception("Database connection failed")
    original_error.context = {"user_id": "user123", "operation": "fetch_data"}
    
    with patch('tests.e2e.helpers.core.service_independence_helpers.backend_operation') as mock_op:
        mock_op.side_effect = original_error
        
        # Call through frontend -> backend chain
        try:
            await error_tester.call_cross_service_operation("complex_operation")
        except Exception as e:
            # Error context should be preserved
            assert hasattr(e, 'context'), "Error context must be preserved"
            assert e.context["user_id"] == "user123", "User context must be preserved"
            assert e.context["operation"] == "fetch_data", "Operation context must be preserved"
