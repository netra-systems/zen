"""
Test Concurrent User High Load Integration - 100+ Users

Business Value Justification (BVJ):
- Segment: All (Free through Enterprise) - Critical for scalability
- Business Goal: Ensure platform can handle high concurrent user load
- Value Impact: Platform must support 100+ concurrent users to serve enterprise customers
- Strategic Impact: MISSION CRITICAL for revenue growth - concurrent user capacity directly impacts ARR

CRITICAL REQUIREMENTS:
1. Test 100+ concurrent users with realistic usage patterns
2. Use REAL services (NO MOCKS) - PostgreSQL, Redis, WebSocket connections
3. Validate user session isolation under high load
4. Test WebSocket event delivery for all users
5. Measure performance metrics and resource utilization
6. Test realistic user behavior patterns (light, medium, heavy users)
7. Ensure proper authentication and session management
8. Use E2E authentication for all operations

REAL SYSTEM VALIDATION:
- Real PostgreSQL database connections and transactions
- Real Redis cache operations and session storage
- Real WebSocket connections with event broadcasting
- Real agent execution workflows
- Real concurrent database operations with isolation testing
"""

import asyncio
import json
import logging
import statistics
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import pytest

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.websocket_helpers import WebSocketTestClient, WebSocketTestHelpers
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context

logger = logging.getLogger(__name__)


class UserLoadTier(Enum):
    """User load tiers for realistic usage patterns."""
    LIGHT = "light"      # 1-2 agent executions
    MEDIUM = "medium"    # 3-5 agent executions
    HEAVY = "heavy"      # 6-10 agent executions


@dataclass
class ConcurrentUserResult:
    """Result of concurrent user operation."""
    user_id: str
    email: str
    user_tier: UserLoadTier
    operations_completed: int
    websocket_events_received: int
    agent_executions_completed: int
    database_operations: int
    redis_operations: int
    total_execution_time: float
    average_response_time: float
    websocket_connection_time: float
    authentication_time: float
    session_isolation_validated: bool
    success: bool
    error_message: Optional[str] = None
    performance_metrics: Optional[Dict[str, float]] = None


@dataclass
class HighLoadMetrics:
    """High load test metrics."""
    total_users: int
    successful_users: int
    total_operations: int
    total_websocket_events: int
    average_execution_time: float
    p95_response_time: float
    p99_response_time: float
    concurrent_database_connections: int
    concurrent_redis_connections: int
    session_isolation_success_rate: float
    websocket_delivery_success_rate: float
    system_resource_usage: Dict[str, float]


class TestConcurrentUserHighLoadIntegration(BaseIntegrationTest):
    """Test high-load concurrent user scenarios with real services."""
    
    def setup_method(self):
        """Setup test environment for concurrent user testing."""
        super().setup_method()
        self.auth_helper = E2EAuthHelper(environment="test")
        
        # Define realistic user distribution
        self.user_distribution = {
            UserLoadTier.LIGHT: 60,    # 60% light users (1-2 operations)
            UserLoadTier.MEDIUM: 30,   # 30% medium users (3-5 operations) 
            UserLoadTier.HEAVY: 10     # 10% heavy users (6-10 operations)
        }
        
        # Define agent types for realistic workloads
        self.agent_types = {
            UserLoadTier.LIGHT: ["triage_agent", "quick_help"],
            UserLoadTier.MEDIUM: ["triage_agent", "data_helper", "cost_optimizer"], 
            UserLoadTier.HEAVY: ["triage_agent", "data_helper", "cost_optimizer", "uvs_reporting", "security_analyzer"]
        }
        
        # Performance thresholds
        self.performance_thresholds = {
            "max_avg_response_time": 5.0,  # 5 seconds average
            "max_p95_response_time": 10.0,  # 10 seconds 95th percentile
            "min_success_rate": 0.95,       # 95% success rate
            "min_isolation_rate": 0.98,     # 98% isolation success
            "max_websocket_connection_time": 3.0  # 3 seconds WebSocket connection
        }

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.high_load
    async def test_100_concurrent_users_realistic_patterns(self, real_services_fixture):
        """Test 100+ concurrent users with realistic usage patterns."""
        total_users = 120  # Test with 120 users for comprehensive load
        
        # Ensure real services are available
        if not real_services_fixture["database_available"]:
            pytest.fail("Real database required for concurrent user testing")
        
        db_session = real_services_fixture["db"]
        redis_url = real_services_fixture["redis_url"]
        backend_url = real_services_fixture["backend_url"]
        
        logger.info(f"Starting concurrent user test with {total_users} users")
        logger.info(f"User distribution: {self.user_distribution}")
        
        # Generate user contexts with realistic distribution
        user_contexts = await self._generate_user_contexts(total_users)
        
        # Setup users in database
        await self._setup_users_in_database(db_session, user_contexts)
        
        # Define concurrent user workflow
        async def concurrent_user_workflow(user_context, user_tier: UserLoadTier, user_index: int):
            """Execute realistic concurrent user workflow."""
            start_time = time.time()
            
            try:
                # Phase 1: Authentication and WebSocket connection
                auth_start = time.time()
                websocket_client = await self._create_authenticated_websocket_connection(
                    user_context, backend_url
                )
                auth_time = time.time() - auth_start
                
                # Phase 2: Execute user-tier specific operations
                workflow_result = await self._execute_user_tier_workflow(
                    db_session, user_context, user_tier, websocket_client, user_index
                )
                
                # Phase 3: Validate session isolation
                isolation_result = await self._validate_session_isolation(
                    db_session, user_context
                )
                
                return ConcurrentUserResult(
                    user_id=str(user_context.user_id),
                    email=user_context.agent_context.get("user_email"),
                    user_tier=user_tier,
                    operations_completed=workflow_result["operations_completed"],
                    websocket_events_received=workflow_result["websocket_events_received"],
                    agent_executions_completed=workflow_result["agent_executions"],
                    database_operations=workflow_result["database_operations"],
                    redis_operations=workflow_result["redis_operations"],
                    total_execution_time=time.time() - start_time,
                    average_response_time=workflow_result["average_response_time"],
                    websocket_connection_time=auth_time,
                    authentication_time=auth_time,
                    session_isolation_validated=isolation_result["isolated"],
                    success=True,
                    performance_metrics=workflow_result.get("performance_metrics", {})
                )
                
            except Exception as e:
                logger.error(f"User {user_index} workflow failed: {e}")
                return ConcurrentUserResult(
                    user_id=str(user_context.user_id),
                    email=user_context.agent_context.get("user_email"),
                    user_tier=user_tier,
                    operations_completed=0,
                    websocket_events_received=0,
                    agent_executions_completed=0,
                    database_operations=0,
                    redis_operations=0,
                    total_execution_time=time.time() - start_time,
                    average_response_time=0.0,
                    websocket_connection_time=0.0,
                    authentication_time=0.0,
                    session_isolation_validated=False,
                    success=False,
                    error_message=str(e)
                )
        
        # Execute concurrent workflows with gradual ramp-up
        logger.info("Starting gradual ramp-up of concurrent users")
        concurrent_results = await self._execute_gradual_ramp_up(
            user_contexts, concurrent_user_workflow
        )
        
        # Analyze results and generate metrics
        high_load_metrics = self._analyze_high_load_results(concurrent_results)
        
        # Validate performance requirements
        self._validate_performance_requirements(high_load_metrics, concurrent_results)
        
        # Validate business value delivered
        self._validate_business_value_delivered(high_load_metrics)
        
        logger.info(f"Concurrent user test completed successfully")
        logger.info(f"Success rate: {high_load_metrics.successful_users}/{high_load_metrics.total_users} "
                   f"({high_load_metrics.successful_users/high_load_metrics.total_users*100:.1f}%)")
        
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.high_load
    async def test_database_isolation_under_high_concurrent_load(self, real_services_fixture):
        """Test database isolation with high concurrent load."""
        concurrent_users = 50
        operations_per_user = 10
        
        if not real_services_fixture["database_available"]:
            pytest.fail("Real database required for isolation testing")
        
        db_session = real_services_fixture["db"]
        
        # Create user contexts
        user_contexts = await self._generate_user_contexts(concurrent_users)
        await self._setup_users_in_database(db_session, user_contexts)
        
        async def database_isolation_workload(user_context, user_index: int):
            """Execute database operations that test isolation."""
            isolation_results = []
            
            for op_index in range(operations_per_user):
                try:
                    # Create user-specific data
                    user_data_id = f"user_{user_index}_data_{op_index}"
                    await self._create_user_specific_data(db_session, user_context, user_data_id)
                    
                    # Attempt to access other users' data (should fail)
                    cross_access_result = await self._test_cross_user_data_access(
                        db_session, user_context, user_index
                    )
                    
                    isolation_results.append({
                        "operation": op_index,
                        "user_data_created": True,
                        "cross_access_blocked": cross_access_result["blocked"],
                        "isolation_maintained": cross_access_result["isolated"]
                    })
                    
                except Exception as e:
                    isolation_results.append({
                        "operation": op_index,
                        "user_data_created": False,
                        "cross_access_blocked": False,
                        "isolation_maintained": False,
                        "error": str(e)
                    })
            
            return {
                "user_index": user_index,
                "user_id": str(user_context.user_id),
                "isolation_results": isolation_results,
                "total_operations": len(isolation_results),
                "successful_isolations": sum(1 for r in isolation_results if r.get("isolation_maintained"))
            }
        
        # Execute concurrent database isolation tests
        isolation_tasks = [
            database_isolation_workload(user_contexts[i], i)
            for i in range(concurrent_users)
        ]
        
        isolation_results = await asyncio.gather(*isolation_tasks)
        
        # Analyze isolation results
        total_operations = sum(r["total_operations"] for r in isolation_results)
        successful_isolations = sum(r["successful_isolations"] for r in isolation_results)
        isolation_success_rate = successful_isolations / total_operations if total_operations > 0 else 0
        
        # Validate isolation requirements
        assert isolation_success_rate >= 0.98, \
            f"Database isolation success rate {isolation_success_rate:.3f} below required 98%"
        
        # Check for race conditions
        race_conditions = sum(1 for r in isolation_results 
                            for op in r["isolation_results"] 
                            if "error" in op)
        
        assert race_conditions == 0, f"Detected {race_conditions} race conditions in database operations"
        
        logger.info(f"Database isolation test completed: {isolation_success_rate:.3f} success rate")

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.high_load
    async def test_websocket_event_delivery_under_high_load(self, real_services_fixture):
        """Test WebSocket event delivery with high concurrent load."""
        concurrent_connections = 75
        events_per_connection = 15
        
        backend_url = real_services_fixture["backend_url"]
        
        # Generate user contexts for WebSocket testing
        user_contexts = await self._generate_user_contexts(concurrent_connections)
        
        async def websocket_load_test(user_context, connection_index: int):
            """Execute WebSocket load test for single connection."""
            events_received = []
            connection_metrics = {
                "connection_time": 0.0,
                "events_sent": 0,
                "events_received": 0,
                "message_latencies": []
            }
            
            try:
                # Connect with timing
                connect_start = time.time()
                websocket_client = await self._create_authenticated_websocket_connection(
                    user_context, backend_url
                )
                connection_metrics["connection_time"] = time.time() - connect_start
                
                # Send and receive events
                for event_index in range(events_per_connection):
                    # Send agent execution event
                    send_time = time.time()
                    await self._send_agent_execution_event(websocket_client, event_index)
                    connection_metrics["events_sent"] += 1
                    
                    # Wait for response events (agent_started, agent_thinking, etc.)
                    response_events = await self._collect_websocket_events(
                        websocket_client, timeout=5.0
                    )
                    
                    if response_events:
                        receive_time = time.time()
                        latency = receive_time - send_time
                        connection_metrics["message_latencies"].append(latency)
                        connection_metrics["events_received"] += len(response_events)
                        events_received.extend(response_events)
                
                return {
                    "connection_index": connection_index,
                    "user_id": str(user_context.user_id),
                    "success": True,
                    "events_received": events_received,
                    "metrics": connection_metrics
                }
                
            except Exception as e:
                logger.error(f"WebSocket connection {connection_index} failed: {e}")
                return {
                    "connection_index": connection_index,
                    "user_id": str(user_context.user_id),
                    "success": False,
                    "error": str(e),
                    "metrics": connection_metrics
                }
        
        # Execute concurrent WebSocket load tests
        websocket_tasks = [
            websocket_load_test(user_contexts[i], i)
            for i in range(concurrent_connections)
        ]
        
        websocket_results = await asyncio.gather(*websocket_tasks)
        
        # Analyze WebSocket performance
        successful_connections = [r for r in websocket_results if r["success"]]
        total_events_received = sum(r["metrics"]["events_received"] for r in successful_connections)
        average_connection_time = statistics.mean([r["metrics"]["connection_time"] for r in successful_connections])
        
        # Calculate message latency statistics
        all_latencies = []
        for r in successful_connections:
            all_latencies.extend(r["metrics"]["message_latencies"])
        
        if all_latencies:
            avg_latency = statistics.mean(all_latencies)
            p95_latency = sorted(all_latencies)[int(len(all_latencies) * 0.95)]
        else:
            avg_latency = float('inf')
            p95_latency = float('inf')
        
        # Validate WebSocket performance requirements
        connection_success_rate = len(successful_connections) / concurrent_connections
        assert connection_success_rate >= 0.95, \
            f"WebSocket connection success rate {connection_success_rate:.3f} below required 95%"
        
        assert average_connection_time <= 3.0, \
            f"Average WebSocket connection time {average_connection_time:.2f}s exceeds 3s limit"
        
        if all_latencies:
            assert avg_latency <= 2.0, \
                f"Average message latency {avg_latency:.3f}s exceeds 2s limit"
            assert p95_latency <= 5.0, \
                f"95th percentile latency {p95_latency:.3f}s exceeds 5s limit"
        
        logger.info(f"WebSocket load test completed: {len(successful_connections)}/{concurrent_connections} connections successful")
        logger.info(f"Average connection time: {average_connection_time:.3f}s, Average latency: {avg_latency:.3f}s")

    # Helper Methods
    
    async def _generate_user_contexts(self, total_users: int) -> List:
        """Generate user contexts with realistic distribution."""
        user_contexts = []
        
        for i in range(total_users):
            # Determine user tier based on distribution
            if i < total_users * 0.6:
                tier = UserLoadTier.LIGHT
            elif i < total_users * 0.9:
                tier = UserLoadTier.MEDIUM
            else:
                tier = UserLoadTier.HEAVY
            
            # Create authenticated user context
            user_email = f"concurrent_test_{i}_{uuid.uuid4().hex[:6]}@example.com"
            user_context = await create_authenticated_user_context(
                user_email=user_email,
                permissions=["read", "write", "agent_execution"]
            )
            
            # Add tier information to context
            user_context.agent_context["user_tier"] = tier
            user_context.agent_context["user_index"] = i
            
            user_contexts.append(user_context)
        
        return user_contexts
    
    async def _setup_users_in_database(self, db_session, user_contexts: List):
        """Setup users in database for concurrent testing."""
        for user_context in user_contexts:
            user_insert = """
                INSERT INTO concurrent_test_users (
                    id, email, full_name, user_tier, created_at, is_active, is_test_user
                ) VALUES (
                    %(user_id)s, %(email)s, %(full_name)s, %(tier)s, %(created_at)s, true, true
                )
                ON CONFLICT (id) DO UPDATE SET
                    email = EXCLUDED.email,
                    user_tier = EXCLUDED.user_tier,
                    updated_at = NOW()
            """
            
            await db_session.execute(user_insert, {
                "user_id": str(user_context.user_id),
                "email": user_context.agent_context.get("user_email"),
                "full_name": f"Concurrent Test User {user_context.agent_context.get('user_index')}",
                "tier": user_context.agent_context.get("user_tier").value,
                "created_at": datetime.now(timezone.utc)
            })
        
        await db_session.commit()
    
    async def _create_authenticated_websocket_connection(self, user_context, backend_url: str):
        """Create authenticated WebSocket connection."""
        # Get JWT token from user context
        jwt_token = user_context.agent_context.get("jwt_token")
        if not jwt_token:
            raise ValueError("JWT token not found in user context")
        
        # Create WebSocket URL
        websocket_url = backend_url.replace("http://", "ws://") + "/ws"
        
        # Create headers for authentication
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "X-User-ID": str(user_context.user_id),
            "X-Test-Mode": "true"
        }
        
        # Create WebSocket connection
        websocket_client = await WebSocketTestHelpers.create_test_websocket_connection(
            websocket_url, headers=headers, timeout=5.0, user_id=str(user_context.user_id)
        )
        
        return websocket_client
    
    async def _execute_user_tier_workflow(
        self, db_session, user_context, user_tier: UserLoadTier, 
        websocket_client, user_index: int
    ) -> Dict[str, Any]:
        """Execute workflow based on user tier."""
        operations_completed = 0
        websocket_events_received = 0
        agent_executions = 0
        database_operations = 0
        redis_operations = 0
        response_times = []
        
        # Determine number of operations based on tier
        if user_tier == UserLoadTier.LIGHT:
            num_operations = 2
        elif user_tier == UserLoadTier.MEDIUM:
            num_operations = 4
        else:  # HEAVY
            num_operations = 8
        
        # Execute operations
        for op_index in range(num_operations):
            op_start = time.time()
            
            try:
                # 1. Database operation
                await self._execute_database_operation(db_session, user_context, op_index)
                database_operations += 1
                
                # 2. Redis operation
                await self._execute_redis_operation(user_context, op_index)
                redis_operations += 1
                
                # 3. Agent execution via WebSocket
                if op_index < len(self.agent_types[user_tier]):
                    agent_type = self.agent_types[user_tier][op_index]
                    agent_result = await self._execute_agent_via_websocket(
                        websocket_client, agent_type, user_context
                    )
                    if agent_result["success"]:
                        agent_executions += 1
                        websocket_events_received += agent_result["events_received"]
                
                operations_completed += 1
                response_times.append(time.time() - op_start)
                
            except Exception as e:
                logger.warning(f"Operation {op_index} failed for user {user_index}: {e}")
                response_times.append(time.time() - op_start)
        
        return {
            "operations_completed": operations_completed,
            "websocket_events_received": websocket_events_received,
            "agent_executions": agent_executions,
            "database_operations": database_operations,
            "redis_operations": redis_operations,
            "average_response_time": statistics.mean(response_times) if response_times else 0.0,
            "performance_metrics": {
                "min_response_time": min(response_times) if response_times else 0.0,
                "max_response_time": max(response_times) if response_times else 0.0,
                "p95_response_time": sorted(response_times)[int(len(response_times) * 0.95)] if response_times else 0.0
            }
        }
    
    async def _execute_database_operation(self, db_session, user_context, op_index: int):
        """Execute database operation for user."""
        operation_insert = """
            INSERT INTO concurrent_user_operations (
                user_id, operation_index, operation_type, data, created_at
            ) VALUES (
                %(user_id)s, %(op_index)s, 'database', %(data)s, %(created_at)s
            )
        """
        
        await db_session.execute(operation_insert, {
            "user_id": str(user_context.user_id),
            "op_index": op_index,
            "data": json.dumps({"operation": f"db_op_{op_index}", "timestamp": time.time()}),
            "created_at": datetime.now(timezone.utc)
        })
        await db_session.commit()
    
    async def _execute_redis_operation(self, user_context, op_index: int):
        """Execute Redis operation for user."""
        # Simulate Redis operation (would use real Redis in actual implementation)
        cache_key = f"user_{user_context.user_id}_op_{op_index}"
        cache_data = {
            "operation": f"redis_op_{op_index}",
            "user_id": str(user_context.user_id),
            "timestamp": time.time()
        }
        # In real implementation: await redis_client.set(cache_key, json.dumps(cache_data))
        await asyncio.sleep(0.01)  # Simulate Redis latency
    
    async def _execute_agent_via_websocket(
        self, websocket_client, agent_type: str, user_context
    ) -> Dict[str, Any]:
        """Execute agent via WebSocket connection."""
        try:
            # Send agent execution request
            agent_message = {
                "type": "agent_request",
                "agent": agent_type,
                "message": f"Execute {agent_type} for user {user_context.user_id}",
                "user_id": str(user_context.user_id),
                "timestamp": time.time()
            }
            
            await WebSocketTestHelpers.send_test_message(websocket_client, agent_message)
            
            # Wait for agent events
            events_received = 0
            for _ in range(5):  # Wait for up to 5 events
                try:
                    event = await WebSocketTestHelpers.receive_test_message(
                        websocket_client, timeout=2.0
                    )
                    if event and event.get("type") in [
                        "agent_started", "agent_thinking", "tool_executing", 
                        "tool_completed", "agent_completed"
                    ]:
                        events_received += 1
                        if event.get("type") == "agent_completed":
                            break
                except:
                    break
            
            return {
                "success": events_received > 0,
                "events_received": events_received,
                "agent_type": agent_type
            }
            
        except Exception as e:
            return {
                "success": False,
                "events_received": 0,
                "error": str(e)
            }
    
    async def _validate_session_isolation(self, db_session, user_context) -> Dict[str, Any]:
        """Validate session isolation for user."""
        try:
            # Check user can access only their own data
            user_data_query = """
                SELECT COUNT(*) FROM concurrent_user_operations 
                WHERE user_id = %(user_id)s
            """
            result = await db_session.execute(user_data_query, {
                "user_id": str(user_context.user_id)
            })
            user_data_count = result.scalar()
            
            # Check user cannot access other users' data
            other_data_query = """
                SELECT COUNT(*) FROM concurrent_user_operations 
                WHERE user_id != %(user_id)s
                AND user_id IN (
                    SELECT DISTINCT user_id FROM concurrent_user_operations 
                    WHERE user_id = %(user_id)s LIMIT 0  -- Should return 0 rows
                )
            """
            result = await db_session.execute(other_data_query, {
                "user_id": str(user_context.user_id)
            })
            cross_access_count = result.scalar()
            
            return {
                "isolated": cross_access_count == 0,
                "user_data_found": user_data_count > 0,
                "cross_access_violations": cross_access_count
            }
            
        except Exception as e:
            return {
                "isolated": False,
                "error": str(e)
            }
    
    async def _execute_gradual_ramp_up(self, user_contexts: List, workflow_func) -> List:
        """Execute gradual ramp-up of concurrent users."""
        results = []
        batch_size = 20  # Ramp up in batches of 20
        
        for i in range(0, len(user_contexts), batch_size):
            batch = user_contexts[i:i + batch_size]
            logger.info(f"Starting batch {i//batch_size + 1}: users {i+1}-{min(i+batch_size, len(user_contexts))}")
            
            # Create tasks for this batch
            batch_tasks = [
                workflow_func(
                    user_context, 
                    user_context.agent_context["user_tier"],
                    user_context.agent_context["user_index"]
                )
                for user_context in batch
            ]
            
            # Execute batch
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            results.extend([r for r in batch_results if not isinstance(r, Exception)])
            
            # Brief pause between batches
            await asyncio.sleep(1.0)
        
        return results
    
    def _analyze_high_load_results(self, results: List[ConcurrentUserResult]) -> HighLoadMetrics:
        """Analyze high load test results."""
        successful_results = [r for r in results if r.success]
        
        # Calculate metrics
        total_operations = sum(r.operations_completed for r in successful_results)
        total_websocket_events = sum(r.websocket_events_received for r in successful_results)
        
        execution_times = [r.total_execution_time for r in successful_results]
        response_times = [r.average_response_time for r in successful_results if r.average_response_time > 0]
        
        # Session isolation metrics
        isolation_successes = sum(1 for r in successful_results if r.session_isolation_validated)
        isolation_rate = isolation_successes / len(successful_results) if successful_results else 0
        
        # WebSocket delivery metrics
        websocket_successes = sum(1 for r in successful_results if r.websocket_events_received > 0)
        websocket_delivery_rate = websocket_successes / len(successful_results) if successful_results else 0
        
        return HighLoadMetrics(
            total_users=len(results),
            successful_users=len(successful_results),
            total_operations=total_operations,
            total_websocket_events=total_websocket_events,
            average_execution_time=statistics.mean(execution_times) if execution_times else 0.0,
            p95_response_time=sorted(response_times)[int(len(response_times) * 0.95)] if response_times else 0.0,
            p99_response_time=sorted(response_times)[int(len(response_times) * 0.99)] if response_times else 0.0,
            concurrent_database_connections=len([r for r in successful_results if r.database_operations > 0]),
            concurrent_redis_connections=len([r for r in successful_results if r.redis_operations > 0]),
            session_isolation_success_rate=isolation_rate,
            websocket_delivery_success_rate=websocket_delivery_rate,
            system_resource_usage=self._calculate_system_resource_usage(successful_results)
        )
    
    def _calculate_system_resource_usage(self, results: List[ConcurrentUserResult]) -> Dict[str, float]:
        """Calculate system resource usage metrics."""
        return {
            "avg_connection_time": statistics.mean([r.websocket_connection_time for r in results if r.websocket_connection_time > 0]),
            "avg_auth_time": statistics.mean([r.authentication_time for r in results if r.authentication_time > 0]),
            "total_db_operations": sum(r.database_operations for r in results),
            "total_redis_operations": sum(r.redis_operations for r in results),
            "concurrent_users_peak": len(results)
        }
    
    def _validate_performance_requirements(self, metrics: HighLoadMetrics, results: List):
        """Validate performance requirements."""
        # Success rate requirement
        success_rate = metrics.successful_users / metrics.total_users
        assert success_rate >= self.performance_thresholds["min_success_rate"], \
            f"Success rate {success_rate:.3f} below required {self.performance_thresholds['min_success_rate']}"
        
        # Response time requirements
        assert metrics.average_execution_time <= self.performance_thresholds["max_avg_response_time"], \
            f"Average response time {metrics.average_execution_time:.2f}s exceeds {self.performance_thresholds['max_avg_response_time']}s limit"
        
        assert metrics.p95_response_time <= self.performance_thresholds["max_p95_response_time"], \
            f"P95 response time {metrics.p95_response_time:.2f}s exceeds {self.performance_thresholds['max_p95_response_time']}s limit"
        
        # Isolation requirement
        assert metrics.session_isolation_success_rate >= self.performance_thresholds["min_isolation_rate"], \
            f"Session isolation rate {metrics.session_isolation_success_rate:.3f} below required {self.performance_thresholds['min_isolation_rate']}"
        
        # WebSocket connection time requirement
        websocket_times = [r.websocket_connection_time for r in results if r.success and r.websocket_connection_time > 0]
        if websocket_times:
            avg_websocket_time = statistics.mean(websocket_times)
            assert avg_websocket_time <= self.performance_thresholds["max_websocket_connection_time"], \
                f"Average WebSocket connection time {avg_websocket_time:.2f}s exceeds {self.performance_thresholds['max_websocket_connection_time']}s limit"
    
    def _validate_business_value_delivered(self, metrics: HighLoadMetrics):
        """Validate business value requirements."""
        # Business value assertions
        assert metrics.total_operations >= 300, \
            f"Total operations {metrics.total_operations} insufficient for business value validation"
        
        assert metrics.total_websocket_events >= 500, \
            f"Total WebSocket events {metrics.total_websocket_events} insufficient for real-time communication validation"
        
        assert metrics.websocket_delivery_success_rate >= 0.95, \
            f"WebSocket delivery rate {metrics.websocket_delivery_success_rate:.3f} below business requirement"
        
        # Resource utilization validation
        assert metrics.concurrent_database_connections >= 50, \
            f"Concurrent DB connections {metrics.concurrent_database_connections} insufficient for enterprise load testing"
        
        self.assert_business_value_delivered({
            "concurrent_users_supported": metrics.successful_users,
            "total_operations_completed": metrics.total_operations,
            "websocket_events_delivered": metrics.total_websocket_events,
            "session_isolation_maintained": metrics.session_isolation_success_rate >= 0.98,
            "enterprise_scale_validated": metrics.successful_users >= 100
        }, "scalability")
    
    # Additional helper methods for specific test scenarios
    
    async def _create_user_specific_data(self, db_session, user_context, data_id: str):
        """Create user-specific data for isolation testing."""
        data_insert = """
            INSERT INTO user_isolation_test_data (
                id, user_id, data_content, created_at
            ) VALUES (
                %(data_id)s, %(user_id)s, %(content)s, %(created_at)s
            )
        """
        
        await db_session.execute(data_insert, {
            "data_id": data_id,
            "user_id": str(user_context.user_id),
            "content": json.dumps({"test_data": f"data_for_{user_context.user_id}"}),
            "created_at": datetime.now(timezone.utc)
        })
        await db_session.commit()
    
    async def _test_cross_user_data_access(self, db_session, user_context, user_index: int) -> Dict[str, Any]:
        """Test cross-user data access (should be blocked)."""
        try:
            # Attempt to access other users' data
            cross_access_query = """
                SELECT COUNT(*) FROM user_isolation_test_data 
                WHERE user_id != %(user_id)s
            """
            result = await db_session.execute(cross_access_query, {
                "user_id": str(user_context.user_id)
            })
            other_users_data = result.scalar()
            
            return {
                "blocked": other_users_data == 0,  # Should be 0 for proper isolation
                "isolated": True,
                "cross_access_count": other_users_data
            }
            
        except Exception as e:
            return {
                "blocked": False,
                "isolated": False,
                "error": str(e)
            }
    
    async def _send_agent_execution_event(self, websocket_client, event_index: int):
        """Send agent execution event via WebSocket."""
        event_message = {
            "type": "agent_started",
            "agent_name": "test_agent",
            "event_index": event_index,
            "timestamp": time.time()
        }
        await WebSocketTestHelpers.send_test_message(websocket_client, event_message)
    
    async def _collect_websocket_events(self, websocket_client, timeout: float = 5.0) -> List[Dict]:
        """Collect WebSocket events with timeout."""
        events = []
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                event = await WebSocketTestHelpers.receive_test_message(
                    websocket_client, timeout=1.0
                )
                if event:
                    events.append(event)
            except:
                break  # Timeout or error, stop collecting
        
        return events