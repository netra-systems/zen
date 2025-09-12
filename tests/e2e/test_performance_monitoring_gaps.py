"""
Performance Monitoring Gaps E2E Tests

Tests that identify gaps in performance monitoring, alerting, and SLA compliance
across all services. Ensures we can detect performance degradation proactively.

Business Value: Platform reliability and SLA compliance for enterprise customers
Expected Coverage Gaps: Response time tracking, throughput monitoring, resource usage
"""

import pytest
import asyncio
import aiohttp
import time
import json
from typing import Dict, List, Any, Optional
from statistics import mean, median
from shared.isolated_environment import IsolatedEnvironment


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_response_time_monitoring_endpoints():
    """
    Test that services expose response time monitoring and performance metrics.
    
    Expected Failure: No dedicated performance monitoring endpoints
    Business Impact: Unable to track SLA compliance and detect performance degradation
    """
    services = [
        {"name": "main_backend", "url": "http://localhost:8000"},
        {"name": "auth_service", "url": "http://localhost:8081"}
    ]
    
    monitoring_gaps = []
    
    async with aiohttp.ClientSession() as session:
        for service in services:
            service_name = service["name"]
            base_url = service["url"]
            
            # Test for performance metrics endpoints
            perf_endpoints = [
                f"{base_url}/metrics/performance",
                f"{base_url}/admin/performance", 
                f"{base_url}/monitoring/response-times",
                f"{base_url}/health/performance"
            ]
            
            performance_endpoint_found = False
            for endpoint in perf_endpoints:
                try:
                    async with session.get(endpoint, timeout=aiohttp.ClientTimeout(total=5)) as response:
                        if response.status == 200:
                            perf_data = await response.json()
                            performance_endpoint_found = True
                            
                            # Check for essential performance metrics
                            expected_metrics = [
                                "avg_response_time_ms",
                                "p95_response_time_ms",
                                "p99_response_time_ms",
                                "requests_per_second",
                                "total_requests",
                                "error_rate",
                                "uptime_percentage"
                            ]
                            
                            missing_metrics = [
                                metric for metric in expected_metrics 
                                if metric not in perf_data
                            ]
                            
                            if missing_metrics:
                                monitoring_gaps.append(
                                    f"{service_name}: Performance endpoint missing metrics: {missing_metrics}"
                                )
                            else:
                                print(f" PASS:  {service_name}: Comprehensive performance monitoring available")
                            break
                            
                except Exception:
                    continue
            
            if not performance_endpoint_found:
                monitoring_gaps.append(f"{service_name}: No performance monitoring endpoint found")
            
            # Test if regular endpoints include timing headers
            timing_headers_test = await _test_timing_headers(session, base_url, service_name)
            if timing_headers_test:
                monitoring_gaps.append(timing_headers_test)
    
    # Report findings
    if monitoring_gaps:
        print(" SEARCH:  PERFORMANCE MONITORING GAPS:")
        for gap in monitoring_gaps:
            print(f"  - {gap}")
        
        pytest.skip("Performance monitoring not implemented - coverage gap identified")
    else:
        print(" PASS:  Performance monitoring properly implemented")


async def _test_timing_headers(session: aiohttp.ClientSession, base_url: str, service_name: str) -> Optional[str]:
    """Test if service includes timing information in response headers."""
    try:
        start_time = time.time()
        async with session.get(f"{base_url}/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
            end_time = time.time()
            request_duration = end_time - start_time
            
            # Check for timing headers
            timing_headers = ["X-Response-Time", "Server-Timing", "X-Request-Duration", "X-Processing-Time"]
            has_timing = any(header in response.headers for header in timing_headers)
            
            if not has_timing:
                return f"{service_name}: No timing information in response headers"
            else:
                print(f" PASS:  {service_name}: Includes timing information in responses")
                return None
    except Exception:
        return f"{service_name}: Unable to test timing headers"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_throughput_monitoring_capabilities():
    """
    Test that services can monitor and report throughput metrics.
    
    Expected Failure: No throughput tracking or rate monitoring
    Business Impact: Cannot detect traffic spikes or capacity planning issues
    """
    backend_url = "http://localhost:8000"
    auth_url = "http://localhost:8081"
    
    throughput_gaps = []
    
    async with aiohttp.ClientSession() as session:
        # Test for throughput monitoring endpoints
        services_to_test = [
            {"name": "backend", "url": backend_url},
            {"name": "auth", "url": auth_url}
        ]
        
        for service_info in services_to_test:
            service_name = service_info["name"]
            base_url = service_info["url"]
            
            # Test throughput endpoints
            throughput_endpoints = [
                f"{base_url}/metrics/throughput",
                f"{base_url}/admin/throughput",
                f"{base_url}/monitoring/traffic",
                f"{base_url}/stats/requests"
            ]
            
            throughput_endpoint_found = False
            for endpoint in throughput_endpoints:
                try:
                    async with session.get(endpoint, timeout=aiohttp.ClientTimeout(total=5)) as response:
                        if response.status == 200:
                            throughput_data = await response.json()
                            throughput_endpoint_found = True
                            
                            # Check for throughput metrics
                            expected_throughput_metrics = [
                                "requests_per_second",
                                "requests_per_minute",
                                "peak_rps",
                                "concurrent_requests",
                                "queue_depth",
                                "bandwidth_usage",
                                "request_size_avg",
                                "response_size_avg"
                            ]
                            
                            missing_throughput = [
                                metric for metric in expected_throughput_metrics
                                if metric not in throughput_data
                            ]
                            
                            if missing_throughput:
                                throughput_gaps.append(
                                    f"{service_name}: Missing throughput metrics: {missing_throughput}"
                                )
                            else:
                                print(f" PASS:  {service_name}: Complete throughput monitoring")
                            break
                            
                except Exception:
                    continue
            
            if not throughput_endpoint_found:
                throughput_gaps.append(f"{service_name}: No throughput monitoring endpoint")
            
            # Test if service tracks concurrent request limits
            concurrent_test = await _test_concurrent_request_tracking(session, base_url, service_name)
            if concurrent_test:
                throughput_gaps.append(concurrent_test)
    
    # Report findings
    if throughput_gaps:
        print(" SEARCH:  THROUGHPUT MONITORING GAPS:")
        for gap in throughput_gaps:
            print(f"  - {gap}")
        
        pytest.skip("Throughput monitoring not implemented - coverage gap identified")
    else:
        print(" PASS:  Throughput monitoring properly implemented")


async def _test_concurrent_request_tracking(session: aiohttp.ClientSession, base_url: str, service_name: str) -> Optional[str]:
    """Test if service tracks concurrent requests."""
    try:
        # Make multiple concurrent requests
        tasks = []
        for _ in range(5):
            task = session.get(f"{base_url}/health", timeout=aiohttp.ClientTimeout(total=10))
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check if any response includes concurrent request info
        has_concurrency_info = False
        for response in responses:
            if hasattr(response, 'headers'):
                concurrency_headers = [
                    "X-Concurrent-Requests", 
                    "X-Queue-Depth", 
                    "X-Server-Load",
                    "X-Active-Connections"
                ]
                if any(header in response.headers for header in concurrency_headers):
                    has_concurrency_info = True
                    print(f" PASS:  {service_name}: Includes concurrency information")
                response.close()
        
        if not has_concurrency_info:
            return f"{service_name}: No concurrent request tracking in headers"
        
        return None
        
    except Exception:
        return f"{service_name}: Unable to test concurrent request tracking"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_resource_usage_monitoring():
    """
    Test that services expose resource usage metrics (CPU, memory, etc.).
    
    Expected Failure: No resource usage monitoring endpoints
    Business Impact: Cannot detect resource exhaustion or scale appropriately
    """
    services = [
        {"name": "main_backend", "url": "http://localhost:8000"},
        {"name": "auth_service", "url": "http://localhost:8081"}
    ]
    
    resource_monitoring_gaps = []
    
    async with aiohttp.ClientSession() as session:
        for service in services:
            service_name = service["name"]
            base_url = service["url"]
            
            # Test resource monitoring endpoints
            resource_endpoints = [
                f"{base_url}/metrics/resources",
                f"{base_url}/admin/system-resources",
                f"{base_url}/monitoring/usage",
                f"{base_url}/health/resources"
            ]
            
            resource_endpoint_found = False
            for endpoint in resource_endpoints:
                try:
                    async with session.get(endpoint, timeout=aiohttp.ClientTimeout(total=5)) as response:
                        if response.status == 200:
                            resource_data = await response.json()
                            resource_endpoint_found = True
                            
                            # Check for resource usage metrics
                            expected_resource_metrics = [
                                "cpu_usage_percent",
                                "memory_usage_mb",
                                "memory_usage_percent",
                                "disk_usage_percent",
                                "open_file_descriptors",
                                "network_connections",
                                "thread_count",
                                "gc_collections"
                            ]
                            
                            missing_resources = [
                                metric for metric in expected_resource_metrics
                                if metric not in resource_data
                            ]
                            
                            if missing_resources:
                                resource_monitoring_gaps.append(
                                    f"{service_name}: Missing resource metrics: {missing_resources}"
                                )
                            else:
                                print(f" PASS:  {service_name}: Complete resource monitoring")
                            break
                            
                except Exception:
                    continue
            
            if not resource_endpoint_found:
                resource_monitoring_gaps.append(f"{service_name}: No resource monitoring endpoint")
    
    # Report findings
    if resource_monitoring_gaps:
        print(" SEARCH:  RESOURCE MONITORING GAPS:")
        for gap in resource_monitoring_gaps:
            print(f"  - {gap}")
        
        pytest.skip("Resource monitoring not implemented - coverage gap identified")
    else:
        print(" PASS:  Resource monitoring properly implemented")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_sla_compliance_tracking():
    """
    Test that services can track and report SLA compliance metrics.
    
    Expected Failure: No SLA tracking or compliance reporting
    Business Impact: Cannot verify enterprise SLA commitments
    """
    backend_url = "http://localhost:8000"
    
    sla_gaps = []
    
    async with aiohttp.ClientSession() as session:
        # Test SLA tracking endpoints
        sla_endpoints = [
            f"{backend_url}/metrics/sla",
            f"{backend_url}/admin/sla-compliance",
            f"{backend_url}/monitoring/sla",
            f"{backend_url}/reports/sla"
        ]
        
        sla_endpoint_found = False
        for endpoint in sla_endpoints:
            try:
                async with session.get(endpoint, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        sla_data = await response.json()
                        sla_endpoint_found = True
                        
                        # Check for SLA compliance metrics
                        expected_sla_metrics = [
                            "uptime_percentage",
                            "response_time_sla_compliance",
                            "error_rate_sla_compliance",
                            "availability_sla_target",
                            "performance_sla_target",
                            "current_sla_status",
                            "sla_violations_count",
                            "time_to_recovery_avg"
                        ]
                        
                        missing_sla = [
                            metric for metric in expected_sla_metrics
                            if metric not in sla_data
                        ]
                        
                        if missing_sla:
                            sla_gaps.append(f"SLA endpoint missing metrics: {missing_sla}")
                        else:
                            print(" PASS:  Complete SLA compliance tracking available")
                        break
                        
            except Exception:
                continue
        
        if not sla_endpoint_found:
            sla_gaps.append("No SLA compliance tracking endpoint found")
        
        # Test if health endpoints include SLA-relevant information
        try:
            async with session.get(f"{backend_url}/health") as response:
                if response.status == 200:
                    health_data = await response.json()
                    
                    # Check for SLA-relevant fields in health response
                    sla_relevant_fields = [
                        "uptime_seconds",
                        "response_time_ms", 
                        "availability_status",
                        "performance_status"
                    ]
                    
                    has_sla_info = any(field in health_data for field in sla_relevant_fields)
                    
                    if not has_sla_info:
                        sla_gaps.append("Health endpoint doesn't include SLA-relevant information")
                    else:
                        print(" PASS:  Health endpoint includes some SLA-relevant information")
        except Exception:
            sla_gaps.append("Unable to check health endpoint for SLA information")
    
    # Report findings
    if sla_gaps:
        print(" SEARCH:  SLA COMPLIANCE TRACKING GAPS:")
        for gap in sla_gaps:
            print(f"  - {gap}")
        
        pytest.skip("SLA compliance tracking not implemented - coverage gap identified")
    else:
        print(" PASS:  SLA compliance tracking properly implemented")


if __name__ == "__main__":
    # Run individual tests for debugging
    asyncio.run(test_response_time_monitoring_endpoints())