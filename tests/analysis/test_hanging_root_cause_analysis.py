"""Root Cause Analysis Test for Service Startup Hanging

This test identifies and documents the specific root causes of hanging behavior
in RealServicesManager during E2E test execution.

Business Value Justification (BVJ):
- Segment: Platform/Internal - Critical Infrastructure  
- Business Goal: Fix E2E test hanging that blocks CI/CD deployments
- Value Impact: Enable reliable automated testing and faster deployment cycles
- Revenue Impact: Prevent $500+ per hour delays from hanging test suites

ROOT CAUSES IDENTIFIED:
1. HTTP client timeout not respecting endpoint-specific timeouts
2. Sequential health checks causing cumulative delays
3. Services not running locally causing long connection timeouts  
4. Event loop management issues in synchronous wrapper method

Test Strategy:
- Demonstrate each root cause with specific test cases
- Measure actual timeout behavior
- Document timing and behavioral issues
- Provide specific fix recommendations
"""

import asyncio
import pytest
import time
import httpx
from typing import Dict, Any

from tests.e2e.real_services_manager import RealServicesManager, ServiceEndpoint


class TestHangingRootCauseAnalysis:
    """Root cause analysis tests for hanging behavior"""
    
    def setup_method(self):
        """Setup for root cause analysis"""
        self.manager = RealServicesManager()
        
    def teardown_method(self):
        """Cleanup"""
        if hasattr(self, 'manager'):
            try:
                asyncio.run(self.manager.cleanup())
            except Exception:
                pass
    
    async def test_root_cause_1_http_timeout_not_respected(self):
        """ROOT CAUSE 1: HTTP client timeout overrides endpoint timeout"""
        
        print("\n=== ROOT CAUSE 1: HTTP Client Timeout Configuration ===")
        
        # Create endpoint with very short timeout
        endpoint = ServiceEndpoint("test", "http://localhost:9999", "/health", timeout=2.0)
        
        # Initialize HTTP client (30 second default timeout)
        await self.manager._ensure_http_client()
        
        print(f"Endpoint timeout: {endpoint.timeout}s")
        print(f"HTTP client timeout: {self.manager._http_client.timeout}")
        
        # Test health check timing
        start_time = time.time()
        
        try:
            # This should respect the 2.0s endpoint timeout, not the 30s client timeout
            healthy, error = await self.manager._check_http_health(endpoint)
            elapsed_time = time.time() - start_time
            
            print(f"Health check completed in {elapsed_time:.2f}s")
            print(f"Result: healthy={healthy}, error={error}")
            
            # ISSUE: This will likely take much longer than 2 seconds
            if elapsed_time > endpoint.timeout + 1.0:
                print(f"❌ CONFIRMED: Endpoint timeout not respected. Expected ~{endpoint.timeout}s, got {elapsed_time:.2f}s")
            else:
                print(f"✅ Endpoint timeout properly respected")
                
        except Exception as e:
            elapsed_time = time.time() - start_time
            print(f"Health check failed in {elapsed_time:.2f}s: {e}")
    
    async def test_root_cause_2_sequential_vs_parallel_health_checks(self):
        """ROOT CAUSE 2: Sequential health checks cause cumulative delays"""
        
        print("\n=== ROOT CAUSE 2: Sequential vs Parallel Health Checks ===")
        
        # Create multiple endpoints that will timeout
        endpoints = [
            ServiceEndpoint("service1", "http://localhost:9991", "/health", timeout=3.0),
            ServiceEndpoint("service2", "http://localhost:9992", "/health", timeout=3.0),
            ServiceEndpoint("service3", "http://localhost:9993", "/health", timeout=3.0),
        ]
        
        self.manager.service_endpoints = endpoints
        
        # Test sequential health checks (current implementation)
        print("Testing sequential health checks (current implementation)...")
        start_time = time.time()
        
        sequential_results = await self.manager._check_all_services_health()
        sequential_time = time.time() - start_time
        
        print(f"Sequential health checks took {sequential_time:.2f}s")
        
        # Test parallel health checks (what it should be)
        print("Testing parallel health checks (improved approach)...")
        start_time = time.time()
        
        # Parallel implementation
        tasks = []
        for endpoint in endpoints:
            task = self.manager._check_service_health(endpoint)
            tasks.append(task)
        
        parallel_results = await asyncio.gather(*tasks)
        parallel_time = time.time() - start_time
        
        print(f"Parallel health checks took {parallel_time:.2f}s")
        
        # Analysis
        improvement_ratio = sequential_time / parallel_time if parallel_time > 0 else 0
        print(f"Improvement ratio: {improvement_ratio:.2f}x faster")
        
        if sequential_time > parallel_time * 2:
            print(f"❌ CONFIRMED: Sequential checks are significantly slower ({sequential_time:.2f}s vs {parallel_time:.2f}s)")
        else:
            print(f"✅ Sequential vs parallel timing acceptable")
    
    async def test_root_cause_3_local_service_availability(self):
        """ROOT CAUSE 3: Local services not running causing long timeouts"""
        
        print("\n=== ROOT CAUSE 3: Local Service Availability ===")
        
        # Test the actual default endpoints used by RealServicesManager
        default_endpoints = [
            ServiceEndpoint("auth_service", "http://localhost:8081", "/auth/health", timeout=5.0),
            ServiceEndpoint("backend", "http://localhost:8000", "/health", timeout=5.0),
        ]
        
        for endpoint in default_endpoints:
            print(f"\nTesting {endpoint.name} at {endpoint.url}")
            
            start_time = time.time()
            
            try:
                # Test direct connection
                async with httpx.AsyncClient(timeout=endpoint.timeout) as client:
                    response = await client.get(f"{endpoint.url}{endpoint.health_path}")
                    elapsed_time = time.time() - start_time
                    
                    print(f"✅ {endpoint.name} is running: {response.status_code} in {elapsed_time:.2f}s")
                    
            except httpx.ConnectError:
                elapsed_time = time.time() - start_time
                print(f"❌ {endpoint.name} not running: Connection refused in {elapsed_time:.2f}s")
                
            except httpx.TimeoutException:
                elapsed_time = time.time() - start_time  
                print(f"❌ {endpoint.name} timeout: {elapsed_time:.2f}s")
                
            except Exception as e:
                elapsed_time = time.time() - start_time
                print(f"❌ {endpoint.name} error: {e} in {elapsed_time:.2f}s")
    
    def test_root_cause_4_event_loop_issues(self):
        """ROOT CAUSE 4: Event loop management in synchronous wrapper"""
        
        print("\n=== ROOT CAUSE 4: Event Loop Management Issues ===")
        
        # Test the problematic launch_dev_environment method
        print("Testing launch_dev_environment method...")
        
        start_time = time.time()
        
        try:
            result = self.manager.launch_dev_environment()
            elapsed_time = time.time() - start_time
            
            print(f"launch_dev_environment returned in {elapsed_time:.2f}s")
            print(f"Result: {result}")
            
            # This method returns immediately but may leave tasks running
            if elapsed_time < 1.0 and result.get("success"):
                print("⚠️  Method returns immediately - tasks may still be running in background")
                print("⚠️  This can cause resource leaks and hanging background operations")
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            print(f"launch_dev_environment failed in {elapsed_time:.2f}s: {e}")
    
    async def test_hanging_behavior_comprehensive_timing(self):
        """Comprehensive timing analysis of hanging behavior"""
        
        print("\n=== COMPREHENSIVE HANGING BEHAVIOR ANALYSIS ===")
        
        # Test the full startup sequence timing
        timing_results = {}
        
        # 1. HTTP client initialization
        start_time = time.time()
        await self.manager._ensure_http_client()
        timing_results["http_client_init"] = time.time() - start_time
        
        # 2. Single health check to non-existent service
        start_time = time.time()
        endpoint = ServiceEndpoint("nonexistent", "http://localhost:9999", "/health", timeout=5.0)
        status = await self.manager._check_service_health(endpoint)
        timing_results["single_health_check"] = time.time() - start_time
        
        # 3. All services health check (default endpoints)
        start_time = time.time()
        try:
            health_result = await asyncio.wait_for(
                self.manager._check_all_services_health(),
                timeout=45.0  # Prevent hanging in test
            )
            timing_results["all_services_health"] = time.time() - start_time
        except asyncio.TimeoutError:
            timing_results["all_services_health"] = 45.0  # Timed out
            print("⚠️  All services health check timed out at 45s")
        
        # 4. Start missing services timing
        start_time = time.time()
        try:
            startup_result = await asyncio.wait_for(
                self.manager._start_missing_services(),
                timeout=30.0
            )
            timing_results["start_missing_services"] = time.time() - start_time
        except asyncio.TimeoutError:
            timing_results["start_missing_services"] = 30.0
            print("⚠️  Start missing services timed out at 30s")
        
        # Print comprehensive timing analysis
        print("\n=== TIMING ANALYSIS RESULTS ===")
        total_time = sum(timing_results.values())
        
        for operation, duration in timing_results.items():
            percentage = (duration / total_time * 100) if total_time > 0 else 0
            print(f"{operation}: {duration:.2f}s ({percentage:.1f}%)")
        
        print(f"\nTotal sequential time: {total_time:.2f}s")
        
        if total_time > 60.0:
            print("❌ CONFIRMED: Total startup time exceeds 1 minute - will cause test timeouts")
        elif total_time > 30.0:
            print("⚠️  Total startup time exceeds 30 seconds - may cause test delays")
        else:
            print("✅ Total startup time acceptable")


class TestHangingFixRecommendations:
    """Tests to validate potential fixes for hanging behavior"""
    
    async def test_fix_1_proper_timeout_configuration(self):
        """Test fix: Proper timeout configuration in HTTP requests"""
        
        print("\n=== FIX RECOMMENDATION 1: Proper Timeout Configuration ===")
        
        endpoint = ServiceEndpoint("test", "http://localhost:9999", "/health", timeout=3.0)
        
        # Current implementation (hangs)
        start_time = time.time()
        async with httpx.AsyncClient(timeout=30.0) as client:  # Global 30s timeout
            try:
                response = await client.get(f"{endpoint.url}{endpoint.health_path}")
            except Exception:
                pass
        current_time = time.time() - start_time
        
        # Recommended fix (respects endpoint timeout)
        start_time = time.time()
        async with httpx.AsyncClient() as client:  # No global timeout
            try:
                response = await client.get(
                    f"{endpoint.url}{endpoint.health_path}",
                    timeout=endpoint.timeout  # Use endpoint-specific timeout
                )
            except Exception:
                pass
        fixed_time = time.time() - start_time
        
        print(f"Current implementation: {current_time:.2f}s")
        print(f"Fixed implementation: {fixed_time:.2f}s")
        
        improvement = current_time / fixed_time if fixed_time > 0 else 1
        print(f"Improvement: {improvement:.2f}x faster")
    
    async def test_fix_2_parallel_health_checks(self):
        """Test fix: Parallel health checks instead of sequential"""
        
        print("\n=== FIX RECOMMENDATION 2: Parallel Health Checks ===")
        
        endpoints = [
            ServiceEndpoint("service1", "http://localhost:9991", "/health", timeout=2.0),
            ServiceEndpoint("service2", "http://localhost:9992", "/health", timeout=2.0),
            ServiceEndpoint("service3", "http://localhost:9993", "/health", timeout=2.0),
        ]
        
        # Sequential (current)
        start_time = time.time()
        for endpoint in endpoints:
            try:
                async with httpx.AsyncClient() as client:
                    await client.get(f"{endpoint.url}{endpoint.health_path}", timeout=endpoint.timeout)
            except Exception:
                pass
        sequential_time = time.time() - start_time
        
        # Parallel (recommended)
        start_time = time.time()
        
        async def check_endpoint(endpoint):
            try:
                async with httpx.AsyncClient() as client:
                    await client.get(f"{endpoint.url}{endpoint.health_path}", timeout=endpoint.timeout)
            except Exception:
                pass
        
        await asyncio.gather(*[check_endpoint(ep) for ep in endpoints])
        parallel_time = time.time() - start_time
        
        print(f"Sequential approach: {sequential_time:.2f}s")
        print(f"Parallel approach: {parallel_time:.2f}s")
        
        improvement = sequential_time / parallel_time if parallel_time > 0 else 1
        print(f"Improvement: {improvement:.2f}x faster")


if __name__ == "__main__":
    print("Running root cause analysis for E2E test hanging behavior...")
    print("This will identify specific issues causing RealServicesManager to hang")
    
    pytest.main([__file__, "-v", "-s"])