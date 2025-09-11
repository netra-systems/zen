"""
Auth Service Circuit Breaker Test - Test #5

BVJ (Business Value Justification):
1. Segment: ALL customer segments (Enterprise critical)
2. Business Goal: Availability - Prevent 100% system downtime during auth service failures  
3. Value Impact: System degrades gracefully when auth service fails
4. Revenue Impact: Protects $150K+ MRR by maintaining core functionality when auth is down

CRITICAL P0 TEST: Validates circuit breaker prevents cascading auth service failures
- Circuit breaker opens after 5 auth service failures
- Fallback authentication mechanism activates  
- Circuit breaker closes after timeout expires
- Cached tokens still work when auth service is down
- Test must complete in <10 seconds

Without this, 100% system downtime occurs when auth has issues.
"""

import asyncio
import logging
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path for imports
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import pytest


from netra_backend.app.clients.auth_client_cache import (
    AuthCircuitBreakerManager,
    AuthTokenCache,
    CachedToken,
)
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from netra_backend.app.core.circuit_breaker import CircuitBreaker
from netra_backend.app.core.circuit_breaker_types import (
    CircuitBreakerOpenError,
    CircuitConfig,
    CircuitState,
)

logger = logging.getLogger(__name__)

# Test configuration constants
TEST_TIMEOUT = 10  # seconds - must complete within 10 seconds
CIRCUIT_FAILURE_THRESHOLD = 5
CIRCUIT_RECOVERY_TIMEOUT = 60
CACHE_TTL_SECONDS = 300


class TestAuthCircuitBreakerer:
    """Comprehensive auth circuit breaker test orchestrator."""
    
    def __init__(self):
        self.test_start_time = time.time()
        self.circuit_breaker = self._create_test_circuit_breaker()
        self.auth_client = AuthServiceClient()
        self.token_cache = AuthTokenCache(CACHE_TTL_SECONDS)
        self.test_token = "test_token_12345"
        self.test_results = {}

    def _create_test_circuit_breaker(self) -> CircuitBreaker:
        """Create circuit breaker for testing."""
        config = CircuitConfig(
            name="test_auth_service",
            failure_threshold=CIRCUIT_FAILURE_THRESHOLD,
            recovery_timeout=CIRCUIT_RECOVERY_TIMEOUT,
            timeout_seconds=30
        )
        return CircuitBreaker(config)

    @pytest.mark.e2e
    async def test_circuit_breaker_opens_after_failures(self) -> Dict[str, Any]:
        """Test circuit breaker opens after 5 consecutive failures."""
        results = {"passed": False, "failures_to_open": 0, "final_state": None}
        
        try:
            # Simulate exactly 5 failures to trigger circuit breaker
            for i in range(CIRCUIT_FAILURE_THRESHOLD):
                self.circuit_breaker.record_failure("ConnectionError")
                results["failures_to_open"] = i + 1
                
                if self.circuit_breaker.state == CircuitState.OPEN:
                    break
            
            results["final_state"] = self.circuit_breaker.state.value
            results["passed"] = (
                self.circuit_breaker.state == CircuitState.OPEN and
                results["failures_to_open"] == CIRCUIT_FAILURE_THRESHOLD
            )
            
        except Exception as e:
            results["error"] = str(e)
            
        return results

    @pytest.mark.e2e
    async def test_fallback_authentication_activates(self) -> Dict[str, Any]:
        """Test fallback auth mechanism when circuit is open."""
        results = {"passed": False, "fallback_used": False, "token_valid": False}
        
        try:
            # Force circuit breaker to OPEN state
            for _ in range(CIRCUIT_FAILURE_THRESHOLD):
                self.circuit_breaker.record_failure("ServiceUnavailable")
            
            # Mock auth service to always fail
            with patch.object(self.auth_client, '_validate_token_remote', 
                            side_effect=httpx.ConnectError("Auth service unavailable")):
                
                # Attempt token validation - should use fallback
                validation_result = await self.auth_client.validate_token_jwt(self.test_token)
                
                results["fallback_used"] = validation_result is not None
                results["token_valid"] = validation_result.get("valid", False) if validation_result else False
                results["passed"] = results["fallback_used"] and results["token_valid"]
                
        except Exception as e:
            results["error"] = str(e)
            
        return results

    @pytest.mark.e2e
    async def test_circuit_breaker_closes_after_timeout(self) -> Dict[str, Any]:
        """Test circuit breaker transitions to half-open after timeout."""
        results = {"passed": False, "initial_state": None, "final_state": None, "timeout_works": False}
        
        try:
            # Open the circuit breaker
            for _ in range(CIRCUIT_FAILURE_THRESHOLD):
                self.circuit_breaker.record_failure("TimeoutError")
            
            results["initial_state"] = self.circuit_breaker.state.value
            
            # Simulate timeout passage by manipulating last failure time
            self.circuit_breaker._last_failure_time = time.time() - (CIRCUIT_RECOVERY_TIMEOUT + 1)
            
            # Check if circuit allows execution (should transition to half-open)
            can_execute = self.circuit_breaker.can_execute()
            results["timeout_works"] = can_execute
            results["final_state"] = self.circuit_breaker.state.value
            
            results["passed"] = (
                results["initial_state"] == "open" and
                results["final_state"] == "half_open" and
                results["timeout_works"]
            )
            
        except Exception as e:
            results["error"] = str(e)
            
        return results

    @pytest.mark.e2e
    async def test_cached_tokens_work_when_auth_down(self) -> Dict[str, Any]:
        """Test cached tokens are served when auth service is unavailable."""
        results = {"passed": False, "token_cached": False, "cache_hit": False, "auth_bypassed": False}
        
        try:
            # Pre-populate the auth client's own cache with valid token
            cached_data = {
                "valid": True,
                "user_id": "cached_user_123",
                "email": "cached@example.com", 
                "permissions": ["user"]
            }
            self.auth_client.token_cache.cache_token(self.test_token, cached_data)
            results["token_cached"] = True
            
            # Verify token is in cache
            cached_result = self.auth_client.token_cache.get_cached_token(self.test_token)
            results["cache_hit"] = cached_result is not None
            
            # Ensure auth service is enabled for this test
            with patch.object(self.auth_client.settings, 'enabled', True):
                # Mock auth service failure
                with patch.object(self.auth_client, '_validate_token_remote',
                                side_effect=httpx.ConnectError("Service down")):
                    
                    # Token validation should use cache, not hit auth service
                    validation_result = await self.auth_client.validate_token_jwt(self.test_token)
                    
                    results["auth_bypassed"] = (
                        validation_result is not None and 
                        validation_result.get("user_id") == "cached_user_123"
                    )
            
            results["passed"] = (
                results["token_cached"] and 
                results["cache_hit"] and 
                results["auth_bypassed"]
            )
            
        except Exception as e:
            results["error"] = str(e)
            
        return results

    @pytest.mark.e2e
    async def test_performance_within_limits(self) -> Dict[str, Any]:
        """Test all operations complete within performance limits."""
        results = {"passed": False, "elapsed_time": 0, "within_limit": False}
        
        try:
            elapsed = time.time() - self.test_start_time
            results["elapsed_time"] = round(elapsed, 2)
            results["within_limit"] = elapsed < TEST_TIMEOUT
            results["passed"] = results["within_limit"]
            
        except Exception as e:
            results["error"] = str(e)
            
        return results

    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """Execute all circuit breaker tests in sequence."""
        test_results = {
            "success": False,
            "test_summary": {},
            "individual_tests": {},
            "errors": []
        }
        
        try:
            # Test 1: Circuit breaker opens after failures
            test_results["individual_tests"]["circuit_opens"] = await self.test_circuit_breaker_opens_after_failures()
            
            # Test 2: Fallback authentication activates
            test_results["individual_tests"]["fallback_auth"] = await self.test_fallback_authentication_activates()
            
            # Test 3: Circuit breaker closes after timeout
            test_results["individual_tests"]["circuit_closes"] = await self.test_circuit_breaker_closes_after_timeout()
            
            # Test 4: Cached tokens work when auth is down
            test_results["individual_tests"]["cached_tokens"] = await self.test_cached_tokens_work_when_auth_down()
            
            # Test 5: Performance within limits
            test_results["individual_tests"]["performance"] = await self.test_performance_within_limits()
            
            # Evaluate overall success
            all_passed = all(
                test.get("passed", False) 
                for test in test_results["individual_tests"].values()
            )
            test_results["success"] = all_passed
            
            # Generate test summary
            test_results["test_summary"] = self._generate_test_summary(test_results["individual_tests"])
            
        except Exception as e:
            test_results["errors"].append(f"Test execution error: {str(e)}")
            test_results["success"] = False
            
        return test_results

    def _generate_test_summary(self, individual_tests: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of test results."""
        total_tests = len(individual_tests)
        passed_tests = sum(1 for test in individual_tests.values() if test.get("passed", False))
        
        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": round((passed_tests / total_tests) * 100, 2) if total_tests > 0 else 0,
            "elapsed_time": round(time.time() - self.test_start_time, 2)
        }


# PYTEST TEST IMPLEMENTATIONS

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_auth_circuit_breaker_comprehensive():
    """
    Test #5: Auth Service Circuit Breaker Comprehensive Test
    
    BVJ: Availability - Prevents 100% system downtime during auth service failures
    - Tests circuit breaker opens after 5 failures
    - Tests fallback authentication mechanism
    - Tests circuit breaker recovery after timeout
    - Tests cached tokens work when auth is down
    - Must complete in <10 seconds
    """
    tester = TestAuthCircuitBreakerer()
    
    results = await _execute_circuit_breaker_tests(tester)
    _validate_circuit_breaker_results(results)
    _print_circuit_breaker_success(results)


async def _execute_circuit_breaker_tests(tester: TestAuthCircuitBreakerer) -> Dict[str, Any]:
    """Execute comprehensive circuit breaker validation."""
    return await tester.run_comprehensive_test()


def _validate_circuit_breaker_results(results: Dict[str, Any]) -> None:
    """Validate circuit breaker test results."""
    assert results["success"], f"Circuit breaker tests failed: {results.get('errors', [])}"
    
    # Validate individual test requirements
    individual_tests = results["individual_tests"]
    
    # Circuit breaker must open after exactly 5 failures
    circuit_opens = individual_tests.get("circuit_opens", {})
    assert circuit_opens.get("passed", False), f"Circuit breaker opening failed: {circuit_opens}"
    assert circuit_opens.get("failures_to_open") == CIRCUIT_FAILURE_THRESHOLD, "Circuit breaker threshold incorrect"
    
    # Fallback authentication must activate
    fallback_auth = individual_tests.get("fallback_auth", {})
    assert fallback_auth.get("passed", False), f"Fallback authentication failed: {fallback_auth}"
    assert fallback_auth.get("fallback_used"), "Fallback authentication not used"
    
    # Circuit breaker must close after timeout
    circuit_closes = individual_tests.get("circuit_closes", {})
    assert circuit_closes.get("passed", False), f"Circuit breaker recovery failed: {circuit_closes}"
    assert circuit_closes.get("timeout_works"), "Circuit breaker timeout not working"
    
    # Cached tokens must work when auth is down
    cached_tokens = individual_tests.get("cached_tokens", {})
    assert cached_tokens.get("passed", False), f"Cached token mechanism failed: {cached_tokens}"
    assert cached_tokens.get("auth_bypassed"), "Auth service not bypassed with cache"
    
    # Performance must be within limits
    performance = individual_tests.get("performance", {})
    assert performance.get("passed", False), f"Performance test failed: {performance}"
    
    # Overall success rate must be 100%
    summary = results["test_summary"]
    assert summary["success_rate"] == 100.0, f"Success rate {summary['success_rate']}% < 100%"
    assert summary["elapsed_time"] < TEST_TIMEOUT, f"Test took {summary['elapsed_time']}s > {TEST_TIMEOUT}s limit"


def _print_circuit_breaker_success(results: Dict[str, Any]) -> None:
    """Print circuit breaker test success message."""
    summary = results["test_summary"]
    print(f"[SUCCESS] Auth Circuit Breaker: {summary['passed_tests']}/{summary['total_tests']} tests passed")
    print(f"[PROTECTED] System availability maintained during auth service failures")
    print(f"[PERFORMANCE] Completed in {summary['elapsed_time']}s (< {TEST_TIMEOUT}s limit)")
    
    # Print detailed results
    for test_name, test_result in results["individual_tests"].items():
        status = "PASS" if test_result.get("passed", False) else "FAIL"
        print(f"  [{status}] {test_name}")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_circuit_breaker_failure_threshold():
    """
    Test circuit breaker opens after exactly 5 failures.
    
    BVJ: Circuit breaker prevents cascading failures by opening after threshold
    """
    tester = TestAuthCircuitBreakerer()
    results = await tester.test_circuit_breaker_opens_after_failures()
    
    assert results.get("passed", False), f"Circuit breaker threshold test failed: {results}"
    assert results.get("failures_to_open") == CIRCUIT_FAILURE_THRESHOLD, "Wrong failure threshold"
    assert results.get("final_state") == "open", "Circuit breaker not in open state"
    
    print(f"[SUCCESS] Circuit Breaker Threshold: Opens after {CIRCUIT_FAILURE_THRESHOLD} failures")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_fallback_authentication_mechanism():
    """
    Test fallback authentication activates when circuit is open.
    
    BVJ: Fallback auth ensures system remains functional when auth service fails
    """
    tester = TestAuthCircuitBreakerer()
    results = await tester.test_fallback_authentication_activates()
    
    assert results.get("passed", False), f"Fallback authentication test failed: {results}"
    assert results.get("fallback_used"), "Fallback authentication not activated"
    assert results.get("token_valid"), "Fallback token validation failed"
    
    print("[SUCCESS] Fallback Authentication: Activates when auth service unavailable")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_cached_tokens_during_outage():
    """
    Test cached tokens work when auth service is down.
    
    BVJ: Token caching maintains user sessions during auth service outages
    """
    tester = TestAuthCircuitBreakerer()
    results = await tester.test_cached_tokens_work_when_auth_down()
    
    assert results.get("passed", False), f"Cached token test failed: {results}"
    assert results.get("cache_hit"), "Token not found in cache"
    assert results.get("auth_bypassed"), "Auth service not bypassed with cache"
    
    print("[SUCCESS] Cached Tokens: Work during auth service outages")


if __name__ == "__main__":
    # Run tests directly for development
    asyncio.run(test_auth_circuit_breaker_comprehensive())