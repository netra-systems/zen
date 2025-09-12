#!/usr/bin/env python3
"""
Direct validation script for Issue #270 - AsyncHealthChecker implementation.

This script directly tests the core functionality without pytest overhead,
providing immediate feedback on the Issue #270 implementation.
"""

import asyncio
import time
import sys
import os
from unittest.mock import Mock, AsyncMock

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Import the classes under test
from tests.e2e.real_services_manager import (
    AsyncHealthChecker, 
    HealthCheckConfig,
    CircuitBreakerState,
    ServiceEndpoint,
    RealServicesManager
)


async def test_async_health_checker_initialization():
    """Test AsyncHealthChecker initialization."""
    print("[TEST] Testing AsyncHealthChecker initialization...")
    
    config = HealthCheckConfig(
        parallel_execution=True,
        circuit_breaker_enabled=True,
        max_concurrent_checks=5
    )
    
    checker = AsyncHealthChecker(config)
    
    assert checker.config == config, "Configuration not set correctly"
    assert checker.config.parallel_execution == True, "Parallel execution not enabled"
    assert checker.config.circuit_breaker_enabled == True, "Circuit breaker not enabled"
    assert len(checker.circuit_breaker_states) == 0, "Circuit breaker states not empty"
    
    print("[PASS] AsyncHealthChecker initialization PASSED")
    return True


async def test_performance_improvement():
    """Test performance improvement from parallel execution."""
    print("[TEST] Testing performance improvement (parallel vs sequential)...")
    
    # Create parallel and sequential checkers
    parallel_config = HealthCheckConfig(parallel_execution=True, retry_attempts=0)
    sequential_config = HealthCheckConfig(parallel_execution=False, retry_attempts=0)
    
    parallel_checker = AsyncHealthChecker(parallel_config)
    sequential_checker = AsyncHealthChecker(sequential_config)
    
    # Mock HTTP client with delay
    async def mock_get_with_delay(*args, **kwargs):
        await asyncio.sleep(0.1)  # 100ms delay
        mock_response = Mock()
        mock_response.status_code = 200
        return mock_response
    
    mock_http_client = AsyncMock()
    mock_http_client.get = mock_get_with_delay
    
    # Test endpoints
    endpoints = [
        ServiceEndpoint(f"service{i}", f"http://localhost:800{i}", "/health")
        for i in range(3)
    ]
    
    # Measure parallel execution time
    start_time = time.time()
    await parallel_checker.check_services_parallel(endpoints, mock_http_client)
    parallel_time = (time.time() - start_time) * 1000
    
    # Measure sequential execution time
    start_time = time.time()
    await sequential_checker.check_services_parallel(endpoints, mock_http_client)
    sequential_time = (time.time() - start_time) * 1000
    
    # Calculate improvement
    improvement = sequential_time / parallel_time
    
    print(f"   Parallel time: {parallel_time:.2f}ms")
    print(f"   Sequential time: {sequential_time:.2f}ms")
    print(f"   Improvement: {improvement:.2f}x")
    
    assert improvement >= 1.2, f"Performance improvement {improvement:.2f}x below target 1.2x"
    
    print(f"[PASS] Performance improvement PASSED (target: >=1.2x, actual: {improvement:.2f}x)")
    return True


async def test_circuit_breaker_functionality():
    """Test circuit breaker state transitions."""
    print("[TEST] Testing circuit breaker functionality...")
    
    config = HealthCheckConfig(
        circuit_breaker_enabled=True,
        circuit_breaker_failure_threshold=2,
        retry_attempts=0
    )
    
    checker = AsyncHealthChecker(config)
    
    # Mock failing HTTP client
    mock_http_client = AsyncMock()
    mock_http_client.get = AsyncMock(side_effect=Exception("Connection failed"))
    
    failing_endpoint = ServiceEndpoint("failing_service", "http://invalid", "/health")
    
    # Test multiple failures to trigger circuit breaker
    results = []
    for i in range(4):
        result = await checker._check_service_with_circuit_breaker(failing_endpoint, mock_http_client)
        results.append(result)
        print(f"   Attempt {i+1}: State={result.circuit_breaker_state.value}, Failures={result.failure_count}")
    
    # Validate circuit breaker opened
    final_result = results[-1]
    assert final_result.circuit_breaker_state == CircuitBreakerState.OPEN, "Circuit breaker not opened"
    
    # Get circuit breaker status
    status = checker.get_circuit_breaker_status()
    assert "failing_service" in status, "Service not in circuit breaker status"
    assert status["failing_service"]["state"] == "open", "Circuit breaker state not open"
    
    print("[PASS] Circuit breaker functionality PASSED")
    return True


def test_real_services_manager_api_compatibility():
    """Test RealServicesManager API compatibility."""
    print("[TEST] Testing RealServicesManager API compatibility...")
    
    manager = RealServicesManager()
    
    # Test existing APIs are available
    existing_apis = [
        'check_all_service_health',
        'check_database_health',
        'test_websocket_health', 
        'test_health_endpoint',
        'test_auth_endpoints',
        'test_service_communication',
        'get_health_check_performance_metrics'
    ]
    
    for api in existing_apis:
        assert hasattr(manager, api), f"Missing API: {api}"
        assert callable(getattr(manager, api)), f"API not callable: {api}"
    
    # Test new APIs are available
    new_apis = [
        'get_circuit_breaker_status',
        'configure_health_checking',
        'enable_parallel_health_checks',
        'enable_circuit_breaker',
        'reset_circuit_breakers'
    ]
    
    for api in new_apis:
        assert hasattr(manager, api), f"Missing new API: {api}"
        assert callable(getattr(manager, api)), f"New API not callable: {api}"
    
    print(f"[PASS] API compatibility PASSED ({len(existing_apis)} existing + {len(new_apis)} new APIs)")
    return True


def test_configuration_management():
    """Test dynamic configuration changes."""
    print("[TEST] Testing configuration management...")
    
    manager = RealServicesManager()
    
    # Test enable/disable parallel execution
    manager.enable_parallel_health_checks(True)
    assert manager.health_checker.config.parallel_execution == True
    
    manager.enable_parallel_health_checks(False)
    assert manager.health_checker.config.parallel_execution == False
    
    # Test enable/disable circuit breaker
    manager.enable_circuit_breaker(True)
    assert manager.health_checker.config.circuit_breaker_enabled == True
    
    manager.enable_circuit_breaker(False)
    assert manager.health_checker.config.circuit_breaker_enabled == False
    
    # Test circuit breaker reset
    manager.health_checker.circuit_breaker_states["test"] = CircuitBreakerState.OPEN
    manager.health_checker.failure_counts["test"] = 5
    manager.reset_circuit_breakers()
    
    assert len(manager.health_checker.circuit_breaker_states) == 0
    assert len(manager.health_checker.failure_counts) == 0
    
    print("[PASS] Configuration management PASSED")
    return True


async def main():
    """Run all validation tests."""
    print("=" * 80)
    print("ISSUE #270 - ASYNC HEALTH CHECKER VALIDATION")
    print("=" * 80)
    print()
    
    test_results = []
    
    try:
        # Unit tests
        result = await test_async_health_checker_initialization()
        test_results.append(("AsyncHealthChecker Initialization", result))
        
        result = await test_performance_improvement()
        test_results.append(("Performance Improvement", result))
        
        result = await test_circuit_breaker_functionality()
        test_results.append(("Circuit Breaker Functionality", result))
        
        # Integration tests
        result = test_real_services_manager_api_compatibility()
        test_results.append(("API Compatibility", result))
        
        result = test_configuration_management()
        test_results.append(("Configuration Management", result))
        
    except Exception as e:
        print(f"[FAIL] Test execution failed: {e}")
        return False
    
    # Summary
    print()
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{test_name:40} {status}")
        if result:
            passed += 1
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("[SUCCESS] ALL TESTS PASSED - Issue #270 implementation validated!")
        print()
        print("Business Value Validation:")
        print("[PASS] Performance improvements confirmed (>=1.2x speedup)")
        print("[PASS] Circuit breaker pattern implemented")
        print("[PASS] Zero breaking changes - all existing APIs preserved")
        print("[PASS] New capabilities added successfully")
        return True
    else:
        print(f"[FAIL] {total - passed} tests failed - Issue #270 needs attention")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)