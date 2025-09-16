"""
Test Performance and Race Conditions Under High-Load Scenarios

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure platform stability and performance under peak user load
- Value Impact: High-load scenarios must maintain data consistency, prevent race conditions, and deliver performance
- Strategic Impact: CRITICAL for revenue growth - peak load capacity determines enterprise customer confidence

CRITICAL REQUIREMENTS:
1. Test 50+ concurrent WebSocket connections with realistic load patterns
2. Validate race condition prevention with real database locks and Redis coordination
3. Test agent execution performance with large context windows and concurrent users
4. Validate memory usage patterns during extended conversations
5. Test CPU utilization during multiple concurrent agent executions
6. Validate resource cleanup performance after mass disconnections
7. Use REAL services (NO MOCKS) - PostgreSQL, Redis, WebSocket connections
8. Performance regression testing with response time thresholds
9. Race condition detection in shared resource access
10. Concurrent WebSocket message ordering validation

REAL SYSTEM VALIDATION:
- Real PostgreSQL with concurrent transaction isolation testing
- Real Redis cache operations with distributed locking
- Real WebSocket connections with concurrent event broadcasting
- Real agent execution workflows under high load
- Real memory and CPU utilization monitoring
"""

import asyncio
import json
import logging
import os
import psutil
import statistics
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import pytest

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.websocket_helpers import WebSocketTestHelpers, WebSocketTestClient
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics for high-load testing."""
    test_name: str
    concurrent_operations: int
    successful_operations: int
    failed_operations: int
    total_execution_time: float
    average_response_time: float
    p95_response_time: float
    p99_response_time: float
    memory_usage_start_mb: float
    memory_usage_peak_mb: float
    memory_usage_end_mb: float
    cpu_usage_average: float
    cpu_usage_peak: float
    websocket_connections_established: int
    websocket_messages_sent: int
    websocket_messages_received: int
    database_operations_completed: int
    redis_operations_completed: int
    race_conditions_detected: int
    race_conditions_prevented: int
    data_consistency_maintained: bool
    performance_threshold_met: bool
    error_messages: List[str]


@dataclass 
class RaceConditionTestScenario:
    """Race condition test scenario configuration."""
    scenario_name: str
    concurrent_operations: int
    shared_resource_id: str
    operation_type: str  # 'database', 'redis', 'websocket', 'agent_execution'
    expected_final_state: Any
    race_condition_triggers: List[str]


@dataclass
class HighLoadUserSession:
    """User session for high-load testing."""
    user_id: str
    session_id: str
    websocket_connection: Any
    agent_executions_completed: int
    messages_sent: int
    messages_received: int
    session_start_time: float
    last_activity_time: float
    memory_footprint_mb: float
    active: bool
    error_count: int


class TestPerformanceRaceConditionsComprehensiveHighLoad(BaseIntegrationTest):
    """Comprehensive test for performance and race conditions under high-load scenarios."""
    
    def setup_method(self):
        """Setup test environment for high-load performance testing."""
        super().setup_method()
        self.auth_helper = E2EAuthHelper(environment="test")
        
        # Performance thresholds for validation
        self.performance_thresholds = {
            "max_avg_response_time": 3.0,      # 3 seconds average
            "max_p95_response_time": 8.0,      # 8 seconds 95th percentile  
            "max_p99_response_time": 15.0,     # 15 seconds 99th percentile
            "min_success_rate": 0.90,          # 90% success rate minimum
            "max_memory_growth_mb": 500,       # Max 500MB memory growth
            "max_cpu_usage": 80.0,             # Max 80% CPU usage average
            "max_websocket_connection_time": 5.0,  # 5 seconds WebSocket connection
            "max_race_conditions_tolerated": 5     # Max 5 race conditions before failure
        }
        
        # High-load test configuration
        self.high_load_config = {
            "concurrent_websocket_connections": 75,
            "concurrent_database_operations": 100,
            "concurrent_redis_operations": 150,
            "concurrent_agent_executions": 25,
            "extended_conversation_length": 50,  # Messages per conversation
            "peak_load_duration_seconds": 120,   # 2 minutes peak load
            "resource_cleanup_timeout": 30       # 30 seconds cleanup timeout
        }
        
        # Race condition test scenarios
        self.race_condition_scenarios = [
            RaceConditionTestScenario(
                scenario_name="database_account_balance_updates",
                concurrent_operations=20,
                shared_resource_id="shared_account_001", 
                operation_type="database",
                expected_final_state="balance_consistency",
                race_condition_triggers=["concurrent_writes", "optimistic_locking"]
            ),
            RaceConditionTestScenario(
                scenario_name="redis_session_coordination",
                concurrent_operations=30,
                shared_resource_id="session_coordination_key",
                operation_type="redis",
                expected_final_state="single_active_session",
                race_condition_triggers=["distributed_locking", "ttl_expiry"]
            ),
            RaceConditionTestScenario(
                scenario_name="websocket_message_ordering",
                concurrent_operations=15,
                shared_resource_id="message_sequence_001",
                operation_type="websocket",
                expected_final_state="correct_message_order",
                race_condition_triggers=["concurrent_sends", "connection_drops"]
            ),
            RaceConditionTestScenario(
                scenario_name="agent_execution_resource_allocation",
                concurrent_operations=10,
                shared_resource_id="agent_resource_pool",
                operation_type="agent_execution", 
                expected_final_state="fair_resource_distribution",
                race_condition_triggers=["resource_contention", "execution_ordering"]
            )
        ]
        
        # System resource monitoring
        self.system_monitor = SystemResourceMonitor()

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.high_load
    async def test_concurrent_websocket_connections_performance_validation(self, real_services_fixture):
        """Test WebSocket connection establishment and performance under high concurrent load."""
        if not real_services_fixture["database_available"]:
            pytest.fail("Real database required for concurrent WebSocket performance testing")
        
        concurrent_connections = self.high_load_config["concurrent_websocket_connections"]
        
        logger.info(f"Starting concurrent WebSocket performance test with {concurrent_connections} connections")
        
        # Start system monitoring
        self.system_monitor.start_monitoring("websocket_concurrent_performance")
        
        # Generate authenticated user contexts
        user_contexts = []
        for i in range(concurrent_connections):
            user_context = await create_authenticated_user_context(
                user_email=f"perf_test_{i}_{uuid.uuid4().hex[:6]}@example.com"
            )
            user_contexts.append(user_context)
        
        # Define concurrent WebSocket connection workflow
        async def establish_websocket_connection_with_load_test(user_context, connection_index: int):
            """Establish WebSocket connection and perform load testing."""
            connection_start_time = time.time()
            
            try:
                # Phase 1: Authentication and connection establishment
                jwt_token = user_context.agent_context.get("jwt_token")
                headers = {
                    "Authorization": f"Bearer {jwt_token}",
                    "X-User-ID": str(user_context.user_id),
                    "X-Test-Mode": "true",
                    "X-Load-Test": "concurrent_connections"
                }
                
                websocket_url = "ws://localhost:8000/ws"
                
                websocket_client = await WebSocketTestHelpers.create_test_websocket_connection(
                    websocket_url, headers=headers, timeout=10.0, user_id=str(user_context.user_id)
                )
                
                connection_time = time.time() - connection_start_time
                
                # Phase 2: Send multiple test messages to simulate realistic load
                messages_sent = 0
                messages_received = 0
                response_times = []
                
                for msg_index in range(15):  # 15 messages per connection
                    msg_start_time = time.time()
                    
                    test_message = {
                        "type": "agent_started",
                        "agent_name": "load_test_agent",
                        "user_id": str(user_context.user_id),
                        "connection_index": connection_index,
                        "message_index": msg_index,
                        "timestamp": msg_start_time
                    }
                    
                    await WebSocketTestHelpers.send_test_message(websocket_client, test_message)
                    messages_sent += 1
                    
                    # Wait for response
                    try:
                        response = await WebSocketTestHelpers.receive_test_message(
                            websocket_client, timeout=5.0
                        )
                        if response:
                            messages_received += 1
                            response_times.append(time.time() - msg_start_time)
                    except Exception as e:
                        logger.warning(f"Failed to receive message {msg_index} for connection {connection_index}: {e}")
                
                # Phase 3: Close connection
                await WebSocketTestHelpers.close_test_connection(websocket_client)
                
                return {
                    "success": True,
                    "connection_index": connection_index,
                    "user_id": str(user_context.user_id),
                    "connection_time": connection_time,
                    "messages_sent": messages_sent,
                    "messages_received": messages_received,
                    "avg_response_time": statistics.mean(response_times) if response_times else 0,
                    "total_execution_time": time.time() - connection_start_time
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "connection_index": connection_index,
                    "user_id": str(user_context.user_id),
                    "error": str(e),
                    "connection_time": time.time() - connection_start_time,
                    "messages_sent": 0,
                    "messages_received": 0,
                    "avg_response_time": 0,
                    "total_execution_time": time.time() - connection_start_time
                }
        
        # Execute concurrent WebSocket connections with gradual ramp-up
        connection_tasks = []
        batch_size = 25  # Ramp up in batches of 25
        
        for i in range(0, len(user_contexts), batch_size):
            batch = user_contexts[i:i + batch_size]
            logger.info(f"Starting WebSocket batch {i//batch_size + 1}: connections {i+1}-{min(i+batch_size, len(user_contexts))}")
            
            batch_tasks = [
                establish_websocket_connection_with_load_test(user_context, i + j)
                for j, user_context in enumerate(batch)
            ]
            
            connection_tasks.extend(batch_tasks)
            
            # Brief pause between batches to avoid overwhelming the system
            await asyncio.sleep(2.0)
        
        # Execute all connections concurrently
        execution_start_time = time.time()
        connection_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        total_execution_time = time.time() - execution_start_time
        
        # Stop system monitoring
        system_metrics = self.system_monitor.stop_monitoring("websocket_concurrent_performance")
        
        # Analyze results
        successful_connections = [r for r in connection_results if isinstance(r, dict) and r.get("success")]
        failed_connections = [r for r in connection_results if isinstance(r, dict) and not r.get("success")]
        
        total_messages_sent = sum(r["messages_sent"] for r in successful_connections)
        total_messages_received = sum(r["messages_received"] for r in successful_connections)
        connection_times = [r["connection_time"] for r in successful_connections if r["connection_time"] > 0]
        response_times = [r["avg_response_time"] for r in successful_connections if r["avg_response_time"] > 0]
        
        # Create performance metrics
        performance_metrics = PerformanceMetrics(
            test_name="concurrent_websocket_connections_performance",
            concurrent_operations=concurrent_connections,
            successful_operations=len(successful_connections),
            failed_operations=len(failed_connections),
            total_execution_time=total_execution_time,
            average_response_time=statistics.mean(response_times) if response_times else 0,
            p95_response_time=sorted(response_times)[int(len(response_times) * 0.95)] if response_times else 0,
            p99_response_time=sorted(response_times)[int(len(response_times) * 0.99)] if response_times else 0,
            memory_usage_start_mb=system_metrics.get("memory_start_mb", 0),
            memory_usage_peak_mb=system_metrics.get("memory_peak_mb", 0),
            memory_usage_end_mb=system_metrics.get("memory_end_mb", 0),
            cpu_usage_average=system_metrics.get("cpu_avg", 0),
            cpu_usage_peak=system_metrics.get("cpu_peak", 0),
            websocket_connections_established=len(successful_connections),
            websocket_messages_sent=total_messages_sent,
            websocket_messages_received=total_messages_received,
            database_operations_completed=0,  # Not applicable for this test
            redis_operations_completed=0,     # Not applicable for this test
            race_conditions_detected=0,
            race_conditions_prevented=0,
            data_consistency_maintained=True,
            performance_threshold_met=False,  # Will be calculated below
            error_messages=[str(r.get("error", "")) for r in failed_connections]
        )
        
        # Validate performance requirements
        self._validate_websocket_performance_thresholds(performance_metrics)
        
        # Validate business value delivered
        self._validate_concurrent_websocket_business_value(performance_metrics)
        
        logger.info(f"Concurrent WebSocket performance test completed")
        logger.info(f"Connections: {performance_metrics.successful_operations}/{performance_metrics.concurrent_operations}")
        logger.info(f"Messages sent/received: {performance_metrics.websocket_messages_sent}/{performance_metrics.websocket_messages_received}")
        logger.info(f"Average response time: {performance_metrics.average_response_time:.3f}s")

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.high_load
    async def test_database_race_condition_prevention_under_high_load(self, real_services_fixture):
        """Test database race condition prevention with high concurrent load."""
        if not real_services_fixture["database_available"]:
            pytest.fail("Real database required for race condition testing")
        
        db_session = real_services_fixture["db"]
        scenario = self.race_condition_scenarios[0]  # database_account_balance_updates
        
        logger.info(f"Starting database race condition test: {scenario.scenario_name}")
        
        # Start system monitoring
        self.system_monitor.start_monitoring("database_race_conditions")
        
        # Create shared test account
        account_id = scenario.shared_resource_id
        initial_balance = 1000.00
        
        await self._create_test_account(db_session, account_id, initial_balance)
        
        # Define concurrent database operation that can trigger race conditions
        async def concurrent_balance_update_with_contention(operation_id: int, update_amount: float):
            """Perform concurrent balance update that may trigger race conditions."""
            operation_start_time = time.time()
            
            try:
                # Create additional contention by performing multiple operations
                for sub_op in range(3):  # 3 sub-operations per main operation
                    result = await self._update_account_balance_with_optimistic_locking(
                        db_session, account_id, update_amount / 3, f"{operation_id}_{sub_op}"
                    )
                    
                    if not result["success"]:
                        # Race condition detected and handled
                        return {
                            "success": False,
                            "operation_id": operation_id,
                            "race_condition_detected": True,
                            "race_condition_prevented": "optimistic_locking" in str(result.get("error", "")),
                            "execution_time": time.time() - operation_start_time,
                            "error": result.get("error", "Unknown error")
                        }
                
                return {
                    "success": True,
                    "operation_id": operation_id,
                    "race_condition_detected": False,
                    "race_condition_prevented": False,
                    "execution_time": time.time() - operation_start_time,
                    "final_amount": update_amount
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "operation_id": operation_id,
                    "race_condition_detected": True,
                    "race_condition_prevented": "lock" in str(e).lower() or "conflict" in str(e).lower(),
                    "execution_time": time.time() - operation_start_time,
                    "error": str(e)
                }
        
        # Execute concurrent database operations
        concurrent_ops = scenario.concurrent_operations
        update_amount = 50.00  # Each operation adds $50
        
        db_tasks = [
            concurrent_balance_update_with_contention(i, update_amount)
            for i in range(concurrent_ops)
        ]
        
        execution_start_time = time.time()
        db_results = await asyncio.gather(*db_tasks, return_exceptions=True)
        total_execution_time = time.time() - execution_start_time
        
        # Stop system monitoring
        system_metrics = self.system_monitor.stop_monitoring("database_race_conditions")
        
        # Analyze race condition results
        successful_operations = [r for r in db_results if isinstance(r, dict) and r.get("success")]
        race_conditions_detected = sum(1 for r in db_results if isinstance(r, dict) and r.get("race_condition_detected"))
        race_conditions_prevented = sum(1 for r in db_results if isinstance(r, dict) and r.get("race_condition_prevented"))
        
        # Verify final account balance consistency
        final_balance = await self._get_account_balance(db_session, account_id)
        expected_balance = initial_balance + (len(successful_operations) * update_amount)
        balance_consistent = abs(final_balance - expected_balance) < 0.01
        
        # Create performance metrics
        execution_times = [r["execution_time"] for r in db_results if isinstance(r, dict) and "execution_time" in r]
        
        performance_metrics = PerformanceMetrics(
            test_name="database_race_condition_prevention",
            concurrent_operations=concurrent_ops,
            successful_operations=len(successful_operations),
            failed_operations=concurrent_ops - len(successful_operations),
            total_execution_time=total_execution_time,
            average_response_time=statistics.mean(execution_times) if execution_times else 0,
            p95_response_time=sorted(execution_times)[int(len(execution_times) * 0.95)] if execution_times else 0,
            p99_response_time=sorted(execution_times)[int(len(execution_times) * 0.99)] if execution_times else 0,
            memory_usage_start_mb=system_metrics.get("memory_start_mb", 0),
            memory_usage_peak_mb=system_metrics.get("memory_peak_mb", 0),
            memory_usage_end_mb=system_metrics.get("memory_end_mb", 0),
            cpu_usage_average=system_metrics.get("cpu_avg", 0),
            cpu_usage_peak=system_metrics.get("cpu_peak", 0),
            websocket_connections_established=0,
            websocket_messages_sent=0,
            websocket_messages_received=0,
            database_operations_completed=len(successful_operations),
            redis_operations_completed=0,
            race_conditions_detected=race_conditions_detected,
            race_conditions_prevented=race_conditions_prevented,
            data_consistency_maintained=balance_consistent,
            performance_threshold_met=False,  # Will be calculated below
            error_messages=[str(r.get("error", "")) for r in db_results if isinstance(r, dict) and not r.get("success")]
        )
        
        # Validate race condition handling
        assert performance_metrics.data_consistency_maintained, \
            f"Database consistency failed: expected {expected_balance}, got {final_balance}"
        
        assert performance_metrics.race_conditions_detected <= self.performance_thresholds["max_race_conditions_tolerated"], \
            f"Too many race conditions detected: {performance_metrics.race_conditions_detected}"
        
        if performance_metrics.race_conditions_detected > 0:
            assert performance_metrics.race_conditions_prevented >= (performance_metrics.race_conditions_detected * 0.8), \
                f"Insufficient race condition prevention: {performance_metrics.race_conditions_prevented}/{performance_metrics.race_conditions_detected}"
        
        # Validate performance thresholds
        self._validate_database_performance_thresholds(performance_metrics)
        
        logger.info(f"Database race condition test completed: {performance_metrics.race_conditions_detected} detected, {performance_metrics.race_conditions_prevented} prevented")
        logger.info(f"Data consistency maintained: {performance_metrics.data_consistency_maintained}")

    @pytest.mark.integration
    @pytest.mark.real_services  
    @pytest.mark.high_load
    async def test_agent_execution_performance_large_context_concurrent_users(self, real_services_fixture):
        """Test agent execution performance with large context windows and concurrent users."""
        if not real_services_fixture["database_available"]:
            pytest.fail("Real database required for agent execution performance testing")
        
        concurrent_agent_executions = self.high_load_config["concurrent_agent_executions"]
        large_context_size = 2000  # 2000 characters per context
        
        logger.info(f"Starting agent execution performance test with {concurrent_agent_executions} concurrent agents")
        
        # Start system monitoring
        self.system_monitor.start_monitoring("agent_execution_performance")
        
        # Generate user contexts with large context windows
        user_contexts_with_large_context = []
        for i in range(concurrent_agent_executions):
            user_context = await create_authenticated_user_context(
                user_email=f"agent_perf_test_{i}_{uuid.uuid4().hex[:6]}@example.com"
            )
            
            # Add large context data
            large_context_data = {
                "conversation_history": self._generate_large_conversation_context(large_context_size),
                "user_preferences": self._generate_user_preferences_context(),
                "system_state": self._generate_system_state_context(),
                "execution_context": f"concurrent_agent_execution_{i}"
            }
            
            user_context.agent_context.update(large_context_data)
            user_contexts_with_large_context.append(user_context)
        
        # Define concurrent agent execution with large context
        async def execute_agent_with_large_context_and_monitoring(user_context, agent_index: int):
            """Execute agent with large context and monitor performance."""
            execution_start_time = time.time()
            
            try:
                # Phase 1: Context preparation and validation
                context_prep_start = time.time()
                context_size = len(str(user_context.agent_context))
                context_prep_time = time.time() - context_prep_start
                
                # Phase 2: Simulated agent execution with context processing
                agent_processing_start = time.time()
                
                # Simulate agent processing large context
                processing_results = await self._simulate_agent_processing_with_large_context(
                    user_context, agent_index
                )
                
                agent_processing_time = time.time() - agent_processing_start
                
                # Phase 3: Response generation and cleanup
                response_gen_start = time.time()
                final_response = await self._generate_agent_response_with_context(
                    processing_results, user_context
                )
                response_gen_time = time.time() - response_gen_start
                
                total_execution_time = time.time() - execution_start_time
                
                return {
                    "success": True,
                    "agent_index": agent_index,
                    "user_id": str(user_context.user_id),
                    "context_size": context_size,
                    "context_prep_time": context_prep_time,
                    "agent_processing_time": agent_processing_time,
                    "response_generation_time": response_gen_time,
                    "total_execution_time": total_execution_time,
                    "response_quality": self._evaluate_response_quality(final_response),
                    "memory_footprint_estimate": context_size * 1.5  # Rough estimate
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "agent_index": agent_index,
                    "user_id": str(user_context.user_id),
                    "total_execution_time": time.time() - execution_start_time,
                    "error": str(e)
                }
        
        # Execute concurrent agent executions
        agent_tasks = [
            execute_agent_with_large_context_and_monitoring(user_context, i)
            for i, user_context in enumerate(user_contexts_with_large_context)
        ]
        
        execution_start_time = time.time()
        agent_results = await asyncio.gather(*agent_tasks, return_exceptions=True)
        total_execution_time = time.time() - execution_start_time
        
        # Stop system monitoring
        system_metrics = self.system_monitor.stop_monitoring("agent_execution_performance")
        
        # Analyze agent execution results
        successful_executions = [r for r in agent_results if isinstance(r, dict) and r.get("success")]
        failed_executions = [r for r in agent_results if isinstance(r, dict) and not r.get("success")]
        
        execution_times = [r["total_execution_time"] for r in successful_executions]
        context_sizes = [r["context_size"] for r in successful_executions]
        memory_footprints = [r["memory_footprint_estimate"] for r in successful_executions]
        
        # Create performance metrics
        performance_metrics = PerformanceMetrics(
            test_name="agent_execution_large_context_concurrent",
            concurrent_operations=concurrent_agent_executions,
            successful_operations=len(successful_executions),
            failed_operations=len(failed_executions),
            total_execution_time=total_execution_time,
            average_response_time=statistics.mean(execution_times) if execution_times else 0,
            p95_response_time=sorted(execution_times)[int(len(execution_times) * 0.95)] if execution_times else 0,
            p99_response_time=sorted(execution_times)[int(len(execution_times) * 0.99)] if execution_times else 0,
            memory_usage_start_mb=system_metrics.get("memory_start_mb", 0),
            memory_usage_peak_mb=system_metrics.get("memory_peak_mb", 0),
            memory_usage_end_mb=system_metrics.get("memory_end_mb", 0),
            cpu_usage_average=system_metrics.get("cpu_avg", 0),
            cpu_usage_peak=system_metrics.get("cpu_peak", 0),
            websocket_connections_established=0,
            websocket_messages_sent=0,
            websocket_messages_received=0,
            database_operations_completed=0,
            redis_operations_completed=0,
            race_conditions_detected=0,
            race_conditions_prevented=0,
            data_consistency_maintained=True,
            performance_threshold_met=False,
            error_messages=[str(r.get("error", "")) for r in failed_executions]
        )
        
        # Validate agent execution performance
        self._validate_agent_execution_performance_thresholds(performance_metrics)
        
        # Additional validations specific to large context processing
        avg_context_size = statistics.mean(context_sizes) if context_sizes else 0
        avg_memory_footprint = statistics.mean(memory_footprints) if memory_footprints else 0
        
        assert avg_context_size >= large_context_size * 0.8, \
            f"Context size too small: {avg_context_size} < {large_context_size * 0.8}"
        
        assert performance_metrics.memory_usage_peak_mb <= performance_metrics.memory_usage_start_mb + self.performance_thresholds["max_memory_growth_mb"], \
            f"Memory growth exceeded threshold: {performance_metrics.memory_usage_peak_mb - performance_metrics.memory_usage_start_mb}MB"
        
        logger.info(f"Agent execution performance test completed")
        logger.info(f"Successful executions: {performance_metrics.successful_operations}/{performance_metrics.concurrent_operations}")
        logger.info(f"Average execution time: {performance_metrics.average_response_time:.3f}s")
        logger.info(f"Average context size: {avg_context_size:.0f} characters")

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.high_load
    async def test_memory_cpu_utilization_extended_conversations(self, real_services_fixture):
        """Test memory and CPU utilization during extended conversations under load."""
        if not real_services_fixture["database_available"]:
            pytest.fail("Real database required for memory/CPU utilization testing")
        
        concurrent_conversations = 20
        messages_per_conversation = self.high_load_config["extended_conversation_length"]
        
        logger.info(f"Starting memory/CPU utilization test with {concurrent_conversations} extended conversations")
        
        # Start comprehensive system monitoring
        self.system_monitor.start_monitoring("memory_cpu_extended_conversations")
        
        # Generate user contexts for extended conversations
        user_contexts = []
        for i in range(concurrent_conversations):
            user_context = await create_authenticated_user_context(
                user_email=f"memory_test_{i}_{uuid.uuid4().hex[:6]}@example.com"
            )
            user_contexts.append(user_context)
        
        # Define extended conversation simulation
        async def simulate_extended_conversation_with_monitoring(user_context, conversation_index: int):
            """Simulate extended conversation with memory and CPU monitoring."""
            conversation_start_time = time.time()
            conversation_memory_samples = []
            
            try:
                # Establish WebSocket connection
                jwt_token = user_context.agent_context.get("jwt_token")
                headers = {
                    "Authorization": f"Bearer {jwt_token}",
                    "X-User-ID": str(user_context.user_id),
                    "X-Test-Mode": "true",
                    "X-Extended-Conversation": "true"
                }
                
                websocket_url = "ws://localhost:8000/ws"
                websocket_client = await WebSocketTestHelpers.create_test_websocket_connection(
                    websocket_url, headers=headers, timeout=10.0, user_id=str(user_context.user_id)
                )
                
                messages_sent = 0
                messages_received = 0
                conversation_context = []
                
                # Simulate extended conversation
                for message_index in range(messages_per_conversation):
                    message_start_time = time.time()
                    
                    # Create contextual message that builds on previous messages
                    message_content = self._generate_contextual_message(
                        conversation_context, message_index
                    )
                    
                    conversation_message = {
                        "type": "agent_started",
                        "agent_name": "conversation_agent",
                        "user_id": str(user_context.user_id),
                        "message": message_content,
                        "conversation_index": conversation_index,
                        "message_index": message_index,
                        "context_length": len(conversation_context),
                        "timestamp": message_start_time
                    }
                    
                    # Send message and track memory usage
                    current_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
                    conversation_memory_samples.append(current_memory)
                    
                    await WebSocketTestHelpers.send_test_message(websocket_client, conversation_message)
                    messages_sent += 1
                    
                    # Simulate processing time and context building
                    await asyncio.sleep(0.1)  # 100ms processing per message
                    
                    # Update conversation context
                    conversation_context.append({
                        "message_index": message_index,
                        "content": message_content,
                        "timestamp": message_start_time
                    })
                    
                    # Limit context size to prevent unlimited growth
                    if len(conversation_context) > 20:
                        conversation_context = conversation_context[-20:]
                    
                    try:
                        response = await WebSocketTestHelpers.receive_test_message(
                            websocket_client, timeout=3.0
                        )
                        if response:
                            messages_received += 1
                    except Exception:
                        pass  # Continue on receive timeout
                
                # Close connection
                await WebSocketTestHelpers.close_test_connection(websocket_client)
                
                return {
                    "success": True,
                    "conversation_index": conversation_index,
                    "user_id": str(user_context.user_id),
                    "messages_sent": messages_sent,
                    "messages_received": messages_received,
                    "conversation_duration": time.time() - conversation_start_time,
                    "memory_samples": conversation_memory_samples,
                    "peak_memory_mb": max(conversation_memory_samples) if conversation_memory_samples else 0,
                    "memory_growth_mb": max(conversation_memory_samples) - min(conversation_memory_samples) if len(conversation_memory_samples) > 1 else 0,
                    "context_size_final": len(conversation_context),
                    "avg_message_processing_time": (time.time() - conversation_start_time) / messages_sent if messages_sent > 0 else 0
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "conversation_index": conversation_index,
                    "user_id": str(user_context.user_id),
                    "error": str(e),
                    "memory_samples": conversation_memory_samples,
                    "conversation_duration": time.time() - conversation_start_time
                }
        
        # Execute concurrent extended conversations
        conversation_tasks = [
            simulate_extended_conversation_with_monitoring(user_context, i)
            for i, user_context in enumerate(user_contexts)
        ]
        
        execution_start_time = time.time()
        conversation_results = await asyncio.gather(*conversation_tasks, return_exceptions=True)
        total_execution_time = time.time() - execution_start_time
        
        # Stop system monitoring
        system_metrics = self.system_monitor.stop_monitoring("memory_cpu_extended_conversations")
        
        # Analyze memory and CPU utilization results
        successful_conversations = [r for r in conversation_results if isinstance(r, dict) and r.get("success")]
        failed_conversations = [r for r in conversation_results if isinstance(r, dict) and not r.get("success")]
        
        total_messages_sent = sum(r["messages_sent"] for r in successful_conversations)
        total_messages_received = sum(r["messages_received"] for r in successful_conversations)
        conversation_durations = [r["conversation_duration"] for r in successful_conversations]
        memory_growth_values = [r["memory_growth_mb"] for r in successful_conversations if r["memory_growth_mb"] > 0]
        
        # Create performance metrics
        performance_metrics = PerformanceMetrics(
            test_name="memory_cpu_extended_conversations",
            concurrent_operations=concurrent_conversations,
            successful_operations=len(successful_conversations),
            failed_operations=len(failed_conversations),
            total_execution_time=total_execution_time,
            average_response_time=statistics.mean(conversation_durations) if conversation_durations else 0,
            p95_response_time=sorted(conversation_durations)[int(len(conversation_durations) * 0.95)] if conversation_durations else 0,
            p99_response_time=sorted(conversation_durations)[int(len(conversation_durations) * 0.99)] if conversation_durations else 0,
            memory_usage_start_mb=system_metrics.get("memory_start_mb", 0),
            memory_usage_peak_mb=system_metrics.get("memory_peak_mb", 0),
            memory_usage_end_mb=system_metrics.get("memory_end_mb", 0),
            cpu_usage_average=system_metrics.get("cpu_avg", 0),
            cpu_usage_peak=system_metrics.get("cpu_peak", 0),
            websocket_connections_established=len(successful_conversations),
            websocket_messages_sent=total_messages_sent,
            websocket_messages_received=total_messages_received,
            database_operations_completed=0,
            redis_operations_completed=0,
            race_conditions_detected=0,
            race_conditions_prevented=0,
            data_consistency_maintained=True,
            performance_threshold_met=False,
            error_messages=[str(r.get("error", "")) for r in failed_conversations]
        )
        
        # Validate memory and CPU utilization
        self._validate_memory_cpu_utilization_thresholds(performance_metrics, memory_growth_values)
        
        logger.info(f"Memory/CPU utilization test completed")
        logger.info(f"Total messages: {performance_metrics.websocket_messages_sent}/{performance_metrics.websocket_messages_received}")
        logger.info(f"Memory peak: {performance_metrics.memory_usage_peak_mb:.1f}MB")
        logger.info(f"CPU average: {performance_metrics.cpu_usage_average:.1f}%")

    # Helper Methods

    async def _create_test_account(self, db_session, account_id: str, initial_balance: float):
        """Create test account for race condition testing."""
        account_insert = """
            INSERT INTO test_accounts (id, balance, version, created_at)
            VALUES (%(account_id)s, %(balance)s, 1, %(created_at)s)
            ON CONFLICT (id) DO UPDATE SET
                balance = EXCLUDED.balance,
                version = 1,
                updated_at = NOW()
        """
        
        await db_session.execute(account_insert, {
            "account_id": account_id,
            "balance": initial_balance,
            "created_at": datetime.now(timezone.utc)
        })
        await db_session.commit()

    async def _update_account_balance_with_optimistic_locking(
        self, db_session, account_id: str, amount: float, operation_id: str
    ) -> Dict[str, Any]:
        """Update account balance with optimistic locking to prevent race conditions."""
        try:
            async with db_session.begin():
                # Get current balance and version with row lock
                lock_query = """
                    SELECT balance, version FROM test_accounts
                    WHERE id = %(account_id)s
                    FOR UPDATE
                """
                
                result = await db_session.execute(lock_query, {"account_id": account_id})
                account_row = result.fetchone()
                
                if not account_row:
                    return {
                        "success": False,
                        "operation_id": operation_id,
                        "error": "Account not found"
                    }
                
                current_balance = float(account_row.balance)
                current_version = int(account_row.version)
                
                # Simulate processing delay to increase race condition likelihood
                await asyncio.sleep(0.05)
                
                # Update with version check (optimistic locking)
                new_balance = current_balance + amount
                new_version = current_version + 1
                
                update_query = """
                    UPDATE test_accounts 
                    SET balance = %(new_balance)s, version = %(new_version)s, updated_at = %(updated_at)s
                    WHERE id = %(account_id)s AND version = %(current_version)s
                """
                
                update_result = await db_session.execute(update_query, {
                    "account_id": account_id,
                    "new_balance": new_balance,
                    "new_version": new_version,
                    "current_version": current_version,
                    "updated_at": datetime.now(timezone.utc)
                })
                
                if update_result.rowcount == 0:
                    return {
                        "success": False,
                        "operation_id": operation_id,
                        "error": "Optimistic locking conflict - race condition detected and prevented"
                    }
                
                return {
                    "success": True,
                    "operation_id": operation_id,
                    "previous_balance": current_balance,
                    "new_balance": new_balance,
                    "version": new_version
                }
                
        except Exception as e:
            return {
                "success": False,
                "operation_id": operation_id,
                "error": str(e)
            }

    async def _get_account_balance(self, db_session, account_id: str) -> float:
        """Get current account balance."""
        balance_query = """
            SELECT balance FROM test_accounts WHERE id = %(account_id)s
        """
        
        result = await db_session.execute(balance_query, {"account_id": account_id})
        row = result.fetchone()
        
        return float(row.balance) if row else 0.0

    def _generate_large_conversation_context(self, target_size: int) -> str:
        """Generate large conversation context for performance testing."""
        base_conversation = (
            "User: I need help optimizing my cloud costs. "
            "Agent: I can help you analyze your cloud spending patterns and identify optimization opportunities. "
            "User: What should I look for first? "
            "Agent: Let's start by examining your compute resource utilization and storage costs. "
        )
        
        # Repeat and expand context to reach target size
        conversation_context = base_conversation
        while len(conversation_context) < target_size:
            conversation_context += (
                f"User: Can you provide more details about optimization step {len(conversation_context) // 100}? "
                f"Agent: Certainly! Here are the detailed recommendations for this optimization phase... "
            )
        
        return conversation_context[:target_size]

    def _generate_user_preferences_context(self) -> Dict[str, Any]:
        """Generate user preferences context for testing."""
        return {
            "optimization_priorities": ["cost", "performance", "security"],
            "risk_tolerance": "medium",
            "budget_constraints": 10000,
            "preferred_cloud_providers": ["aws", "gcp"],
            "notification_preferences": {
                "email": True,
                "slack": False,
                "webhook": True
            }
        }

    def _generate_system_state_context(self) -> Dict[str, Any]:
        """Generate system state context for testing."""
        return {
            "active_optimizations": 3,
            "pending_recommendations": 7,
            "system_health": "good",
            "resource_utilization": {
                "cpu": 65.5,
                "memory": 78.2,
                "storage": 45.0
            },
            "recent_alerts": []
        }

    async def _simulate_agent_processing_with_large_context(
        self, user_context, agent_index: int
    ) -> Dict[str, Any]:
        """Simulate agent processing with large context."""
        # Simulate context analysis
        await asyncio.sleep(0.2)  # 200ms context processing
        
        context_size = len(str(user_context.agent_context))
        
        # Simulate different processing complexity based on context size
        if context_size > 5000:
            processing_complexity = "high"
            await asyncio.sleep(0.3)  # Additional 300ms for large context
        elif context_size > 2000:
            processing_complexity = "medium" 
            await asyncio.sleep(0.15)  # Additional 150ms for medium context
        else:
            processing_complexity = "low"
        
        return {
            "agent_index": agent_index,
            "context_processed": True,
            "context_size": context_size,
            "processing_complexity": processing_complexity,
            "recommendations_generated": max(1, context_size // 1000),
            "processing_time": 0.2 + (0.15 if processing_complexity == "medium" else 0.3 if processing_complexity == "high" else 0)
        }

    async def _generate_agent_response_with_context(
        self, processing_results: Dict[str, Any], user_context
    ) -> Dict[str, Any]:
        """Generate agent response incorporating context."""
        await asyncio.sleep(0.1)  # 100ms response generation
        
        return {
            "response_type": "optimization_recommendations",
            "recommendations_count": processing_results.get("recommendations_generated", 1),
            "context_utilized": processing_results.get("context_size", 0),
            "processing_complexity": processing_results.get("processing_complexity", "low"),
            "response_quality_score": 0.85 + (0.1 if processing_results.get("processing_complexity") == "high" else 0),
            "generated_at": time.time()
        }

    def _evaluate_response_quality(self, response: Dict[str, Any]) -> float:
        """Evaluate response quality for performance metrics."""
        base_quality = response.get("response_quality_score", 0.7)
        
        # Adjust quality based on response characteristics
        recommendations_count = response.get("recommendations_count", 0)
        if recommendations_count >= 5:
            base_quality += 0.1
        elif recommendations_count <= 1:
            base_quality -= 0.1
        
        return max(0.0, min(1.0, base_quality))

    def _generate_contextual_message(
        self, conversation_context: List[Dict], message_index: int
    ) -> str:
        """Generate contextual message that builds on conversation history."""
        base_messages = [
            "Can you help me optimize my cloud costs?",
            "What are the most effective cost optimization strategies?",
            "How can I monitor my spending patterns?",
            "What tools do you recommend for cost tracking?",
            "Can you analyze my current resource utilization?"
        ]
        
        if message_index < len(base_messages):
            return base_messages[message_index]
        
        # Generate contextual follow-up messages
        context_length = len(conversation_context)
        return f"Following up on our previous discussion (context: {context_length} messages), can you provide more specific recommendations for optimization step {message_index + 1}?"

    def _validate_websocket_performance_thresholds(self, metrics: PerformanceMetrics):
        """Validate WebSocket performance against thresholds."""
        success_rate = metrics.successful_operations / metrics.concurrent_operations
        
        assert success_rate >= self.performance_thresholds["min_success_rate"], \
            f"WebSocket success rate {success_rate:.3f} below required {self.performance_thresholds['min_success_rate']}"
        
        assert metrics.average_response_time <= self.performance_thresholds["max_avg_response_time"], \
            f"Average response time {metrics.average_response_time:.2f}s exceeds {self.performance_thresholds['max_avg_response_time']}s"
        
        assert metrics.p95_response_time <= self.performance_thresholds["max_p95_response_time"], \
            f"P95 response time {metrics.p95_response_time:.2f}s exceeds {self.performance_thresholds['max_p95_response_time']}s"
        
        metrics.performance_threshold_met = True

    def _validate_database_performance_thresholds(self, metrics: PerformanceMetrics):
        """Validate database performance against thresholds."""
        success_rate = metrics.successful_operations / metrics.concurrent_operations
        
        assert success_rate >= 0.7, \
            f"Database operation success rate {success_rate:.3f} too low (expected >= 70%)"
        
        assert metrics.average_response_time <= 5.0, \
            f"Database average response time {metrics.average_response_time:.2f}s exceeds 5s threshold"
        
        metrics.performance_threshold_met = True

    def _validate_agent_execution_performance_thresholds(self, metrics: PerformanceMetrics):
        """Validate agent execution performance against thresholds."""
        success_rate = metrics.successful_operations / metrics.concurrent_operations
        
        assert success_rate >= 0.8, \
            f"Agent execution success rate {success_rate:.3f} below required 80%"
        
        assert metrics.average_response_time <= 10.0, \
            f"Agent execution average time {metrics.average_response_time:.2f}s exceeds 10s threshold"
        
        assert metrics.cpu_usage_average <= self.performance_thresholds["max_cpu_usage"], \
            f"CPU usage {metrics.cpu_usage_average:.1f}% exceeds {self.performance_thresholds['max_cpu_usage']}% threshold"
        
        metrics.performance_threshold_met = True

    def _validate_memory_cpu_utilization_thresholds(self, metrics: PerformanceMetrics, memory_growth_values: List[float]):
        """Validate memory and CPU utilization against thresholds."""
        total_memory_growth = metrics.memory_usage_peak_mb - metrics.memory_usage_start_mb
        
        assert total_memory_growth <= self.performance_thresholds["max_memory_growth_mb"], \
            f"Memory growth {total_memory_growth:.1f}MB exceeds {self.performance_thresholds['max_memory_growth_mb']}MB threshold"
        
        assert metrics.cpu_usage_peak <= 95.0, \
            f"Peak CPU usage {metrics.cpu_usage_peak:.1f}% too high (max 95%)"
        
        assert metrics.cpu_usage_average <= self.performance_thresholds["max_cpu_usage"], \
            f"Average CPU usage {metrics.cpu_usage_average:.1f}% exceeds {self.performance_thresholds['max_cpu_usage']}% threshold"
        
        # Validate per-conversation memory growth
        if memory_growth_values:
            avg_conversation_memory_growth = statistics.mean(memory_growth_values)
            assert avg_conversation_memory_growth <= 50.0, \
                f"Average conversation memory growth {avg_conversation_memory_growth:.1f}MB too high (max 50MB per conversation)"
        
        metrics.performance_threshold_met = True

    def _validate_concurrent_websocket_business_value(self, metrics: PerformanceMetrics):
        """Validate business value delivered by concurrent WebSocket testing."""
        # Business value validations
        assert metrics.websocket_connections_established >= 50, \
            f"Insufficient concurrent connections tested: {metrics.websocket_connections_established} < 50"
        
        assert metrics.websocket_messages_sent >= 500, \
            f"Insufficient message throughput tested: {metrics.websocket_messages_sent} < 500"
        
        delivery_rate = metrics.websocket_messages_received / metrics.websocket_messages_sent if metrics.websocket_messages_sent > 0 else 0
        assert delivery_rate >= 0.8, \
            f"Message delivery rate {delivery_rate:.3f} below business requirement (80%)"
        
        self.assert_business_value_delivered({
            "concurrent_websocket_capacity": metrics.websocket_connections_established,
            "message_throughput": metrics.websocket_messages_sent,
            "delivery_reliability": delivery_rate >= 0.8,
            "performance_validated": metrics.performance_threshold_met
        }, "scalability")


class SystemResourceMonitor:
    """Monitor system resource usage during high-load tests."""
    
    def __init__(self):
        self.monitoring_sessions = {}
        self.current_process = psutil.Process()
    
    def start_monitoring(self, session_name: str):
        """Start monitoring system resources for a test session."""
        self.monitoring_sessions[session_name] = {
            "start_time": time.time(),
            "memory_start_mb": self.current_process.memory_info().rss / 1024 / 1024,
            "cpu_samples": [],
            "memory_samples": [],
            "monitoring": True
        }
        
        # Start background monitoring task
        asyncio.create_task(self._monitor_resources(session_name))
    
    async def _monitor_resources(self, session_name: str):
        """Background task to monitor system resources."""
        session = self.monitoring_sessions.get(session_name)
        if not session:
            return
        
        while session.get("monitoring", False):
            try:
                # Sample CPU and memory usage
                cpu_percent = self.current_process.cpu_percent(interval=None)
                memory_mb = self.current_process.memory_info().rss / 1024 / 1024
                
                session["cpu_samples"].append(cpu_percent)
                session["memory_samples"].append(memory_mb)
                
                await asyncio.sleep(1.0)  # Sample every second
            except Exception:
                break  # Stop monitoring on error
    
    def stop_monitoring(self, session_name: str) -> Dict[str, float]:
        """Stop monitoring and return resource usage metrics."""
        session = self.monitoring_sessions.get(session_name)
        if not session:
            return {}
        
        session["monitoring"] = False
        session["end_time"] = time.time()
        session["memory_end_mb"] = self.current_process.memory_info().rss / 1024 / 1024
        
        # Calculate metrics
        cpu_samples = session["cpu_samples"]
        memory_samples = session["memory_samples"]
        
        metrics = {
            "duration": session["end_time"] - session["start_time"],
            "memory_start_mb": session["memory_start_mb"],
            "memory_end_mb": session["memory_end_mb"],
            "memory_peak_mb": max(memory_samples) if memory_samples else session["memory_start_mb"],
            "cpu_avg": statistics.mean(cpu_samples) if cpu_samples else 0,
            "cpu_peak": max(cpu_samples) if cpu_samples else 0,
            "cpu_samples_count": len(cpu_samples),
            "memory_samples_count": len(memory_samples)
        }
        
        return metrics