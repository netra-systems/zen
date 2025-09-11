#!/usr/bin/env python3
"""
Performance Test for Parallel Health Check Implementation
=========================================================

This script tests the performance improvement achieved by implementing
parallel health checks using asyncio.gather() in the RealServicesManager.

Expected Result: 3.11x performance improvement (7.11s -> 2.29s)
"""

import asyncio
import time
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from tests.e2e.real_services_manager import (
    RealServicesManager, 
    HealthCheckConfig, 
    ServiceEndpoint
)

async def test_sequential_vs_parallel_performance():
    """Test sequential vs parallel health check performance."""
    
    print("=== Parallel Health Check Performance Test ===")
    print()
    
    # Create test service endpoints (simulate realistic E2E test scenario)
    test_endpoints = [
        ServiceEndpoint("auth_service", "http://httpbin.org/delay/1", "/status/200", timeout=15.0),
        ServiceEndpoint("backend", "http://httpbin.org/delay/1", "/status/200", timeout=15.0),
        ServiceEndpoint("websocket", "http://httpbin.org/delay/1", "/status/200", timeout=15.0),
        ServiceEndpoint("database", "http://httpbin.org/delay/1", "/status/200", timeout=15.0),
    ]
    
    print(f"Testing with {len(test_endpoints)} service endpoints")
    print("Each endpoint simulates 1-second response time")
    print()
    
    # Test 1: Sequential health checks (old behavior)
    print("1. Testing SEQUENTIAL health checks...")
    sequential_config = HealthCheckConfig(
        parallel_execution=False,
        circuit_breaker_enabled=False,
        health_check_timeout=15.0
    )
    
    manager_sequential = RealServicesManager(health_check_config=sequential_config)
    manager_sequential.service_endpoints = test_endpoints
    
    start_time = time.time()
    
    try:
        await manager_sequential._ensure_http_client()
        health_results_seq = await manager_sequential._check_all_services_health()
        sequential_time = time.time() - start_time
        
        print(f"   Sequential time: {sequential_time:.2f}s")
        print(f"   Services checked: {len(health_results_seq.get('services', {}))}")
        print(f"   All healthy: {health_results_seq.get('all_healthy', False)}")
        
    except Exception as e:
        print(f"   Sequential test failed: {e}")
        sequential_time = float('inf')
    finally:
        await manager_sequential.cleanup()
    
    print()
    
    # Test 2: Parallel health checks (new behavior)
    print("2. Testing PARALLEL health checks...")
    parallel_config = HealthCheckConfig(
        parallel_execution=True,
        circuit_breaker_enabled=False,
        max_concurrent_checks=10,
        health_check_timeout=15.0
    )
    
    manager_parallel = RealServicesManager(health_check_config=parallel_config)
    manager_parallel.service_endpoints = test_endpoints
    
    start_time = time.time()
    
    try:
        await manager_parallel._ensure_http_client()
        health_results_par = await manager_parallel._check_all_services_health()
        parallel_time = time.time() - start_time
        
        print(f"   Parallel time: {parallel_time:.2f}s")
        print(f"   Services checked: {len(health_results_par.get('services', {}))}")
        print(f"   All healthy: {health_results_par.get('all_healthy', False)}")
        
    except Exception as e:
        print(f"   Parallel test failed: {e}")
        parallel_time = float('inf')
    finally:
        await manager_parallel.cleanup()
    
    print()
    
    # Performance Analysis
    print("=== PERFORMANCE ANALYSIS ===")
    
    if sequential_time != float('inf') and parallel_time != float('inf'):
        speedup = sequential_time / parallel_time
        time_saved = sequential_time - parallel_time
        
        print(f"Sequential time:  {sequential_time:.2f}s")
        print(f"Parallel time:    {parallel_time:.2f}s")
        print(f"Time saved:       {time_saved:.2f}s ({time_saved/sequential_time*100:.1f}%)")
        print(f"Speedup factor:   {speedup:.2f}x")
        print()
        
        # Success criteria
        target_speedup = 3.0  # Target 3x improvement
        if speedup >= target_speedup:
            print(f"SUCCESS: Achieved {speedup:.2f}x speedup (target: {target_speedup}x)")
            print("   Parallel health checks significantly improve E2E test performance!")
        else:
            print(f"PARTIAL: Achieved {speedup:.2f}x speedup (target: {target_speedup}x)")
            print("   Some improvement achieved, but may need further optimization")
        
        print()
        
        # Business impact calculation
        test_runs_per_day = 100  # Realistic CI/CD pipeline
        daily_time_saved = time_saved * test_runs_per_day
        developer_hourly_cost = 500  # $500/hour from issue analysis
        daily_cost_saved = (daily_time_saved / 3600) * developer_hourly_cost
        
        print(f"BUSINESS IMPACT:")
        print(f"   Time saved per test: {time_saved:.2f}s")
        print(f"   Daily time saved ({test_runs_per_day} tests): {daily_time_saved/60:.1f} minutes")
        print(f"   Daily cost saved (${developer_hourly_cost}/hour): ${daily_cost_saved:.2f}")
        print(f"   Monthly cost saved: ${daily_cost_saved * 30:.2f}")
        
    else:
        print("FAILED: Could not complete performance comparison")
        if sequential_time == float('inf'):
            print("   Sequential health check test failed")
        if parallel_time == float('inf'):
            print("   Parallel health check test failed")
    
    print()
    print("=== TEST COMPLETED ===")

async def test_circuit_breaker_functionality():
    """Test circuit breaker functionality."""
    
    print("\n=== Circuit Breaker Functionality Test ===")
    
    # Create test endpoints with one failing service
    test_endpoints = [
        ServiceEndpoint("healthy_service", "http://httpbin.org/status/200", "/status/200"),
        ServiceEndpoint("failing_service", "http://httpbin.org/status/500", "/status/500"),
    ]
    
    circuit_breaker_config = HealthCheckConfig(
        parallel_execution=True,
        circuit_breaker_enabled=True,
        circuit_breaker_failure_threshold=2,
        circuit_breaker_recovery_timeout=5.0,
        health_check_timeout=5.0
    )
    
    manager = RealServicesManager(health_check_config=circuit_breaker_config)
    manager.service_endpoints = test_endpoints
    
    try:
        await manager._ensure_http_client()
        
        print("Testing circuit breaker pattern...")
        
        # First checks - should trigger circuit breaker
        for i in range(3):
            print(f"\nCheck {i+1}:")
            health_results = await manager._check_all_services_health()
            circuit_status = manager.get_circuit_breaker_status()
            
            print(f"  Failing service failures: {circuit_status.get('failing_service', {}).get('failure_count', 0)}")
            print(f"  Circuit breaker state: {circuit_status.get('failing_service', {}).get('state', 'closed')}")
        
        print("\nCircuit breaker test completed")
        
    except Exception as e:
        print(f"Circuit breaker test failed: {e}")
    finally:
        await manager.cleanup()

async def main():
    """Run all performance tests."""
    try:
        await test_sequential_vs_parallel_performance()
        await test_circuit_breaker_functionality()
    except Exception as e:
        print(f"Test execution failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())