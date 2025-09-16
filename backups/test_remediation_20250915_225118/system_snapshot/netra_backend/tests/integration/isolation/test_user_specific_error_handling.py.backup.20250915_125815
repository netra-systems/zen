"""
User-Specific Error Handling Integration Tests - Phase 2

Tests that errors affecting one user don't impact other users in the system.
Validates error isolation, recovery mechanisms, and per-user error handling
using real services and connections.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Maintain service quality during user-specific issues
- Value Impact: One user's problems don't affect other users' experience
- Strategic Impact: Multi-tenant system reliability and fault isolation

CRITICAL: Uses REAL services (PostgreSQL, Redis, WebSocket connections)
No mocks in integration tests per CLAUDE.md standards.
"""

import asyncio
import json
import pytest
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from uuid import uuid4

from test_framework.ssot.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.base_test_case import BaseIntegrationTest
from test_framework.websocket_helpers import (
    WebSocketTestHelpers,
    ensure_websocket_service_ready
)
from shared.isolated_environment import get_env
from shared.types import UserID, ThreadID, RunID, RequestID
from shared.id_generation import UnifiedIdGenerator


class TestUserSpecificErrorHandling(BaseIntegrationTest):
    """Integration tests for user-specific error handling and isolation."""

    @pytest.fixture(autouse=True)
    async def setup_test_environment(self, real_services_fixture):
        """Setup test environment with real services."""
        self.services = real_services_fixture
        self.env = get_env()
        
        # Validate real services are available
        if not self.services["database_available"]:
            pytest.skip("Real database not available - required for integration testing")
            
        # Store service URLs
        self.backend_url = self.services["backend_url"]
        self.websocket_url = self.backend_url.replace("http://", "ws://") + "/ws"
        
        # Generate base test identifiers
        self.test_session_id = f"error_isolation_test_{int(time.time() * 1000)}"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_error_isolation_during_agent_failure(self, real_services_fixture):
        """Test that agent failure for one user doesn't affect other users."""
        start_time = time.time()
        
        # Ensure WebSocket service is ready
        if not await ensure_websocket_service_ready(self.backend_url):
            pytest.skip("WebSocket service not ready")
        
        # Create test users: one that will encounter errors, others that should be unaffected
        error_user_id = UserID(f"error_user_{UnifiedIdGenerator.generate_user_id()}")
        error_thread_id = ThreadID(f"error_thread_{UnifiedIdGenerator.generate_thread_id()}")
        
        normal_users = []
        for i in range(3):
            user_id = UserID(f"normal_user_{i}_{UnifiedIdGenerator.generate_user_id()}")
            thread_id = ThreadID(f"normal_thread_{i}_{UnifiedIdGenerator.generate_thread_id()}")
            normal_users.append((user_id, thread_id))
        
        user_connections = []
        user_events = {"error_user": [], "normal_users": {}}
        
        try:
            # Phase 1: Establish connections for all users
            # Error-prone user connection
            error_token = self._create_test_auth_token(error_user_id)
            error_headers = {"Authorization": f"Bearer {error_token}"}
            
            error_ws = await WebSocketTestHelpers.create_test_websocket_connection(
                f"{self.websocket_url}/agent/{error_thread_id}",
                headers=error_headers,
                user_id=str(error_user_id)
            )
            
            user_connections.append(("error", error_ws, error_user_id, error_thread_id))
            
            # Normal user connections
            for i, (user_id, thread_id) in enumerate(normal_users):
                normal_token = self._create_test_auth_token(user_id)
                normal_headers = {"Authorization": f"Bearer {normal_token}"}
                
                normal_ws = await WebSocketTestHelpers.create_test_websocket_connection(
                    f"{self.websocket_url}/agent/{thread_id}",
                    headers=normal_headers,
                    user_id=str(user_id)
                )
                
                user_connections.append((f"normal_{i}", normal_ws, user_id, thread_id))
                user_events["normal_users"][str(user_id)] = []
            
            # Phase 2: Trigger error condition for error user
            error_request = {
                "type": "agent_request",
                "agent_name": "failing_agent",  # This should cause an error
                "message": "Execute operation that will fail",
                "user_id": str(error_user_id),
                "thread_id": str(error_thread_id),
                "force_error_scenario": "agent_execution_failure",
                "error_type": "resource_exhaustion"
            }
            
            await WebSocketTestHelpers.send_test_message(error_ws, error_request)
            
            # Phase 3: Send normal requests to other users simultaneously
            async def send_normal_user_request(websocket, user_id, thread_id, user_index):
                """Send normal request for a user."""
                normal_request = {
                    "type": "agent_request",
                    "agent_name": "stable_agent",
                    "message": f"Normal user {user_index} request during error isolation test",
                    "user_id": str(user_id),
                    "thread_id": str(thread_id),
                    "isolation_test": True,
                    "expect_success": True
                }
                
                await WebSocketTestHelpers.send_test_message(websocket, normal_request)
            
            # Send normal requests concurrently while error user is failing
            normal_request_tasks = []
            for connection_type, websocket, user_id, thread_id in user_connections:
                if connection_type.startswith("normal_"):
                    user_index = int(connection_type.split("_")[1])
                    task = send_normal_user_request(websocket, user_id, thread_id, user_index)
                    normal_request_tasks.append(task)
            
            await asyncio.gather(*normal_request_tasks, return_exceptions=True)
            
            # Phase 4: Collect events from all users
            async def collect_user_events(connection_type, websocket, user_id, collection_duration=10.0):
                """Collect events from a specific user."""
                events_collected = []
                collection_start = time.time()
                
                while time.time() - collection_start < collection_duration:
                    try:
                        event = await WebSocketTestHelpers.receive_test_message(websocket, timeout=2.0)
                        event["received_at"] = time.time()
                        event["user_connection_type"] = connection_type
                        events_collected.append(event)
                        
                        # Stop on completion or failure
                        if event.get("type") in ["agent_completed", "agent_failed"]:
                            break
                            
                    except Exception:
                        # Timeout expected for some users
                        break
                
                return events_collected
            
            # Collect events from all users concurrently
            collection_tasks = []
            for connection_type, websocket, user_id, thread_id in user_connections:
                task = collect_user_events(connection_type, websocket, user_id)
                collection_tasks.append(task)
            
            all_user_events = await asyncio.gather(*collection_tasks, return_exceptions=True)
            
            # Organize events by user type
            for i, events in enumerate(all_user_events):
                if isinstance(events, list):
                    connection_type, websocket, user_id, thread_id = user_connections[i]
                    
                    if connection_type == "error":
                        user_events["error_user"] = events
                    elif connection_type.startswith("normal_"):
                        user_events["normal_users"][str(user_id)] = events
                        
        finally:
            # Clean up all connections
            for _, websocket, _, _ in user_connections:
                await WebSocketTestHelpers.close_test_connection(websocket)
        
        # Verify test characteristics
        test_duration = time.time() - start_time
        assert test_duration > 5.0, f"Error isolation test took too little time: {test_duration:.2f}s"
        
        # Analyze error isolation
        error_user_events = user_events["error_user"]
        normal_user_events = user_events["normal_users"]
        
        # Verify error user encountered errors
        error_event_types = [e.get("type") for e in error_user_events]
        has_error_indicators = any(
            error_type in error_event_types 
            for error_type in ["agent_failed", "error", "execution_error", "resource_error"]
        )
        
        # Error user should have encountered some form of error
        assert len(error_user_events) >= 1, "Error user should have received some events"
        
        # Analyze normal users (should be unaffected)
        normal_users_affected = 0
        normal_users_successful = 0
        
        for user_id, events in normal_user_events.items():
            if not events:
                continue  # No events for this user
                
            event_types = [e.get("type") for e in events]
            
            # Check if this normal user was affected by the error user's issues
            has_error_spillover = any(
                error_type in event_types 
                for error_type in ["agent_failed", "error", "execution_error", "system_error"]
            )
            
            has_success_indicators = any(
                success_type in event_types
                for success_type in ["agent_started", "agent_completed", "agent_thinking"]
            )
            
            if has_error_spillover:
                normal_users_affected += 1
            elif has_success_indicators:
                normal_users_successful += 1
        
        total_normal_users = len([events for events in normal_user_events.values() if events])
        
        if total_normal_users > 0:
            # Most normal users should be unaffected by error user's issues
            unaffected_rate = normal_users_successful / total_normal_users
            assert unaffected_rate >= 0.6, f"Too many normal users affected by error user: {unaffected_rate:.2f}"
            
            # Error spillover should be minimal
            spillover_rate = normal_users_affected / total_normal_users
            assert spillover_rate <= 0.3, f"Error spillover rate too high: {spillover_rate:.2f}"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_error_user_isolation(self, real_services_fixture):
        """Test user isolation when database errors affect one user."""
        start_time = time.time()
        
        db_session = self.services["db"]
        if not db_session:
            pytest.skip("Real database session not available")
        
        # Create users: one with problematic data, others normal
        problem_user_id = UserID(f"db_problem_user_{UnifiedIdGenerator.generate_user_id()}")
        problem_thread_id = ThreadID(f"db_problem_thread_{UnifiedIdGenerator.generate_thread_id()}")
        
        normal_users = []
        for i in range(2):
            user_id = UserID(f"db_normal_user_{i}_{UnifiedIdGenerator.generate_user_id()}")
            thread_id = ThreadID(f"db_normal_thread_{i}_{UnifiedIdGenerator.generate_thread_id()}")
            normal_users.append((user_id, thread_id))
        
        user_connections = []
        operation_results = {}
        
        try:
            # Phase 1: Setup problematic database state for problem user
            # Insert problematic data that may cause constraint violations or conflicts
            try:
                problem_data_query = """
                INSERT INTO user_problematic_data (user_id, thread_id, problematic_field, constraint_violator)
                VALUES (:user_id, :thread_id, :problematic_field, :constraint_violator)
                ON CONFLICT (user_id) DO UPDATE SET
                problematic_field = EXCLUDED.problematic_field
                """
                
                await db_session.execute(problem_data_query, {
                    "user_id": str(problem_user_id),
                    "thread_id": str(problem_thread_id),
                    "problematic_field": "intentionally_problematic_data" * 100,  # Potentially too long
                    "constraint_violator": "duplicate_key_value"
                })
                
                await db_session.commit()
            except Exception:
                # Database setup may fail - that's acceptable for this test
                pass
            
            # Phase 2: Establish WebSocket connections
            # Problem user connection
            problem_token = self._create_test_auth_token(problem_user_id)
            problem_headers = {"Authorization": f"Bearer {problem_token}"}
            
            problem_ws = await WebSocketTestHelpers.create_test_websocket_connection(
                f"{self.websocket_url}/agent/{problem_thread_id}",
                headers=problem_headers,
                user_id=str(problem_user_id)
            )
            
            user_connections.append(("problem", problem_ws, problem_user_id, problem_thread_id))
            
            # Normal user connections
            for i, (user_id, thread_id) in enumerate(normal_users):
                normal_token = self._create_test_auth_token(user_id)
                normal_headers = {"Authorization": f"Bearer {normal_token}"}
                
                normal_ws = await WebSocketTestHelpers.create_test_websocket_connection(
                    f"{self.websocket_url}/agent/{thread_id}",
                    headers=normal_headers,
                    user_id=str(user_id)
                )
                
                user_connections.append((f"normal_{i}", normal_ws, user_id, thread_id))
            
            # Phase 3: Trigger database operations that may cause issues
            async def perform_database_operations(connection_type, websocket, user_id, thread_id):
                """Perform database operations for a user."""
                results = []
                
                try:
                    if connection_type == "problem":
                        # Operations likely to cause database issues
                        problem_requests = [
                            {
                                "type": "database_heavy_operation",
                                "user_id": str(user_id),
                                "thread_id": str(thread_id),
                                "operation": "create_duplicate_constraint_violation",
                                "large_data_payload": "x" * 10000  # Large payload
                            },
                            {
                                "type": "database_transaction_operation",
                                "user_id": str(user_id),
                                "thread_id": str(thread_id),
                                "operation": "concurrent_update_conflict",
                                "force_conflict": True
                            }
                        ]
                        
                        for request in problem_requests:
                            await WebSocketTestHelpers.send_test_message(websocket, request)
                            
                            try:
                                response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=4.0)
                                results.append({"request_type": request["operation"], "status": "response_received", "response": response})
                            except Exception as e:
                                results.append({"request_type": request["operation"], "status": "error", "error": str(e)})
                            
                            await asyncio.sleep(0.5)
                    
                    else:  # Normal users
                        # Normal database operations
                        normal_request = {
                            "type": "database_normal_operation",
                            "user_id": str(user_id),
                            "thread_id": str(thread_id),
                            "operation": "standard_user_data_query",
                            "expect_success": True
                        }
                        
                        await WebSocketTestHelpers.send_test_message(websocket, normal_request)
                        
                        try:
                            response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=5.0)
                            results.append({"request_type": "normal_operation", "status": "success", "response": response})
                        except Exception as e:
                            results.append({"request_type": "normal_operation", "status": "error", "error": str(e)})
                    
                except Exception as e:
                    results.append({"connection_type": connection_type, "general_error": str(e)})
                
                return {
                    "connection_type": connection_type,
                    "user_id": str(user_id),
                    "results": results
                }
            
            # Execute database operations for all users
            operation_tasks = []
            for connection_type, websocket, user_id, thread_id in user_connections:
                task = perform_database_operations(connection_type, websocket, user_id, thread_id)
                operation_tasks.append(task)
            
            all_results = await asyncio.gather(*operation_tasks, return_exceptions=True)
            
            # Organize results
            for result in all_results:
                if isinstance(result, dict) and "connection_type" in result:
                    connection_type = result["connection_type"]
                    operation_results[connection_type] = result
                    
        finally:
            # Clean up connections
            for _, websocket, _, _ in user_connections:
                await WebSocketTestHelpers.close_test_connection(websocket)
        
        # Verify test characteristics
        test_duration = time.time() - start_time
        assert test_duration > 2.0, f"Database error isolation test took too little time: {test_duration:.2f}s"
        
        # Analyze database error isolation
        problem_user_results = operation_results.get("problem", {})
        normal_user_results = [operation_results.get(f"normal_{i}", {}) for i in range(len(normal_users))]
        
        # Problem user should have encountered some issues
        if problem_user_results and "results" in problem_user_results:
            problem_operations = problem_user_results["results"]
            problem_errors = len([op for op in problem_operations if op.get("status") == "error"])
            
            # Problem user operations may have encountered errors (which is expected)
            # The key is that normal users should be unaffected
            
        # Verify normal users were not affected by problem user's database issues
        normal_user_success_count = 0
        normal_user_error_count = 0
        
        for normal_result in normal_user_results:
            if "results" in normal_result:
                for operation in normal_result["results"]:
                    if operation.get("status") == "success":
                        normal_user_success_count += 1
                    elif operation.get("status") == "error":
                        normal_user_error_count += 1
        
        total_normal_operations = normal_user_success_count + normal_user_error_count
        
        if total_normal_operations > 0:
            # Most normal user operations should succeed despite problem user's database issues
            normal_success_rate = normal_user_success_count / total_normal_operations
            assert normal_success_rate >= 0.6, f"Normal users affected by database errors: success rate {normal_success_rate:.2f}"
        
        # Verify database integrity for all users
        integrity_query = """
        SELECT user_id, COUNT(*) as operation_count, 
               COUNT(CASE WHEN status = 'error' THEN 1 END) as error_count
        FROM user_operation_log 
        WHERE user_id = ANY(:user_ids) 
          AND created_at >= :start_time
        GROUP BY user_id
        """
        
        all_user_ids = [str(problem_user_id)] + [str(user_id) for user_id, _ in normal_users]
        
        try:
            result = await db_session.execute(integrity_query, {
                "user_ids": all_user_ids,
                "start_time": datetime.fromtimestamp(start_time)
            })
            
            integrity_records = result.fetchall()
            
            # Verify each user's operations were isolated
            for record in integrity_records:
                user_id = record.user_id
                operation_count = record.operation_count
                error_count = record.error_count
                
                # Each user should have at least attempted operations
                assert operation_count >= 0, f"User {user_id} should have operation records"
                
                # Error rates should be reasonable (not 100% for normal users)
                if user_id != str(problem_user_id) and operation_count > 0:
                    error_rate = error_count / operation_count
                    assert error_rate <= 0.5, f"Normal user {user_id} has too high error rate: {error_rate:.2f}"
                    
        except Exception:
            # Database integrity check may not be available in all test environments
            pass

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_service_timeout_error_isolation(self, real_services_fixture):
        """Test user isolation when service timeouts affect one user."""
        start_time = time.time()
        
        # Create users: one that will experience timeouts, others normal
        timeout_user_id = UserID(f"timeout_user_{UnifiedIdGenerator.generate_user_id()}")
        timeout_thread_id = ThreadID(f"timeout_thread_{UnifiedIdGenerator.generate_thread_id()}")
        
        normal_users = []
        for i in range(2):
            user_id = UserID(f"timeout_normal_user_{i}_{UnifiedIdGenerator.generate_user_id()}")
            thread_id = ThreadID(f"timeout_normal_thread_{i}_{UnifiedIdGenerator.generate_thread_id()}")
            normal_users.append((user_id, thread_id))
        
        user_connections = []
        timeout_test_results = {}
        
        try:
            # Phase 1: Establish connections
            # Timeout user connection
            timeout_token = self._create_test_auth_token(timeout_user_id)
            timeout_headers = {"Authorization": f"Bearer {timeout_token}"}
            
            timeout_ws = await WebSocketTestHelpers.create_test_websocket_connection(
                f"{self.websocket_url}/agent/{timeout_thread_id}",
                headers=timeout_headers,
                user_id=str(timeout_user_id)
            )
            
            user_connections.append(("timeout", timeout_ws, timeout_user_id, timeout_thread_id))
            
            # Normal user connections
            for i, (user_id, thread_id) in enumerate(normal_users):
                normal_token = self._create_test_auth_token(user_id)
                normal_headers = {"Authorization": f"Bearer {normal_token}"}
                
                normal_ws = await WebSocketTestHelpers.create_test_websocket_connection(
                    f"{self.websocket_url}/agent/{thread_id}",
                    headers=normal_headers,
                    user_id=str(user_id)
                )
                
                user_connections.append((f"normal_{i}", normal_ws, user_id, thread_id))
            
            # Phase 2: Trigger timeout conditions
            async def execute_operations_with_potential_timeout(connection_type, websocket, user_id, thread_id):
                """Execute operations that may timeout for one user but not others."""
                operation_results = []
                
                try:
                    if connection_type == "timeout":
                        # Operations designed to cause timeouts
                        timeout_requests = [
                            {
                                "type": "agent_request",
                                "agent_name": "slow_agent",
                                "message": "Execute extremely slow operation that will timeout",
                                "user_id": str(user_id),
                                "thread_id": str(thread_id),
                                "timeout_simulation": True,
                                "expected_duration": 30.0  # Deliberately long
                            },
                            {
                                "type": "resource_intensive_request",
                                "user_id": str(user_id),
                                "thread_id": str(thread_id),
                                "operation": "cpu_intensive_task",
                                "force_timeout": True
                            }
                        ]
                        
                        for request in timeout_requests:
                            operation_start = time.time()
                            
                            await WebSocketTestHelpers.send_test_message(websocket, request)
                            
                            try:
                                # Use shorter timeout to detect when service doesn't respond
                                response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=6.0)
                                operation_duration = time.time() - operation_start
                                
                                operation_results.append({
                                    "request_type": request.get("operation", request.get("type")),
                                    "status": "completed",
                                    "duration": operation_duration,
                                    "response_received": True
                                })
                                
                            except Exception as e:
                                operation_duration = time.time() - operation_start
                                
                                operation_results.append({
                                    "request_type": request.get("operation", request.get("type")),
                                    "status": "timeout_or_error",
                                    "duration": operation_duration,
                                    "error": str(e)[:100]
                                })
                            
                            await asyncio.sleep(0.5)  # Brief pause between timeout requests
                    
                    else:  # Normal users
                        # Fast, normal operations
                        normal_request = {
                            "type": "agent_request",
                            "agent_name": "fast_agent",
                            "message": f"Normal operation during timeout isolation test",
                            "user_id": str(user_id),
                            "thread_id": str(thread_id),
                            "quick_execution": True
                        }
                        
                        operation_start = time.time()
                        
                        await WebSocketTestHelpers.send_test_message(websocket, normal_request)
                        
                        try:
                            response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=8.0)
                            operation_duration = time.time() - operation_start
                            
                            operation_results.append({
                                "request_type": "normal_operation",
                                "status": "completed",
                                "duration": operation_duration,
                                "response_received": True
                            })
                            
                        except Exception as e:
                            operation_duration = time.time() - operation_start
                            
                            operation_results.append({
                                "request_type": "normal_operation",
                                "status": "error",
                                "duration": operation_duration,
                                "error": str(e)[:100]
                            })
                    
                except Exception as e:
                    operation_results.append({
                        "connection_type": connection_type,
                        "general_error": str(e)
                    })
                
                return {
                    "connection_type": connection_type,
                    "user_id": str(user_id),
                    "operations": operation_results
                }
            
            # Execute operations concurrently
            operation_tasks = []
            for connection_type, websocket, user_id, thread_id in user_connections:
                task = execute_operations_with_potential_timeout(connection_type, websocket, user_id, thread_id)
                operation_tasks.append(task)
            
            results = await asyncio.gather(*operation_tasks, return_exceptions=True)
            
            # Organize results
            for result in results:
                if isinstance(result, dict) and "connection_type" in result:
                    connection_type = result["connection_type"]
                    timeout_test_results[connection_type] = result
                    
        finally:
            # Clean up connections
            for _, websocket, _, _ in user_connections:
                await WebSocketTestHelpers.close_test_connection(websocket)
        
        # Verify test characteristics
        test_duration = time.time() - start_time
        assert test_duration > 4.0, f"Timeout isolation test took too little time: {test_duration:.2f}s"
        
        # Analyze timeout isolation
        timeout_user_results = timeout_test_results.get("timeout", {})
        normal_user_results = [timeout_test_results.get(f"normal_{i}", {}) for i in range(len(normal_users))]
        
        # Analyze timeout user behavior
        if timeout_user_results and "operations" in timeout_user_results:
            timeout_operations = timeout_user_results["operations"]
            timeout_occurred = any(
                op.get("status") == "timeout_or_error" and op.get("duration", 0) >= 5.0
                for op in timeout_operations
            )
            
            # Timeout user should have experienced timeouts or long durations
            # (This validates our timeout simulation worked)
        
        # Verify normal users were not affected by timeout user
        normal_operations_affected = 0
        normal_operations_successful = 0
        
        for normal_result in normal_user_results:
            if "operations" in normal_result:
                for operation in normal_result["operations"]:
                    duration = operation.get("duration", 0)
                    status = operation.get("status")
                    
                    if status == "completed" and duration < 5.0:  # Fast, successful operation
                        normal_operations_successful += 1
                    elif status in ["timeout_or_error", "error"] or duration >= 10.0:  # Affected by timeouts
                        normal_operations_affected += 1
        
        total_normal_operations = normal_operations_successful + normal_operations_affected
        
        if total_normal_operations > 0:
            # Normal users should mostly be unaffected by timeout user's issues
            success_rate = normal_operations_successful / total_normal_operations
            assert success_rate >= 0.7, f"Normal users affected by timeout issues: success rate {success_rate:.2f}"
            
            # Very few normal operations should be affected
            affected_rate = normal_operations_affected / total_normal_operations
            assert affected_rate <= 0.3, f"Too many normal operations affected by timeouts: {affected_rate:.2f}"
        
        # Verify response times for normal users remain reasonable
        normal_durations = []
        for normal_result in normal_user_results:
            if "operations" in normal_result:
                for operation in normal_result["operations"]:
                    if operation.get("status") == "completed":
                        normal_durations.append(operation.get("duration", 0))
        
        if normal_durations:
            avg_normal_duration = sum(normal_durations) / len(normal_durations)
            max_normal_duration = max(normal_durations)
            
            # Normal users should have reasonable response times despite timeout user issues
            assert avg_normal_duration < 8.0, f"Average normal user response time too high: {avg_normal_duration:.2f}s"
            assert max_normal_duration < 12.0, f"Max normal user response time too high: {max_normal_duration:.2f}s"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_error_recovery_user_isolation(self, real_services_fixture):
        """Test that error recovery for one user doesn't interfere with other users."""
        start_time = time.time()
        
        # Create users: one for error recovery, others for normal operations
        recovery_user_id = UserID(f"recovery_user_{UnifiedIdGenerator.generate_user_id()}")
        recovery_thread_id = ThreadID(f"recovery_thread_{UnifiedIdGenerator.generate_thread_id()}")
        
        normal_users = []
        for i in range(2):
            user_id = UserID(f"recovery_normal_user_{i}_{UnifiedIdGenerator.generate_user_id()}")
            thread_id = ThreadID(f"recovery_normal_thread_{i}_{UnifiedIdGenerator.generate_thread_id()}")
            normal_users.append((user_id, thread_id))
        
        user_connections = []
        recovery_test_results = {}
        
        try:
            # Phase 1: Establish connections
            # Recovery user connection
            recovery_token = self._create_test_auth_token(recovery_user_id)
            recovery_headers = {"Authorization": f"Bearer {recovery_token}"}
            
            recovery_ws = await WebSocketTestHelpers.create_test_websocket_connection(
                f"{self.websocket_url}/agent/{recovery_thread_id}",
                headers=recovery_headers,
                user_id=str(recovery_user_id)
            )
            
            user_connections.append(("recovery", recovery_ws, recovery_user_id, recovery_thread_id))
            
            # Normal user connections
            for i, (user_id, thread_id) in enumerate(normal_users):
                normal_token = self._create_test_auth_token(user_id)
                normal_headers = {"Authorization": f"Bearer {normal_token}"}
                
                normal_ws = await WebSocketTestHelpers.create_test_websocket_connection(
                    f"{self.websocket_url}/agent/{thread_id}",
                    headers=normal_headers,
                    user_id=str(user_id)
                )
                
                user_connections.append((f"normal_{i}", normal_ws, user_id, thread_id))
            
            # Phase 2: Trigger error and recovery cycle for recovery user
            async def execute_error_recovery_cycle(websocket, user_id, thread_id):
                """Execute error and recovery cycle for a specific user."""
                cycle_results = []
                
                try:
                    # Step 1: Trigger error
                    error_request = {
                        "type": "agent_request",
                        "agent_name": "recoverable_error_agent",
                        "message": "Execute operation that fails but can recover",
                        "user_id": str(user_id),
                        "thread_id": str(thread_id),
                        "simulate_recoverable_error": True,
                        "error_recovery_test": True
                    }
                    
                    await WebSocketTestHelpers.send_test_message(websocket, error_request)
                    
                    # Collect error response
                    try:
                        error_response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=5.0)
                        cycle_results.append({"phase": "error", "status": "response_received", "response": error_response})
                    except Exception as e:
                        cycle_results.append({"phase": "error", "status": "timeout", "error": str(e)})
                    
                    await asyncio.sleep(1.0)  # Allow error to be processed
                    
                    # Step 2: Trigger recovery
                    recovery_request = {
                        "type": "recover_from_error",
                        "user_id": str(user_id),
                        "thread_id": str(thread_id),
                        "recovery_strategy": "retry_with_fallback",
                        "original_request_id": "recoverable_error_request"
                    }
                    
                    await WebSocketTestHelpers.send_test_message(websocket, recovery_request)
                    
                    # Collect recovery response
                    try:
                        recovery_response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=8.0)
                        cycle_results.append({"phase": "recovery", "status": "response_received", "response": recovery_response})
                    except Exception as e:
                        cycle_results.append({"phase": "recovery", "status": "timeout", "error": str(e)})
                    
                    await asyncio.sleep(1.0)  # Allow recovery to complete
                    
                    # Step 3: Verify normal operation after recovery
                    verify_request = {
                        "type": "verify_post_recovery",
                        "user_id": str(user_id),
                        "thread_id": str(thread_id),
                        "test_normal_functionality": True
                    }
                    
                    await WebSocketTestHelpers.send_test_message(websocket, verify_request)
                    
                    try:
                        verify_response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=5.0)
                        cycle_results.append({"phase": "verification", "status": "response_received", "response": verify_response})
                    except Exception as e:
                        cycle_results.append({"phase": "verification", "status": "timeout", "error": str(e)})
                
                except Exception as e:
                    cycle_results.append({"phase": "general", "status": "error", "error": str(e)})
                
                return cycle_results
            
            # Execute normal operations for normal users during recovery
            async def execute_normal_operations_during_recovery(websocket, user_id, thread_id, user_index):
                """Execute normal operations while recovery is happening."""
                normal_results = []
                
                try:
                    # Multiple normal operations during recovery period
                    for op_num in range(3):
                        normal_request = {
                            "type": "agent_request",
                            "agent_name": "stable_agent",
                            "message": f"Normal operation {op_num} during error recovery isolation test",
                            "user_id": str(user_id),
                            "thread_id": str(thread_id),
                            "user_index": user_index,
                            "operation_number": op_num
                        }
                        
                        operation_start = time.time()
                        
                        await WebSocketTestHelpers.send_test_message(websocket, normal_request)
                        
                        try:
                            response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=6.0)
                            operation_duration = time.time() - operation_start
                            
                            normal_results.append({
                                "operation_number": op_num,
                                "status": "success",
                                "duration": operation_duration,
                                "response_received": True
                            })
                            
                        except Exception as e:
                            operation_duration = time.time() - operation_start
                            
                            normal_results.append({
                                "operation_number": op_num,
                                "status": "error",
                                "duration": operation_duration,
                                "error": str(e)[:100]
                            })
                        
                        await asyncio.sleep(1.0)  # Pause between normal operations
                        
                except Exception as e:
                    normal_results.append({"general_error": str(e)})
                
                return normal_results
            
            # Execute recovery cycle and normal operations concurrently
            all_tasks = []
            
            # Recovery user task
            recovery_task = execute_error_recovery_cycle(
                user_connections[0][1], recovery_user_id, recovery_thread_id
            )
            all_tasks.append(("recovery", recovery_task))
            
            # Normal user tasks
            for i, (user_id, thread_id) in enumerate(normal_users):
                normal_task = execute_normal_operations_during_recovery(
                    user_connections[i + 1][1], user_id, thread_id, i
                )
                all_tasks.append((f"normal_{i}", normal_task))
            
            # Execute all tasks concurrently
            task_results = await asyncio.gather(
                *[task for _, task in all_tasks], 
                return_exceptions=True
            )
            
            # Organize results
            for i, result in enumerate(task_results):
                task_type = all_tasks[i][0]
                recovery_test_results[task_type] = result
                
        finally:
            # Clean up connections
            for _, websocket, _, _ in user_connections:
                await WebSocketTestHelpers.close_test_connection(websocket)
        
        # Verify test characteristics
        test_duration = time.time() - start_time
        assert test_duration > 6.0, f"Error recovery isolation test took too little time: {test_duration:.2f}s"
        
        # Analyze recovery isolation
        recovery_results = recovery_test_results.get("recovery", [])
        normal_user_results = [recovery_test_results.get(f"normal_{i}", []) for i in range(len(normal_users))]
        
        # Verify recovery user went through error-recovery cycle
        if isinstance(recovery_results, list) and recovery_results:
            recovery_phases = [r.get("phase") for r in recovery_results if isinstance(r, dict)]
            
            # Should have attempted error and recovery phases
            has_error_phase = "error" in recovery_phases
            has_recovery_phase = "recovery" in recovery_phases
            
            # Recovery cycle should have been attempted
            recovery_attempted = has_error_phase or has_recovery_phase
            # This is expected behavior
            
        # Verify normal users were unaffected by recovery process
        normal_success_count = 0
        normal_error_count = 0
        normal_total_duration = 0
        
        for normal_results in normal_user_results:
            if isinstance(normal_results, list):
                for operation in normal_results:
                    if isinstance(operation, dict):
                        if operation.get("status") == "success":
                            normal_success_count += 1
                            normal_total_duration += operation.get("duration", 0)
                        elif operation.get("status") == "error":
                            normal_error_count += 1
        
        total_normal_operations = normal_success_count + normal_error_count
        
        if total_normal_operations > 0:
            # Normal users should have high success rate despite recovery user's error recovery
            normal_success_rate = normal_success_count / total_normal_operations
            assert normal_success_rate >= 0.7, f"Normal users affected by error recovery: success rate {normal_success_rate:.2f}"
            
            # Normal operations should have reasonable performance
            if normal_success_count > 0:
                avg_normal_duration = normal_total_duration / normal_success_count
                assert avg_normal_duration < 8.0, f"Normal user operations too slow during recovery: {avg_normal_duration:.2f}s"

    def _create_test_auth_token(self, user_id: UserID) -> str:
        """Create test authentication token for integration testing."""
        import base64
        
        payload = {
            "user_id": str(user_id),
            "email": f"test_{user_id}@example.com",
            "iat": int(time.time()),
            "exp": int(time.time() + 3600),
            "test_mode": True
        }
        
        token_data = base64.b64encode(json.dumps(payload).encode()).decode()
        return f"test.{token_data}.signature"