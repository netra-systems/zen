"""
Performance and Concurrency Test Suite for UnifiedWebSocketManager - $500K+ ARR Protection

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Platform scalability protects all revenue
- Business Goal: Ensure platform scales to support business growth and concurrent users
- Value Impact: Performance tests protect $500K+ ARR by preventing system failures under load
- Strategic Impact: MISSION CRITICAL - Platform must scale to support customer growth

This performance test suite validates UnifiedWebSocketManager under realistic load conditions
that could be encountered in production, ensuring the platform can support business growth
without performance degradation that could cause customer churn.

PERFORMANCE CRITICAL AREAS (10/10 Business Criticality):
1. Concurrent User Scalability (supports business growth to 1000+ concurrent users)
2. Message Throughput Under Load (maintains chat responsiveness during peak usage)
3. Memory Management at Scale (prevents crashes during high-usage periods)
4. Connection Pool Efficiency (optimizes resource usage for cost management)
5. Race Condition Prevention (ensures data integrity under concurrent access)
6. Error Recovery Performance (maintains availability during partial failures)
7. Network Latency Tolerance (works across global user base)
8. Resource Leak Prevention (ensures long-term stability and cost control)
9. Degraded Mode Performance (maintains service during infrastructure issues)
10. Business Value Delivery Speed (fast response times improve user satisfaction)

Performance SLAs to Protect Revenue:
- Connection establishment: < 2 seconds (prevents user abandonment)
- Message delivery: < 500ms (maintains chat responsiveness) 
- Concurrent users: 100+ without degradation (supports current scale)
- Memory usage: < 1GB for 100 connections (cost efficiency)
- Error recovery: < 5 seconds (maintains user confidence)
"""

import asyncio
import pytest
import time
import uuid
import json
import threading
import psutil
import os
import gc
import weakref
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Union
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import statistics
from contextlib import asynccontextmanager
import websockets
import aiohttp
import resource

# SSOT Imports - Following CLAUDE.md absolute import requirements
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import RealServicesTestFixtures
from shared.isolated_environment import get_env
from shared.types.core_types import (
    UserID, ThreadID, ConnectionID, WebSocketID, RequestID,
    ensure_user_id, ensure_thread_id, ensure_websocket_id
)

# System Under Test - SSOT imports
from netra_backend.app.websocket_core.unified_manager import (
    UnifiedWebSocketManager,
    WebSocketConnection,
    WebSocketManagerMode
)

# Performance Monitoring Imports
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics for business value analysis."""
    operation_name: str
    start_time: float
    end_time: float
    success: bool
    error: Optional[str] = None
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    
    @property
    def duration_ms(self) -> float:
        """Get operation duration in milliseconds."""
        return (self.end_time - self.start_time) * 1000
        
    @property 
    def meets_sla(self) -> bool:
        """Check if operation meets business SLA requirements."""
        sla_requirements = {
            'connection_establishment': 2000,  # 2 seconds
            'message_delivery': 500,           # 500ms
            'user_isolation': 100,             # 100ms
            'error_recovery': 5000,            # 5 seconds
            'concurrent_operation': 1000       # 1 second
        }
        
        return self.duration_ms <= sla_requirements.get(self.operation_name, 1000)


class PerformanceMonitor:
    """Monitor system performance during testing."""
    
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.baseline_memory = self.process.memory_info().rss
        self.metrics = []
        
    def start_operation(self, operation_name: str) -> str:
        """Start monitoring an operation."""
        operation_id = str(uuid.uuid4())
        return operation_id
        
    def end_operation(self, operation_id: str, operation_name: str, success: bool, error: str = None) -> PerformanceMetrics:
        """End monitoring and record metrics."""
        current_memory = self.process.memory_info().rss
        cpu_usage = self.process.cpu_percent()
        
        metrics = PerformanceMetrics(
            operation_name=operation_name,
            start_time=time.time(),
            end_time=time.time(),
            success=success,
            error=error,
            memory_usage_mb=(current_memory - self.baseline_memory) / (1024 * 1024),
            cpu_usage_percent=cpu_usage
        )
        
        self.metrics.append(metrics)
        return metrics
        
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get summary of all performance metrics."""
        if not self.metrics:
            return {}
            
        successful_operations = [m for m in self.metrics if m.success]
        failed_operations = [m for m in self.metrics if not m.success]
        
        durations = [m.duration_ms for m in successful_operations]
        memory_usage = [m.memory_usage_mb for m in self.metrics]
        
        return {
            'total_operations': len(self.metrics),
            'successful_operations': len(successful_operations),
            'failed_operations': len(failed_operations),
            'success_rate': len(successful_operations) / len(self.metrics) * 100 if self.metrics else 0,
            'average_duration_ms': statistics.mean(durations) if durations else 0,
            'median_duration_ms': statistics.median(durations) if durations else 0,
            'p95_duration_ms': statistics.quantiles(durations, n=20)[18] if len(durations) >= 20 else max(durations) if durations else 0,
            'max_duration_ms': max(durations) if durations else 0,
            'average_memory_mb': statistics.mean(memory_usage) if memory_usage else 0,
            'max_memory_mb': max(memory_usage) if memory_usage else 0,
            'sla_compliance_rate': sum(1 for m in successful_operations if m.meets_sla) / len(successful_operations) * 100 if successful_operations else 0
        }


class LoadTestWebSocketServer:
    """WebSocket server optimized for load testing."""
    
    def __init__(self, port: int = 0):
        self.port = port
        self.server = None
        self.connected_clients = {}
        self.message_count = 0
        self.start_time = None
        
    async def start(self) -> int:
        """Start the load test WebSocket server."""
        async def handle_client(websocket, path):
            client_id = str(uuid.uuid4())
            self.connected_clients[client_id] = {
                'websocket': websocket,
                'connected_at': datetime.now(timezone.utc),
                'message_count': 0
            }
            
            try:
                async for message in websocket:
                    self.message_count += 1
                    self.connected_clients[client_id]['message_count'] += 1
                    
                    # Echo back for latency testing
                    response = {
                        'type': 'echo',
                        'original_message': json.loads(message),
                        'server_timestamp': datetime.now(timezone.utc).isoformat(),
                        'message_id': self.message_count
                    }
                    
                    await websocket.send(json.dumps(response))
                    
            except websockets.exceptions.ConnectionClosed:
                pass
            finally:
                if client_id in self.connected_clients:
                    del self.connected_clients[client_id]
        
        self.server = await websockets.serve(handle_client, "localhost", self.port or 0)
        
        if self.port == 0:
            self.port = self.server.sockets[0].getsockname()[1]
            
        self.start_time = time.time()
        logger.info(f"Load test WebSocket server started on port {self.port}")
        return self.port
        
    async def stop(self):
        """Stop the load test server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            
    def get_server_stats(self) -> Dict[str, Any]:
        """Get server performance statistics."""
        uptime = time.time() - self.start_time if self.start_time else 0
        
        return {
            'connected_clients': len(self.connected_clients),
            'total_messages': self.message_count,
            'uptime_seconds': uptime,
            'messages_per_second': self.message_count / uptime if uptime > 0 else 0,
            'client_details': {
                client_id: {
                    'connected_duration': (datetime.now(timezone.utc) - client['connected_at']).total_seconds(),
                    'message_count': client['message_count']
                }
                for client_id, client in self.connected_clients.items()
            }
        }


@pytest.mark.performance 
class TestUnifiedWebSocketManagerPerformanceConcurrency(BaseIntegrationTest):
    """Performance and concurrency test suite for UnifiedWebSocketManager."""
    
    async def setUp(self):
        """Set up performance testing environment."""
        await super().setUp()
        self.manager = UnifiedWebSocketManager()
        self.performance_monitor = PerformanceMonitor()
        self.load_server = LoadTestWebSocketServer()
        self.server_port = await self.load_server.start()
        
    async def tearDown(self):
        """Clean up performance testing environment."""
        await self.load_server.stop()
        
        # Generate performance report
        performance_summary = self.performance_monitor.get_performance_summary()
        if performance_summary:
            logger.info(f"Performance Summary: {json.dumps(performance_summary, indent=2)}")
            
        await super().tearDown()
        
    # ========== HIGH-LOAD PERFORMANCE TESTS ==========
    
    async def test_concurrent_user_scalability_protects_business_growth_performance_critical(self):
        """
        PERFORMANCE CRITICAL: Test concurrent user scalability to support business growth.
        
        Business Value: Platform must support 100+ concurrent users without degradation.
        Can Fail: If scalability breaks, platform cannot grow beyond current customer base.
        """
        num_concurrent_users = 50  # Conservative for testing, production target is 100+
        concurrent_connections = []
        connection_times = []
        
        logger.info(f"Testing scalability with {num_concurrent_users} concurrent users")
        
        # Phase 1: Establish all connections concurrently
        async def create_connection(user_index: int) -> tuple:
            user_id = ensure_user_id(f"scale-user-{user_index}")
            
            connection_start = time.time()
            
            try:
                # Create real WebSocket connection
                websocket = await websockets.connect(f"ws://localhost:{self.server_port}")
                
                connection = WebSocketConnection(
                    connection_id=str(uuid.uuid4()),
                    user_id=user_id,
                    websocket=websocket,
                    connected_at=datetime.now(timezone.utc),
                    metadata={"performance_test": True, "user_index": user_index}
                )
                
                await self.manager.add_connection(connection)
                
                connection_time = time.time() - connection_start
                connection_times.append(connection_time)
                
                return (user_id, connection, websocket, True, None)
                
            except Exception as e:
                connection_time = time.time() - connection_start
                connection_times.append(connection_time)
                return (user_id, None, None, False, str(e))
        
        # Create all connections concurrently
        scale_start = time.time()
        connection_results = await asyncio.gather(*[
            create_connection(i) for i in range(num_concurrent_users)
        ], return_exceptions=True)
        total_connection_time = time.time() - scale_start
        
        # Analyze connection performance
        successful_connections = []
        failed_connections = []
        
        for result in connection_results:
            if isinstance(result, Exception):
                failed_connections.append(str(result))
            else:
                user_id, connection, websocket, success, error = result
                if success:
                    successful_connections.append((user_id, connection, websocket))
                else:
                    failed_connections.append(error)
        
        success_rate = len(successful_connections) / num_concurrent_users
        avg_connection_time = statistics.mean(connection_times) if connection_times else 0
        p95_connection_time = statistics.quantiles(connection_times, n=20)[18] if len(connection_times) >= 20 else max(connection_times) if connection_times else 0
        
        # Performance assertions for business scalability
        self.assertGreaterEqual(success_rate, 0.9, 
                               f"Connection success rate below business requirement: {success_rate:.1%} "
                               f"(need 90%+ for scalability)")
        
        self.assertLess(avg_connection_time, 2.0,
                       f"Average connection time exceeds SLA: {avg_connection_time:.2f}s "
                       f"(SLA: 2s for user retention)")
        
        self.assertLess(p95_connection_time, 5.0,
                       f"95th percentile connection time too high: {p95_connection_time:.2f}s "
                       f"(impacts user experience)")
        
        logger.info(f"Scalability Results: {success_rate:.1%} success, "
                   f"avg {avg_connection_time:.2f}s, p95 {p95_connection_time:.2f}s")
        
        # Phase 2: Test message throughput under load
        if successful_connections:
            message_tasks = []
            messages_per_user = 10
            
            throughput_start = time.time()
            
            for user_id, connection, websocket in successful_connections:
                for msg_num in range(messages_per_user):
                    message = {
                        "type": "scalability_test",
                        "user_id": user_id,
                        "message_number": msg_num,
                        "business_data": f"Critical business message {msg_num}",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    message_tasks.append(self.manager.send_to_user(user_id, message))
            
            # Send all messages concurrently
            message_results = await asyncio.gather(*message_tasks, return_exceptions=True)
            throughput_time = time.time() - throughput_start
            
            # Analyze message throughput
            successful_messages = sum(1 for result in message_results 
                                    if not isinstance(result, Exception))
            total_messages = len(message_tasks)
            message_success_rate = successful_messages / total_messages
            messages_per_second = successful_messages / throughput_time
            
            # Throughput assertions for business performance
            self.assertGreaterEqual(message_success_rate, 0.95,
                                   f"Message success rate below business requirement: {message_success_rate:.1%}")
            
            self.assertGreater(messages_per_second, 50,
                              f"Message throughput below business requirement: {messages_per_second:.1f} msg/s "
                              f"(need 50+ for responsive chat)")
            
            logger.info(f"Throughput Results: {message_success_rate:.1%} success, "
                       f"{messages_per_second:.1f} msg/s")
        
        # Clean up connections
        cleanup_tasks = []
        for user_id, connection, websocket in successful_connections:
            cleanup_tasks.append(websocket.close())
        
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
    async def test_memory_management_prevents_resource_exhaustion_performance_critical(self):
        """
        PERFORMANCE CRITICAL: Test memory management under sustained load.
        
        Business Value: Prevents crashes that could cause service outages and revenue loss.
        Can Fail: If memory leaks exist, platform crashes during extended usage.
        """
        process = psutil.Process(os.getpid())
        baseline_memory = process.memory_info().rss
        memory_samples = []
        
        # Test with sustained connection churn
        num_iterations = 20
        connections_per_iteration = 10
        
        logger.info(f"Testing memory management with {num_iterations} iterations of {connections_per_iteration} connections")
        
        for iteration in range(num_iterations):
            iteration_connections = []
            
            # Create connections
            for i in range(connections_per_iteration):
                user_id = ensure_user_id(f"memory-test-{iteration}-{i}")
                
                websocket = await websockets.connect(f"ws://localhost:{self.server_port}")
                
                connection = WebSocketConnection(
                    connection_id=str(uuid.uuid4()),
                    user_id=user_id,
                    websocket=websocket,
                    connected_at=datetime.now(timezone.utc),
                    metadata={"memory_test": True, "iteration": iteration}
                )
                
                await self.manager.add_connection(connection)
                iteration_connections.append((user_id, connection, websocket))
            
            # Send messages to stress memory
            for user_id, connection, websocket in iteration_connections:
                message = {
                    "type": "memory_stress_test",
                    "user_id": user_id,
                    "iteration": iteration,
                    "large_payload": ["data"] * 100,  # Create some memory pressure
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                await self.manager.send_to_user(user_id, message)
            
            # Clean up connections
            for user_id, connection, websocket in iteration_connections:
                await self.manager.remove_connection(connection.connection_id)
                await websocket.close()
            
            # Force garbage collection
            gc.collect()
            
            # Sample memory usage
            current_memory = process.memory_info().rss
            memory_increase_mb = (current_memory - baseline_memory) / (1024 * 1024)
            memory_samples.append(memory_increase_mb)
            
            # Log progress every 5 iterations
            if (iteration + 1) % 5 == 0:
                logger.info(f"Iteration {iteration + 1}/{num_iterations}: "
                           f"Memory increase: {memory_increase_mb:.1f}MB")
        
        # Analyze memory usage patterns
        final_memory_increase = memory_samples[-1]
        max_memory_increase = max(memory_samples)
        avg_memory_increase = statistics.mean(memory_samples)
        
        # Memory management assertions for business stability
        self.assertLess(final_memory_increase, 100,
                       f"Final memory increase too high: {final_memory_increase:.1f}MB "
                       f"(indicates memory leak)")
        
        self.assertLess(max_memory_increase, 200,
                       f"Peak memory usage too high: {max_memory_increase:.1f}MB "
                       f"(could cause crashes)")
        
        # Check for memory leaks (memory should not grow linearly)
        if len(memory_samples) >= 10:
            first_half = memory_samples[:len(memory_samples)//2]
            second_half = memory_samples[len(memory_samples)//2:]
            
            first_half_avg = statistics.mean(first_half)
            second_half_avg = statistics.mean(second_half)
            
            memory_growth_rate = (second_half_avg - first_half_avg) / len(second_half)
            
            self.assertLess(memory_growth_rate, 5.0,
                           f"Memory growth rate indicates leak: {memory_growth_rate:.2f}MB per iteration")
        
        logger.info(f"Memory Management Results: Final {final_memory_increase:.1f}MB, "
                   f"Peak {max_memory_increase:.1f}MB, Avg {avg_memory_increase:.1f}MB")
        
    async def test_race_condition_prevention_ensures_data_integrity_performance_critical(self):
        """
        PERFORMANCE CRITICAL: Test race condition prevention under concurrent access.
        
        Business Value: Ensures data integrity during concurrent operations.
        Can Fail: If race conditions exist, user data could be corrupted or lost.
        """
        num_concurrent_operations = 20
        operations_per_thread = 10
        shared_user_id = ensure_user_id("race-condition-test-user")
        
        # Results tracking
        successful_operations = []
        failed_operations = []
        data_integrity_violations = []
        
        async def concurrent_connection_operations(thread_id: int):
            """Perform concurrent connection operations that could race."""
            thread_results = []
            
            for op_num in range(operations_per_thread):
                operation_start = time.time()
                
                try:
                    # Create connection
                    websocket = await websockets.connect(f"ws://localhost:{self.server_port}")
                    
                    connection_id = f"race-test-{thread_id}-{op_num}"
                    connection = WebSocketConnection(
                        connection_id=connection_id,
                        user_id=shared_user_id,
                        websocket=websocket,
                        connected_at=datetime.now(timezone.utc),
                        metadata={"thread_id": thread_id, "operation": op_num}
                    )
                    
                    # Add connection (potential race condition)
                    await self.manager.add_connection(connection)
                    
                    # Verify connection is tracked
                    user_connections = self.manager.get_user_connections(shared_user_id)
                    if connection_id not in user_connections:
                        data_integrity_violations.append(
                            f"Thread {thread_id} Op {op_num}: Connection not tracked after add"
                        )
                    
                    # Send message (potential race condition)
                    message = {
                        "type": "race_condition_test",
                        "thread_id": thread_id,
                        "operation": op_num,
                        "connection_id": connection_id,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
                    await self.manager.send_to_user(shared_user_id, message)
                    
                    # Remove connection (potential race condition)
                    await self.manager.remove_connection(connection_id)
                    
                    # Verify connection is removed
                    user_connections_after = self.manager.get_user_connections(shared_user_id)
                    if connection_id in user_connections_after:
                        data_integrity_violations.append(
                            f"Thread {thread_id} Op {op_num}: Connection not removed after delete"
                        )
                    
                    await websocket.close()
                    
                    operation_time = time.time() - operation_start
                    thread_results.append({
                        'thread_id': thread_id,
                        'operation': op_num,
                        'success': True,
                        'duration': operation_time
                    })
                    
                except Exception as e:
                    operation_time = time.time() - operation_start
                    thread_results.append({
                        'thread_id': thread_id,
                        'operation': op_num,
                        'success': False,
                        'error': str(e),
                        'duration': operation_time
                    })
            
            return thread_results
        
        # Run concurrent operations
        race_test_start = time.time()
        
        operation_tasks = [
            concurrent_connection_operations(thread_id)
            for thread_id in range(num_concurrent_operations)
        ]
        
        thread_results = await asyncio.gather(*operation_tasks, return_exceptions=True)
        total_race_test_time = time.time() - race_test_start
        
        # Analyze race condition results
        for thread_result in thread_results:
            if isinstance(thread_result, Exception):
                failed_operations.append(str(thread_result))
            else:
                for operation_result in thread_result:
                    if operation_result['success']:
                        successful_operations.append(operation_result)
                    else:
                        failed_operations.append(operation_result)
        
        total_operations = num_concurrent_operations * operations_per_thread
        success_rate = len(successful_operations) / total_operations
        operations_per_second = len(successful_operations) / total_race_test_time
        
        # Race condition assertions for data integrity
        self.assertEqual(len(data_integrity_violations), 0,
                        f"Data integrity violations detected: {data_integrity_violations[:10]}... "
                        f"(showing first 10 of {len(data_integrity_violations)})")
        
        self.assertGreaterEqual(success_rate, 0.9,
                               f"Race condition test success rate too low: {success_rate:.1%}")
        
        # Verify final state consistency
        final_user_connections = self.manager.get_user_connections(shared_user_id)
        self.assertEqual(len(final_user_connections), 0,
                        f"Connections remaining after cleanup: {len(final_user_connections)} "
                        f"(indicates race condition in cleanup)")
        
        logger.info(f"Race Condition Results: {success_rate:.1%} success, "
                   f"{operations_per_second:.1f} ops/s, "
                   f"{len(data_integrity_violations)} violations")
        
    async def test_error_recovery_performance_maintains_availability_performance_critical(self):
        """
        PERFORMANCE CRITICAL: Test error recovery performance under failure conditions.
        
        Business Value: Maintains service availability during partial failures.
        Can Fail: If error recovery is slow, service appears down during issues.
        """
        num_connections = 20
        connections = []
        
        # Create stable connections
        for i in range(num_connections):
            user_id = ensure_user_id(f"recovery-test-user-{i}")
            websocket = await websockets.connect(f"ws://localhost:{self.server_port}")
            
            connection = WebSocketConnection(
                connection_id=str(uuid.uuid4()),
                user_id=user_id,
                websocket=websocket,
                connected_at=datetime.now(timezone.utc),
                metadata={"recovery_test": True}
            )
            
            await self.manager.add_connection(connection)
            connections.append((user_id, connection, websocket))
        
        # Simulate various failure scenarios
        failure_scenarios = [
            ("connection_failure", lambda ws: ws.close()),
            ("network_timeout", lambda ws: asyncio.create_task(ws.close())),
        ]
        
        recovery_times = []
        service_availability_during_failures = []
        
        for scenario_name, failure_simulator in failure_scenarios:
            logger.info(f"Testing error recovery for scenario: {scenario_name}")
            
            # Select random connections to fail
            failing_connections = connections[:num_connections//4]  # Fail 25% of connections
            healthy_connections = connections[num_connections//4:]
            
            # Simulate failures
            failure_start = time.time()
            
            for user_id, connection, websocket in failing_connections:
                try:
                    await failure_simulator(websocket)
                except:
                    pass  # Expected failures
            
            # Measure recovery time - how long until system detects and handles failures
            recovery_start = time.time()
            
            # Try to send messages to all users (including failed ones)
            message_results = []
            for user_id, connection, websocket in connections:
                try:
                    message = {
                        "type": "recovery_test",
                        "scenario": scenario_name,
                        "user_id": user_id,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
                    await self.manager.send_to_user(user_id, message)
                    message_results.append(True)
                except Exception as e:
                    message_results.append(False)
            
            recovery_time = time.time() - recovery_start
            recovery_times.append(recovery_time)
            
            # Check service availability for healthy connections
            healthy_success_count = sum(1 for i, (user_id, _, _) in enumerate(healthy_connections) 
                                      if i + num_connections//4 < len(message_results) and 
                                      message_results[i + num_connections//4])
            
            healthy_availability = healthy_success_count / len(healthy_connections) if healthy_connections else 0
            service_availability_during_failures.append(healthy_availability)
            
            logger.info(f"Scenario {scenario_name}: Recovery {recovery_time:.2f}s, "
                       f"Healthy availability {healthy_availability:.1%}")
        
        # Error recovery performance assertions
        avg_recovery_time = statistics.mean(recovery_times) if recovery_times else 0
        avg_availability = statistics.mean(service_availability_during_failures) if service_availability_during_failures else 0
        
        self.assertLess(avg_recovery_time, 5.0,
                       f"Error recovery too slow: {avg_recovery_time:.2f}s (SLA: 5s)")
        
        self.assertGreaterEqual(avg_availability, 0.9,
                               f"Service availability during failures too low: {avg_availability:.1%} "
                               f"(need 90%+ for business continuity)")
        
        # Clean up remaining connections
        for user_id, connection, websocket in connections:
            try:
                await websocket.close()
            except:
                pass
        
    # ========== STANDARD PERFORMANCE TESTS ==========
    
    async def test_message_delivery_latency_meets_chat_responsiveness_sla(self):
        """Test message delivery latency meets chat responsiveness requirements."""
        num_test_messages = 100
        user_id = ensure_user_id("latency-test-user")
        
        websocket = await websockets.connect(f"ws://localhost:{self.server_port}")
        connection = WebSocketConnection(
            connection_id=str(uuid.uuid4()),
            user_id=user_id,
            websocket=websocket,
            connected_at=datetime.now(timezone.utc)
        )
        
        await self.manager.add_connection(connection)
        
        # Measure message delivery latencies
        latencies = []
        
        for i in range(num_test_messages):
            send_start = time.time()
            
            message = {
                "type": "latency_test",
                "message_id": i,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await self.manager.send_to_user(user_id, message)
            
            # For latency testing, we measure send completion time
            send_latency = (time.time() - send_start) * 1000  # Convert to ms
            latencies.append(send_latency)
            
            # Small delay between messages
            await asyncio.sleep(0.01)
        
        # Analyze latency distribution
        avg_latency = statistics.mean(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies)
        max_latency = max(latencies)
        
        # Chat responsiveness assertions
        self.assertLess(avg_latency, 100,
                       f"Average message latency too high: {avg_latency:.2f}ms (SLA: 100ms)")
        
        self.assertLess(p95_latency, 500,
                       f"95th percentile latency too high: {p95_latency:.2f}ms (SLA: 500ms)")
        
        logger.info(f"Latency Results: Avg {avg_latency:.2f}ms, "
                   f"P95 {p95_latency:.2f}ms, Max {max_latency:.2f}ms")
        
        await websocket.close()
        
    async def test_connection_pool_efficiency_optimizes_resources(self):
        """Test connection pool efficiency for resource optimization."""
        num_connections = 30
        connections = []
        
        # Measure connection establishment efficiency
        batch_size = 5
        establishment_times = []
        
        for batch_start in range(0, num_connections, batch_size):
            batch_end = min(batch_start + batch_size, num_connections)
            batch_tasks = []
            
            batch_start_time = time.time()
            
            for i in range(batch_start, batch_end):
                user_id = ensure_user_id(f"pool-test-user-{i}")
                websocket = await websockets.connect(f"ws://localhost:{self.server_port}")
                
                connection = WebSocketConnection(
                    connection_id=str(uuid.uuid4()),
                    user_id=user_id,
                    websocket=websocket,
                    connected_at=datetime.now(timezone.utc)
                )
                
                batch_tasks.append(self.manager.add_connection(connection))
                connections.append((user_id, connection, websocket))
            
            await asyncio.gather(*batch_tasks)
            
            batch_time = time.time() - batch_start_time
            establishment_times.append(batch_time / batch_size)  # Time per connection in batch
        
        # Measure resource usage
        process = psutil.Process(os.getpid())
        memory_usage = process.memory_info().rss / (1024 * 1024)  # MB
        cpu_usage = process.cpu_percent()
        
        # Test connection lookup efficiency
        lookup_times = []
        
        for _ in range(100):  # Test 100 random lookups
            random_user_id = connections[len(connections)//2][0]  # Pick middle connection
            
            lookup_start = time.time()
            user_connections = self.manager.get_user_connections(random_user_id)
            lookup_time = (time.time() - lookup_start) * 1000  # Convert to ms
            
            lookup_times.append(lookup_time)
            self.assertGreater(len(user_connections), 0)
        
        # Resource efficiency assertions
        avg_establishment_time = statistics.mean(establishment_times)
        avg_lookup_time = statistics.mean(lookup_times)
        memory_per_connection = memory_usage / num_connections
        
        self.assertLess(avg_establishment_time, 0.5,
                       f"Connection establishment too slow: {avg_establishment_time:.3f}s per connection")
        
        self.assertLess(avg_lookup_time, 1.0,
                       f"Connection lookup too slow: {avg_lookup_time:.3f}ms")
        
        self.assertLess(memory_per_connection, 10.0,
                       f"Memory usage per connection too high: {memory_per_connection:.1f}MB")
        
        logger.info(f"Pool Efficiency: {avg_establishment_time:.3f}s establishment, "
                   f"{avg_lookup_time:.3f}ms lookup, {memory_per_connection:.1f}MB per connection")
        
        # Clean up
        for user_id, connection, websocket in connections:
            await websocket.close()
            
    async def test_degraded_mode_performance_maintains_basic_service(self):
        """Test performance in degraded mode during infrastructure issues."""
        # Test degraded mode manager
        degraded_manager = UnifiedWebSocketManager(mode=WebSocketManagerMode.DEGRADED)
        user_id = ensure_user_id("degraded-mode-test-user")
        
        websocket = await websockets.connect(f"ws://localhost:{self.server_port}")
        connection = WebSocketConnection(
            connection_id=str(uuid.uuid4()),
            user_id=user_id,
            websocket=websocket,
            connected_at=datetime.now(timezone.utc)
        )
        
        await degraded_manager.add_connection(connection)
        
        # Test degraded mode performance
        num_messages = 20
        degraded_latencies = []
        
        for i in range(num_messages):
            send_start = time.time()
            
            message = {
                "type": "degraded_mode_test",
                "message_id": i,
                "content": "Testing degraded mode performance"
            }
            
            await degraded_manager.send_to_user(user_id, message)
            
            send_latency = (time.time() - send_start) * 1000
            degraded_latencies.append(send_latency)
            
            await asyncio.sleep(0.1)
        
        # Degraded mode should still provide basic service
        avg_degraded_latency = statistics.mean(degraded_latencies)
        
        # Degraded mode performance assertions (relaxed SLAs)
        self.assertLess(avg_degraded_latency, 2000,
                       f"Degraded mode latency too high: {avg_degraded_latency:.2f}ms "
                       f"(should provide basic service)")
        
        logger.info(f"Degraded Mode Performance: {avg_degraded_latency:.2f}ms average latency")
        
        await websocket.close()
        
    async def test_business_value_delivery_speed_improves_satisfaction(self):
        """Test business value delivery speed for user satisfaction."""
        user_id = ensure_user_id("business-value-speed-test")
        
        websocket = await websockets.connect(f"ws://localhost:{self.server_port}")
        connection = WebSocketConnection(
            connection_id=str(uuid.uuid4()),
            user_id=user_id,
            websocket=websocket,
            connected_at=datetime.now(timezone.utc)
        )
        
        await self.manager.add_connection(connection)
        
        # Test delivery speed of business-critical event sequence
        business_events = [
            {"type": "agent_started", "agent_name": "BusinessAnalyzer", "value_prop": "$50K savings"},
            {"type": "agent_thinking", "thought": "Analyzing revenue opportunities..."},
            {"type": "tool_executing", "tool": "revenue_analyzer"},
            {"type": "tool_completed", "tool": "revenue_analyzer", "result": "Found 15 opportunities"},
            {"type": "agent_completed", "result": "Analysis complete - $75K revenue increase identified"}
        ]
        
        delivery_times = []
        sequence_start = time.time()
        
        for event in business_events:
            event_start = time.time()
            await self.manager.send_to_user(user_id, event)
            event_time = (time.time() - event_start) * 1000
            delivery_times.append(event_time)
            
            await asyncio.sleep(0.1)  # Realistic delay between events
        
        total_sequence_time = time.time() - sequence_start
        avg_event_delivery = statistics.mean(delivery_times)
        
        # Business value delivery speed assertions
        self.assertLess(total_sequence_time, 10.0,
                       f"Business value sequence too slow: {total_sequence_time:.2f}s "
                       f"(impacts user engagement)")
        
        self.assertLess(avg_event_delivery, 100,
                       f"Individual event delivery too slow: {avg_event_delivery:.2f}ms")
        
        logger.info(f"Business Value Speed: {total_sequence_time:.2f}s total, "
                   f"{avg_event_delivery:.2f}ms per event")
        
        await websocket.close()


if __name__ == "__main__":
    # Run with: python -m pytest tests/performance/test_websocket_unified_manager_performance_concurrency.py -v -m performance
    pytest.main([__file__, "-v", "-m", "performance", "--tb=short"])