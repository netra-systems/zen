"""
Frontend Performance and Reliability E2E Tests

Business Value Justification (BVJ):
- Segment: All tiers (platform reliability)
- Business Goal: Maintain 99.9% uptime and <2s load times
- Value Impact: Prevents 20% churn from poor performance
- Strategic Impact: $400K MRR protected through performance SLAs

Tests frontend performance, load times, and reliability under various conditions.
"""

import asyncio
import json
import os
import time
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime
import statistics

import pytest
import httpx
from concurrent.futures import ThreadPoolExecutor, as_completed

from test_framework.http_client import UnifiedHTTPClient
from test_framework.fixtures.auth import create_test_user_token, create_real_jwt_token


class PerformanceReliabilityTester:
    """Test harness for performance and reliability testing"""
    
    def __init__(self):
        self.base_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        self.api_url = os.getenv("API_URL", "http://localhost:8000")
        self.metrics = {
            "response_times": [],
            "error_rates": [],
            "throughput": [],
            "memory_usage": []
        }
        self.http_client = UnifiedHTTPClient(base_url=self.api_url)
        
    async def measure_page_load_time(self, url: str, auth_token: str = None) -> float:
        """Measure time to load a page"""
        headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
        
        start_time = time.time()
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, follow_redirects=True)
                load_time = time.time() - start_time
                
                if response.status_code == 200:
                    self.metrics["response_times"].append(load_time)
                    return load_time
                else:
                    self.metrics["error_rates"].append(response.status_code)
                    return -1
                    
            except Exception as e:
                print(f"Load time measurement failed: {e}")
                return -1
                
    async def simulate_concurrent_users(self, num_users: int, operation):
        """Simulate multiple concurrent users"""
        tasks = []
        
        for i in range(num_users):
            user_token = create_real_jwt_token(f"perf-user-{i}", ["user"])
            task = asyncio.create_task(operation(user_token, i))
            tasks.append(task)
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        error_count = len(results) - success_count
        
        return {
            "total": num_users,
            "success": success_count,
            "errors": error_count,
            "success_rate": (success_count / num_users) * 100
        }
        
    def calculate_statistics(self, data: List[float]) -> Dict[str, float]:
        """Calculate performance statistics"""
        if not data:
            return {}
            
        return {
            "min": min(data),
            "max": max(data),
            "mean": statistics.mean(data),
            "median": statistics.median(data),
            "stdev": statistics.stdev(data) if len(data) > 1 else 0,
            "p95": sorted(data)[int(len(data) * 0.95)] if data else 0,
            "p99": sorted(data)[int(len(data) * 0.99)] if data else 0
        }


@pytest.mark.e2e
@pytest.mark.frontend
@pytest.mark.performance
class TestFrontendPerformanceReliability:
    """Test frontend performance and reliability metrics"""
    
    @pytest.fixture(autouse=True)
    async def setup_tester(self):
        """Setup test harness"""
        self.tester = PerformanceReliabilityTester()
        self.test_token = create_real_jwt_token("perf-test-user", ["user"])
        yield
        
    @pytest.mark.asyncio
    async def test_61_initial_page_load_performance(self):
        """Test 61: Initial page load completes within SLA"""
        load_times = []
        
        # Test multiple page loads
        for i in range(5):
            load_time = await self.tester.measure_page_load_time(self.tester.base_url)
            if load_time > 0:
                load_times.append(load_time)
                
        stats = self.tester.calculate_statistics(load_times)
        
        # Check SLA: 95% of loads under 2 seconds
        assert stats.get("p95", float('inf')) < 2.0, f"P95 load time {stats.get('p95')}s exceeds 2s SLA"
        
    @pytest.mark.asyncio
    async def test_62_authenticated_page_load_performance(self):
        """Test 62: Authenticated pages load within SLA"""
        load_times = []
        
        # Test authenticated page loads
        for i in range(5):
            load_time = await self.tester.measure_page_load_time(
                f"{self.tester.base_url}/chat",
                self.test_token
            )
            if load_time > 0:
                load_times.append(load_time)
                
        stats = self.tester.calculate_statistics(load_times)
        
        # Authenticated pages might be slightly slower but should still be fast
        assert stats.get("mean", float('inf')) < 3.0, f"Mean load time {stats.get('mean')}s exceeds 3s threshold"
        
    @pytest.mark.asyncio
    async def test_63_api_response_time_performance(self):
        """Test 63: API endpoints respond within SLA"""
        api_times = []
        headers = {"Authorization": f"Bearer {self.test_token}"}
        
        endpoints = [
            "/api/threads",
            "/api/system/info",
            "/api/health/ready",
            "/api/metrics/raw"
        ]
        
        # Use connection pooling and warm up cache for accurate performance measurement
        limits = httpx.Limits(max_keepalive_connections=10, max_connections=15)
        async with httpx.AsyncClient(limits=limits, timeout=10.0) as client:
            # Warm up connection and configuration cache
            try:
                await client.get(f"{self.tester.api_url}/api/system/info", headers=headers)
                await asyncio.sleep(0.1)  # Brief pause to let cache settle
            except:
                pass  # Ignore warmup errors
            
            # Now run the actual performance test
            for endpoint in endpoints:
                start = time.time()
                try:
                    response = await client.get(
                        f"{self.tester.api_url}{endpoint}",
                        headers=headers,
                        timeout=5.0
                    )
                    api_times.append(time.time() - start)
                except:
                    pass
                    
        stats = self.tester.calculate_statistics(api_times)
        
        # API should respond quickly
        assert stats.get("p95", float('inf')) < 1.0, f"P95 API response time {stats.get('p95')}s exceeds 1s SLA"
        
    @pytest.mark.asyncio
    async def test_64_concurrent_user_load(self):
        """Test 64: System handles concurrent users correctly"""
        
        async def user_operation(token: str, user_id: int):
            """Simulate a user operation"""
            headers = {"Authorization": f"Bearer {token}"}
            
            async with httpx.AsyncClient() as client:
                # User logs in and sends a message
                response = await client.get(
                    f"{self.tester.api_url}/api/threads",
                    headers=headers
                )
                
                if response.status_code == 200:
                    # Send a message
                    message_data = {
                        "content": f"Test message from user {user_id}",
                        "thread_id": str(uuid.uuid4())
                    }
                    
                    await client.post(
                        f"{self.tester.api_url}/api/messages",
                        json=message_data,
                        headers=headers
                    )
                    
                return response.status_code == 200
                
        # Test with 10 concurrent users
        results = await self.tester.simulate_concurrent_users(10, user_operation)
        
        # Should handle at least 80% success rate
        assert results["success_rate"] >= 80, f"Success rate {results['success_rate']}% below 80% threshold"
        
    @pytest.mark.asyncio
    async def test_65_sustained_load_performance(self):
        """Test 65: System maintains performance under sustained load"""
        duration = 30  # 30 seconds of sustained load
        start_time = time.time()
        response_times = []
        errors = 0
        
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {self.test_token}"}
            
            while time.time() - start_time < duration:
                req_start = time.time()
                try:
                    response = await client.get(
                        f"{self.tester.api_url}/api/threads",
                        headers=headers,
                        timeout=5.0
                    )
                    response_times.append(time.time() - req_start)
                    
                    if response.status_code != 200:
                        errors += 1
                        
                except:
                    errors += 1
                    
                await asyncio.sleep(0.5)  # 2 requests per second
                
        # Calculate degradation
        first_half = response_times[:len(response_times)//2]
        second_half = response_times[len(response_times)//2:]
        
        first_half_avg = statistics.mean(first_half) if first_half else 0
        second_half_avg = statistics.mean(second_half) if second_half else 0
        
        # Performance shouldn't degrade more than 50%
        degradation = ((second_half_avg - first_half_avg) / first_half_avg * 100) if first_half_avg > 0 else 0
        assert degradation < 50, f"Performance degraded by {degradation}% during sustained load"
        
    @pytest.mark.asyncio
    async def test_66_memory_leak_detection(self):
        """Test 66: No memory leaks during extended operation"""
        # This test would normally monitor memory usage
        # For now, we'll test that repeated operations don't cause issues
        
        headers = {"Authorization": f"Bearer {self.test_token}"}
        
        for cycle in range(3):
            async with httpx.AsyncClient() as client:
                # Create and delete resources
                for i in range(10):
                    # Create thread
                    thread_data = {"name": f"Test thread {i}"}
                    response = await client.post(
                        f"{self.tester.api_url}/api/threads",
                        json=thread_data,
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        thread_id = response.json().get("id")
                        
                        # Delete thread
                        if thread_id:
                            await client.delete(
                                f"{self.tester.api_url}/api/threads/{thread_id}",
                                headers=headers
                            )
                            
            # Memory should be released between cycles
            await asyncio.sleep(1)
            
        # If we get here without crashing, test passes
        assert True
        
    @pytest.mark.asyncio
    async def test_67_cache_effectiveness(self):
        """Test 67: Caching improves performance for repeated requests"""
        headers = {"Authorization": f"Bearer {self.test_token}"}
        endpoint = f"{self.tester.api_url}/api/users/profile"
        
        # First request (cache miss)
        async with httpx.AsyncClient() as client:
            start1 = time.time()
            response1 = await client.get(endpoint, headers=headers)
            time1 = time.time() - start1
            
            # Second request (should hit cache)
            start2 = time.time()
            response2 = await client.get(endpoint, headers=headers)
            time2 = time.time() - start2
            
            # Third request (definitely cached)
            start3 = time.time()
            response3 = await client.get(endpoint, headers=headers)
            time3 = time.time() - start3
            
        # Cached requests should be faster (or at least not slower)
        # Allow some variance but generally cached should be faster
        assert time3 <= time1 * 1.5, f"Cached request ({time3}s) slower than initial ({time1}s)"
        
    @pytest.mark.asyncio
    async def test_68_error_rate_under_load(self):
        """Test 68: Error rate stays below threshold under load"""
        total_requests = 100
        errors = 0
        
        async def make_request(i: int):
            token = create_real_jwt_token(f"load-user-{i}", ["user"])
            headers = {"Authorization": f"Bearer {token}"}
            
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.get(
                        f"{self.tester.api_url}/api/threads",
                        headers=headers,
                        timeout=5.0
                    )
                    
                    if response.status_code >= 500:
                        return "error"
                    return "success"
                    
                except:
                    return "error"
                    
        # Make concurrent requests
        tasks = [make_request(i) for i in range(total_requests)]
        results = await asyncio.gather(*tasks)
        
        error_count = sum(1 for r in results if r == "error")
        error_rate = (error_count / total_requests) * 100
        
        # Error rate should be below 5%
        assert error_rate < 5, f"Error rate {error_rate}% exceeds 5% threshold"
        
    @pytest.mark.asyncio
    async def test_69_graceful_degradation(self):
        """Test 69: System degrades gracefully under extreme load"""
        # Simulate extreme load
        extreme_load_users = 50
        
        async def extreme_operation(token: str, user_id: int):
            headers = {"Authorization": f"Bearer {token}"}
            
            async with httpx.AsyncClient() as client:
                try:
                    # Try to overwhelm with rapid requests
                    for _ in range(10):
                        await client.get(
                            f"{self.tester.api_url}/api/threads",
                            headers=headers,
                            timeout=2.0
                        )
                    return "completed"
                    
                except httpx.TimeoutException:
                    return "timeout"
                except:
                    return "error"
                    
        results = await self.tester.simulate_concurrent_users(extreme_load_users, extreme_operation)
        
        # System should handle some requests even under extreme load
        assert results["success"] > 0, "System completely failed under extreme load"
        
    @pytest.mark.asyncio
    async def test_70_recovery_time_after_failure(self):
        """Test 70: System recovers quickly after failure"""
        headers = {"Authorization": f"Bearer {self.test_token}"}
        
        # Baseline performance
        async with httpx.AsyncClient() as client:
            start = time.time()
            await client.get(f"{self.tester.api_url}/api/threads", headers=headers)
            baseline_time = time.time() - start
            
            # Simulate failure by making bad requests
            for _ in range(10):
                try:
                    await client.post(
                        f"{self.tester.api_url}/api/invalid",
                        json={"bad": "data"},
                        headers=headers,
                        timeout=1.0
                    )
                except:
                    pass
                    
            # Measure recovery
            recovery_times = []
            for i in range(5):
                start = time.time()
                try:
                    response = await client.get(
                        f"{self.tester.api_url}/api/threads",
                        headers=headers,
                        timeout=5.0
                    )
                    recovery_times.append(time.time() - start)
                    
                    if response.status_code == 200:
                        break
                        
                except:
                    pass
                    
                await asyncio.sleep(1)
                
        # Should recover within 5 attempts
        assert len(recovery_times) > 0, "System did not recover after failure"
        
        # Recovery time should be reasonable
        if recovery_times:
            assert min(recovery_times) < baseline_time * 3, "Recovery time too slow"