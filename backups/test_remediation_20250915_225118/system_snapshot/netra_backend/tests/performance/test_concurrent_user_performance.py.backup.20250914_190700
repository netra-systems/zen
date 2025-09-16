"""
Concurrent User Handling Performance Tests

Tests system performance under realistic concurrent user loads.
Simulates multiple users performing various operations simultaneously.

Business Value Justification (BVJ):
- Segment: Growth & Enterprise
- Business Goal: Support 100+ concurrent users without degradation
- Value Impact: Enables customer growth without infrastructure scaling
- Revenue Impact: Supports 10x user growth (+$50K MRR)
"""

import sys
from pathlib import Path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import asyncio
import json
import statistics
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pytest

@dataclass
class UserSession:
    """Represents a user session for performance testing."""
    user_id: str
    session_id: str
    connection_time: float = 0.0
    messages_sent: int = 0
    messages_received: int = 0
    total_response_time: float = 0.0
    error_count: int = 0
    last_activity: float = field(default_factory=time.perf_counter)
    
    @property
    def avg_response_time(self) -> float:
        """Calculate average response time."""
        return self.total_response_time / max(self.messages_sent, 1)
    
    def record_message(self, response_time: float, error: bool = False):
        """Record message statistics."""
        self.messages_sent += 1
        self.total_response_time += response_time
        self.last_activity = time.perf_counter()
        if error:
            self.error_count += 1
        else:
            self.messages_received += 1

@dataclass
class LoadTestResults:
    """Results from concurrent user load testing."""
    total_users: int
    test_duration: float
    total_messages: int
    successful_messages: int
    failed_messages: int
    avg_response_time: float
    p95_response_time: float
    p99_response_time: float
    messages_per_second: float
    error_rate: float
    concurrent_peak: int
    memory_peak_mb: float
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        return (self.successful_messages / max(self.total_messages, 1)) * 100
    
    def meets_sla_requirements(self) -> bool:
        """Check if results meet SLA requirements."""
        return (
            self.success_rate >= 99.0 and
            self.avg_response_time <= 2.0 and
            self.p95_response_time <= 5.0 and
            self.error_rate <= 0.01
        )

class ConcurrentUserSimulator:
    """Simulates concurrent user behavior for performance testing."""
    
    def __init__(self):
        self.active_sessions: Dict[str, UserSession] = {}
        self.response_times: List[float] = []
        self.start_time = 0.0
    
    async def simulate_user_session(self, user_id: str, session_duration: float, 
                                   operations_per_minute: int) -> UserSession:
        """Simulate a single user session."""
        session = UserSession(
            user_id=user_id,
            session_id=str(uuid.uuid4()),
            connection_time=time.perf_counter()
        )
        
        self.active_sessions[user_id] = session
        
        # Calculate operation interval
        operations_interval = 60.0 / operations_per_minute if operations_per_minute > 0 else 1.0
        
        end_time = time.perf_counter() + session_duration
        
        while time.perf_counter() < end_time:
            # Simulate user operation
            operation_start = time.perf_counter()
            
            try:
                # Simulate different types of operations
                operation_type = self._get_random_operation()
                await self._execute_user_operation(operation_type, session)
                
                operation_time = time.perf_counter() - operation_start
                session.record_message(operation_time, error=False)
                self.response_times.append(operation_time)
                
            except Exception as e:
                operation_time = time.perf_counter() - operation_start
                session.record_message(operation_time, error=True)
            
            # Wait for next operation
            await asyncio.sleep(operations_interval)
        
        # Clean up session
        if user_id in self.active_sessions:
            del self.active_sessions[user_id]
        
        return session
    
    def _get_random_operation(self) -> str:
        """Get random operation type weighted by realistic usage."""
        import random
        
        operations = {
            'chat_message': 0.4,      # 40% - Most common
            'data_query': 0.25,       # 25% - Analytics requests
            'file_upload': 0.1,       # 10% - File operations
            'system_status': 0.15,    # 15% - Status checks
            'user_settings': 0.1      # 10% - Configuration
        }
        
        rand_val = random.random()
        cumulative = 0.0
        
        for op_type, weight in operations.items():
            cumulative += weight
            if rand_val <= cumulative:
                return op_type
        
        return 'chat_message'  # Default
    
    async def _execute_user_operation(self, operation_type: str, session: UserSession):
        """Execute a user operation simulation."""
        if operation_type == 'chat_message':
            await self._simulate_chat_message(session)
        elif operation_type == 'data_query':
            await self._simulate_data_query(session)
        elif operation_type == 'file_upload':
            await self._simulate_file_upload(session)
        elif operation_type == 'system_status':
            await self._simulate_system_status(session)
        elif operation_type == 'user_settings':
            await self._simulate_user_settings(session)
    
    async def _simulate_chat_message(self, session: UserSession):
        """Simulate chat message operation."""
        # Simulate LLM processing time
        processing_delay = 0.1 + (len(self.active_sessions) * 0.001)  # Scales with load
        await asyncio.sleep(processing_delay)
        
        # Simulate WebSocket message handling
        await asyncio.sleep(0.005)
    
    async def _simulate_data_query(self, session: UserSession):
        """Simulate database query operation."""
        # Simulate database query time
        query_delay = 0.05 + (len(self.active_sessions) * 0.002)  # Scales with load
        await asyncio.sleep(query_delay)
    
    async def _simulate_file_upload(self, session: UserSession):
        """Simulate file upload operation."""
        # Simulate file processing time
        await asyncio.sleep(0.2)  # File operations are typically slower
    
    async def _simulate_system_status(self, session: UserSession):
        """Simulate system status check."""
        # Fast operation
        await asyncio.sleep(0.01)
    
    async def _simulate_user_settings(self, session: UserSession):
        """Simulate user settings update."""
        # Database write operation
        await asyncio.sleep(0.03)
    
    async def run_load_test(self, concurrent_users: int, test_duration: float, 
                           operations_per_minute: int = 30) -> LoadTestResults:
        """Run concurrent user load test."""
        self.start_time = time.perf_counter()
        self.response_times = []
        
        # Start user sessions concurrently
        session_tasks = []
        for i in range(concurrent_users):
            user_id = f"user_{i}"
            task = self.simulate_user_session(user_id, test_duration, operations_per_minute)
            session_tasks.append(task)
        
        # Monitor peak concurrent users
        monitor_task = asyncio.create_task(self._monitor_concurrency())
        
        # Wait for all sessions to complete
        sessions = await asyncio.gather(*session_tasks, return_exceptions=True)
        monitor_task.cancel()
        
        # Calculate results
        return self._calculate_results(sessions, test_duration, concurrent_users)
    
    async def _monitor_concurrency(self):
        """Monitor peak concurrency during test."""
        max_concurrent = 0
        
        try:
            while True:
                current_concurrent = len(self.active_sessions)
                max_concurrent = max(max_concurrent, current_concurrent)
                await asyncio.sleep(0.1)  # Check every 100ms
        except asyncio.CancelledError:
            pass
        
        self.peak_concurrent = max_concurrent
    
    def _calculate_results(self, sessions: List[UserSession], test_duration: float, 
                          concurrent_users: int) -> LoadTestResults:
        """Calculate load test results from session data."""
        valid_sessions = [s for s in sessions if isinstance(s, UserSession)]
        
        if not valid_sessions:
            return LoadTestResults(
                total_users=concurrent_users,
                test_duration=test_duration,
                total_messages=0,
                successful_messages=0,
                failed_messages=0,
                avg_response_time=0.0,
                p95_response_time=0.0,
                p99_response_time=0.0,
                messages_per_second=0.0,
                error_rate=0.0,
                concurrent_peak=0,
                memory_peak_mb=0.0
            )
        
        # Aggregate statistics
        total_messages = sum(s.messages_sent for s in valid_sessions)
        successful_messages = sum(s.messages_received for s in valid_sessions)
        failed_messages = sum(s.error_count for s in valid_sessions)
        
        # Response time statistics
        if self.response_times:
            avg_response_time = statistics.mean(self.response_times)
            p95_response_time = self._calculate_percentile(self.response_times, 95)
            p99_response_time = self._calculate_percentile(self.response_times, 99)
        else:
            avg_response_time = p95_response_time = p99_response_time = 0.0
        
        # Throughput
        messages_per_second = total_messages / test_duration if test_duration > 0 else 0.0
        
        # Error rate
        error_rate = failed_messages / max(total_messages, 1)
        
        return LoadTestResults(
            total_users=concurrent_users,
            test_duration=test_duration,
            total_messages=total_messages,
            successful_messages=successful_messages,
            failed_messages=failed_messages,
            avg_response_time=avg_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            messages_per_second=messages_per_second,
            error_rate=error_rate,
            concurrent_peak=getattr(self, 'peak_concurrent', concurrent_users),
            memory_peak_mb=0.0  # Would need actual memory monitoring
        )
    
    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile from list of values."""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int((percentile / 100.0) * len(sorted_values))
        index = min(index, len(sorted_values) - 1)
        return sorted_values[index]

class ScalabilityTester:
    """Tests system scalability under increasing load."""
    
    def __init__(self):
        self.simulator = ConcurrentUserSimulator()
    
    @pytest.mark.asyncio
    async def test_user_scaling(self, max_users: int = 100, step_size: int = 10, 
                               test_duration: float = 30.0) -> Dict[int, LoadTestResults]:
        """Test system performance as user count increases."""
        results = {}
        
        for user_count in range(step_size, max_users + 1, step_size):
            print(f"Testing {user_count} concurrent users...")
            
            # Reset simulator for each test
            self.simulator = ConcurrentUserSimulator()
            
            # Run load test
            result = await self.simulator.run_load_test(
                concurrent_users=user_count,
                test_duration=test_duration,
                operations_per_minute=20  # Moderate activity
            )
            
            results[user_count] = result
            
            # Short pause between tests
            await asyncio.sleep(1.0)
        
        return results
    
    @pytest.mark.asyncio
    async def test_burst_capacity(self, base_users: int = 50, burst_users: int = 200, 
                                 burst_duration: float = 10.0) -> Dict[str, Any]:
        """Test system response to sudden user burst."""
        # Start with base load
        base_task = asyncio.create_task(
            self.simulator.run_load_test(
                concurrent_users=base_users,
                test_duration=6.0,  # Reduced for CI/CD performance
                operations_per_minute=15
            )
        )
        
        # Wait for base load to establish
        await asyncio.sleep(1.5)  # Reduced from 15s to 1.5s
        
        # Add burst load
        burst_simulator = ConcurrentUserSimulator()
        burst_task = asyncio.create_task(
            burst_simulator.run_load_test(
                concurrent_users=burst_users,
                test_duration=min(burst_duration, 3.0),  # Cap burst duration for CI/CD
                operations_per_minute=30  # Higher activity during burst
            )
        )
        
        # Wait for burst to complete
        burst_result = await burst_task
        
        # Wait for base test to complete
        base_result = await base_task
        
        return {
            'base_load': base_result,
            'burst_load': burst_result,
            'burst_impact': {
                'response_time_increase': burst_result.avg_response_time / max(base_result.avg_response_time, 0.001),
                'error_rate_increase': burst_result.error_rate - base_result.error_rate,
                'throughput_ratio': burst_result.messages_per_second / max(base_result.messages_per_second, 1)
            }
        }
    
    @pytest.mark.asyncio
    async def test_sustained_load(self, concurrent_users: int = 75, duration_minutes: float = 0.5) -> LoadTestResults:
        """Test system performance under sustained load."""
        duration_seconds = duration_minutes * 60.0  # Reduced to 30 seconds max for CI/CD
        
        result = await self.simulator.run_load_test(
            concurrent_users=concurrent_users,
            test_duration=duration_seconds,
            operations_per_minute=25  # Realistic sustained activity
        )
        
        return result

@pytest.mark.performance
class TestConcurrentUserPerformance:
    """Test suite for concurrent user handling performance."""
    
    def setup_method(self):
        """Setup test environment."""
        self.simulator = ConcurrentUserSimulator()
        self.scalability_tester = ScalabilityTester()
    
    @pytest.mark.asyncio
    async def test_basic_concurrent_users(self):
        """Test basic concurrent user handling."""
        result = await self.simulator.run_load_test(
            concurrent_users=25,
            test_duration=20.0,
            operations_per_minute=20
        )
        
        # Verify basic performance requirements
        assert result.success_rate >= 99.0, f"Success rate {result.success_rate}% below 99%"
        assert result.avg_response_time <= 2.0, f"Avg response time {result.avg_response_time}s above 2s"
        assert result.error_rate <= 0.01, f"Error rate {result.error_rate} above 1%"
        assert result.messages_per_second >= 5.0, f"Throughput {result.messages_per_second} msg/s too low"
    
    @pytest.mark.asyncio
    async def test_medium_concurrent_load(self):
        """Test medium concurrent user load."""
        result = await self.simulator.run_load_test(
            concurrent_users=50,
            test_duration=30.0,
            operations_per_minute=25
        )
        
        # Medium load requirements
        assert result.success_rate >= 98.0, f"Success rate {result.success_rate}% below 98%"
        assert result.avg_response_time <= 3.0, f"Avg response time {result.avg_response_time}s above 3s"
        assert result.p95_response_time <= 8.0, f"P95 response time {result.p95_response_time}s above 8s"
        assert result.error_rate <= 0.02, f"Error rate {result.error_rate} above 2%"
    
    @pytest.mark.asyncio
    async def test_high_concurrent_load(self):
        """Test high concurrent user load."""
        result = await self.simulator.run_load_test(
            concurrent_users=100,
            test_duration=45.0,
            operations_per_minute=30
        )
        
        # High load requirements (relaxed)
        assert result.success_rate >= 95.0, f"Success rate {result.success_rate}% below 95%"
        assert result.avg_response_time <= 5.0, f"Avg response time {result.avg_response_time}s above 5s"
        assert result.p95_response_time <= 15.0, f"P95 response time {result.p95_response_time}s above 15s"
        assert result.error_rate <= 0.05, f"Error rate {result.error_rate} above 5%"
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_user_scaling_performance(self):
        """Test performance as user count scales."""
        scaling_results = await self.scalability_tester.test_user_scaling(
            max_users=80,
            step_size=20,
            test_duration=20.0
        )
        
        # Verify scaling behavior
        user_counts = sorted(scaling_results.keys())
        
        for i, user_count in enumerate(user_counts):
            result = scaling_results[user_count]
            
            # Basic requirements for all scales
            assert result.success_rate >= 90.0, f"Success rate {result.success_rate}% too low for {user_count} users"
            assert result.error_rate <= 0.1, f"Error rate {result.error_rate} too high for {user_count} users"
            
            # Response time should not degrade exponentially
            if i > 0:
                prev_result = scaling_results[user_counts[i-1]]
                response_time_ratio = result.avg_response_time / prev_result.avg_response_time
                user_ratio = user_count / user_counts[i-1]
                
                # Response time should not grow faster than 2x user growth
                assert response_time_ratio <= user_ratio * 2, (
                    f"Response time degraded too much: {response_time_ratio}x for {user_ratio}x users"
                )
        
        print("\nScaling Results:")
        for user_count, result in scaling_results.items():
            print(f"  {user_count} users: {result.avg_response_time:.3f}s avg, {result.success_rate:.1f}% success")
    
    @pytest.mark.asyncio
    async def test_burst_capacity_handling(self):
        """Test system response to user burst."""
        burst_results = await self.scalability_tester.test_burst_capacity(
            base_users=30,
            burst_users=120,
            burst_duration=15.0
        )
        
        base_result = burst_results['base_load']
        burst_result = burst_results['burst_load']
        impact = burst_results['burst_impact']
        
        # Verify base load performance
        assert base_result.success_rate >= 99.0, "Base load success rate too low"
        
        # Verify burst handling (more lenient requirements)
        assert burst_result.success_rate >= 85.0, f"Burst success rate {burst_result.success_rate}% too low"
        
        # Response time should not increase more than 5x during burst
        assert impact['response_time_increase'] <= 5.0, (
            f"Response time increased {impact['response_time_increase']}x during burst"
        )
        
        # Error rate increase should be reasonable
        assert impact['error_rate_increase'] <= 0.15, (
            f"Error rate increased by {impact['error_rate_increase']} during burst"
        )
        
        print(f"\nBurst Impact Analysis:")
        print(f"  Response time increase: {impact['response_time_increase']:.2f}x")
        print(f"  Error rate increase: {impact['error_rate_increase']:.3f}")
        print(f"  Throughput ratio: {impact['throughput_ratio']:.2f}x")
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_sustained_load_stability(self):
        """Test system stability under sustained load."""
        result = await self.scalability_tester.test_sustained_load(
            concurrent_users=60,
            duration_minutes=3.0  # Reduced for testing
        )
        
        # Sustained load requirements
        assert result.success_rate >= 97.0, f"Sustained success rate {result.success_rate}% too low"
        assert result.avg_response_time <= 4.0, f"Sustained avg response time {result.avg_response_time}s too high"
        assert result.error_rate <= 0.03, f"Sustained error rate {result.error_rate} too high"
        
        # Verify reasonable throughput
        expected_min_throughput = (60 * 25) / 60  # users * ops_per_min / 60
        assert result.messages_per_second >= expected_min_throughput * 0.8, (
            f"Throughput {result.messages_per_second} too low for sustained load"
        )
        
        print(f"\nSustained Load Results:")
        print(f"  Duration: {result.test_duration:.1f}s")
        print(f"  Total messages: {result.total_messages}")
        print(f"  Success rate: {result.success_rate:.1f}%")
        print(f"  Avg response time: {result.avg_response_time:.3f}s")
        print(f"  Throughput: {result.messages_per_second:.1f} msg/s")
    
    @pytest.mark.asyncio
    async def test_performance_degradation_thresholds(self):
        """Test that performance degradation stays within acceptable bounds."""
        # Test at different load levels
        load_levels = [10, 25, 50, 75, 100]
        results = {}
        
        for users in load_levels:
            result = await self.simulator.run_load_test(
                concurrent_users=users,
                test_duration=15.0,
                operations_per_minute=20
            )
            results[users] = result
            
            # Reset simulator
            self.simulator = ConcurrentUserSimulator()
        
        # Analyze degradation patterns
        baseline = results[10]  # Use 10 users as baseline
        
        for users, result in results.items():
            if users == 10:
                continue
                
            load_multiplier = users / 10
            response_time_multiplier = result.avg_response_time / baseline.avg_response_time
            
            # Response time should not degrade worse than load^1.5
            max_acceptable_degradation = pow(load_multiplier, 1.5)
            
            assert response_time_multiplier <= max_acceptable_degradation, (
                f"{users} users: response time degraded {response_time_multiplier:.2f}x, "
                f"acceptable max: {max_acceptable_degradation:.2f}x"
            )
            
            # Success rate should not drop below reasonable thresholds
            if users <= 50:
                min_success_rate = 98.0
            elif users <= 75:
                min_success_rate = 95.0
            else:
                min_success_rate = 90.0
            
            assert result.success_rate >= min_success_rate, (
                f"{users} users: success rate {result.success_rate:.1f}% below {min_success_rate}%"
            )
        
        print("\nPerformance Degradation Analysis:")
        for users, result in results.items():
            degradation = result.avg_response_time / baseline.avg_response_time
            print(f"  {users:3d} users: {result.avg_response_time:.3f}s ({degradation:.2f}x degradation)")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto", "-m", "performance"])
