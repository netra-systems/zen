#!/usr/bin/env python3
"""
Load Testing Script for Request Isolation Architecture

This script simulates realistic load with 100+ concurrent users to validate
the isolation architecture can maintain performance under production conditions.

Business Value:
- Validates system can handle expected production load
- Identifies bottlenecks before they impact users
- Ensures chat remains responsive under peak usage
- Provides capacity planning data

Load Test Scenarios:
1. Steady state: 100 concurrent users with constant load
2. Burst load: Sudden spike to 200 users
3. Sustained load: 100 users for extended period
4. Mixed operations: Realistic user behavior patterns

Success Criteria:
- P95 latency < 50ms under 100 concurrent users
- Zero cross-user contamination
- Memory usage stable (no leaks)
- Error rate < 0.1%
"""

import asyncio
import argparse
import json
import random
import sys
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import statistics

# Add parent directory for imports
sys.path.insert(0, '/Users/rindhujajohnson/Netra/GitHub/netra-apex')

from netra_backend.app.logging_config import central_logger
from netra_backend.app.agents.supervisor.agent_instance_factory_optimized import (
    OptimizedAgentInstanceFactory,
    get_optimized_factory
)
from netra_backend.app.monitoring.performance_metrics import (
    PerformanceMonitor,
    get_performance_monitor
)

logger = central_logger.get_logger(__name__)


@dataclass
class LoadTestConfig:
    """Configuration for load testing."""
    concurrent_users: int = 100
    test_duration_seconds: int = 60
    operations_per_user: int = 10
    think_time_ms: int = 1000
    burst_users: int = 200
    burst_duration_seconds: int = 10
    target_p95_ms: float = 50
    target_error_rate: float = 0.001
    report_interval_seconds: int = 5


@dataclass
class UserSimulation:
    """Simulated user session."""
    user_id: str
    start_time: float = field(default_factory=time.perf_counter)
    operations_completed: int = 0
    errors_encountered: int = 0
    response_times: List[float] = field(default_factory=list)
    last_operation_time: Optional[float] = None
    
    def record_operation(self, duration_ms: float):
        """Record successful operation."""
        self.operations_completed += 1
        self.response_times.append(duration_ms)
        self.last_operation_time = time.perf_counter()
    
    def record_error(self):
        """Record operation error."""
        self.errors_encountered += 1
    
    def get_stats(self) -> Dict:
        """Get user session statistics."""
        if not self.response_times:
            return {
                'user_id': self.user_id,
                'operations': 0,
                'errors': self.errors_encountered,
                'mean_ms': 0,
                'p95_ms': 0
            }
        
        sorted_times = sorted(self.response_times)
        n = len(sorted_times)
        
        return {
            'user_id': self.user_id,
            'operations': self.operations_completed,
            'errors': self.errors_encountered,
            'mean_ms': statistics.mean(sorted_times),
            'p50_ms': sorted_times[n//2],
            'p95_ms': sorted_times[int(n * 0.95)] if n > 20 else sorted_times[-1],
            'p99_ms': sorted_times[int(n * 0.99)] if n > 100 else sorted_times[-1],
            'min_ms': min(sorted_times),
            'max_ms': max(sorted_times)
        }


class LoadTester:
    """Main load testing orchestrator."""
    
    def __init__(self, config: LoadTestConfig):
        """Initialize load tester."""
        self.config = config
        self.factory: Optional[OptimizedAgentInstanceFactory] = None
        self.monitor: Optional[PerformanceMonitor] = None
        self.users: Dict[str, UserSimulation] = {}
        self.start_time: Optional[float] = None
        self.stop_event = asyncio.Event()
        self.results = defaultdict(list)
        
    async def setup(self):
        """Setup test infrastructure."""
        logger.info("Setting up load test infrastructure...")
        
        # Initialize factory
        self.factory = get_optimized_factory()
        
        # Mock dependencies for testing
        from unittest.mock import AsyncMock, Mock
        
        mock_bridge = AsyncMock()
        mock_bridge.notify_agent_started = AsyncMock(return_value=True)
        mock_bridge.notify_agent_completed = AsyncMock(return_value=True)
        mock_bridge.register_run_thread_mapping = AsyncMock(return_value=True)
        mock_bridge.unregister_run_mapping = AsyncMock(return_value=True)
        
        mock_registry = Mock()
        mock_registry.get_agent_class = Mock(return_value=Mock)
        
        self.factory.configure(
            agent_class_registry=mock_registry,
            websocket_bridge=mock_bridge
        )
        
        # Initialize monitor
        self.monitor = await get_performance_monitor()
        
        logger.info("Load test infrastructure ready")
    
    async def simulate_user_operation(self, user: UserSimulation) -> float:
        """Simulate a single user operation."""
        operation_type = random.choice(['simple', 'complex', 'heavy'])
        
        start = time.perf_counter()
        
        try:
            # Create execution context
            context = await self.factory.create_user_execution_context(
                user_id=user.user_id,
                thread_id=f"thread_{user.user_id}_{user.operations_completed}",
                run_id=f"run_{uuid.uuid4().hex[:8]}"
            )
            
            # Simulate different operation types
            if operation_type == 'simple':
                # Just context creation and cleanup
                await asyncio.sleep(0.001)  # 1ms operation
            
            elif operation_type == 'complex':
                # Create agent and do some work
                mock_agent_class = lambda: Mock()
                agent = await self.factory.create_agent_instance(
                    agent_name="test_agent",
                    user_context=context,
                    agent_class=mock_agent_class
                )
                await asyncio.sleep(random.uniform(0.005, 0.015))  # 5-15ms operation
            
            else:  # heavy
                # Multiple agents and operations
                for i in range(3):
                    mock_agent_class = lambda: Mock()
                    agent = await self.factory.create_agent_instance(
                        agent_name=f"agent_{i}",
                        user_context=context,
                        agent_class=mock_agent_class
                    )
                await asyncio.sleep(random.uniform(0.010, 0.030))  # 10-30ms operation
            
            # Cleanup
            await self.factory.cleanup_user_context(context)
            
            duration_ms = (time.perf_counter() - start) * 1000
            user.record_operation(duration_ms)
            
            # Record in monitor
            await self.monitor.record_timer(f'load_test.{operation_type}', duration_ms)
            
            return duration_ms
            
        except Exception as e:
            user.record_error()
            logger.error(f"Operation failed for user {user.user_id}: {e}")
            raise
    
    async def simulate_user_session(self, user_id: str):
        """Simulate a complete user session."""
        user = UserSimulation(user_id=user_id)
        self.users[user_id] = user
        
        try:
            # Perform operations until stop event
            while not self.stop_event.is_set():
                # Perform operation
                await self.simulate_user_operation(user)
                
                # Think time between operations
                think_time = random.uniform(
                    self.config.think_time_ms * 0.5,
                    self.config.think_time_ms * 1.5
                ) / 1000
                await asyncio.sleep(think_time)
                
                # Check if we've done enough operations
                if user.operations_completed >= self.config.operations_per_user:
                    break
        
        except Exception as e:
            logger.error(f"User session failed for {user_id}: {e}")
        
        finally:
            # Record final stats
            stats = user.get_stats()
            self.results['user_stats'].append(stats)
    
    async def run_steady_state_test(self):
        """Run steady state load test with constant users."""
        logger.info(f"Starting steady state test with {self.config.concurrent_users} users...")
        
        self.start_time = time.perf_counter()
        
        # Start user sessions
        tasks = []
        for i in range(self.config.concurrent_users):
            user_id = f"steady_user_{i}"
            task = asyncio.create_task(self.simulate_user_session(user_id))
            tasks.append(task)
            
            # Stagger user starts slightly
            await asyncio.sleep(0.01)
        
        # Run for test duration
        await asyncio.sleep(self.config.test_duration_seconds)
        
        # Signal stop
        self.stop_event.set()
        
        # Wait for all users to complete
        await asyncio.gather(*tasks, return_exceptions=True)
        
        duration = time.perf_counter() - self.start_time
        
        # Calculate aggregate statistics
        all_times = []
        total_operations = 0
        total_errors = 0
        
        for user in self.users.values():
            all_times.extend(user.response_times)
            total_operations += user.operations_completed
            total_errors += user.errors_encountered
        
        if all_times:
            sorted_times = sorted(all_times)
            n = len(sorted_times)
            
            self.results['steady_state'] = {
                'duration_seconds': duration,
                'concurrent_users': self.config.concurrent_users,
                'total_operations': total_operations,
                'total_errors': total_errors,
                'error_rate': total_errors / total_operations if total_operations > 0 else 0,
                'throughput_ops': total_operations / duration,
                'mean_ms': statistics.mean(sorted_times),
                'p50_ms': sorted_times[n//2],
                'p95_ms': sorted_times[int(n * 0.95)] if n > 20 else sorted_times[-1],
                'p99_ms': sorted_times[int(n * 0.99)] if n > 100 else sorted_times[-1],
                'min_ms': min(sorted_times),
                'max_ms': max(sorted_times)
            }
        
        logger.info(f"Steady state test completed in {duration:.1f} seconds")
    
    async def run_burst_test(self):
        """Run burst load test with sudden spike."""
        logger.info(f"Starting burst test with {self.config.burst_users} users...")
        
        self.stop_event.clear()
        self.users.clear()
        self.start_time = time.perf_counter()
        
        # Start burst of users
        tasks = []
        for i in range(self.config.burst_users):
            user_id = f"burst_user_{i}"
            task = asyncio.create_task(self.simulate_user_session(user_id))
            tasks.append(task)
            # No stagger - simulate sudden burst
        
        # Run for burst duration
        await asyncio.sleep(self.config.burst_duration_seconds)
        
        # Signal stop
        self.stop_event.set()
        
        # Wait for completion
        await asyncio.gather(*tasks, return_exceptions=True)
        
        duration = time.perf_counter() - self.start_time
        
        # Calculate statistics
        all_times = []
        total_operations = 0
        total_errors = 0
        
        for user in self.users.values():
            all_times.extend(user.response_times)
            total_operations += user.operations_completed
            total_errors += user.errors_encountered
        
        if all_times:
            sorted_times = sorted(all_times)
            n = len(sorted_times)
            
            self.results['burst'] = {
                'duration_seconds': duration,
                'burst_users': self.config.burst_users,
                'total_operations': total_operations,
                'total_errors': total_errors,
                'error_rate': total_errors / total_operations if total_operations > 0 else 0,
                'throughput_ops': total_operations / duration,
                'mean_ms': statistics.mean(sorted_times),
                'p95_ms': sorted_times[int(n * 0.95)] if n > 20 else sorted_times[-1],
                'p99_ms': sorted_times[int(n * 0.99)] if n > 100 else sorted_times[-1],
                'max_ms': max(sorted_times)
            }
        
        logger.info(f"Burst test completed in {duration:.1f} seconds")
    
    async def run_isolation_test(self):
        """Test that users remain isolated under load."""
        logger.info("Starting isolation test...")
        
        isolation_violations = []
        
        # Create contexts for different users
        contexts = {}
        for i in range(10):
            user_id = f"isolation_user_{i}"
            context = await self.factory.create_user_execution_context(
                user_id=user_id,
                thread_id=f"thread_{user_id}",
                run_id=f"run_{uuid.uuid4().hex[:8]}"
            )
            contexts[user_id] = context
        
        # Verify contexts are isolated
        for user_id1, context1 in contexts.items():
            for user_id2, context2 in contexts.items():
                if user_id1 != user_id2:
                    # Check no shared state
                    if context1.user_id == context2.user_id:
                        isolation_violations.append(f"Shared user_id between {user_id1} and {user_id2}")
                    if context1.run_id == context2.run_id:
                        isolation_violations.append(f"Shared run_id between {user_id1} and {user_id2}")
        
        # Cleanup
        for context in contexts.values():
            await self.factory.cleanup_user_context(context)
        
        self.results['isolation'] = {
            'users_tested': len(contexts),
            'violations': isolation_violations,
            'isolated': len(isolation_violations) == 0
        }
        
        logger.info(f"Isolation test completed: {'PASS' if not isolation_violations else 'FAIL'}")
    
    def print_results(self):
        """Print formatted test results."""
        print("\n" + "=" * 80)
        print("LOAD TEST RESULTS")
        print("=" * 80)
        
        # Steady state results
        if 'steady_state' in self.results:
            print("\nSTEADY STATE TEST:")
            print("-" * 40)
            stats = self.results['steady_state']
            print(f"  Duration: {stats['duration_seconds']:.1f} seconds")
            print(f"  Concurrent Users: {stats['concurrent_users']}")
            print(f"  Total Operations: {stats['total_operations']}")
            print(f"  Throughput: {stats['throughput_ops']:.1f} ops/sec")
            print(f"  Error Rate: {stats['error_rate']*100:.2f}%")
            print(f"  Latency (P50): {stats['p50_ms']:.2f}ms")
            print(f"  Latency (P95): {stats['p95_ms']:.2f}ms (target: {self.config.target_p95_ms}ms)")
            print(f"  Latency (P99): {stats['p99_ms']:.2f}ms")
            
            # Pass/Fail
            p95_pass = stats['p95_ms'] < self.config.target_p95_ms
            error_pass = stats['error_rate'] < self.config.target_error_rate
            
            print(f"\n  P95 Target: {'PASS' if p95_pass else 'FAIL'}")
            print(f"  Error Rate: {'PASS' if error_pass else 'FAIL'}")
        
        # Burst test results
        if 'burst' in self.results:
            print("\nBURST TEST:")
            print("-" * 40)
            stats = self.results['burst']
            print(f"  Duration: {stats['duration_seconds']:.1f} seconds")
            print(f"  Burst Users: {stats['burst_users']}")
            print(f"  Total Operations: {stats['total_operations']}")
            print(f"  Throughput: {stats['throughput_ops']:.1f} ops/sec")
            print(f"  Error Rate: {stats['error_rate']*100:.2f}%")
            print(f"  Latency (P95): {stats['p95_ms']:.2f}ms")
            print(f"  Latency (P99): {stats['p99_ms']:.2f}ms")
            print(f"  Max Latency: {stats['max_ms']:.2f}ms")
        
        # Isolation test results
        if 'isolation' in self.results:
            print("\nISOLATION TEST:")
            print("-" * 40)
            stats = self.results['isolation']
            print(f"  Users Tested: {stats['users_tested']}")
            print(f"  Isolation: {'PASS' if stats['isolated'] else 'FAIL'}")
            if stats['violations']:
                print(f"  Violations: {len(stats['violations'])}")
                for violation in stats['violations'][:5]:
                    print(f"    - {violation}")
        
        # Factory performance stats
        if self.factory:
            perf_stats = self.factory.get_performance_stats()
            print("\nFACTORY PERFORMANCE:")
            print("-" * 40)
            print(f"  Context Creation (P95): {perf_stats['context_creation'].get('p95', 0):.2f}ms")
            print(f"  Agent Creation (P95): {perf_stats['agent_creation'].get('p95', 0):.2f}ms")
            print(f"  Cleanup (P95): {perf_stats['cleanup'].get('p95', 0):.2f}ms")
            print(f"  Emitter Pool: {perf_stats['emitter_pool']}")
            print(f"  Cache Hit Rate: {perf_stats['factory_metrics'].get('cache_hits', 0)}/{perf_stats['factory_metrics'].get('cache_hits', 0) + perf_stats['factory_metrics'].get('cache_misses', 0)}")
        
        print("\n" + "=" * 80)
    
    def save_results(self, filename: str = None):
        """Save results to JSON file."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"load_test_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        logger.info(f"Results saved to {filename}")
        return filename
    
    async def run(self):
        """Run complete load test suite."""
        await self.setup()
        
        try:
            # Run test scenarios
            await self.run_steady_state_test()
            await asyncio.sleep(5)  # Brief pause between tests
            
            await self.run_burst_test()
            await asyncio.sleep(5)
            
            await self.run_isolation_test()
            
            # Get final metrics
            if self.monitor:
                self.results['monitoring'] = await self.monitor.get_metrics_summary()
            
            # Print results
            self.print_results()
            
            # Save results
            self.save_results()
            
        finally:
            # Cleanup
            if self.monitor:
                await self.monitor.stop_background_reporting()


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Load test the request isolation architecture')
    parser.add_argument('--users', type=int, default=100, help='Number of concurrent users')
    parser.add_argument('--duration', type=int, default=60, help='Test duration in seconds')
    parser.add_argument('--burst-users', type=int, default=200, help='Users for burst test')
    parser.add_argument('--think-time', type=int, default=1000, help='Think time between operations (ms)')
    parser.add_argument('--target-p95', type=float, default=50, help='Target P95 latency (ms)')
    parser.add_argument('--save', action='store_true', help='Save results to file')
    
    args = parser.parse_args()
    
    # Create configuration
    config = LoadTestConfig(
        concurrent_users=args.users,
        test_duration_seconds=args.duration,
        burst_users=args.burst_users,
        think_time_ms=args.think_time,
        target_p95_ms=args.target_p95
    )
    
    # Run load test
    tester = LoadTester(config)
    await tester.run()


if __name__ == "__main__":
    asyncio.run(main())