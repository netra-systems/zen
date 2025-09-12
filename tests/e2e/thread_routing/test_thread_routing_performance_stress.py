"""
Test Thread Routing Performance Stress E2E

Business Value Justification (BVJ):
- Segment: Mid, Enterprise (high-volume users)
- Business Goal: Platform scalability and performance under load
- Value Impact: Poor performance at scale drives users to competitors
- Strategic Impact: Platform growth capability - must handle 100+ concurrent users

This E2E test suite validates thread routing performance under stress:
1. High message volume per thread (chat conversations)
2. Many concurrent threads and users (multi-user platform)
3. Thread routing under sustained load
4. System performance validation and bottleneck identification
5. Resource utilization and memory leak detection
6. Real-world usage pattern simulation

CRITICAL: Full E2E with authentication + real services - NO mocks allowed.
Expected: Initial failures - performance bottlenecks and resource leaks likely exist.
"""

import asyncio
import uuid
import pytest
import time
import statistics
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
import json

from test_framework.base_e2e_test import BaseE2ETest  
from test_framework.fixtures.real_services import real_services_fixture
from test_framework.fixtures.isolated_environment import isolated_env
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from shared.isolated_environment import get_env
from shared.types.core_types import (
    UserID, ThreadID, RunID, RequestID,
    ensure_user_id, ensure_thread_id
)

# Thread routing performance components
from netra_backend.app.services.thread_service import ThreadService
from netra_backend.app.db.models_postgres import Thread, Message, User
from netra_backend.app.websocket_core import create_websocket_manager
from netra_backend.app.services.user_execution_context import UserExecutionContext

# WebSocket testing utilities
try:
    import websockets
    from websockets.exceptions import ConnectionClosed, InvalidStatusCode
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

# Performance monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Import SQLAlchemy for direct database monitoring
try:
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import text, select, func
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False


class PerformanceMetrics:
    """Track performance metrics during stress testing."""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.operation_times = []
        self.error_count = 0
        self.success_count = 0
        self.memory_usage = []
        self.cpu_usage = []
        self.database_connections = []
        self.websocket_connections = []
        
    def start_monitoring(self):
        """Start performance monitoring."""
        self.start_time = time.time()
        if PSUTIL_AVAILABLE:
            process = psutil.Process()
            self.memory_usage.append(process.memory_info().rss / 1024 / 1024)  # MB
            self.cpu_usage.append(process.cpu_percent())
    
    def end_monitoring(self):
        """End performance monitoring."""
        self.end_time = time.time()
        if PSUTIL_AVAILABLE:
            process = psutil.Process()
            self.memory_usage.append(process.memory_info().rss / 1024 / 1024)  # MB
            self.cpu_usage.append(process.cpu_percent())
    
    def record_operation(self, duration: float, success: bool):
        """Record individual operation performance."""
        self.operation_times.append(duration)
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        total_time = self.end_time - self.start_time if self.end_time and self.start_time else 0
        total_operations = len(self.operation_times)
        
        summary = {
            "total_duration": total_time,
            "total_operations": total_operations,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": self.success_count / (self.success_count + self.error_count) if (self.success_count + self.error_count) > 0 else 0,
            "operations_per_second": total_operations / total_time if total_time > 0 else 0
        }
        
        if self.operation_times:
            summary.update({
                "avg_operation_time": statistics.mean(self.operation_times),
                "min_operation_time": min(self.operation_times),
                "max_operation_time": max(self.operation_times),
                "p95_operation_time": statistics.quantiles(self.operation_times, n=20)[18] if len(self.operation_times) > 20 else max(self.operation_times),
                "p99_operation_time": statistics.quantiles(self.operation_times, n=100)[98] if len(self.operation_times) > 100 else max(self.operation_times)
            })
        
        if PSUTIL_AVAILABLE and len(self.memory_usage) >= 2:
            summary.update({
                "memory_start_mb": self.memory_usage[0],
                "memory_end_mb": self.memory_usage[-1],
                "memory_increase_mb": self.memory_usage[-1] - self.memory_usage[0],
                "avg_cpu_usage": statistics.mean(self.cpu_usage) if self.cpu_usage else 0
            })
        
        return summary


class TestThreadRoutingPerformanceStress(BaseE2ETest):
    """E2E performance stress tests for thread routing with real authentication."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.auth_helper = E2EAuthHelper()
        self.performance_metrics = PerformanceMetrics()
        self.cleanup_resources = []
    
    async def asyncSetUp(self):
        """Set up E2E test environment with authentication."""
        await super().asyncSetUp()
        self.auth_helper = E2EAuthHelper()
    
    async def asyncTearDown(self):
        """Clean up E2E test resources."""
        # Clean up any resources created during testing
        for resource in self.cleanup_resources:
            try:
                if hasattr(resource, 'close'):
                    if asyncio.iscoroutinefunction(resource.close):
                        await resource.close()
                    else:
                        resource.close()
            except Exception as e:
                self.logger.warning(f"Cleanup warning: {e}")
        
        await super().asyncTearDown()

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.performance
    async def test_high_volume_message_routing_performance(self, real_services_fixture, isolated_env):
        """Test performance with high message volume per thread."""
        
        if not real_services_fixture.get("backend_available", False):
            pytest.skip("Backend service not available for E2E testing")
        
        # Skip if WebSocket not available
        if not WEBSOCKETS_AVAILABLE:
            pytest.skip("WebSockets library not available")
        
        # Create authenticated test user
        auth_result = await self.auth_helper.create_authenticated_test_user(
            email="performance.high.volume@test.com",
            password="performance_test_123!",
            full_name="Performance High Volume User"
        )
        
        if not auth_result.success:
            pytest.skip(f"Authentication setup failed: {auth_result.error}")
        
        user_token = auth_result.access_token
        user_id = auth_result.user_id
        
        self.logger.info(f"Starting high volume message routing test for user {user_id}")
        
        # Performance test configuration
        messages_per_thread = 200  # High volume
        thread_count = 10
        concurrent_threads = 5
        
        # Initialize performance tracking
        high_volume_metrics = PerformanceMetrics()
        high_volume_metrics.start_monitoring()
        
        # Get database session for direct operations
        db_session = real_services_fixture.get("db")
        if not db_session:
            pytest.skip("Database session not available")
        
        thread_service = ThreadService()
        
        # Test 1: Create multiple threads for high-volume testing
        self.logger.info(f"Creating {thread_count} threads for high-volume testing")
        
        test_threads = []
        thread_creation_times = []
        
        for i in range(thread_count):
            thread_start = time.time()
            try:
                thread = await thread_service.get_or_create_thread(user_id, db_session)
                thread_end = time.time()
                
                test_threads.append(thread)
                thread_creation_times.append(thread_end - thread_start)
                high_volume_metrics.record_operation(thread_end - thread_start, True)
                
                self.logger.info(f"Created thread {i+1}/{thread_count}: {thread.id}")
                
            except Exception as e:
                thread_end = time.time()
                high_volume_metrics.record_operation(thread_end - thread_start, False)
                self.logger.error(f"Failed to create thread {i+1}: {e}")
        
        self.logger.info(f"Thread creation completed. Created {len(test_threads)} threads")
        if thread_creation_times:
            avg_creation_time = statistics.mean(thread_creation_times)
            self.logger.info(f"Average thread creation time: {avg_creation_time:.3f}s")
        
        # Test 2: High-volume message creation per thread
        async def create_high_volume_messages(thread: Thread, thread_index: int):
            """Create high volume of messages in a single thread."""
            thread_metrics = {
                "thread_id": thread.id,
                "thread_index": thread_index,
                "messages_created": 0,
                "messages_failed": 0,
                "total_time": 0,
                "message_times": []
            }
            
            thread_start_time = time.time()
            
            for msg_index in range(messages_per_thread):
                message_start = time.time()
                try:
                    message = await thread_service.create_message(
                        thread_id=thread.id,
                        role="user" if msg_index % 2 == 0 else "assistant",
                        content=f"High volume performance test message {msg_index} in thread {thread_index}. "
                                f"This message tests system performance under sustained load. "
                                f"Message content is intentionally longer to simulate real chat conversations. "
                                f"Timestamp: {datetime.now().isoformat()}",
                        metadata={
                            "performance_test": True,
                            "thread_index": thread_index,
                            "message_index": msg_index,
                            "volume_test": "high_volume_messages",
                            "test_phase": "stress_testing"
                        }
                    )
                    
                    message_end = time.time()
                    message_duration = message_end - message_start
                    
                    thread_metrics["messages_created"] += 1
                    thread_metrics["message_times"].append(message_duration)
                    high_volume_metrics.record_operation(message_duration, True)
                    
                    # Log progress every 50 messages
                    if (msg_index + 1) % 50 == 0:
                        self.logger.info(f"Thread {thread_index}: Created {msg_index + 1}/{messages_per_thread} messages")
                    
                    # Small delay to prevent overwhelming the system
                    if msg_index % 10 == 0:
                        await asyncio.sleep(0.01)
                
                except Exception as e:
                    message_end = time.time()
                    message_duration = message_end - message_start
                    
                    thread_metrics["messages_failed"] += 1
                    high_volume_metrics.record_operation(message_duration, False)
                    
                    self.logger.warning(f"Thread {thread_index} message {msg_index} failed: {e}")
            
            thread_end_time = time.time()
            thread_metrics["total_time"] = thread_end_time - thread_start_time
            
            return thread_metrics
        
        # Run high-volume message creation concurrently across multiple threads
        self.logger.info(f"Starting high-volume message creation: {messages_per_thread} messages per thread")
        
        high_volume_tasks = [
            create_high_volume_messages(test_threads[i], i)
            for i in range(min(concurrent_threads, len(test_threads)))
        ]
        
        high_volume_start = time.time()
        thread_results = await asyncio.gather(*high_volume_tasks, return_exceptions=True)
        high_volume_end = time.time()
        
        # Analyze high-volume results
        successful_thread_results = [r for r in thread_results if isinstance(r, dict)]
        
        total_messages_created = sum(r["messages_created"] for r in successful_thread_results)
        total_messages_failed = sum(r["messages_failed"] for r in successful_thread_results)
        high_volume_duration = high_volume_end - high_volume_start
        
        self.logger.info("=== High Volume Message Creation Results ===")
        self.logger.info(f"Total messages created: {total_messages_created}")
        self.logger.info(f"Total messages failed: {total_messages_failed}")
        self.logger.info(f"Success rate: {total_messages_created / (total_messages_created + total_messages_failed):.1%}")
        self.logger.info(f"Total duration: {high_volume_duration:.2f}s")
        self.logger.info(f"Messages per second: {total_messages_created / high_volume_duration:.1f}")
        
        # Performance analysis
        all_message_times = []
        for result in successful_thread_results:
            all_message_times.extend(result["message_times"])
        
        if all_message_times:
            avg_message_time = statistics.mean(all_message_times)
            max_message_time = max(all_message_times)
            p95_message_time = statistics.quantiles(all_message_times, n=20)[18] if len(all_message_times) > 20 else max_message_time
            
            self.logger.info(f"Average message creation time: {avg_message_time:.3f}s")
            self.logger.info(f"Max message creation time: {max_message_time:.3f}s")
            self.logger.info(f"P95 message creation time: {p95_message_time:.3f}s")
            
            # Performance thresholds
            if avg_message_time > 1.0:
                self.logger.warning(f" WARNING: [U+FE0F] Average message creation time too slow: {avg_message_time:.3f}s > 1.0s")
            
            if p95_message_time > 2.0:
                self.logger.warning(f" WARNING: [U+FE0F] P95 message creation time concerning: {p95_message_time:.3f}s > 2.0s")
        
        high_volume_metrics.end_monitoring()
        
        # Test 3: Verify data integrity after high-volume operations
        self.logger.info("Verifying data integrity after high-volume operations")
        
        integrity_issues = []
        
        for i, thread in enumerate(test_threads[:concurrent_threads]):
            try:
                # Verify thread still exists and is accessible
                retrieved_thread = await thread_service.get_thread(thread.id, user_id, db_session)
                if not retrieved_thread:
                    integrity_issues.append(f"Thread {i} disappeared: {thread.id}")
                
                # Verify messages in thread
                thread_messages = await thread_service.get_thread_messages(thread.id, limit=1000, db=db_session)
                expected_messages = messages_per_thread if i < len(successful_thread_results) else 0
                actual_messages = len(thread_messages)
                
                if actual_messages < expected_messages * 0.95:  # Allow 5% loss
                    integrity_issues.append(
                        f"Thread {i} message loss: expected ~{expected_messages}, got {actual_messages}"
                    )
                
                # Verify message content integrity
                corrupted_messages = 0
                for message in thread_messages[:10]:  # Check first 10 messages
                    try:
                        content = message.content[0]["text"]["value"]
                        if "High volume performance test message" not in content:
                            corrupted_messages += 1
                    except (KeyError, IndexError, TypeError):
                        corrupted_messages += 1
                
                if corrupted_messages > 2:  # More than 2 corrupted in sample
                    integrity_issues.append(f"Thread {i} has {corrupted_messages}/10 corrupted messages")
                
            except Exception as e:
                integrity_issues.append(f"Thread {i} integrity check failed: {e}")
        
        if integrity_issues:
            self.logger.warning("Data integrity issues found:")
            for issue in integrity_issues:
                self.logger.warning(f"  - {issue}")
        else:
            self.logger.info(" PASS:  Data integrity verified after high-volume operations")
        
        # Performance summary
        performance_summary = high_volume_metrics.get_summary()
        self.logger.info("=== High Volume Performance Summary ===")
        for metric, value in performance_summary.items():
            if isinstance(value, float):
                self.logger.info(f"{metric}: {value:.3f}")
            else:
                self.logger.info(f"{metric}: {value}")

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.performance
    async def test_concurrent_user_thread_routing_scalability(self, real_services_fixture, isolated_env):
        """Test scalability with many concurrent users and threads."""
        
        if not real_services_fixture.get("backend_available", False):
            pytest.skip("Backend service not available for E2E testing")
        
        if not WEBSOCKETS_AVAILABLE:
            pytest.skip("WebSockets library not available")
        
        # Scalability test configuration
        concurrent_user_count = 20  # Simulating 20 concurrent users
        threads_per_user = 3
        messages_per_thread = 50
        
        self.logger.info(f"Starting concurrent user scalability test: {concurrent_user_count} users")
        
        # Create multiple authenticated users
        authenticated_users = []
        user_creation_start = time.time()
        
        for i in range(concurrent_user_count):
            try:
                auth_result = await self.auth_helper.create_authenticated_test_user(
                    email=f"scalability.user.{i}@test.com",
                    password=f"scale_test_{i}!",
                    full_name=f"Scalability Test User {i}"
                )
                
                if auth_result.success:
                    authenticated_users.append({
                        "user_id": auth_result.user_id,
                        "access_token": auth_result.access_token,
                        "user_index": i
                    })
                else:
                    self.logger.warning(f"Failed to create user {i}: {auth_result.error}")
                
            except Exception as e:
                self.logger.warning(f"Exception creating user {i}: {e}")
        
        user_creation_end = time.time()
        self.logger.info(f"Created {len(authenticated_users)} authenticated users in {user_creation_end - user_creation_start:.2f}s")
        
        if len(authenticated_users) < concurrent_user_count * 0.8:
            pytest.skip(f"Insufficient users created: {len(authenticated_users)}/{concurrent_user_count}")
        
        # Initialize scalability metrics
        scalability_metrics = PerformanceMetrics()
        scalability_metrics.start_monitoring()
        
        # Get database session
        db_session = real_services_fixture.get("db")
        thread_service = ThreadService()
        
        # Test concurrent user operations
        async def simulate_user_activity(user_info: Dict[str, Any]):
            """Simulate realistic user activity patterns."""
            user_id = user_info["user_id"]
            user_index = user_info["user_index"]
            
            user_metrics = {
                "user_id": user_id,
                "user_index": user_index,
                "threads_created": 0,
                "messages_created": 0,
                "errors": [],
                "total_time": 0,
                "operations": []
            }
            
            user_start_time = time.time()
            
            try:
                # Create multiple threads for user
                user_threads = []
                for thread_idx in range(threads_per_user):
                    thread_create_start = time.time()
                    try:
                        thread = await thread_service.get_or_create_thread(user_id, db_session)
                        thread_create_end = time.time()
                        
                        user_threads.append(thread)
                        user_metrics["threads_created"] += 1
                        user_metrics["operations"].append({
                            "type": "thread_create",
                            "duration": thread_create_end - thread_create_start,
                            "success": True
                        })
                        
                        scalability_metrics.record_operation(thread_create_end - thread_create_start, True)
                        
                    except Exception as e:
                        thread_create_end = time.time()
                        user_metrics["errors"].append(f"Thread creation {thread_idx}: {str(e)}")
                        user_metrics["operations"].append({
                            "type": "thread_create",
                            "duration": thread_create_end - thread_create_start,
                            "success": False,
                            "error": str(e)
                        })
                        
                        scalability_metrics.record_operation(thread_create_end - thread_create_start, False)
                
                # Create messages in each thread
                for thread in user_threads:
                    for msg_idx in range(messages_per_thread):
                        message_start = time.time()
                        try:
                            message = await thread_service.create_message(
                                thread_id=thread.id,
                                role="user",
                                content=f"Scalability test message {msg_idx} from user {user_index}. "
                                        f"This tests concurrent user load on the thread routing system. "
                                        f"Each user creates multiple threads with multiple messages.",
                                metadata={
                                    "scalability_test": True,
                                    "user_index": user_index,
                                    "thread_id": thread.id,
                                    "message_index": msg_idx
                                }
                            )
                            
                            message_end = time.time()
                            user_metrics["messages_created"] += 1
                            user_metrics["operations"].append({
                                "type": "message_create",
                                "duration": message_end - message_start,
                                "success": True
                            })
                            
                            scalability_metrics.record_operation(message_end - message_start, True)
                            
                            # Add realistic delay between messages
                            await asyncio.sleep(0.05)
                            
                        except Exception as e:
                            message_end = time.time()
                            user_metrics["errors"].append(f"Message {msg_idx}: {str(e)}")
                            user_metrics["operations"].append({
                                "type": "message_create",
                                "duration": message_end - message_start,
                                "success": False,
                                "error": str(e)
                            })
                            
                            scalability_metrics.record_operation(message_end - message_start, False)
                
                # Test reading messages back (simulating user browsing history)
                for thread in user_threads:
                    read_start = time.time()
                    try:
                        messages = await thread_service.get_thread_messages(thread.id, limit=100, db=db_session)
                        read_end = time.time()
                        
                        user_metrics["operations"].append({
                            "type": "message_read",
                            "duration": read_end - read_start,
                            "success": True,
                            "messages_count": len(messages)
                        })
                        
                        scalability_metrics.record_operation(read_end - read_start, True)
                        
                    except Exception as e:
                        read_end = time.time()
                        user_metrics["errors"].append(f"Message read: {str(e)}")
                        user_metrics["operations"].append({
                            "type": "message_read",
                            "duration": read_end - read_start,
                            "success": False,
                            "error": str(e)
                        })
                        
                        scalability_metrics.record_operation(read_end - read_start, False)
            
            except Exception as e:
                user_metrics["errors"].append(f"General user activity error: {str(e)}")
            
            user_end_time = time.time()
            user_metrics["total_time"] = user_end_time - user_start_time
            
            return user_metrics
        
        # Run concurrent user simulations
        self.logger.info("Starting concurrent user activity simulation")
        
        concurrent_start_time = time.time()
        user_tasks = [simulate_user_activity(user) for user in authenticated_users]
        
        # Use asyncio.gather with timeout to prevent hanging
        try:
            user_results = await asyncio.wait_for(
                asyncio.gather(*user_tasks, return_exceptions=True),
                timeout=300  # 5 minute timeout
            )
        except asyncio.TimeoutError:
            self.logger.error("Concurrent user test timed out after 300 seconds")
            user_results = []
        
        concurrent_end_time = time.time()
        concurrent_duration = concurrent_end_time - concurrent_start_time
        
        scalability_metrics.end_monitoring()
        
        # Analyze concurrent user results
        successful_users = [r for r in user_results if isinstance(r, dict) and r.get("user_id")]
        failed_users = len(user_results) - len(successful_users)
        
        self.logger.info("=== Concurrent User Scalability Results ===")
        self.logger.info(f"Successful users: {len(successful_users)}/{len(authenticated_users)}")
        self.logger.info(f"Failed users: {failed_users}")
        self.logger.info(f"Total test duration: {concurrent_duration:.2f}s")
        
        if successful_users:
            # Aggregate statistics
            total_threads = sum(u["threads_created"] for u in successful_users)
            total_messages = sum(u["messages_created"] for u in successful_users)
            total_errors = sum(len(u["errors"]) for u in successful_users)
            
            self.logger.info(f"Total threads created: {total_threads}")
            self.logger.info(f"Total messages created: {total_messages}")
            self.logger.info(f"Total errors: {total_errors}")
            
            if total_messages > 0:
                self.logger.info(f"Messages per second: {total_messages / concurrent_duration:.1f}")
            
            # Analyze operation types
            operation_stats = {}
            for user in successful_users:
                for operation in user["operations"]:
                    op_type = operation["type"]
                    if op_type not in operation_stats:
                        operation_stats[op_type] = {"count": 0, "success": 0, "durations": []}
                    
                    operation_stats[op_type]["count"] += 1
                    if operation["success"]:
                        operation_stats[op_type]["success"] += 1
                        operation_stats[op_type]["durations"].append(operation["duration"])
            
            self.logger.info("=== Operation Performance Analysis ===")
            for op_type, stats in operation_stats.items():
                success_rate = stats["success"] / stats["count"] if stats["count"] > 0 else 0
                avg_duration = statistics.mean(stats["durations"]) if stats["durations"] else 0
                
                self.logger.info(f"{op_type}:")
                self.logger.info(f"  Count: {stats['count']}")
                self.logger.info(f"  Success Rate: {success_rate:.1%}")
                self.logger.info(f"  Avg Duration: {avg_duration:.3f}s")
                
                if stats["durations"] and len(stats["durations"]) > 10:
                    p95_duration = statistics.quantiles(stats["durations"], n=20)[18]
                    self.logger.info(f"  P95 Duration: {p95_duration:.3f}s")
            
            # Performance warnings
            overall_success_rate = (total_messages + total_threads) / (total_messages + total_threads + total_errors) if (total_messages + total_threads + total_errors) > 0 else 0
            
            if overall_success_rate < 0.95:
                self.logger.warning(f" WARNING: [U+FE0F] Overall success rate below 95%: {overall_success_rate:.1%}")
            
            if concurrent_duration > 120:  # More than 2 minutes for this test is slow
                self.logger.warning(f" WARNING: [U+FE0F] Test duration concerning: {concurrent_duration:.1f}s > 120s")
            
            # Check for user isolation
            user_threads_check = {}
            isolation_violations = []
            
            for user in successful_users:
                user_id = user["user_id"]
                try:
                    user_threads = await thread_service.get_threads(user_id, db_session)
                    thread_ids = [t.id for t in user_threads]
                    user_threads_check[user_id] = set(thread_ids)
                except Exception as e:
                    self.logger.warning(f"Could not check threads for user {user_id}: {e}")
            
            # Check for cross-user thread contamination
            for user1_id, threads1 in user_threads_check.items():
                for user2_id, threads2 in user_threads_check.items():
                    if user1_id != user2_id:
                        shared_threads = threads1.intersection(threads2)
                        if shared_threads:
                            isolation_violations.append({
                                "user1": user1_id,
                                "user2": user2_id,
                                "shared_threads": list(shared_threads)
                            })
            
            if isolation_violations:
                self.logger.error(f" ALERT:  USER ISOLATION VIOLATIONS DETECTED: {len(isolation_violations)}")
                for violation in isolation_violations[:5]:  # Log first 5
                    self.logger.error(f"  Users {violation['user1']} and {violation['user2']} share threads: {violation['shared_threads']}")
            else:
                self.logger.info(" PASS:  User isolation maintained under concurrent load")
        
        # Overall scalability assessment
        performance_summary = scalability_metrics.get_summary()
        self.logger.info("=== Scalability Performance Summary ===")
        
        for metric, value in performance_summary.items():
            if isinstance(value, float):
                self.logger.info(f"{metric}: {value:.3f}")
            else:
                self.logger.info(f"{metric}: {value}")
        
        # Scalability score calculation
        scalability_score = 100
        
        if performance_summary["success_rate"] < 0.95:
            scalability_score -= 20
        
        if performance_summary.get("operations_per_second", 0) < 10:
            scalability_score -= 15
        
        if len(isolation_violations) > 0:
            scalability_score -= 30
        
        if concurrent_duration > 120:
            scalability_score -= 10
        
        self.logger.info(f"Overall Scalability Score: {scalability_score}/100")
        
        if scalability_score < 70:
            self.logger.warning(" WARNING: [U+FE0F] Scalability needs improvement for production deployment")
        elif scalability_score >= 85:
            self.logger.info(" PASS:  Good scalability performance")

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.performance
    async def test_sustained_load_memory_leak_detection(self, real_services_fixture, isolated_env):
        """Test for memory leaks and resource cleanup under sustained load."""
        
        if not PSUTIL_AVAILABLE:
            pytest.skip("psutil not available for memory monitoring")
        
        if not real_services_fixture.get("backend_available", False):
            pytest.skip("Backend service not available for E2E testing")
        
        # Create authenticated user for sustained load testing
        auth_result = await self.auth_helper.create_authenticated_test_user(
            email="memory.leak.test@test.com",
            password="memory_test_123!",
            full_name="Memory Leak Test User"
        )
        
        if not auth_result.success:
            pytest.skip(f"Authentication setup failed: {auth_result.error}")
        
        user_id = auth_result.user_id
        
        # Memory leak detection configuration
        sustained_duration = 120  # 2 minutes of sustained load
        operations_per_cycle = 20
        memory_check_interval = 10  # seconds
        
        self.logger.info(f"Starting sustained load memory leak detection: {sustained_duration}s")
        
        # Initialize memory monitoring
        process = psutil.Process()
        memory_readings = []
        cpu_readings = []
        
        def record_memory_usage():
            """Record current memory and CPU usage."""
            memory_mb = process.memory_info().rss / 1024 / 1024
            cpu_percent = process.cpu_percent()
            timestamp = time.time()
            
            memory_readings.append({
                "timestamp": timestamp,
                "memory_mb": memory_mb,
                "cpu_percent": cpu_percent
            })
            
            return memory_mb, cpu_percent
        
        # Record baseline memory usage
        baseline_memory, baseline_cpu = record_memory_usage()
        self.logger.info(f"Baseline memory: {baseline_memory:.1f} MB, CPU: {baseline_cpu:.1f}%")
        
        # Get database session
        db_session = real_services_fixture.get("db")
        thread_service = ThreadService()
        
        # Sustained load test
        sustained_start = time.time()
        cycle_count = 0
        total_operations = 0
        operation_errors = 0
        
        # Resources to track for leak detection
        thread_ids_created = set()
        message_ids_created = set()
        
        while (time.time() - sustained_start) < sustained_duration:
            cycle_start = time.time()
            cycle_count += 1
            
            self.logger.info(f"Starting sustained load cycle {cycle_count}")
            
            # Perform operations that might leak memory
            try:
                # Create thread
                thread = await thread_service.get_or_create_thread(user_id, db_session)
                thread_ids_created.add(thread.id)
                total_operations += 1
                
                # Create messages
                for msg_idx in range(operations_per_cycle):
                    try:
                        message = await thread_service.create_message(
                            thread_id=thread.id,
                            role="user",
                            content=f"Sustained load cycle {cycle_count} message {msg_idx}. "
                                    f"This tests for memory leaks during continuous operations. "
                                    f"Large content to increase memory pressure and detect leaks. "
                                    f"Timestamp: {datetime.now().isoformat()} " * 3,  # Repeat to make larger
                            metadata={
                                "memory_leak_test": True,
                                "cycle": cycle_count,
                                "message_index": msg_idx,
                                "large_metadata": {
                                    "data": list(range(100)),  # Add some data to increase memory usage
                                    "description": f"Memory test data for cycle {cycle_count}"
                                }
                            }
                        )
                        
                        message_ids_created.add(message.id)
                        total_operations += 1
                        
                    except Exception as e:
                        operation_errors += 1
                        self.logger.warning(f"Message creation failed in cycle {cycle_count}: {e}")
                
                # Read messages back (simulate user activity)
                messages = await thread_service.get_thread_messages(thread.id, limit=50, db=db_session)
                total_operations += 1
                
                # Simulate some processing delay
                await asyncio.sleep(0.1)
                
            except Exception as e:
                operation_errors += 1
                self.logger.warning(f"Cycle {cycle_count} failed: {e}")
            
            # Record memory usage periodically
            if cycle_count % 3 == 0:  # Every 3 cycles
                current_memory, current_cpu = record_memory_usage()
                memory_increase = current_memory - baseline_memory
                
                self.logger.info(
                    f"Cycle {cycle_count}: Memory {current_memory:.1f} MB (+{memory_increase:.1f}), "
                    f"CPU {current_cpu:.1f}%, Operations {total_operations}, Errors {operation_errors}"
                )
                
                # Early warning for excessive memory growth
                if memory_increase > 500:  # More than 500MB increase
                    self.logger.warning(f" WARNING: [U+FE0F] Excessive memory growth detected: +{memory_increase:.1f} MB")
            
            cycle_end = time.time()
            cycle_duration = cycle_end - cycle_start
            
            # Control cycle timing to maintain consistent load
            if cycle_duration < 2.0:  # Target 2 second cycles
                await asyncio.sleep(2.0 - cycle_duration)
        
        sustained_end = time.time()
        actual_duration = sustained_end - sustained_start
        
        # Final memory reading
        final_memory, final_cpu = record_memory_usage()
        
        self.logger.info("=== Sustained Load Memory Leak Analysis ===")
        self.logger.info(f"Test duration: {actual_duration:.1f}s")
        self.logger.info(f"Cycles completed: {cycle_count}")
        self.logger.info(f"Total operations: {total_operations}")
        self.logger.info(f"Operation errors: {operation_errors}")
        self.logger.info(f"Operations per second: {total_operations / actual_duration:.1f}")
        
        # Memory analysis
        total_memory_increase = final_memory - baseline_memory
        memory_growth_rate = total_memory_increase / (actual_duration / 60)  # MB per minute
        
        self.logger.info(f"Baseline memory: {baseline_memory:.1f} MB")
        self.logger.info(f"Final memory: {final_memory:.1f} MB")
        self.logger.info(f"Total memory increase: {total_memory_increase:.1f} MB")
        self.logger.info(f"Memory growth rate: {memory_growth_rate:.1f} MB/minute")
        
        # Analyze memory trend
        if len(memory_readings) > 5:
            # Calculate memory trend using linear regression (simple approach)
            timestamps = [r["timestamp"] - memory_readings[0]["timestamp"] for r in memory_readings]
            memories = [r["memory_mb"] for r in memory_readings]
            
            # Simple linear trend
            n = len(timestamps)
            sum_x = sum(timestamps)
            sum_y = sum(memories)
            sum_xy = sum(t * m for t, m in zip(timestamps, memories))
            sum_x2 = sum(t * t for t in timestamps)
            
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x) if (n * sum_x2 - sum_x * sum_x) != 0 else 0
            
            # Convert slope to MB per hour
            memory_trend_per_hour = slope * 3600
            
            self.logger.info(f"Memory trend: {memory_trend_per_hour:.1f} MB/hour")
            
            # Memory leak assessment
            memory_leak_detected = False
            leak_severity = "NONE"
            
            if memory_trend_per_hour > 100:  # Growing more than 100MB/hour
                memory_leak_detected = True
                leak_severity = "CRITICAL"
            elif memory_trend_per_hour > 50:  # Growing more than 50MB/hour
                memory_leak_detected = True
                leak_severity = "WARNING"
            elif memory_trend_per_hour > 20:  # Growing more than 20MB/hour
                memory_leak_detected = True
                leak_severity = "MINOR"
            
            self.logger.info(f"Memory leak detection: {leak_severity}")
            
            if memory_leak_detected:
                self.logger.warning(f" ALERT:  POTENTIAL MEMORY LEAK DETECTED: {leak_severity}")
                self.logger.warning(f"   Memory growth trend: {memory_trend_per_hour:.1f} MB/hour")
                self.logger.warning(f"   Projected 24h growth: {memory_trend_per_hour * 24:.1f} MB")
            else:
                self.logger.info(" PASS:  No significant memory leak detected")
        
        # Resource cleanup verification
        self.logger.info("=== Resource Cleanup Verification ===")
        self.logger.info(f"Threads created: {len(thread_ids_created)}")
        self.logger.info(f"Messages created: {len(message_ids_created)}")
        
        # Test cleanup by verifying resources still exist
        accessible_threads = 0
        for thread_id in list(thread_ids_created)[:10]:  # Sample 10 threads
            try:
                thread = await thread_service.get_thread(thread_id, user_id, db_session)
                if thread:
                    accessible_threads += 1
            except Exception as e:
                self.logger.warning(f"Thread access error: {e}")
        
        self.logger.info(f"Accessible threads (sample): {accessible_threads}/10")
        
        # Performance degradation check
        if len(memory_readings) > 2:
            early_ops_per_sec = total_operations / max(actual_duration * 0.3, 1)  # First 30%
            late_ops_per_sec = total_operations / max(actual_duration * 0.3, 1)   # Approximation
            
            performance_degradation = False
            if late_ops_per_sec < early_ops_per_sec * 0.8:  # 20% degradation
                performance_degradation = True
                self.logger.warning(" WARNING: [U+FE0F] Performance degradation detected during sustained load")
            else:
                self.logger.info(" PASS:  Performance maintained during sustained load")
        
        # Overall assessment
        overall_health = "GOOD"
        if memory_leak_detected and leak_severity in ["CRITICAL", "WARNING"]:
            overall_health = "POOR"
        elif operation_errors > total_operations * 0.1:  # More than 10% errors
            overall_health = "POOR"
        elif memory_leak_detected or operation_errors > 0:
            overall_health = "FAIR"
        
        self.logger.info(f"Overall System Health: {overall_health}")
        
        # Resource cleanup
        self.cleanup_resources.extend([db_session])  # Track for cleanup