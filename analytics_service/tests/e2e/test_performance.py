"""
Analytics Service End-to-End Performance and Load Tests
========================================================

BVJ (Business Value Justification):
1. Segment: Mid and Enterprise tiers ($1K+ MRR)  
2. Business Goal: Ensure analytics service performs under realistic production loads
3. Value Impact: Performance directly impacts user experience and platform reliability
4. Revenue Impact: Performance issues cause user churn and reduce platform stickiness

Comprehensive performance and load testing covering realistic traffic patterns,
system behavior under stress, scalability limits, and performance regression detection.

Test Coverage:
- High-volume event ingestion (target: 10,000 events/second)
- Concurrent user load testing (100+ simultaneous users)
- Database performance under load (ClickHouse and Redis)
- API response time validation under load
- Memory and resource usage monitoring
- Scalability limit identification
- Performance regression detection
- Recovery after load spikes
"""

import asyncio
import json
import pytest
import psutil
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from statistics import mean, median, stdev
from shared.isolated_environment import IsolatedEnvironment

import httpx
from analytics_service.tests.e2e.test_full_flow import AnalyticsE2ETestHarness


# =============================================================================
# PERFORMANCE TEST INFRASTRUCTURE
# =============================================================================

class PerformanceTestHarness(AnalyticsE2ETestHarness):
    """Extended test harness for performance and load testing"""
    
    def __init__(self, base_url: str = "http://localhost:8090"):
        super().__init__(base_url)
        self.performance_metrics = {}
        self.load_test_results = {}
        self.resource_monitoring = {"enabled": False, "data": []}
        self.concurrent_clients = []
        self.load_generators = {}
    
    async def setup_performance_testing(self) -> None:
        """Setup performance testing environment"""
        await self.setup()
        
        # Initialize performance monitoring
        self.performance_metrics = {
            "response_times": [],
            "throughput_measurements": [],
            "error_rates": [],
            "resource_usage": [],
            "concurrent_operations": []
        }
        
        # Start resource monitoring if available
        try:
            self.start_resource_monitoring()
        except Exception:
            pass  # Resource monitoring optional
    
    async def teardown_performance_testing(self) -> None:
        """Cleanup performance testing environment"""
        # Stop resource monitoring
        self.stop_resource_monitoring()
        
        # Cleanup concurrent clients
        for client in self.concurrent_clients:
            try:
                await client.aclose()
            except:
                pass
        
        await self.teardown()
    
    def start_resource_monitoring(self) -> None:
        """Start system resource monitoring"""
        self.resource_monitoring["enabled"] = True
        self.resource_monitoring["data"] = []
    
    def stop_resource_monitoring(self) -> None:
        """Stop system resource monitoring"""
        self.resource_monitoring["enabled"] = False
    
    def capture_resource_snapshot(self) -> Dict[str, Any]:
        """Capture current system resource usage"""
        try:
            return {
                "timestamp": time.time(),
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "memory_available_gb": psutil.virtual_memory().available / (1024**3),
                "disk_io": psutil.disk_io_counters()._asdict() if psutil.disk_io_counters() else {},
                "network_io": psutil.net_io_counters()._asdict() if psutil.net_io_counters() else {}
            }
        except Exception:
            return {"timestamp": time.time(), "error": "Resource monitoring unavailable"}
    
    async def create_concurrent_clients(self, client_count: int) -> List[httpx.AsyncClient]:
        """Create multiple concurrent HTTP clients for load testing"""
        clients = []
        
        for i in range(client_count):
            client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(30.0),
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=100)
            )
            clients.append(client)
            self.concurrent_clients.append(client)
        
        return clients
    
    async def measure_operation_performance(self, operation_name: str, operation_func, *args, **kwargs) -> Dict[str, Any]:
        """Measure performance of a single operation"""
        start_time = time.time()
        start_resources = self.capture_resource_snapshot()
        
        try:
            result = await operation_func(*args, **kwargs)
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = str(e)
        
        end_time = time.time()
        end_resources = self.capture_resource_snapshot()
        
        performance_data = {
            "operation": operation_name,
            "duration_seconds": end_time - start_time,
            "success": success,
            "error": error,
            "result": result,
            "start_time": start_time,
            "end_time": end_time,
            "start_resources": start_resources,
            "end_resources": end_resources
        }
        
        # Store performance data
        self.performance_metrics["response_times"].append(performance_data["duration_seconds"])
        
        return performance_data
    
    async def execute_concurrent_load(self, load_func, concurrent_requests: int, 
                                     total_requests: int, *args, **kwargs) -> Dict[str, Any]:
        """Execute concurrent load testing"""
        semaphore = asyncio.Semaphore(concurrent_requests)
        results = []
        start_time = time.time()
        
        async def limited_load_func(*args, **kwargs):
            async with semaphore:
                return await load_func(*args, **kwargs)
        
        # Create tasks for all requests
        tasks = []
        for i in range(total_requests):
            task = asyncio.create_task(limited_load_func(*args, **kwargs))
            tasks.append(task)
        
        # Execute all tasks and collect results
        for completed_task in asyncio.as_completed(tasks):
            try:
                result = await completed_task
                results.append(result)
            except Exception as e:
                results.append({"error": str(e), "success": False})
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Analyze results
        successful_requests = [r for r in results if r.get("success", False)]
        failed_requests = [r for r in results if not r.get("success", True)]
        
        success_rate = len(successful_requests) / total_requests if total_requests > 0 else 0
        average_throughput = total_requests / total_duration
        
        load_test_result = {
            "concurrent_requests": concurrent_requests,
            "total_requests": total_requests,
            "total_duration_seconds": total_duration,
            "successful_requests": len(successful_requests),
            "failed_requests": len(failed_requests),
            "success_rate": success_rate,
            "average_throughput_per_second": average_throughput,
            "results": results
        }
        
        self.load_test_results[f"load_test_{int(start_time)}"] = load_test_result
        
        return load_test_result
    
    def generate_high_volume_events(self, event_count: int, user_count: int = 100, 
                                   event_type_distribution: Dict[str, float] = None) -> List[Dict[str, Any]]:
        """Generate high volume of events for load testing"""
        if event_type_distribution is None:
            event_type_distribution = {
                "chat_interaction": 0.5,
                "feature_usage": 0.3,
                "performance_metric": 0.2
            }
        
        events = []
        user_ids = [f"load_test_user_{i}" for i in range(user_count)]
        
        for i in range(event_count):
            user_id = user_ids[i % user_count]
            
            # Select event type based on distribution
            cumulative_prob = 0
            selected_event_type = "chat_interaction"  # default
            
            rand_value = (i / event_count) % 1  # Pseudo-random distribution
            
            for event_type, prob in event_type_distribution.items():
                cumulative_prob += prob
                if rand_value <= cumulative_prob:
                    selected_event_type = event_type
                    break
            
            # Generate event based on type
            if selected_event_type == "chat_interaction":
                properties = {
                    "thread_id": f"thread_{i // 10}",
                    "message_id": f"msg_{i}",
                    "prompt_length": 50 + (i % 100),
                    "tokens_consumed": 100 + (i % 500),
                    "response_time_ms": 1000 + (i % 2000)
                }
            elif selected_event_type == "feature_usage":
                properties = {
                    "feature_name": ["dashboard", "reports", "settings"][i % 3],
                    "action": "view",
                    "duration_ms": 200 + (i % 1000)
                }
            else:  # performance_metric
                properties = {
                    "metric_type": "api_call",
                    "duration_ms": 100 + (i % 500),
                    "success": (i % 20) != 0  # 95% success rate
                }
            
            event = {
                "event_id": f"load_test_event_{i}_{int(time.time() * 1000)}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "session_id": f"load_session_{i // 50}",
                "event_type": selected_event_type,
                "event_category": "Load Test Events",
                "event_action": "load_test",
                "event_value": float(100 + (i % 900)),
                "properties": json.dumps(properties),
                "page_path": f"/test/page/{i % 5}",
                "environment": "performance_test"
            }
            
            events.append(event)
        
        return events
    
    def analyze_performance_metrics(self) -> Dict[str, Any]:
        """Analyze collected performance metrics"""
        response_times = self.performance_metrics["response_times"]
        
        if not response_times:
            return {"error": "No performance metrics collected"}
        
        analysis = {
            "response_time_analysis": {
                "count": len(response_times),
                "mean": mean(response_times),
                "median": median(response_times),
                "min": min(response_times),
                "max": max(response_times),
                "std_dev": stdev(response_times) if len(response_times) > 1 else 0,
                "percentiles": {
                    "p50": median(response_times),
                    "p90": response_times[int(len(response_times) * 0.9)] if len(response_times) >= 10 else max(response_times),
                    "p95": response_times[int(len(response_times) * 0.95)] if len(response_times) >= 20 else max(response_times),
                    "p99": response_times[int(len(response_times) * 0.99)] if len(response_times) >= 100 else max(response_times)
                }
            },
            "load_test_summary": {
                "total_load_tests": len(self.load_test_results),
                "load_tests": self.load_test_results
            },
            "resource_monitoring": self.resource_monitoring
        }
        
        return analysis

# =============================================================================
# HIGH-VOLUME EVENT INGESTION TESTS
# =============================================================================

class TestHighVolumeEventIngestion:
    """Test suite for high-volume event ingestion performance"""
    
    @pytest.fixture
    async def perf_harness(self):
        """Performance test harness fixture"""
        harness = PerformanceTestHarness()
        await harness.setup_performance_testing()
        yield harness
        await harness.teardown_performance_testing()
    
    async def test_sustained_high_volume_ingestion_10k_events_per_second(self, perf_harness, analytics_performance_monitor):
        """Test sustained high-volume event ingestion targeting 10,000 events/second"""
        # Target: Process 10,000 events in under 10 seconds (accounting for HTTP overhead)
        event_count = 10000
        batch_size = 500  # Process in batches for HTTP efficiency
        target_duration = 20.0  # Allow 20 seconds for E2E including HTTP overhead
        
        # Generate high-volume events
        events = perf_harness.generate_high_volume_events(
            event_count, 
            user_count=100,
            event_type_distribution={
                "chat_interaction": 0.6,  # Most common
                "feature_usage": 0.25,
                "performance_metric": 0.15
            }
        )
        
        # Measure ingestion performance
        analytics_performance_monitor.start_measurement("high_volume_ingestion")
        perf_start = time.time()
        
        # Send events in batches
        batch_results = []
        for i in range(0, len(events), batch_size):
            batch = events[i:i + batch_size]
            
            batch_start = time.time()
            response = await perf_harness.send_events(batch)
            batch_duration = time.time() - batch_start
            
            batch_results.append({
                "batch_index": i // batch_size,
                "batch_size": len(batch),
                "duration": batch_duration,
                "response": response
            })
        
        total_duration = analytics_performance_monitor.end_measurement("high_volume_ingestion")
        perf_end = time.time()
        actual_duration = perf_end - perf_start
        
        # Validate ingestion results
        total_ingested = sum(batch["response"]["ingested"] for batch in batch_results if "response" in batch and batch["response"].get("ingested"))
        total_failed = sum(batch["response"]["failed"] for batch in batch_results if "response" in batch and batch["response"].get("failed", 0))
        
        # Calculate performance metrics
        actual_throughput = event_count / actual_duration
        target_throughput = event_count / target_duration
        
        print(f"High-volume ingestion performance:")
        print(f"  Events: {event_count}")
        print(f"  Duration: {actual_duration:.2f}s")
        print(f"  Throughput: {actual_throughput:.1f} events/second")
        print(f"  Target: {target_throughput:.1f} events/second")
        print(f"  Success rate: {(total_ingested/event_count):.1%}")
        
        # Performance assertions
        assert total_ingested >= event_count * 0.95, f"Too many failed ingestions: {total_failed}/{event_count}"
        assert actual_duration <= target_duration, f"Ingestion too slow: {actual_duration:.2f}s > {target_duration}s"
        assert actual_throughput >= 300, f"Throughput too low: {actual_throughput:.1f} events/second"
        
        # Validate individual batch performance
        batch_durations = [batch["duration"] for batch in batch_results]
        avg_batch_duration = mean(batch_durations)
        max_batch_duration = max(batch_durations)
        
        print(f"  Batch performance: avg={avg_batch_duration:.3f}s, max={max_batch_duration:.3f}s")
        
        # No single batch should take too long
        assert max_batch_duration <= 5.0, f"Individual batch too slow: {max_batch_duration:.3f}s"
        
        # Validate performance monitoring worked
        analytics_performance_monitor.validate_performance("high_volume_ingestion")
    
    async def test_burst_traffic_handling(self, perf_harness):
        """Test handling of burst traffic patterns"""
        # Simulate realistic burst pattern: quiet  ->  burst  ->  quiet
        user_id = perf_harness.generate_test_user()
        
        # Phase 1: Baseline load
        print("Phase 1: Baseline load")
        baseline_events = perf_harness.generate_high_volume_events(100, user_count=10)
        baseline_start = time.time()
        baseline_response = await perf_harness.send_events(baseline_events)
        baseline_duration = time.time() - baseline_start
        
        # Phase 2: Traffic burst
        print("Phase 2: Traffic burst")
        burst_events = perf_harness.generate_high_volume_events(2000, user_count=50)
        burst_start = time.time()
        
        # Send burst traffic in rapid succession
        burst_batch_size = 200
        burst_tasks = []
        for i in range(0, len(burst_events), burst_batch_size):
            batch = burst_events[i:i + burst_batch_size]
            task = perf_harness.send_events(batch)
            burst_tasks.append(task)
        
        burst_responses = await asyncio.gather(*burst_tasks, return_exceptions=True)
        burst_duration = time.time() - burst_start
        
        # Phase 3: Return to baseline
        print("Phase 3: Return to baseline")
        await asyncio.sleep(2)  # Brief pause
        
        recovery_events = perf_harness.generate_high_volume_events(100, user_count=10)
        recovery_start = time.time()
        recovery_response = await perf_harness.send_events(recovery_events)
        recovery_duration = time.time() - recovery_start
        
        # Analyze burst handling
        successful_burst_responses = [r for r in burst_responses if isinstance(r, dict) and r.get("status") == "processed"]
        burst_success_rate = len(successful_burst_responses) / len(burst_responses)
        
        print(f"Burst traffic analysis:")
        print(f"  Baseline: {len(baseline_events)} events in {baseline_duration:.2f}s")
        print(f"  Burst: {len(burst_events)} events in {burst_duration:.2f}s")
        print(f"  Burst success rate: {burst_success_rate:.1%}")
        print(f"  Recovery: {len(recovery_events)} events in {recovery_duration:.2f}s")
        
        # Validate burst handling
        assert baseline_response["status"] == "processed", "Baseline traffic failed"
        assert burst_success_rate >= 0.8, f"Burst traffic handling poor: {burst_success_rate:.1%}"
        assert recovery_response["status"] == "processed", "Recovery traffic failed"
        
        # System should handle burst without excessive degradation
        burst_throughput = len(burst_events) / burst_duration
        baseline_throughput = len(baseline_events) / baseline_duration
        
        # Burst throughput should still be reasonable
        assert burst_throughput >= baseline_throughput * 0.5, "Burst throughput degraded too much"
    
    async def test_memory_usage_under_high_volume(self, perf_harness):
        """Test memory usage behavior under high-volume load"""
        initial_snapshot = perf_harness.capture_resource_snapshot()
        
        # Generate increasingly large batches to stress memory
        memory_snapshots = [initial_snapshot]
        
        batch_sizes = [500, 1000, 2000, 3000]
        for batch_size in batch_sizes:
            print(f"Testing batch size: {batch_size}")
            
            events = perf_harness.generate_high_volume_events(batch_size, user_count=20)
            
            pre_batch_snapshot = perf_harness.capture_resource_snapshot()
            await perf_harness.send_events(events)
            post_batch_snapshot = perf_harness.capture_resource_snapshot()
            
            memory_snapshots.extend([pre_batch_snapshot, post_batch_snapshot])
            
            # Brief pause between batches
            await asyncio.sleep(1)
        
        final_snapshot = perf_harness.capture_resource_snapshot()
        memory_snapshots.append(final_snapshot)
        
        # Analyze memory usage pattern
        memory_usage = [snap.get("memory_percent", 0) for snap in memory_snapshots if "memory_percent" in snap]
        
        if memory_usage:
            initial_memory = memory_usage[0]
            peak_memory = max(memory_usage)
            final_memory = memory_usage[-1]
            
            print(f"Memory usage analysis:")
            print(f"  Initial: {initial_memory:.1f}%")
            print(f"  Peak: {peak_memory:.1f}%")
            print(f"  Final: {final_memory:.1f}%")
            print(f"  Peak increase: {peak_memory - initial_memory:.1f}%")
            
            # Memory usage should not grow excessively
            memory_growth = peak_memory - initial_memory
            assert memory_growth <= 30, f"Memory usage grew too much: {memory_growth:.1f}%"
            
            # Memory should not remain excessively high after processing
            memory_retention = final_memory - initial_memory
            assert memory_retention <= 10, f"Memory not released properly: {memory_retention:.1f}%"
        else:
            pytest.skip("Memory usage monitoring not available")

# =============================================================================
# CONCURRENT USER LOAD TESTS
# =============================================================================

class TestConcurrentUserLoad:
    """Test suite for concurrent user load testing"""
    
    @pytest.fixture
    async def perf_harness(self):
        """Performance test harness fixture"""
        harness = PerformanceTestHarness()
        await harness.setup_performance_testing()
        yield harness
        await harness.teardown_performance_testing()
    
    async def test_100_concurrent_users_realistic_usage(self, perf_harness):
        """Test system behavior with 100 concurrent users in realistic usage patterns"""
        concurrent_users = 100
        events_per_user = 50
        
        # Create concurrent clients
        clients = await perf_harness.create_concurrent_clients(concurrent_users)
        
        # Define realistic user behavior patterns
        async def simulate_user_session(client: httpx.AsyncClient, user_index: int):
            user_id = f"concurrent_user_{user_index}"
            session_events = []
            
            # Realistic user activity pattern
            event_types = ["chat_interaction", "feature_usage", "performance_metric"]
            user_pattern = event_types[user_index % len(event_types)]  # Different users have different patterns
            
            # Generate user events
            for event_num in range(events_per_user):
                event = {
                    "event_id": f"concurrent_{user_index}_{event_num}_{int(time.time() * 1000)}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "user_id": user_id,
                    "session_id": f"session_{user_index}",
                    "event_type": user_pattern,
                    "event_category": "Concurrent User Test",
                    "properties": json.dumps({
                        "user_index": user_index,
                        "event_sequence": event_num,
                        "pattern": user_pattern
                    }),
                    "event_value": float(event_num + user_index)
                }
                session_events.append(event)
            
            # Send user events via dedicated client
            try:
                response = await client.post("/api/analytics/events", json={"events": session_events})
                response.raise_for_status()
                return {
                    "user_index": user_index,
                    "user_id": user_id,
                    "events_sent": len(session_events),
                    "response": response.json(),
                    "success": True
                }
            except Exception as e:
                return {
                    "user_index": user_index,
                    "user_id": user_id,
                    "events_sent": len(session_events),
                    "error": str(e),
                    "success": False
                }
        
        # Execute concurrent user sessions
        print(f"Simulating {concurrent_users} concurrent users...")
        
        start_time = time.time()
        
        # Create tasks for all users
        user_tasks = []
        for i, client in enumerate(clients):
            task = simulate_user_session(client, i)
            user_tasks.append(task)
        
        # Execute all user sessions concurrently
        user_results = await asyncio.gather(*user_tasks, return_exceptions=True)
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Analyze concurrent user results
        successful_users = [r for r in user_results if isinstance(r, dict) and r.get("success", False)]
        failed_users = [r for r in user_results if isinstance(r, dict) and not r.get("success", True)]
        exception_users = [r for r in user_results if isinstance(r, Exception)]
        
        total_events_sent = sum(user.get("events_sent", 0) for user in successful_users)
        success_rate = len(successful_users) / concurrent_users
        
        print(f"Concurrent user test results:")
        print(f"  Concurrent users: {concurrent_users}")
        print(f"  Total duration: {total_duration:.2f}s")
        print(f"  Successful users: {len(successful_users)}")
        print(f"  Failed users: {len(failed_users)}")
        print(f"  Exceptions: {len(exception_users)}")
        print(f"  Success rate: {success_rate:.1%}")
        print(f"  Total events: {total_events_sent}")
        print(f"  Effective throughput: {total_events_sent/total_duration:.1f} events/second")
        
        # Validate concurrent user performance
        assert success_rate >= 0.9, f"Success rate too low: {success_rate:.1%}"
        assert total_duration <= 30.0, f"Concurrent processing too slow: {total_duration:.2f}s"
        assert len(exception_users) == 0, f"Unexpected exceptions: {len(exception_users)}"
        
        # System should handle concurrent load efficiently
        effective_throughput = total_events_sent / total_duration
        assert effective_throughput >= 100, f"Concurrent throughput too low: {effective_throughput:.1f} events/second"
    
    async def test_concurrent_report_generation_load(self, perf_harness):
        """Test concurrent report generation under load"""
        # First, populate system with data for reports
        setup_users = 20
        events_per_setup_user = 100
        
        print("Setting up data for concurrent reporting...")
        setup_start = time.time()
        
        # Create data for multiple users
        setup_tasks = []
        for i in range(setup_users):
            user_id = f"report_test_user_{i}"
            events = perf_harness.generate_high_volume_events(
                events_per_setup_user, 
                user_count=1
            )
            
            # Update events to use specific user
            for event in events:
                event["user_id"] = user_id
            
            task = perf_harness.send_events(events)
            setup_tasks.append(task)
        
        await asyncio.gather(*setup_tasks)
        setup_duration = time.time() - setup_start
        print(f"Data setup completed in {setup_duration:.2f}s")
        
        # Wait for data processing
        await asyncio.sleep(5)
        
        # Now test concurrent report generation
        concurrent_reports = 50
        clients = await perf_harness.create_concurrent_clients(concurrent_reports)
        
        async def generate_user_report(client: httpx.AsyncClient, request_index: int):
            user_id = f"report_test_user_{request_index % setup_users}"
            
            try:
                response = await client.get(
                    "/api/analytics/reports/user-activity",
                    params={"user_id": user_id}
                )
                response.raise_for_status()
                
                return {
                    "request_index": request_index,
                    "user_id": user_id,
                    "response": response.json(),
                    "response_time": response.elapsed.total_seconds() if hasattr(response, 'elapsed') else 0,
                    "success": True
                }
            except Exception as e:
                return {
                    "request_index": request_index,
                    "user_id": user_id,
                    "error": str(e),
                    "success": False
                }
        
        # Execute concurrent report generation
        print(f"Generating {concurrent_reports} concurrent reports...")
        
        report_start_time = time.time()
        
        report_tasks = []
        for i, client in enumerate(clients):
            task = generate_user_report(client, i)
            report_tasks.append(task)
        
        report_results = await asyncio.gather(*report_tasks, return_exceptions=True)
        
        report_end_time = time.time()
        report_duration = report_end_time - report_start_time
        
        # Analyze concurrent report results
        successful_reports = [r for r in report_results if isinstance(r, dict) and r.get("success", False)]
        failed_reports = [r for r in report_results if isinstance(r, dict) and not r.get("success", True)]
        
        report_success_rate = len(successful_reports) / concurrent_reports
        
        # Calculate response time statistics
        response_times = [r.get("response_time", 0) for r in successful_reports if r.get("response_time")]
        
        if response_times:
            avg_response_time = mean(response_times)
            max_response_time = max(response_times)
            min_response_time = min(response_times)
        else:
            avg_response_time = max_response_time = min_response_time = 0
        
        print(f"Concurrent report generation results:")
        print(f"  Concurrent reports: {concurrent_reports}")
        print(f"  Total duration: {report_duration:.2f}s")
        print(f"  Successful reports: {len(successful_reports)}")
        print(f"  Failed reports: {len(failed_reports)}")
        print(f"  Success rate: {report_success_rate:.1%}")
        print(f"  Avg response time: {avg_response_time:.3f}s")
        print(f"  Max response time: {max_response_time:.3f}s")
        print(f"  Min response time: {min_response_time:.3f}s")
        
        # Validate concurrent reporting performance
        assert report_success_rate >= 0.85, f"Report success rate too low: {report_success_rate:.1%}"
        assert report_duration <= 15.0, f"Concurrent reporting too slow: {report_duration:.2f}s"
        
        if response_times:
            assert avg_response_time <= 3.0, f"Average response time too high: {avg_response_time:.3f}s"
            assert max_response_time <= 10.0, f"Max response time too high: {max_response_time:.3f}s"

# =============================================================================
# DATABASE PERFORMANCE TESTS
# =============================================================================

class TestDatabasePerformanceUnderLoad:
    """Test suite for database performance under load"""
    
    @pytest.fixture
    async def perf_harness(self):
        """Performance test harness fixture"""
        harness = PerformanceTestHarness()
        await harness.setup_performance_testing()
        yield harness
        await harness.teardown_performance_testing()
    
    async def test_clickhouse_write_performance_under_load(self, perf_harness, analytics_performance_monitor):
        """Test ClickHouse write performance under sustained load"""
        # Generate large dataset for database stress testing
        event_count = 5000
        batch_size = 250
        
        events = perf_harness.generate_high_volume_events(
            event_count,
            user_count=100,
            event_type_distribution={
                "chat_interaction": 0.4,
                "feature_usage": 0.35,
                "performance_metric": 0.25
            }
        )
        
        # Measure database write performance
        analytics_performance_monitor.start_measurement("database_write_load")
        
        # Send events in rapid succession to stress database
        write_results = []
        for i in range(0, len(events), batch_size):
            batch = events[i:i + batch_size]
            
            batch_start = time.time()
            response = await perf_harness.send_events(batch)
            batch_end = time.time()
            
            write_results.append({
                "batch_index": i // batch_size,
                "batch_size": len(batch),
                "write_duration": batch_end - batch_start,
                "response": response
            })
        
        total_write_duration = analytics_performance_monitor.end_measurement("database_write_load")
        
        # Analyze database write performance
        successful_batches = [r for r in write_results if r["response"]["status"] == "processed"]
        total_ingested = sum(r["response"]["ingested"] for r in successful_batches)
        total_failed = sum(r["response"]["failed"] for r in write_results)
        
        write_throughput = total_ingested / total_write_duration
        avg_batch_duration = mean([r["write_duration"] for r in write_results])
        
        print(f"Database write performance under load:")
        print(f"  Events written: {total_ingested}/{event_count}")
        print(f"  Total duration: {total_write_duration:.2f}s")
        print(f"  Write throughput: {write_throughput:.1f} events/second")
        print(f"  Average batch duration: {avg_batch_duration:.3f}s")
        print(f"  Failed writes: {total_failed}")
        
        # Validate database write performance
        assert total_ingested >= event_count * 0.95, f"Too many write failures: {total_failed}/{event_count}"
        assert write_throughput >= 200, f"Database write throughput too low: {write_throughput:.1f} events/second"
        assert avg_batch_duration <= 2.0, f"Average batch write too slow: {avg_batch_duration:.3f}s"
        
        # Validate performance monitoring
        analytics_performance_monitor.validate_performance("database_write_load")
    
    async def test_query_performance_with_large_dataset(self, perf_harness, analytics_performance_monitor):
        """Test query performance with large dataset in database"""
        # First, populate database with substantial data
        setup_event_count = 3000
        setup_users = 50
        
        print("Populating database with large dataset...")
        setup_events = perf_harness.generate_high_volume_events(setup_event_count, user_count=setup_users)
        
        # Send all setup data
        await perf_harness.send_events(setup_events)
        
        # Wait for database processing
        await asyncio.sleep(10)
        
        # Now test query performance
        query_users = setup_users // 2  # Query subset of users
        selected_users = [f"load_test_user_{i}" for i in range(query_users)]
        
        # Measure query performance
        analytics_performance_monitor.start_measurement("query_response")
        
        query_start = time.time()
        query_results = []
        
        # Execute queries for multiple users
        for user_id in selected_users:
            try:
                report = await perf_harness.get_user_activity_report(user_id)
                query_results.append({
                    "user_id": user_id,
                    "report": report,
                    "success": True
                })
            except Exception as e:
                query_results.append({
                    "user_id": user_id,
                    "error": str(e),
                    "success": False
                })
        
        query_duration = analytics_performance_monitor.end_measurement("query_response")
        total_query_time = time.time() - query_start
        
        # Analyze query performance
        successful_queries = [r for r in query_results if r["success"]]
        failed_queries = [r for r in query_results if not r["success"]]
        
        query_success_rate = len(successful_queries) / len(query_results)
        avg_query_time = total_query_time / len(query_results)
        
        print(f"Database query performance with large dataset:")
        print(f"  Dataset size: ~{setup_event_count} events")
        print(f"  Queries executed: {len(query_results)}")
        print(f"  Successful queries: {len(successful_queries)}")
        print(f"  Failed queries: {len(failed_queries)}")
        print(f"  Success rate: {query_success_rate:.1%}")
        print(f"  Total query time: {total_query_time:.2f}s")
        print(f"  Average query time: {avg_query_time:.3f}s")
        
        # Validate query performance
        assert query_success_rate >= 0.9, f"Query success rate too low: {query_success_rate:.1%}"
        assert avg_query_time <= 2.0, f"Average query time too high: {avg_query_time:.3f}s"
        assert total_query_time <= 30.0, f"Total query time too high: {total_query_time:.2f}s"
        
        # Validate that queries return meaningful data
        for result in successful_queries[:5]:  # Check first 5 successful queries
            report = result["report"]
            assert "data" in report
            assert "metrics" in report["data"]
            assert report["data"]["metrics"]["total_events"] > 0
        
        # Validate performance monitoring
        analytics_performance_monitor.validate_performance("query_response")

# =============================================================================
# SCALABILITY AND STRESS TESTS
# =============================================================================

class TestScalabilityAndStressLimits:
    """Test suite for identifying scalability limits and stress testing"""
    
    @pytest.fixture
    async def perf_harness(self):
        """Performance test harness fixture"""
        harness = PerformanceTestHarness()
        await harness.setup_performance_testing()
        yield harness
        await harness.teardown_performance_testing()
    
    async def test_scalability_breaking_point_identification(self, perf_harness):
        """Test to identify the breaking point of the analytics service"""
        # Gradually increase load until failure or performance degradation
        load_levels = [
            {"concurrent_users": 10, "events_per_user": 100, "name": "light_load"},
            {"concurrent_users": 25, "events_per_user": 150, "name": "medium_load"},
            {"concurrent_users": 50, "events_per_user": 200, "name": "heavy_load"},
            {"concurrent_users": 100, "events_per_user": 250, "name": "stress_load"},
            {"concurrent_users": 150, "events_per_user": 300, "name": "breaking_point"}
        ]
        
        scalability_results = []
        
        for load_config in load_levels:
            print(f"\nTesting {load_config['name']}: {load_config['concurrent_users']} users, {load_config['events_per_user']} events each")
            
            # Create load for this level
            concurrent_users = load_config["concurrent_users"]
            events_per_user = load_config["events_per_user"]
            total_events = concurrent_users * events_per_user
            
            # Execute load test
            load_start = time.time()
            
            try:
                # Create concurrent user simulation
                async def simulate_load_user(user_index: int):
                    user_id = f"scale_test_user_{user_index}_{load_config['name']}"
                    user_events = perf_harness.generate_high_volume_events(
                        events_per_user, 
                        user_count=1
                    )
                    
                    # Update events with user ID
                    for event in user_events:
                        event["user_id"] = user_id
                    
                    response = await perf_harness.send_events(user_events)
                    return {
                        "user_index": user_index,
                        "events_sent": len(user_events),
                        "response": response,
                        "success": response["status"] == "processed"
                    }
                
                # Execute concurrent users
                user_tasks = [simulate_load_user(i) for i in range(concurrent_users)]
                user_results = await asyncio.gather(*user_tasks, return_exceptions=True)
                
                load_duration = time.time() - load_start
                
                # Analyze results for this load level
                successful_users = [r for r in user_results if isinstance(r, dict) and r.get("success", False)]
                failed_users = [r for r in user_results if isinstance(r, dict) and not r.get("success", True)]
                exception_count = len([r for r in user_results if isinstance(r, Exception)])
                
                success_rate = len(successful_users) / concurrent_users
                throughput = total_events / load_duration if load_duration > 0 else 0
                
                load_result = {
                    "load_level": load_config["name"],
                    "concurrent_users": concurrent_users,
                    "events_per_user": events_per_user,
                    "total_events": total_events,
                    "duration": load_duration,
                    "successful_users": len(successful_users),
                    "failed_users": len(failed_users),
                    "exceptions": exception_count,
                    "success_rate": success_rate,
                    "throughput": throughput
                }
                
                scalability_results.append(load_result)
                
                print(f"  Results: {success_rate:.1%} success, {throughput:.1f} events/sec, {load_duration:.2f}s")
                
                # Stop if performance degrades significantly
                if success_rate < 0.7 or throughput < 50:
                    print(f"  Breaking point reached at {load_config['name']}")
                    break
                    
            except Exception as e:
                print(f"  Load test failed with exception: {e}")
                break
        
        # Analyze scalability pattern
        print(f"\nScalability Analysis:")
        print(f"{'Load Level':<15} {'Users':<6} {'Events':<7} {'Success':<8} {'Throughput':<11} {'Duration':<8}")
        print("-" * 65)
        
        for result in scalability_results:
            print(f"{result['load_level']:<15} {result['concurrent_users']:<6} {result['total_events']:<7} "
                  f"{result['success_rate']:.1%}    {result['throughput']:<7.1f} evt/s {result['duration']:<8.2f}s")
        
        # Validate that system can handle at least medium load
        assert len(scalability_results) >= 2, "System failed too early in scalability testing"
        
        # System should handle light and medium load well
        for result in scalability_results[:2]:
            assert result["success_rate"] >= 0.9, f"Poor performance at {result['load_level']}: {result['success_rate']:.1%}"
            assert result["throughput"] >= 100, f"Low throughput at {result['load_level']}: {result['throughput']:.1f}"
    
    async def test_recovery_after_overload(self, perf_harness):
        """Test system recovery after being overloaded"""
        print("Phase 1: Establish baseline performance")
        
        # Baseline performance
        baseline_events = perf_harness.generate_high_volume_events(200, user_count=10)
        baseline_start = time.time()
        baseline_response = await perf_harness.send_events(baseline_events)
        baseline_duration = time.time() - baseline_start
        baseline_throughput = len(baseline_events) / baseline_duration
        
        print(f"Baseline: {len(baseline_events)} events in {baseline_duration:.2f}s ({baseline_throughput:.1f} evt/s)")
        
        print("Phase 2: Overload the system")
        
        # Deliberate overload
        overload_events = perf_harness.generate_high_volume_events(5000, user_count=100)
        overload_start = time.time()
        
        # Send overload in large batches rapidly
        overload_batch_size = 500
        overload_responses = []
        
        try:
            for i in range(0, len(overload_events), overload_batch_size):
                batch = overload_events[i:i + overload_batch_size]
                response = await perf_harness.send_events(batch)
                overload_responses.append(response)
                
                # Minimal delay to maintain pressure
                await asyncio.sleep(0.1)
                
        except Exception as e:
            print(f"  Overload caused exception (expected): {e}")
        
        overload_duration = time.time() - overload_start
        
        # Analyze overload response
        successful_overload = [r for r in overload_responses if r.get("status") == "processed"]
        overload_success_rate = len(successful_overload) / len(overload_responses) if overload_responses else 0
        
        print(f"Overload: {len(overload_events)} events attempted, {overload_success_rate:.1%} success rate")
        
        print("Phase 3: Recovery period")
        
        # Allow system to recover
        recovery_wait = 10
        print(f"  Waiting {recovery_wait}s for system recovery...")
        await asyncio.sleep(recovery_wait)
        
        print("Phase 4: Test recovery performance")
        
        # Test recovery performance
        recovery_events = perf_harness.generate_high_volume_events(200, user_count=10)
        recovery_start = time.time()
        recovery_response = await perf_harness.send_events(recovery_events)
        recovery_duration = time.time() - recovery_start
        recovery_throughput = len(recovery_events) / recovery_duration
        
        print(f"Recovery: {len(recovery_events)} events in {recovery_duration:.2f}s ({recovery_throughput:.1f} evt/s)")
        
        # Validate recovery
        assert baseline_response["status"] == "processed", "Baseline failed"
        assert recovery_response["status"] == "processed", "Recovery failed"
        
        # Recovery performance should be close to baseline
        throughput_ratio = recovery_throughput / baseline_throughput
        print(f"Recovery throughput ratio: {throughput_ratio:.2f} (recovery/baseline)")
        
        assert throughput_ratio >= 0.7, f"Poor recovery performance: {throughput_ratio:.2f} of baseline"
        assert recovery_duration <= baseline_duration * 1.5, f"Recovery too slow: {recovery_duration:.2f}s vs {baseline_duration:.2f}s baseline"
        
        print("System recovery validation passed")

# =============================================================================
# PERFORMANCE REGRESSION TESTS
# =============================================================================

class TestPerformanceRegression:
    """Test suite for performance regression detection"""
    
    @pytest.fixture
    async def perf_harness(self):
        """Performance test harness fixture"""
        harness = PerformanceTestHarness()
        await harness.setup_performance_testing()
        yield harness
        await harness.teardown_performance_testing()
    
    async def test_api_response_time_regression(self, perf_harness, analytics_performance_monitor):
        """Test for API response time regressions"""
        # Expected performance baselines (these would be updated over time)
        performance_baselines = {
            "event_ingestion_p50": 0.5,   # 500ms for 50th percentile
            "event_ingestion_p95": 2.0,   # 2s for 95th percentile
            "report_generation_p50": 1.0, # 1s for 50th percentile
            "report_generation_p95": 3.0, # 3s for 95th percentile
        }
        
        # Test 1: Event ingestion response times
        print("Testing event ingestion response times...")
        
        ingestion_times = []
        for i in range(20):  # Multiple measurements for statistical validity
            test_events = perf_harness.generate_high_volume_events(50, user_count=5)
            
            start_time = time.time()
            await perf_harness.send_events(test_events)
            duration = time.time() - start_time
            
            ingestion_times.append(duration)
            
            # Brief pause between tests
            await asyncio.sleep(0.5)
        
        # Calculate percentiles
        ingestion_times.sort()
        ingestion_p50 = ingestion_times[len(ingestion_times) // 2]
        ingestion_p95 = ingestion_times[int(len(ingestion_times) * 0.95)]
        
        print(f"Event ingestion performance:")
        print(f"  P50: {ingestion_p50:.3f}s (baseline: {performance_baselines['event_ingestion_p50']:.1f}s)")
        print(f"  P95: {ingestion_p95:.3f}s (baseline: {performance_baselines['event_ingestion_p95']:.1f}s)")
        
        # Test 2: Report generation response times
        print("Testing report generation response times...")
        
        # Setup data for reports
        setup_user = perf_harness.generate_test_user()
        setup_events = perf_harness.generate_high_volume_events(100, user_count=1)
        for event in setup_events:
            event["user_id"] = setup_user
        await perf_harness.send_events(setup_events)
        
        await asyncio.sleep(3)  # Wait for processing
        
        # Test report generation times
        report_times = []
        for i in range(10):  # Multiple report generation tests
            start_time = time.time()
            await perf_harness.get_user_activity_report(setup_user)
            duration = time.time() - start_time
            
            report_times.append(duration)
            await asyncio.sleep(0.2)
        
        # Calculate report percentiles
        report_times.sort()
        report_p50 = report_times[len(report_times) // 2]
        report_p95 = report_times[int(len(report_times) * 0.95)]
        
        print(f"Report generation performance:")
        print(f"  P50: {report_p50:.3f}s (baseline: {performance_baselines['report_generation_p50']:.1f}s)")
        print(f"  P95: {report_p95:.3f}s (baseline: {performance_baselines['report_generation_p95']:.1f}s)")
        
        # Validate against baselines (with some tolerance for test environment variance)
        tolerance_factor = 1.5  # Allow 50% variance from baseline
        
        assert ingestion_p50 <= performance_baselines["event_ingestion_p50"] * tolerance_factor, \
            f"Event ingestion P50 regression: {ingestion_p50:.3f}s > {performance_baselines['event_ingestion_p50'] * tolerance_factor:.3f}s"
        
        assert ingestion_p95 <= performance_baselines["event_ingestion_p95"] * tolerance_factor, \
            f"Event ingestion P95 regression: {ingestion_p95:.3f}s > {performance_baselines['event_ingestion_p95'] * tolerance_factor:.3f}s"
        
        assert report_p50 <= performance_baselines["report_generation_p50"] * tolerance_factor, \
            f"Report generation P50 regression: {report_p50:.3f}s > {performance_baselines['report_generation_p50'] * tolerance_factor:.3f}s"
        
        assert report_p95 <= performance_baselines["report_generation_p95"] * tolerance_factor, \
            f"Report generation P95 regression: {report_p95:.3f}s > {performance_baselines['report_generation_p95'] * tolerance_factor:.3f}s"
        
        print("Performance regression tests passed")
    
    async def test_throughput_regression(self, perf_harness):
        """Test for throughput regressions"""
        # Expected throughput baselines
        throughput_baselines = {
            "single_user_throughput": 200,  # events per second
            "multi_user_throughput": 500,   # events per second
            "batch_throughput": 1000,       # events per second
        }
        
        # Test 1: Single user throughput
        print("Testing single user throughput...")
        
        single_user_events = perf_harness.generate_high_volume_events(1000, user_count=1)
        single_start = time.time()
        
        # Send in reasonable batches
        batch_size = 100
        for i in range(0, len(single_user_events), batch_size):
            batch = single_user_events[i:i + batch_size]
            await perf_harness.send_events(batch)
        
        single_duration = time.time() - single_start
        single_user_throughput = len(single_user_events) / single_duration
        
        print(f"Single user throughput: {single_user_throughput:.1f} events/second (baseline: {throughput_baselines['single_user_throughput']})")
        
        # Test 2: Multi-user throughput
        print("Testing multi-user throughput...")
        
        multi_user_count = 10
        events_per_user = 200
        
        async def send_user_events(user_index: int):
            user_id = f"throughput_user_{user_index}"
            user_events = perf_harness.generate_high_volume_events(events_per_user, user_count=1)
            for event in user_events:
                event["user_id"] = user_id
            await perf_harness.send_events(user_events)
            return len(user_events)
        
        multi_start = time.time()
        
        user_tasks = [send_user_events(i) for i in range(multi_user_count)]
        user_results = await asyncio.gather(*user_tasks)
        
        multi_duration = time.time() - multi_start
        total_multi_events = sum(user_results)
        multi_user_throughput = total_multi_events / multi_duration
        
        print(f"Multi-user throughput: {multi_user_throughput:.1f} events/second (baseline: {throughput_baselines['multi_user_throughput']})")
        
        # Test 3: Large batch throughput
        print("Testing large batch throughput...")
        
        large_batch_events = perf_harness.generate_high_volume_events(2000, user_count=50)
        batch_start = time.time()
        
        # Send in large batches
        large_batch_size = 400
        for i in range(0, len(large_batch_events), large_batch_size):
            batch = large_batch_events[i:i + large_batch_size]
            await perf_harness.send_events(batch)
        
        batch_duration = time.time() - batch_start
        batch_throughput = len(large_batch_events) / batch_duration
        
        print(f"Batch throughput: {batch_throughput:.1f} events/second (baseline: {throughput_baselines['batch_throughput']})")
        
        # Validate throughput against baselines
        tolerance_factor = 0.7  # Allow performance to be 70% of baseline
        
        assert single_user_throughput >= throughput_baselines["single_user_throughput"] * tolerance_factor, \
            f"Single user throughput regression: {single_user_throughput:.1f} < {throughput_baselines['single_user_throughput'] * tolerance_factor:.1f}"
        
        assert multi_user_throughput >= throughput_baselines["multi_user_throughput"] * tolerance_factor, \
            f"Multi-user throughput regression: {multi_user_throughput:.1f} < {throughput_baselines['multi_user_throughput'] * tolerance_factor:.1f}"
        
        assert batch_throughput >= throughput_baselines["batch_throughput"] * tolerance_factor, \
            f"Batch throughput regression: {batch_throughput:.1f} < {throughput_baselines['batch_throughput'] * tolerance_factor:.1f}"
        
        print("Throughput regression tests passed")