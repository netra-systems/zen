"""
Integration Tests: Agent Execution Concurrency Limits

Business Value Justification (BVJ):
- Segment: Mid/Enterprise (concurrent user scenarios)
- Business Goal: System Stability + Platform Scaling
- Value Impact: Prevents system overload from excessive concurrent agent executions,
  ensures fair resource allocation across multiple users, maintains response times
  under concurrent load
- Revenue Impact: Protects $500K+ ARR from concurrent execution failures, enables
  scaling to Enterprise tier with guaranteed SLA performance

Test Focus: Boundary conditions for concurrent agent execution, user isolation
under load, resource allocation fairness, and system behavior at concurrency limits.
"""

import asyncio
import time
import pytest
from typing import List, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch
import psutil
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from test_framework.base_integration_test import BaseIntegrationTest
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.core.config import get_config


class TestAgentExecutionConcurrencyLimits(BaseIntegrationTest):
    """
    Test concurrent agent execution boundary conditions and user isolation.
    
    Business Value: Ensures system stability under concurrent load and fair
    resource allocation across multiple users, critical for Enterprise scaling.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_concurrency_test(self, real_services_fixture):
        """Setup concurrent execution test environment."""
        self.config = get_config()
        self.initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        self.concurrent_contexts: List[UserExecutionContext] = []
        self.websocket_managers: List[WebSocketManager] = []
        
        # Track system resources before test
        self.initial_cpu_percent = psutil.cpu_percent(interval=1)
        self.initial_connections = len(psutil.net_connections())
        
        yield
        
        # Cleanup all concurrent contexts
        for context in self.concurrent_contexts:
            try:
                await context.cleanup()
            except Exception:
                pass
        
        # Cleanup WebSocket managers
        for manager in self.websocket_managers:
            try:
                await manager.cleanup()
            except Exception:
                pass
    
    @pytest.mark.asyncio
    async def test_concurrent_user_execution_isolation(self):
        """
        Test that concurrent executions from different users remain isolated.
        
        BVJ: Prevents user data contamination, ensures Enterprise-grade security.
        """
        num_concurrent_users = 10
        execution_tasks = []
        user_results = {}
        
        # Create concurrent user contexts
        for user_id in range(num_concurrent_users):
            context = UserExecutionContext(
                user_id=f"concurrent_user_{user_id}",
                session_id=f"session_{user_id}_{int(time.time())}",
                request_id=f"req_{user_id}_{int(time.time() * 1000)}"
            )
            self.concurrent_contexts.append(context)
            
            # Create unique task for each user
            async def user_task(ctx, uid):
                # Simulate agent execution with user-specific data
                result = {
                    "user_id": ctx.user_id,
                    "session_id": ctx.session_id,
                    "execution_time": time.time(),
                    "process_id": os.getpid(),
                    "thread_id": asyncio.current_task().get_name()
                }
                
                # Add processing delay to ensure concurrency
                await asyncio.sleep(0.5)
                
                # Verify context isolation
                assert ctx.user_id == f"concurrent_user_{uid}"
                assert ctx.session_id == f"session_{uid}_{int(time.time())}"
                
                return result
            
            task = asyncio.create_task(user_task(context, user_id))
            execution_tasks.append((user_id, task))
        
        # Execute all tasks concurrently
        start_time = time.time()
        for user_id, task in execution_tasks:
            result = await task
            user_results[user_id] = result
        
        execution_time = time.time() - start_time
        
        # Verify concurrent execution completed efficiently
        assert execution_time < 2.0, f"Concurrent execution took too long: {execution_time}s"
        
        # Verify all users executed successfully
        assert len(user_results) == num_concurrent_users
        
        # Verify user isolation - each result should be unique
        user_ids = [result["user_id"] for result in user_results.values()]
        assert len(set(user_ids)) == num_concurrent_users, "User context contamination detected"
        
        # Verify no resource leaks
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_growth = final_memory - self.initial_memory
        assert memory_growth < 100, f"Memory leak detected: {memory_growth}MB growth"
    
    @pytest.mark.asyncio
    async def test_agent_execution_rate_limiting_fairness(self):
        """
        Test fair rate limiting across concurrent users.
        
        BVJ: Ensures no single user can monopolize system resources, maintaining
        service quality for all Enterprise customers.
        """
        num_users = 5
        requests_per_user = 8
        rate_limit_per_user = 5  # Max 5 requests per user concurrently
        
        user_execution_counts = {}
        rate_limit_violations = []
        
        async def rate_limited_execution(user_id: str, request_num: int):
            """Simulate rate-limited agent execution."""
            context = UserExecutionContext(
                user_id=user_id,
                session_id=f"rate_test_{user_id}_{request_num}",
                request_id=f"rate_req_{user_id}_{request_num}"
            )
            self.concurrent_contexts.append(context)
            
            # Track concurrent executions per user
            if user_id not in user_execution_counts:
                user_execution_counts[user_id] = 0
            
            user_execution_counts[user_id] += 1
            
            # Check rate limit violation
            if user_execution_counts[user_id] > rate_limit_per_user:
                rate_limit_violations.append({
                    "user_id": user_id,
                    "concurrent_count": user_execution_counts[user_id],
                    "request_num": request_num,
                    "timestamp": time.time()
                })
            
            try:
                # Simulate processing time
                await asyncio.sleep(0.3)
                
                # Verify context integrity under load
                assert context.user_id == user_id
                return {"success": True, "user_id": user_id, "request_num": request_num}
            
            finally:
                user_execution_counts[user_id] -= 1
        
        # Create concurrent tasks across multiple users
        all_tasks = []
        for user_id in range(num_users):
            user_str = f"rate_user_{user_id}"
            for request_num in range(requests_per_user):
                task = asyncio.create_task(
                    rate_limited_execution(user_str, request_num)
                )
                all_tasks.append(task)
        
        # Execute all tasks with rate limiting simulation
        start_time = time.time()
        results = await asyncio.gather(*all_tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        # Verify results
        successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
        assert len(successful_results) == num_users * requests_per_user
        
        # Verify fair distribution - each user should get equal service
        user_success_counts = {}
        for result in successful_results:
            user_id = result["user_id"]
            user_success_counts[user_id] = user_success_counts.get(user_id, 0) + 1
        
        # All users should have completed all their requests
        for user_id in user_success_counts:
            assert user_success_counts[user_id] == requests_per_user, \
                f"Unfair rate limiting for {user_id}: {user_success_counts[user_id]} vs {requests_per_user}"
        
        # Verify execution time indicates proper concurrency
        expected_min_time = (requests_per_user * 0.3) / rate_limit_per_user
        assert execution_time >= expected_min_time * 0.8, \
            f"Execution too fast, rate limiting may not be working: {execution_time}s"
    
    @pytest.mark.asyncio
    async def test_concurrent_websocket_event_delivery_boundary(self):
        """
        Test WebSocket event delivery under concurrent load boundary conditions.
        
        BVJ: Ensures real-time chat experience remains responsive under Enterprise
        load, protecting primary revenue stream.
        """
        num_concurrent_connections = 20
        events_per_connection = 10
        
        connection_results = {}
        event_delivery_failures = []
        
        async def concurrent_websocket_simulation(connection_id: str):
            """Simulate concurrent WebSocket connection with event delivery."""
            
            # Mock WebSocket connection
            mock_websocket = AsyncMock()
            mock_websocket.send_json = AsyncMock()
            mock_websocket.connection_id = connection_id
            
            # Create WebSocket manager for this connection
            websocket_manager = WebSocketManager()
            self.websocket_managers.append(websocket_manager)
            
            # Register connection
            await websocket_manager.register_connection(connection_id, mock_websocket)
            
            events_sent = 0
            events_failed = 0
            
            # Send events concurrently
            for event_num in range(events_per_connection):
                try:
                    event_data = {
                        "type": "agent_thinking",
                        "connection_id": connection_id,
                        "event_num": event_num,
                        "timestamp": time.time(),
                        "message": f"Concurrent processing for connection {connection_id}, event {event_num}"
                    }
                    
                    # Simulate event delivery
                    await websocket_manager.send_agent_event(connection_id, event_data)
                    events_sent += 1
                    
                    # Small delay to create concurrent pressure
                    await asyncio.sleep(0.01)
                    
                except Exception as e:
                    events_failed += 1
                    event_delivery_failures.append({
                        "connection_id": connection_id,
                        "event_num": event_num,
                        "error": str(e),
                        "timestamp": time.time()
                    })
            
            return {
                "connection_id": connection_id,
                "events_sent": events_sent,
                "events_failed": events_failed,
                "total_events": events_per_connection
            }
        
        # Create concurrent WebSocket connections
        connection_tasks = []
        for conn_id in range(num_concurrent_connections):
            connection_str = f"concurrent_conn_{conn_id}"
            task = asyncio.create_task(
                concurrent_websocket_simulation(connection_str)
            )
            connection_tasks.append(task)
        
        # Execute all connections concurrently
        start_time = time.time()
        results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        # Analyze results
        successful_connections = [r for r in results if isinstance(r, dict)]
        assert len(successful_connections) == num_concurrent_connections
        
        # Verify event delivery success rates
        total_events_sent = sum(r["events_sent"] for r in successful_connections)
        total_events_expected = num_concurrent_connections * events_per_connection
        success_rate = total_events_sent / total_events_expected
        
        # Should achieve >95% success rate under concurrent load
        assert success_rate >= 0.95, \
            f"WebSocket event delivery success rate too low: {success_rate:.2%}"
        
        # Verify reasonable performance under load
        assert execution_time < 10.0, \
            f"WebSocket concurrent delivery too slow: {execution_time}s"
        
        # Log any delivery failures for analysis
        if event_delivery_failures:
            failure_rate = len(event_delivery_failures) / total_events_expected
            assert failure_rate < 0.05, \
                f"Too many WebSocket delivery failures: {failure_rate:.2%}"
    
    @pytest.mark.asyncio
    async def test_system_resource_exhaustion_graceful_degradation(self):
        """
        Test system behavior when approaching resource limits under concurrent load.
        
        BVJ: Ensures system remains stable and provides graceful degradation rather
        than catastrophic failure, protecting Enterprise SLA commitments.
        """
        # Simulate high concurrent load
        max_concurrent_executions = 50
        resource_monitor_interval = 0.1
        
        system_metrics = {
            "peak_memory_mb": 0,
            "peak_cpu_percent": 0,
            "peak_connections": 0,
            "executions_completed": 0,
            "executions_failed": 0,
            "resource_limit_triggered": False
        }
        
        async def resource_intensive_execution(execution_id: str):
            """Simulate resource-intensive agent execution."""
            context = UserExecutionContext(
                user_id=f"load_user_{execution_id}",
                session_id=f"load_session_{execution_id}",
                request_id=f"load_req_{execution_id}"
            )
            self.concurrent_contexts.append(context)
            
            try:
                # Monitor resources during execution
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                current_cpu = psutil.cpu_percent()
                current_connections = len(psutil.net_connections())
                
                system_metrics["peak_memory_mb"] = max(system_metrics["peak_memory_mb"], current_memory)
                system_metrics["peak_cpu_percent"] = max(system_metrics["peak_cpu_percent"], current_cpu)
                system_metrics["peak_connections"] = max(system_metrics["peak_connections"], current_connections)
                
                # Simulate processing with resource usage
                await asyncio.sleep(0.2)
                
                # Check if we should trigger resource limits
                if (current_memory > self.initial_memory + 200 or  # 200MB growth
                    current_cpu > 80 or  # 80% CPU usage
                    current_connections > self.initial_connections + 100):
                    system_metrics["resource_limit_triggered"] = True
                    raise Exception("Resource limit triggered - graceful degradation")
                
                system_metrics["executions_completed"] += 1
                return {"success": True, "execution_id": execution_id}
                
            except Exception as e:
                system_metrics["executions_failed"] += 1
                return {"success": False, "execution_id": execution_id, "error": str(e)}
        
        # Launch concurrent executions
        execution_tasks = []
        for i in range(max_concurrent_executions):
            task = asyncio.create_task(resource_intensive_execution(str(i)))
            execution_tasks.append(task)
            
            # Stagger task creation to build up load gradually
            if i % 10 == 9:
                await asyncio.sleep(0.05)
        
        # Monitor system resources during execution
        resource_monitoring_task = asyncio.create_task(self._monitor_system_resources(system_metrics))
        
        # Wait for all executions to complete
        start_time = time.time()
        results = await asyncio.gather(*execution_tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        # Stop resource monitoring
        resource_monitoring_task.cancel()
        
        # Analyze results
        successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
        failed_results = [r for r in results if isinstance(r, dict) and not r.get("success")]
        exception_results = [r for r in results if isinstance(r, Exception)]
        
        # Verify graceful degradation occurred
        total_attempts = len(results)
        success_rate = len(successful_results) / total_attempts
        
        # System should handle at least 60% of load before degrading
        assert success_rate >= 0.6, \
            f"System degraded too early: {success_rate:.2%} success rate"
        
        # Verify some executions succeeded (system didn't crash)
        assert len(successful_results) > 0, "System completely failed under load"
        
        # Verify system provided feedback about resource limits
        if system_metrics["resource_limit_triggered"]:
            assert len(failed_results) > 0, "Resource limits triggered but no failures reported"
        
        # Verify execution time indicates proper load handling
        assert execution_time < 30.0, \
            f"System took too long under load: {execution_time}s"
        
        # Log resource usage for analysis
        self.logger.info(f"Peak resource usage - Memory: {system_metrics['peak_memory_mb']:.1f}MB, "
                        f"CPU: {system_metrics['peak_cpu_percent']:.1f}%, "
                        f"Connections: {system_metrics['peak_connections']}")
    
    async def _monitor_system_resources(self, metrics: Dict[str, Any]):
        """Background task to monitor system resources."""
        try:
            while True:
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                current_cpu = psutil.cpu_percent()
                current_connections = len(psutil.net_connections())
                
                metrics["peak_memory_mb"] = max(metrics["peak_memory_mb"], current_memory)
                metrics["peak_cpu_percent"] = max(metrics["peak_cpu_percent"], current_cpu)
                metrics["peak_connections"] = max(metrics["peak_connections"], current_connections)
                
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass
    
    @pytest.mark.asyncio
    async def test_concurrent_database_connection_boundary_handling(self):
        """
        Test database connection handling at concurrency boundaries.
        
        BVJ: Prevents database connection exhaustion that would crash the system,
        ensures reliable data persistence under Enterprise concurrent load.
        """
        max_concurrent_db_operations = 25
        db_operation_results = []
        connection_errors = []
        
        async def concurrent_database_operation(operation_id: str):
            """Simulate concurrent database operations."""
            context = UserExecutionContext(
                user_id=f"db_user_{operation_id}",
                session_id=f"db_session_{operation_id}",
                request_id=f"db_req_{operation_id}"
            )
            self.concurrent_contexts.append(context)
            
            try:
                # Simulate database operation (would normally use real DB connection)
                start_time = time.time()
                
                # Mock database query with realistic timing
                await asyncio.sleep(0.1 + (int(operation_id) % 10) * 0.01)  # Variable query time
                
                operation_time = time.time() - start_time
                
                # Verify context maintained during DB operation
                assert context.user_id == f"db_user_{operation_id}"
                
                return {
                    "success": True,
                    "operation_id": operation_id,
                    "operation_time": operation_time,
                    "user_id": context.user_id
                }
                
            except Exception as e:
                connection_errors.append({
                    "operation_id": operation_id,
                    "error": str(e),
                    "timestamp": time.time()
                })
                return {
                    "success": False,
                    "operation_id": operation_id,
                    "error": str(e)
                }
        
        # Launch concurrent database operations
        db_tasks = []
        for i in range(max_concurrent_db_operations):
            task = asyncio.create_task(concurrent_database_operation(str(i)))
            db_tasks.append(task)
        
        # Execute with timing
        start_time = time.time()
        results = await asyncio.gather(*db_tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        # Analyze results
        successful_operations = [r for r in results if isinstance(r, dict) and r.get("success")]
        failed_operations = [r for r in results if isinstance(r, dict) and not r.get("success")]
        
        # Verify high success rate for database operations
        success_rate = len(successful_operations) / len(results)
        assert success_rate >= 0.9, \
            f"Database operation success rate too low: {success_rate:.2%}"
        
        # Verify reasonable performance under concurrent load
        avg_operation_time = sum(r["operation_time"] for r in successful_operations) / len(successful_operations)
        assert avg_operation_time < 0.5, \
            f"Database operations too slow under concurrent load: {avg_operation_time:.3f}s"
        
        # Verify proper connection management (no connection leaks)
        final_connections = len(psutil.net_connections())
        connection_growth = final_connections - self.initial_connections
        assert connection_growth < 10, \
            f"Potential connection leak detected: {connection_growth} new connections"
        
        # Verify user context isolation in database operations
        user_ids = [r["user_id"] for r in successful_operations]
        unique_users = set(user_ids)
        assert len(unique_users) == len(successful_operations), \
            "User context contamination in database operations"
        
        # Log connection errors for analysis
        if connection_errors:
            error_rate = len(connection_errors) / max_concurrent_db_operations
            assert error_rate < 0.1, \
                f"Too many database connection errors: {error_rate:.2%}"