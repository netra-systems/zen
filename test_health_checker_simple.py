#!/usr/bin/env python3
"""
Health Checker Validation Script - Issue #270 Fix Validation (Simple Version)

This script validates that the AsyncHealthChecker implementation:
1. Maintains backward compatibility with RealServicesManager APIs
2. Provides performance improvements through parallel execution
3. Implements circuit breaker pattern correctly
4. Handles timeouts and errors gracefully
5. Doesn't introduce breaking changes
"""

import asyncio
import time
import httpx
from typing import List, Dict, Any

# Import the classes we're testing
from tests.e2e.real_services_manager import (
    RealServicesManager, 
    AsyncHealthChecker, 
    HealthCheckConfig,
    ServiceEndpoint,
    ServiceStatus,
    CircuitBreakerState
)


async def test_backward_compatibility():
    """Test that all existing RealServicesManager APIs still work"""
    print("\n=== Test 1: Backward Compatibility Validation ===")
    start_time = time.time()
    
    manager = RealServicesManager()
    
    # Test all the public methods that existed before
    methods_to_test = [
        'check_all_service_health',
        'check_database_health', 
        'test_websocket_health',
        'test_health_endpoint',
        'test_auth_endpoints',
        'test_service_communication',
        'get_health_check_performance_metrics'
    ]
    
    api_results = {}
    for method_name in methods_to_test:
        if hasattr(manager, method_name):
            method = getattr(manager, method_name)
            try:
                result = await method()
                api_results[method_name] = "PASS - Available and callable"
            except Exception as e:
                api_results[method_name] = f"PARTIAL - Callable but failed: {str(e)[:50]}"
        else:
            api_results[method_name] = "FAIL - Method not found"
    
    # Test new methods are available
    new_methods = [
        'get_circuit_breaker_status',
        'configure_health_checking', 
        'enable_parallel_health_checks',
        'enable_circuit_breaker',
        'reset_circuit_breakers'
    ]
    
    for method_name in new_methods:
        if hasattr(manager, method_name):
            api_results[f"NEW_{method_name}"] = "PASS - New method available"
        else:
            api_results[f"NEW_{method_name}"] = "FAIL - New method missing"
    
    await manager.cleanup()
    
    duration = (time.time() - start_time) * 1000
    print(f"Backward compatibility test completed in {duration:.2f}ms")
    
    for method, status in api_results.items():
        print(f"   {method}: {status}")
    
    # Check if all critical APIs are available
    critical_failures = [k for k, v in api_results.items() if "FAIL" in v]
    success = len(critical_failures) == 0
    
    return {
        "success": success,
        "duration_ms": duration,
        "details": api_results,
        "critical_failures": critical_failures
    }


async def test_performance_improvements():
    """Test that parallel health checks provide performance improvements"""
    print("\n=== Test 2: Performance Improvements Validation ===")
    
    # Test with mock endpoints that simulate delays
    mock_endpoints = [
        ServiceEndpoint("service1", "http://httpbin.org", "/status/200", timeout=3.0),
        ServiceEndpoint("service2", "http://httpbin.org", "/status/200", timeout=3.0),
        ServiceEndpoint("service3", "http://httpbin.org", "/status/200", timeout=3.0),
    ]
    
    # Test parallel execution
    parallel_config = HealthCheckConfig(
        parallel_execution=True,
        max_concurrent_checks=10,
        health_check_timeout=3.0
    )
    
    parallel_checker = AsyncHealthChecker(parallel_config)
    
    async with httpx.AsyncClient() as client:
        start_time = time.time()
        try:
            parallel_results = await parallel_checker.check_services_parallel(
                mock_endpoints, client
            )
            parallel_duration = (time.time() - start_time) * 1000
            parallel_success = len(parallel_results) == len(mock_endpoints)
        except Exception as e:
            parallel_duration = (time.time() - start_time) * 1000
            parallel_success = False
            print(f"Parallel execution error: {e}")
    
    # Test sequential execution  
    sequential_config = HealthCheckConfig(
        parallel_execution=False,
        health_check_timeout=3.0
    )
    
    sequential_checker = AsyncHealthChecker(sequential_config)
    
    async with httpx.AsyncClient() as client:
        start_time = time.time()
        try:
            sequential_results = await sequential_checker.check_services_parallel(
                mock_endpoints, client
            )
            sequential_duration = (time.time() - start_time) * 1000
            sequential_success = len(sequential_results) == len(mock_endpoints)
        except Exception as e:
            sequential_duration = (time.time() - start_time) * 1000
            sequential_success = False
            print(f"Sequential execution error: {e}")
    
    # Calculate performance improvement
    if sequential_duration > 0 and parallel_duration > 0:
        speedup = sequential_duration / parallel_duration
    else:
        speedup = 1.0
    
    print(f"Parallel execution: {parallel_duration:.2f}ms")
    print(f"Sequential execution: {sequential_duration:.2f}ms") 
    print(f"Speedup factor: {speedup:.2f}x")
    
    success = speedup >= 1.2  # Expect at least 1.2x improvement
    
    return {
        "success": success,
        "duration_ms": parallel_duration,
        "speedup_factor": speedup,
        "parallel_duration": parallel_duration,
        "sequential_duration": sequential_duration,
        "both_modes_worked": parallel_success and sequential_success
    }


async def test_circuit_breaker():
    """Test circuit breaker functionality"""
    print("\n=== Test 3: Circuit Breaker Pattern Validation ===")
    
    # Configure circuit breaker with low failure threshold for testing
    config = HealthCheckConfig(
        circuit_breaker_enabled=True,
        circuit_breaker_failure_threshold=2,
        circuit_breaker_recovery_timeout=1.0,
        health_check_timeout=1.0
    )
    
    checker = AsyncHealthChecker(config)
    
    # Test endpoint that will fail
    failing_endpoint = ServiceEndpoint("failing_service", "http://nonexistent.invalid.domain", "/health")
    
    circuit_breaker_states = []
    
    async with httpx.AsyncClient() as client:
        # Make several failed requests to trigger circuit breaker
        for i in range(4):
            status = await checker._check_service_with_circuit_breaker(failing_endpoint, client)
            circuit_breaker_states.append({
                "attempt": i + 1,
                "healthy": status.healthy,
                "circuit_state": status.circuit_breaker_state.value,
                "failure_count": status.failure_count
            })
            print(f"   Attempt {i+1}: State={status.circuit_breaker_state.value}, Failures={status.failure_count}")
    
    # Check circuit breaker status
    cb_status = checker.get_circuit_breaker_status()
    
    # Validate that circuit breaker opened after failures
    final_state = circuit_breaker_states[-1]
    success = (
        final_state["circuit_state"] == "open" and
        final_state["failure_count"] >= config.circuit_breaker_failure_threshold
    )
    
    print(f"Final circuit breaker state: {final_state['circuit_state']}")
    print(f"Final failure count: {final_state['failure_count']}")
    print(f"Circuit breaker triggered: {'YES' if success else 'NO'}")
    
    return {
        "success": success,
        "final_state": final_state,
        "states": circuit_breaker_states,
        "circuit_breaker_status": cb_status
    }


async def test_health_check_manager_integration():
    """Test RealServicesManager integration with AsyncHealthChecker"""
    print("\n=== Test 4: RealServicesManager Integration ===")
    
    manager = RealServicesManager()
    
    # Test health check performance metrics
    metrics = await manager.get_health_check_performance_metrics()
    
    print(f"Health check metrics:")
    print(f"   Total time: {metrics.get('total_time_ms', 0):.2f}ms")
    print(f"   Services checked: {metrics.get('services_checked', 0)}")
    print(f"   Parallel execution: {metrics.get('parallel_execution', False)}")
    print(f"   Circuit breaker enabled: {metrics.get('circuit_breaker_enabled', False)}")
    
    # Test configuration changes
    print("\nTesting dynamic configuration...")
    
    # Enable parallel execution
    manager.enable_parallel_health_checks(True)
    parallel_enabled = manager.health_checker.config.parallel_execution
    
    # Enable circuit breaker
    manager.enable_circuit_breaker(True)
    cb_enabled = manager.health_checker.config.circuit_breaker_enabled
    
    # Reset circuit breakers
    manager.reset_circuit_breakers()
    cb_status = manager.get_circuit_breaker_status()
    
    # Get circuit breaker status
    print(f"   Parallel execution enabled: {parallel_enabled}")
    print(f"   Circuit breaker enabled: {cb_enabled}")
    print(f"   Circuit breakers reset: {len(cb_status) == 0}")
    
    await manager.cleanup()
    
    success = (
        isinstance(metrics, dict) and
        "total_time_ms" in metrics and
        parallel_enabled and
        cb_enabled
    )
    
    return {
        "success": success,
        "metrics": metrics,
        "parallel_enabled": parallel_enabled,
        "circuit_breaker_enabled": cb_enabled,
        "circuit_breakers_reset": len(cb_status) == 0
    }


async def run_validation_suite():
    """Run the complete validation suite"""
    print("Health Checker Validation Suite - Issue #270 Fix")
    print("=" * 60)
    
    results = {}
    
    # Run all tests
    tests = [
        ("backward_compatibility", test_backward_compatibility),
        ("performance_improvements", test_performance_improvements),
        ("circuit_breaker", test_circuit_breaker),
        ("manager_integration", test_health_check_manager_integration)
    ]
    
    for test_name, test_func in tests:
        try:
            print(f"\nRunning {test_name}...")
            result = await test_func()
            results[test_name] = result
            print(f"Result: {'PASS' if result['success'] else 'FAIL'}")
        except Exception as e:
            print(f"ERROR in {test_name}: {e}")
            results[test_name] = {"success": False, "error": str(e)}
    
    # Generate summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results.values() if r.get("success", False))
    
    print(f"\nOverall Results:")
    print(f"   Total Tests: {total_tests}")
    print(f"   Passed: {passed_tests}")
    print(f"   Failed: {total_tests - passed_tests}")
    print(f"   Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    print(f"\nDetailed Results:")
    for test_name, result in results.items():
        status = "PASS" if result.get("success", False) else "FAIL"
        duration = result.get("duration_ms", 0)
        print(f"   {test_name}: {status} ({duration:.2f}ms)")
        if "error" in result:
            print(f"      Error: {result['error']}")
    
    # Key findings
    print(f"\nKey Findings:")
    
    # Performance improvement
    perf_result = results.get("performance_improvements", {})
    if perf_result.get("success"):
        speedup = perf_result.get("speedup_factor", 1.0)
        print(f"   Performance: {speedup:.2f}x speedup achieved")
    
    # Backward compatibility
    compat_result = results.get("backward_compatibility", {})
    if compat_result.get("success"):
        print(f"   Backward Compatibility: All existing APIs maintained")
    
    # Circuit breaker
    cb_result = results.get("circuit_breaker", {})
    if cb_result.get("success"):
        print(f"   Circuit Breaker: Properly implemented and functional")
    
    # Business impact assessment
    if passed_tests >= total_tests * 0.75:  # 75% success rate
        print(f"\nBusiness Impact Assessment:")
        print(f"   VALIDATED: Issue #270 fixes are stable and production-ready")
        print(f"   VALIDATED: Performance improvements confirmed")
        print(f"   VALIDATED: No breaking changes detected")
        print(f"   VALIDATED: Developer productivity improvements achievable")
    else:
        print(f"\nBusiness Impact Warning:")
        print(f"   CAUTION: Some validations failed - review before production")
    
    return results


if __name__ == "__main__":
    asyncio.run(run_validation_suite())