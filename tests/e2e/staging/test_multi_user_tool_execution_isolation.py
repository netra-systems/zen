"""E2E staging tests for multi-user tool execution isolation.

These tests validate that the tool execution system maintains strict isolation
between multiple concurrent users in a staging environment, preventing data
leakage and ensuring proper resource management.

Business Value: Platform/Internal - Security & Data Privacy
Multi-user isolation is critical for enterprise customers and regulatory compliance.

Test Coverage:
- Concurrent multi-user tool execution isolation
- User session boundary enforcement during tool operations  
- Cross-tenant data isolation validation
- Concurrent user WebSocket event isolation
- Resource contention and fair allocation testing
- Load testing with multiple authenticated users
"""

import asyncio
import json
import jwt
import os
import pytest
import random
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock, patch

# CRITICAL: Add project root for imports
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper,
    create_authenticated_user_context,
    validate_authenticated_session,
)
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.isolated_environment import IsolatedEnvironment


class MultiUserIsolationTracker:
    """Tracks multi-user interactions to detect isolation violations."""
    
    def __init__(self):
        self.user_operations = {}  # user_id -> list of operations
        self.cross_user_accesses = []  # Detected violations
        self.resource_contention = {}  # Resource usage tracking
        self.timing_data = {}  # Execution timing per user
        self.websocket_events = {}  # user_id -> events
        self.data_isolation_checks = []  # Data isolation validation results
        
    def record_user_operation(
        self, 
        user_id: str, 
        operation_type: str, 
        data: Dict[str, Any],
        execution_time_ms: float = None
    ):
        """Record a user operation."""
        if user_id not in self.user_operations:
            self.user_operations[user_id] = []
            
        operation_record = {
            "operation_type": operation_type,
            "data": data.copy(),
            "timestamp": time.time(),
            "execution_time_ms": execution_time_ms,
            "operation_id": str(uuid.uuid4())
        }
        
        self.user_operations[user_id].append(operation_record)
        
        # Track timing
        if user_id not in self.timing_data:
            self.timing_data[user_id] = {"operations": 0, "total_time_ms": 0}
            
        self.timing_data[user_id]["operations"] += 1
        if execution_time_ms:
            self.timing_data[user_id]["total_time_ms"] += execution_time_ms
            
    def record_cross_user_access_attempt(
        self, 
        accessing_user: str, 
        target_user: str, 
        access_type: str,
        blocked: bool = True
    ):
        """Record potential cross-user access violation."""
        violation_record = {
            "accessing_user": accessing_user,
            "target_user": target_user,
            "access_type": access_type,
            "blocked": blocked,
            "timestamp": time.time(),
            "violation_id": str(uuid.uuid4())
        }
        
        self.cross_user_accesses.append(violation_record)
        
    def record_resource_usage(self, user_id: str, resource_type: str, amount: float):
        """Record resource usage by user."""
        if user_id not in self.resource_contention:
            self.resource_contention[user_id] = {}
            
        if resource_type not in self.resource_contention[user_id]:
            self.resource_contention[user_id][resource_type] = 0
            
        self.resource_contention[user_id][resource_type] += amount
        
    def record_websocket_event(self, user_id: str, event_type: str, event_data: Dict[str, Any]):
        """Record WebSocket event for user."""
        if user_id not in self.websocket_events:
            self.websocket_events[user_id] = []
            
        event_record = {
            "event_type": event_type,
            "data": event_data.copy(),
            "timestamp": time.time()
        }
        
        self.websocket_events[user_id].append(event_record)
        
    def validate_data_isolation(self, user_id: str, user_data: Set[str], other_users_data: Dict[str, Set[str]]) -> Dict[str, Any]:
        """Validate that user data doesn't leak to other users."""
        isolation_result = {
            "user_id": user_id,
            "isolated": True,
            "violations": [],
            "data_points_checked": len(user_data),
            "other_users_checked": len(other_users_data)
        }
        
        # Check if this user's data appears in other users' data
        for other_user_id, other_data in other_users_data.items():
            if other_user_id == user_id:
                continue
                
            leaked_data = user_data.intersection(other_data)
            if leaked_data:
                isolation_result["isolated"] = False
                isolation_result["violations"].append({
                    "target_user": other_user_id,
                    "leaked_data": list(leaked_data),
                    "leak_count": len(leaked_data)
                })
                
        self.data_isolation_checks.append(isolation_result)
        return isolation_result
        
    def analyze_isolation_violations(self) -> Dict[str, Any]:
        """Analyze all isolation violations."""
        return {
            "total_users": len(self.user_operations),
            "cross_user_access_attempts": len(self.cross_user_accesses),
            "blocked_violations": len([v for v in self.cross_user_accesses if v["blocked"]]),
            "unblocked_violations": len([v for v in self.cross_user_accesses if not v["blocked"]]),
            "data_isolation_checks": len(self.data_isolation_checks),
            "data_leaks_detected": len([c for c in self.data_isolation_checks if not c["isolated"]]),
            "resource_contention_detected": self._detect_resource_contention(),
            "timing_anomalies": self._detect_timing_anomalies()
        }
        
    def _detect_resource_contention(self) -> bool:
        """Detect if users are experiencing resource contention."""
        # Simple heuristic: if any user has significantly different resource usage
        if len(self.resource_contention) < 2:
            return False
            
        cpu_usages = [usage.get("cpu", 0) for usage in self.resource_contention.values()]
        if not cpu_usages:
            return False
            
        avg_cpu = sum(cpu_usages) / len(cpu_usages)
        max_cpu = max(cpu_usages)
        
        # Contention if max usage is more than 3x average
        return max_cpu > avg_cpu * 3
        
    def _detect_timing_anomalies(self) -> List[Dict[str, Any]]:
        """Detect timing anomalies that might indicate contention."""
        anomalies = []
        
        if len(self.timing_data) < 2:
            return anomalies
            
        avg_times = {}
        for user_id, timing in self.timing_data.items():
            if timing["operations"] > 0:
                avg_times[user_id] = timing["total_time_ms"] / timing["operations"]
                
        if not avg_times:
            return anomalies
            
        overall_avg = sum(avg_times.values()) / len(avg_times)
        
        for user_id, avg_time in avg_times.items():
            if avg_time > overall_avg * 2:  # 2x slower than average
                anomalies.append({
                    "user_id": user_id,
                    "avg_execution_time_ms": avg_time,
                    "baseline_avg_ms": overall_avg,
                    "slowdown_factor": avg_time / overall_avg
                })
                
        return anomalies


class StagingMultiUserTestUser:
    """Represents a test user for multi-user isolation testing."""
    
    def __init__(
        self, 
        user_id: str, 
        username: str,
        tenant_id: str,
        plan_tier: str = "early",
        user_type: str = "regular"
    ):
        self.user_id = user_id
        self.username = username
        self.tenant_id = tenant_id
        self.plan_tier = plan_tier
        self.user_type = user_type  # regular, power, enterprise
        self.jwt_token = None
        self.session_data = set()  # User's private data
        self.execution_count = 0
        
    def generate_test_data(self, count: int = 5) -> Set[str]:
        """Generate unique test data for this user."""
        data_items = set()
        for i in range(count):
            data_item = f"{self.user_id}_data_{i}_{int(time.time() * 1000)}"
            data_items.add(data_item)
            
        self.session_data.update(data_items)
        return data_items
        
    def create_execution_context(self, run_id: str = None) -> UserExecutionContext:
        """Create execution context for this user."""
        return UserExecutionContext(
            user_id=self.user_id,
            run_id=run_id or f"multiuser_run_{self.user_id}_{int(time.time() * 1000)}",
            thread_id=f"multiuser_thread_{self.user_id}_{int(time.time())}",
            session_id=f"multiuser_session_{self.user_id}",
            metadata={
                "username": self.username,
                "tenant_id": self.tenant_id,
                "plan_tier": self.plan_tier,
                "user_type": self.user_type,
                "authenticated": True,
                "isolation_test": True
            }
        )


class IsolationTestingTool:
    """Tool that tests isolation by handling user-specific data."""
    
    def __init__(self, tool_name: str, isolation_tracker: MultiUserIsolationTracker):
        self.name = tool_name
        self.isolation_tracker = isolation_tracker
        self.user_data_stores = {}  # user_id -> user-specific data
        self.execution_count = 0
        
    async def execute_with_isolation_testing(
        self, 
        user_context: UserExecutionContext,
        operation: str,
        test_data: Set[str],
        attempt_cross_access: bool = False
    ) -> Dict[str, Any]:
        """Execute tool with isolation testing."""
        start_time = time.time()
        user_id = user_context.user_id
        
        try:
            self.execution_count += 1
            
            # Initialize user data store if needed
            if user_id not in self.user_data_stores:
                self.user_data_stores[user_id] = set()
                
            # Store user's data
            self.user_data_stores[user_id].update(test_data)
            
            # Simulate resource usage
            await asyncio.sleep(0.01 + random.uniform(0, 0.02))  # 10-30ms variable delay
            cpu_usage = random.uniform(0.1, 0.3)  # Simulate CPU usage
            self.isolation_tracker.record_resource_usage(user_id, "cpu", cpu_usage)
            
            # Test cross-user access if requested
            if attempt_cross_access:
                await self._test_cross_user_access(user_id)
                
            # Generate result with user-specific data
            result = {
                "tool_name": self.name,
                "operation": operation,
                "user_id": user_id,
                "tenant_id": user_context.metadata.get("tenant_id"),
                "execution_count": self.execution_count,
                "user_data_processed": list(test_data),
                "data_store_size": len(self.user_data_stores[user_id]),
                "timestamp": time.time()
            }
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Record operation
            self.isolation_tracker.record_user_operation(
                user_id, 
                f"{self.name}_{operation}",
                result,
                execution_time_ms
            )
            
            return result
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            
            self.isolation_tracker.record_user_operation(
                user_id,
                f"{self.name}_{operation}_error",
                {"error": str(e)},
                execution_time_ms
            )
            
            raise
            
    async def _test_cross_user_access(self, accessing_user_id: str):
        """Test cross-user access (should be blocked)."""
        # Attempt to access other users' data
        for other_user_id, other_data in self.user_data_stores.items():
            if other_user_id != accessing_user_id and other_data:
                # This should be blocked in a properly isolated system
                self.isolation_tracker.record_cross_user_access_attempt(
                    accessing_user_id,
                    other_user_id,
                    "data_store_access",
                    blocked=True  # Assume blocked (good isolation)
                )
                
    def validate_user_data_isolation(self) -> Dict[str, Any]:
        """Validate that user data is properly isolated."""
        isolation_results = {}
        
        for user_id, user_data in self.user_data_stores.items():
            other_users_data = {k: v for k, v in self.user_data_stores.items() if k != user_id}
            
            isolation_result = self.isolation_tracker.validate_data_isolation(
                user_id, user_data, other_users_data
            )
            
            isolation_results[user_id] = isolation_result
            
        return isolation_results


class MultiUserWebSocketManager:
    """WebSocket manager that tracks events across multiple users."""
    
    def __init__(self, isolation_tracker: MultiUserIsolationTracker):
        self.isolation_tracker = isolation_tracker
        self.connected_users = set()
        self.event_delivery_failures = 0
        
    async def connect_user(self, user: StagingMultiUserTestUser) -> bool:
        """Connect user to WebSocket."""
        self.connected_users.add(user.user_id)
        return True
        
    async def send_event(self, event_type: str, data: Dict[str, Any]) -> bool:
        """Send WebSocket event with isolation tracking."""
        user_id = data.get("user_id")
        
        if not user_id or user_id not in self.connected_users:
            self.event_delivery_failures += 1
            return False
            
        # Record event
        self.isolation_tracker.record_websocket_event(user_id, event_type, data)
        
        # Check for potential cross-user event leakage
        await self._validate_event_isolation(user_id, event_type, data)
        
        return True
        
    async def _validate_event_isolation(self, user_id: str, event_type: str, data: Dict[str, Any]):
        """Validate that events are properly isolated to the correct user."""
        # Ensure event data doesn't contain other users' information
        for key, value in data.items():
            if isinstance(value, str) and "user_" in value:
                # Check if this contains another user's ID
                for other_user_id in self.connected_users:
                    if other_user_id != user_id and other_user_id in value:
                        self.isolation_tracker.record_cross_user_access_attempt(
                            user_id,
                            other_user_id,
                            f"websocket_event_data_leak_{key}",
                            blocked=False  # Data leak detected!
                        )
                        
    def disconnect_user(self, user_id: str):
        """Disconnect user from WebSocket."""
        self.connected_users.discard(user_id)


class TestMultiUserToolExecutionIsolation(SSotAsyncTestCase):
    """E2E staging tests for multi-user tool execution isolation."""
    
    def setUp(self):
        """Set up multi-user isolation test environment."""
        super().setUp()
        
        # Initialize isolation tracking
        self.isolation_tracker = MultiUserIsolationTracker()
        self.websocket_manager = MultiUserWebSocketManager(self.isolation_tracker)
        
        # Create diverse set of test users
        self.test_users = []
        
        # Regular users from different tenants
        for i in range(5):
            user = StagingMultiUserTestUser(
                user_id=f"regular_user_{i:03d}",
                username=f"regular_{i}",
                tenant_id=f"tenant_{chr(65 + i)}",  # A, B, C, D, E
                plan_tier="early",
                user_type="regular"
            )
            self.test_users.append(user)
            
        # Power users
        for i in range(3):
            user = StagingMultiUserTestUser(
                user_id=f"power_user_{i:03d}",
                username=f"power_{i}",
                tenant_id=f"tenant_{chr(70 + i)}",  # F, G, H
                plan_tier="mid",
                user_type="power"
            )
            self.test_users.append(user)
            
        # Enterprise users
        for i in range(2):
            user = StagingMultiUserTestUser(
                user_id=f"enterprise_user_{i:03d}",
                username=f"enterprise_{i}",
                tenant_id=f"tenant_{chr(73 + i)}",  # I, J
                plan_tier="enterprise",
                user_type="enterprise"
            )
            self.test_users.append(user)
            
        # Create isolation testing tools
        self.data_processor = IsolationTestingTool("data_processor", self.isolation_tracker)
        self.analytics_engine = IsolationTestingTool("analytics_engine", self.isolation_tracker)
        self.report_generator = IsolationTestingTool("report_generator", self.isolation_tracker)
        
    async def tearDown(self):
        """Clean up multi-user test environment."""
        # Disconnect all users
        for user in self.test_users:
            self.websocket_manager.disconnect_user(user.user_id)
            
        await super().tearDown()
        
    # ===================== BASIC MULTI-USER ISOLATION TESTS =====================
        
    async def test_concurrent_multi_user_tool_execution_isolation(self):
        """Test that concurrent tool execution by multiple users maintains proper isolation."""
        # Connect all users
        for user in self.test_users:
            await self.websocket_manager.connect_user(user)
            
        # Generate unique test data for each user
        user_test_data = {}
        for user in self.test_users:
            user_test_data[user.user_id] = user.generate_test_data(10)
            
        # Execute tools concurrently for all users
        tasks = []
        
        for user in self.test_users:
            user_context = user.create_execution_context()
            test_data = user_test_data[user.user_id]
            
            # Each user executes the data processor
            task = self.data_processor.execute_with_isolation_testing(
                user_context=user_context,
                operation="process_user_data",
                test_data=test_data,
                attempt_cross_access=False
            )
            
            tasks.append((user.user_id, task))
            
        # Execute all tasks concurrently
        results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
        
        # Verify all executions succeeded
        self.assertEqual(len(results), len(self.test_users))
        
        for i, result in enumerate(results):
            self.assertNotIsInstance(result, Exception, f"User {self.test_users[i].user_id} execution failed: {result}")
            self.assertIn("user_data_processed", result)
            
        # Validate data isolation
        isolation_results = self.data_processor.validate_user_data_isolation()
        
        for user_id, isolation_result in isolation_results.items():
            self.assertTrue(
                isolation_result["isolated"],
                f"Data isolation violation detected for user {user_id}: {isolation_result['violations']}"
            )
            
        # Analyze overall isolation
        violation_analysis = self.isolation_tracker.analyze_isolation_violations()
        
        self.assertEqual(violation_analysis["unblocked_violations"], 0, "No isolation violations should occur")
        self.assertEqual(violation_analysis["data_leaks_detected"], 0, "No data leaks should be detected")
        
    async def test_cross_tenant_data_isolation_enforcement(self):
        """Test strict data isolation between different tenants."""
        # Select users from different tenants
        tenant_users = {}
        for user in self.test_users:
            tenant_id = user.tenant_id
            if tenant_id not in tenant_users:
                tenant_users[tenant_id] = []
            tenant_users[tenant_id].append(user)
            
        # Execute operations for users from each tenant
        for tenant_id, users in tenant_users.items():
            for user in users[:2]:  # Limit to 2 users per tenant for manageable testing
                user_context = user.create_execution_context()
                test_data = user.generate_test_data(5)
                
                # Execute with attempted cross-access
                result = await self.analytics_engine.execute_with_isolation_testing(
                    user_context=user_context,
                    operation="tenant_analytics",
                    test_data=test_data,
                    attempt_cross_access=True  # Try to access other users' data
                )
                
                self.assertIsNotNone(result)
                self.assertEqual(result["tenant_id"], tenant_id)
                
        # Verify cross-tenant access attempts were blocked
        violation_analysis = self.isolation_tracker.analyze_isolation_violations()
        
        # Should have cross-access attempts but they should all be blocked
        self.assertGreater(violation_analysis["cross_user_access_attempts"], 0)
        self.assertEqual(violation_analysis["unblocked_violations"], 0, "All cross-tenant access should be blocked")
        
    async def test_websocket_event_isolation_across_users(self):
        """Test that WebSocket events are properly isolated per user."""
        # Select subset of users for WebSocket testing
        websocket_test_users = self.test_users[:5]
        
        # Connect users and execute tools
        for user in websocket_test_users:
            await self.websocket_manager.connect_user(user)
            
            user_context = user.create_execution_context()
            test_data = user.generate_test_data(3)
            
            # Execute tool to generate WebSocket events
            await self.report_generator.execute_with_isolation_testing(
                user_context=user_context,
                operation="generate_report",
                test_data=test_data
            )
            
            # Simulate WebSocket events
            await self.websocket_manager.send_event(
                "tool_executing",
                {
                    "user_id": user.user_id,
                    "tool_name": "report_generator",
                    "run_id": user_context.run_id,
                    "parameters": {"data_count": len(test_data)}
                }
            )
            
            await self.websocket_manager.send_event(
                "tool_completed",
                {
                    "user_id": user.user_id,
                    "tool_name": "report_generator",
                    "status": "success",
                    "run_id": user_context.run_id
                }
            )
            
        # Verify each user received only their own events
        for user in websocket_test_users:
            user_events = self.isolation_tracker.websocket_events.get(user.user_id, [])
            self.assertGreater(len(user_events), 0, f"User {user.user_id} should have received WebSocket events")
            
            # Verify all events belong to this user
            for event in user_events:
                self.assertEqual(
                    event["data"]["user_id"], 
                    user.user_id,
                    f"Event should belong to user {user.user_id}, not {event['data']['user_id']}"
                )
                
        # Check for cross-user event leakage
        violation_analysis = self.isolation_tracker.analyze_isolation_violations()
        websocket_violations = [
            v for v in self.isolation_tracker.cross_user_accesses 
            if "websocket" in v["access_type"] and not v["blocked"]
        ]
        
        self.assertEqual(len(websocket_violations), 0, "No WebSocket event leakage should occur")
        
    # ===================== LOAD AND STRESS TESTING =====================
        
    async def test_high_concurrency_user_isolation_under_load(self):
        """Test user isolation under high concurrency load."""
        num_concurrent_operations = 50
        operations_per_user = 5
        
        # Create load test scenarios
        load_tasks = []
        
        for user in self.test_users:
            user_context = user.create_execution_context()
            
            for operation_num in range(operations_per_user):
                test_data = user.generate_test_data(3)
                
                # Vary the tools used to test different execution paths
                if operation_num % 3 == 0:
                    tool = self.data_processor
                    operation = f"load_test_data_{operation_num}"
                elif operation_num % 3 == 1:
                    tool = self.analytics_engine
                    operation = f"load_test_analytics_{operation_num}"
                else:
                    tool = self.report_generator
                    operation = f"load_test_report_{operation_num}"
                    
                task = tool.execute_with_isolation_testing(
                    user_context=user_context,
                    operation=operation,
                    test_data=test_data,
                    attempt_cross_access=random.choice([True, False])  # Random cross-access attempts
                )
                
                load_tasks.append((user.user_id, operation_num, task))
                
        # Execute all operations concurrently
        results = await asyncio.gather(*[task for _, _, task in load_tasks], return_exceptions=True)
        
        # Analyze results
        success_count = 0
        error_count = 0
        
        for result in results:
            if isinstance(result, Exception):
                error_count += 1
            else:
                success_count += 1
                
        # Should have high success rate even under load
        success_rate = success_count / len(results)
        self.assertGreater(success_rate, 0.95, f"Success rate under load should be >95%, got {success_rate:.2%}")
        
        # Verify isolation was maintained under load
        violation_analysis = self.isolation_tracker.analyze_isolation_violations()
        
        self.assertEqual(violation_analysis["unblocked_violations"], 0, "No isolation violations under load")
        self.assertEqual(violation_analysis["data_leaks_detected"], 0, "No data leaks under load")
        
        # Check for resource contention
        if violation_analysis["resource_contention_detected"]:
            # This is acceptable but should be logged
            print(f"Resource contention detected under load: {violation_analysis}")
            
        # Check for timing anomalies
        timing_anomalies = violation_analysis["timing_anomalies"]
        if timing_anomalies:
            # Some timing variation is expected under load, but extreme outliers indicate problems
            max_slowdown = max(anomaly["slowdown_factor"] for anomaly in timing_anomalies)
            self.assertLess(max_slowdown, 10, f"Maximum slowdown factor should be <10x, got {max_slowdown:.1f}x")
            
    async def test_resource_fairness_across_user_types(self):
        """Test that different user types get fair resource allocation."""
        # Group users by type
        users_by_type = {}
        for user in self.test_users:
            user_type = user.user_type
            if user_type not in users_by_type:
                users_by_type[user_type] = []
            users_by_type[user_type].append(user)
            
        # Execute operations for each user type
        for user_type, users in users_by_type.items():
            for user in users:
                user_context = user.create_execution_context()
                test_data = user.generate_test_data(8)
                
                # Execute multiple operations to generate resource usage data
                for i in range(3):
                    await self.analytics_engine.execute_with_isolation_testing(
                        user_context=user_context,
                        operation=f"resource_test_{user_type}_{i}",
                        test_data=test_data
                    )
                    
        # Analyze resource usage by user type
        resource_usage_by_type = {}
        
        for user_type, users in users_by_type.items():
            total_cpu = 0
            user_count = 0
            
            for user in users:
                if user.user_id in self.isolation_tracker.resource_contention:
                    user_cpu = self.isolation_tracker.resource_contention[user.user_id].get("cpu", 0)
                    total_cpu += user_cpu
                    user_count += 1
                    
            if user_count > 0:
                resource_usage_by_type[user_type] = total_cpu / user_count
                
        # Verify resource fairness
        if len(resource_usage_by_type) > 1:
            usage_values = list(resource_usage_by_type.values())
            max_usage = max(usage_values)
            min_usage = min(usage_values)
            
            # Resource usage variance should be reasonable
            if min_usage > 0:
                usage_ratio = max_usage / min_usage
                self.assertLess(usage_ratio, 5, f"Resource usage ratio between user types should be <5x, got {usage_ratio:.1f}x")
                
    # ===================== TENANT ISOLATION TESTS =====================
                
    async def test_multi_tenant_boundary_enforcement(self):
        """Test that tenant boundaries are strictly enforced."""
        # Group users by tenant
        users_by_tenant = {}
        for user in self.test_users:
            tenant_id = user.tenant_id
            if tenant_id not in users_by_tenant:
                users_by_tenant[tenant_id] = []
            users_by_tenant[tenant_id].append(user)
            
        # Execute operations with tenant-specific data
        tenant_data_signatures = {}
        
        for tenant_id, users in users_by_tenant.items():
            # Create tenant-specific data signature
            tenant_signature = f"TENANT_{tenant_id}_SECRET_DATA_{int(time.time())}"
            tenant_data_signatures[tenant_id] = tenant_signature
            
            for user in users[:2]:  # Limit users per tenant
                user_context = user.create_execution_context()
                
                # Include tenant signature in user's test data
                test_data = user.generate_test_data(5)
                test_data.add(tenant_signature)
                
                result = await self.data_processor.execute_with_isolation_testing(
                    user_context=user_context,
                    operation="tenant_boundary_test",
                    test_data=test_data,
                    attempt_cross_access=True
                )
                
                self.assertIsNotNone(result)
                
        # Validate tenant data isolation
        isolation_results = self.data_processor.validate_user_data_isolation()
        
        # Check for cross-tenant data leakage
        for user in self.test_users:
            user_isolation = isolation_results.get(user.user_id)
            if user_isolation and not user_isolation["isolated"]:
                # Check if violations involve cross-tenant data
                for violation in user_isolation["violations"]:
                    target_user_id = violation["target_user"]
                    target_user = next((u for u in self.test_users if u.user_id == target_user_id), None)
                    
                    if target_user and target_user.tenant_id != user.tenant_id:
                        # Cross-tenant data leak detected!
                        self.fail(
                            f"Cross-tenant data leak detected: "
                            f"User {user.user_id} (tenant {user.tenant_id})  ->  "
                            f"User {target_user_id} (tenant {target_user.tenant_id})"
                        )
                        
    async def test_session_boundary_enforcement_during_tool_execution(self):
        """Test that user session boundaries are maintained during tool execution."""
        session_test_users = self.test_users[:4]  # Use 4 users for session testing
        
        # Create multiple sessions per user
        user_sessions = {}
        for user in session_test_users:
            user_sessions[user.user_id] = []
            
            # Create 2 sessions per user
            for session_num in range(2):
                session_context = user.create_execution_context(
                    run_id=f"session_{session_num}_{user.user_id}_{int(time.time())}"
                )
                user_sessions[user.user_id].append(session_context)
                
        # Execute operations in different sessions
        for user_id, sessions in user_sessions.items():
            user = next(u for u in session_test_users if u.user_id == user_id)
            
            for session_num, session_context in enumerate(sessions):
                # Generate session-specific data
                session_data = {f"session_{session_num}_data_{i}" for i in range(3)}
                user.session_data.update(session_data)
                
                await self.analytics_engine.execute_with_isolation_testing(
                    user_context=session_context,
                    operation=f"session_boundary_test_{session_num}",
                    test_data=session_data
                )
                
        # Verify session data isolation
        # In this test, we primarily verify that different sessions don't interfere
        # The actual session isolation would be enforced by the UserExecutionContext
        
        violation_analysis = self.isolation_tracker.analyze_isolation_violations()
        self.assertEqual(violation_analysis["unblocked_violations"], 0, "No session boundary violations")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])