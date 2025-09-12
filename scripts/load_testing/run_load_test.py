#!/usr/bin/env python3
"""
Concurrent User Load Testing for Staging Validation
Tests request isolation under 100+ concurrent users
"""

import os
import time
import asyncio
import aiohttp
import json
import random
from typing import Dict, List, Any
from dataclasses import dataclass
from datetime import datetime
import concurrent.futures
import threading
from collections import defaultdict

@dataclass
class TestResult:
    success: bool
    duration: float
    status_code: int
    error: str = None
    user_id: str = None

class ConcurrentUserTester:
    """Simulates concurrent users to test request isolation."""
    
    def __init__(self, target_url: str, max_users: int = 150, test_duration: int = 3600):
        self.target_url = target_url
        self.max_users = max_users
        self.test_duration = test_duration
        self.results = []
        self.metrics = defaultdict(int)
        self.start_time = None
        self.running = False
        
    async def simulate_user_session(self, user_id: str, session: aiohttp.ClientSession) -> List[TestResult]:
        """Simulate a complete user session with multiple requests."""
        results = []
        
        # Simulate typical user workflow
        endpoints = [
            "/health",
            "/api/threads",
            "/api/agents/triage",
            "/api/chat/start",
        ]
        
        for endpoint in endpoints:
            try:
                start_time = time.time()
                
                async with session.get(f"{self.target_url}{endpoint}") as response:
                    duration = time.time() - start_time
                    
                    result = TestResult(
                        success=response.status < 400,
                        duration=duration,
                        status_code=response.status,
                        user_id=user_id
                    )
                    results.append(result)
                    
                    # Random delay between requests (0.1-2 seconds)
                    await asyncio.sleep(random.uniform(0.1, 2.0))
                    
            except Exception as e:
                result = TestResult(
                    success=False,
                    duration=0,
                    status_code=0,
                    error=str(e),
                    user_id=user_id
                )
                results.append(result)
                
        return results
    
    async def run_concurrent_users(self, num_users: int) -> List[TestResult]:
        """Run concurrent user sessions."""
        print(f"[U+1F680] Starting {num_users} concurrent users...")
        
        connector = aiohttp.TCPConnector(limit=num_users * 2)
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            tasks = [
                self.simulate_user_session(f"user_{i}", session)
                for i in range(num_users)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Flatten results
            all_results = []
            for user_results in results:
                if isinstance(user_results, list):
                    all_results.extend(user_results)
                else:
                    # Handle exceptions
                    all_results.append(TestResult(
                        success=False,
                        duration=0,
                        status_code=0,
                        error=str(user_results)
                    ))
                    
        return all_results
    
    def analyze_results(self, results: List[TestResult]) -> Dict[str, Any]:
        """Analyze test results for isolation validation."""
        total_requests = len(results)
        successful_requests = sum(1 for r in results if r.success)
        failed_requests = total_requests - successful_requests
        
        success_rate = (successful_requests / total_requests) * 100 if total_requests > 0 else 0
        
        # Response time analysis
        successful_durations = [r.duration for r in results if r.success]
        avg_response_time = sum(successful_durations) / len(successful_durations) if successful_durations else 0
        
        # Status code distribution
        status_codes = defaultdict(int)
        for result in results:
            status_codes[result.status_code] += 1
            
        # Error analysis
        errors = defaultdict(int)
        for result in results:
            if result.error:
                errors[result.error] += 1
        
        return {
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": success_rate,
            "avg_response_time": avg_response_time,
            "status_codes": dict(status_codes),
            "errors": dict(errors),
            "isolation_test_passed": success_rate > 95.0,  # 95% success rate threshold
        }
    
    async def run_isolation_test(self):
        """Run the complete isolation test with increasing concurrent users."""
        print(f"[U+1F9EA] Starting Request Isolation Test")
        print(f"   Target: {self.target_url}")
        print(f"   Max Users: {self.max_users}")
        print(f"   Duration: {self.test_duration}s")
        
        self.start_time = datetime.now()
        self.running = True
        
        # Test with increasing concurrency levels
        concurrency_levels = [10, 25, 50, 100, 150]
        all_results = {}
        
        for level in concurrency_levels:
            if level > self.max_users:
                break
                
            print(f"\n CHART:  Testing with {level} concurrent users...")
            
            start_time = time.time()
            results = await self.run_concurrent_users(level)
            test_duration = time.time() - start_time
            
            analysis = self.analyze_results(results)
            analysis["test_duration"] = test_duration
            analysis["concurrent_users"] = level
            
            all_results[f"level_{level}"] = analysis
            
            # Print immediate results
            print(f"    PASS:  Success Rate: {analysis['success_rate']:.1f}%")
            print(f"   [U+23F1][U+FE0F]  Avg Response Time: {analysis['avg_response_time']:.3f}s")
            print(f"    CYCLE:  Total Requests: {analysis['total_requests']}")
            
            # Brief pause between levels
            await asyncio.sleep(5)
        
        # Save results
        self.save_results(all_results)
        self.running = False
        
        return all_results
    
    def save_results(self, results: Dict[str, Any]):
        """Save test results to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"/app/results/load_test_{timestamp}.json"
        
        try:
            os.makedirs("/app/results", exist_ok=True)
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"[U+1F4BE] Results saved to {filename}")
        except Exception as e:
            print(f" FAIL:  Failed to save results: {e}")
    
    def print_summary(self, results: Dict[str, Any]):
        """Print test summary."""
        print(f"\n{'='*60}")
        print(f"REQUEST ISOLATION TEST SUMMARY")
        print(f"{'='*60}")
        
        for level_key, analysis in results.items():
            level = analysis["concurrent_users"]
            print(f"\n FIRE:  {level} Concurrent Users:")
            print(f"   Success Rate: {analysis['success_rate']:.1f}%")
            print(f"   Isolation Test: {' PASS:  PASSED' if analysis['isolation_test_passed'] else ' FAIL:  FAILED'}")
            print(f"   Avg Response: {analysis['avg_response_time']:.3f}s")
            print(f"   Total Requests: {analysis['total_requests']}")
            
        # Overall assessment
        all_passed = all(analysis['isolation_test_passed'] for analysis in results.values())
        print(f"\n TARGET:  OVERALL ISOLATION TEST: {' PASS:  PASSED' if all_passed else ' FAIL:  FAILED'}")
        
        if not all_passed:
            print(" WARNING: [U+FE0F]  Request isolation issues detected!")
            print("   Check logs for cross-contamination between users")

async def main():
    """Main entry point for load testing."""
    target_url = os.getenv("TARGET_URL", "http://backend:8000")
    max_users = int(os.getenv("MAX_USERS", "150"))
    run_time = int(os.getenv("RUN_TIME", "3600"))
    
    print("[U+1F680] Starting Concurrent User Load Test")
    print(f"   Target URL: {target_url}")
    
    # Wait for backend to be ready
    print("[U+23F3] Waiting for backend to be ready...")
    import aiohttp
    
    for attempt in range(30):  # 5 minute timeout
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{target_url}/health") as response:
                    if response.status == 200:
                        print(" PASS:  Backend is ready!")
                        break
        except:
            pass
        
        await asyncio.sleep(10)
    else:
        print(" FAIL:  Backend not ready after 5 minutes, starting test anyway...")
    
    # Run the test
    tester = ConcurrentUserTester(target_url, max_users, run_time)
    results = await tester.run_isolation_test()
    tester.print_summary(results)

if __name__ == "__main__":
    asyncio.run(main())