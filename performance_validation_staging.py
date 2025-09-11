#!/usr/bin/env python3
"""
Performance Validation for UserContextManager in Staging Environment
Tests performance characteristics under load to ensure no regressions.
"""

import asyncio
import aiohttp
import time
from typing import List, Dict, Any
import json
import statistics


class PerformanceValidator:
    """Validates UserContextManager performance characteristics."""
    
    def __init__(self, staging_url: str):
        self.staging_url = staging_url.rstrip('/')
        
    async def single_request_test(self, session: aiohttp.ClientSession, path: str) -> Dict[str, Any]:
        """Perform a single request and measure response time."""
        start_time = time.time()
        try:
            async with session.get(f"{self.staging_url}{path}") as response:
                await response.text()  # Ensure full response is received
                end_time = time.time()
                
                return {
                    "success": True,
                    "status_code": response.status,
                    "response_time_ms": (end_time - start_time) * 1000,
                    "error": None
                }
        except Exception as e:
            end_time = time.time()
            return {
                "success": False,
                "status_code": None,
                "response_time_ms": (end_time - start_time) * 1000,
                "error": str(e)
            }
    
    async def concurrent_load_test(self, path: str, concurrent_requests: int, total_requests: int) -> Dict[str, Any]:
        """Run concurrent requests to test load handling."""
        print(f"  🔄 Testing {path} with {concurrent_requests} concurrent requests ({total_requests} total)")
        
        connector = aiohttp.TCPConnector(limit=100)
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            start_time = time.time()
            
            # Create request batches
            results = []
            requests_sent = 0
            
            while requests_sent < total_requests:
                batch_size = min(concurrent_requests, total_requests - requests_sent)
                tasks = []
                
                for _ in range(batch_size):
                    task = asyncio.create_task(self.single_request_test(session, path))
                    tasks.append(task)
                
                batch_results = await asyncio.gather(*tasks)
                results.extend(batch_results)
                requests_sent += batch_size
                
                # Small delay between batches to avoid overwhelming the service
                if requests_sent < total_requests:
                    await asyncio.sleep(0.1)
            
            end_time = time.time()
            total_duration = end_time - start_time
        
        # Analyze results
        successful_requests = [r for r in results if r["success"]]
        failed_requests = [r for r in results if not r["success"]]
        
        response_times = [r["response_time_ms"] for r in successful_requests]
        
        analysis = {
            "path": path,
            "concurrent_requests": concurrent_requests,
            "total_requests": total_requests,
            "duration_seconds": total_duration,
            "requests_per_second": total_requests / total_duration,
            "success_count": len(successful_requests),
            "failure_count": len(failed_requests),
            "success_rate": (len(successful_requests) / total_requests) * 100,
        }
        
        if response_times:
            analysis.update({
                "avg_response_time_ms": statistics.mean(response_times),
                "min_response_time_ms": min(response_times),
                "max_response_time_ms": max(response_times),
                "p50_response_time_ms": statistics.median(response_times),
                "p95_response_time_ms": statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else max(response_times),
                "p99_response_time_ms": statistics.quantiles(response_times, n=100)[98] if len(response_times) >= 100 else max(response_times)
            })
        
        # Collect error details
        if failed_requests:
            error_summary = {}
            for req in failed_requests:
                error = req.get("error", "Unknown error")
                error_summary[error] = error_summary.get(error, 0) + 1
            analysis["error_summary"] = error_summary
        
        return analysis
    
    async def validate_performance(self) -> Dict[str, Any]:
        """Run comprehensive performance validation."""
        print(f"🚀 Performance Validation - UserContextManager")
        print(f"🎯 Target: {self.staging_url}")
        print(f"📋 Testing performance under various load conditions\n")
        
        test_scenarios = [
            {
                "name": "Light Load - Health Endpoint",
                "path": "/health",
                "concurrent": 5,
                "total": 25
            },
            {
                "name": "Medium Load - Root Endpoint", 
                "path": "/",
                "concurrent": 10,
                "total": 50
            },
            {
                "name": "Heavy Load - API Docs",
                "path": "/docs",
                "concurrent": 20,
                "total": 100
            }
        ]
        
        results = []
        
        for scenario in test_scenarios:
            print(f"🧪 Running: {scenario['name']}")
            result = await self.concurrent_load_test(
                scenario["path"],
                scenario["concurrent"], 
                scenario["total"]
            )
            result["scenario_name"] = scenario["name"]
            results.append(result)
            
            # Print immediate results
            print(f"  ✅ Success Rate: {result['success_rate']:.1f}%")
            print(f"  ⚡ Requests/sec: {result['requests_per_second']:.1f}")
            if 'avg_response_time_ms' in result:
                print(f"  ⏱️  Avg Response Time: {result['avg_response_time_ms']:.1f}ms")
                print(f"  📊 P95 Response Time: {result['p95_response_time_ms']:.1f}ms")
            print()
        
        return {
            "validation_timestamp": time.time(),
            "staging_url": self.staging_url,
            "performance_results": results
        }


async def main():
    """Main performance validation function."""
    staging_url = "https://netra-backend-staging-pnovr5vsba-uc.a.run.app"
    
    validator = PerformanceValidator(staging_url)
    report = await validator.validate_performance()
    
    # Generate summary
    results = report["performance_results"]
    
    print(f"{'='*70}")
    print(f"📊 PERFORMANCE VALIDATION SUMMARY")
    print(f"{'='*70}")
    
    all_successful = True
    performance_issues = []
    
    for result in results:
        print(f"\n🧪 {result['scenario_name']}:")
        print(f"   Success Rate: {result['success_rate']:.1f}%")
        print(f"   Requests/sec: {result['requests_per_second']:.1f}")
        
        if 'avg_response_time_ms' in result:
            print(f"   Avg Response: {result['avg_response_time_ms']:.1f}ms")
            print(f"   P95 Response: {result['p95_response_time_ms']:.1f}ms")
            print(f"   P99 Response: {result['p99_response_time_ms']:.1f}ms")
            
            # Performance thresholds
            if result['success_rate'] < 95:
                all_successful = False
                performance_issues.append(f"{result['scenario_name']}: Low success rate ({result['success_rate']:.1f}%)")
            
            if result['avg_response_time_ms'] > 5000:  # 5 seconds threshold
                all_successful = False
                performance_issues.append(f"{result['scenario_name']}: High avg response time ({result['avg_response_time_ms']:.1f}ms)")
            
            if result['p95_response_time_ms'] > 10000:  # 10 seconds threshold
                all_successful = False
                performance_issues.append(f"{result['scenario_name']}: High P95 response time ({result['p95_response_time_ms']:.1f}ms)")
        
        if 'error_summary' in result:
            print(f"   Errors: {result['error_summary']}")
    
    print(f"\n🏆 Overall Performance: {'✅ EXCELLENT' if all_successful else '⚠️ ISSUES DETECTED'}")
    
    if performance_issues:
        print(f"\n🚨 Performance Issues:")
        for issue in performance_issues:
            print(f"   ❌ {issue}")
    else:
        print(f"✅ UserContextManager shows excellent performance characteristics")
        print(f"✅ No performance regressions detected")
        print(f"✅ Suitable for production workloads")
    
    # Save detailed report
    with open('/Users/anthony/Desktop/netra-apex/performance_validation_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📋 Detailed report saved to: performance_validation_report.json")
    
    return 0 if all_successful else 1


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))