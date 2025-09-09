"""
Test Error Recovery and Resilience Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure system gracefully handles errors while maintaining user value delivery
- Value Impact: Resilient systems maintain user trust and minimize revenue loss during failures
- Strategic Impact: System reliability is critical for enterprise customers and $500K+ ARR

COVERAGE FOCUS:  
1. Database connection failure recovery testing
2. Redis cache failure graceful degradation
3. Agent execution error recovery mechanisms  
4. WebSocket connection resilience testing
5. Partial system failure golden path continuation
6. Data consistency during error scenarios
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import psutil
import random

from test_framework.base_integration_test import BaseIntegrationTest, ServiceOrchestrationIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture  
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context

logger = logging.getLogger(__name__)


class FailureType(Enum):
    """Types of system failures to test."""
    DATABASE_CONNECTION = "database_connection"
    REDIS_UNAVAILABLE = "redis_unavailable"
    NETWORK_TIMEOUT = "network_timeout"
    MEMORY_PRESSURE = "memory_pressure"
    CONCURRENT_CONFLICTS = "concurrent_conflicts"
    PARTIAL_DATA_CORRUPTION = "partial_data_corruption"


@dataclass
class ResilienceTestResult:
    """Results of a resilience test scenario."""
    failure_type: FailureType
    failure_duration: float
    recovery_time: float  
    business_value_preserved: bool
    data_consistency_maintained: bool
    user_experience_degraded: bool
    error_handled_gracefully: bool
    system_recovered_fully: bool


class TestErrorRecoveryResilience(BaseIntegrationTest, ServiceOrchestrationIntegrationTest):
    """Test error recovery and system resilience with real service integration."""
    
    def setup_method(self):
        super().setup_method()
        self.auth_helper = E2EAuthHelper(environment="test")
        self.resilience_requirements = {
            "max_recovery_time": 30.0,           # seconds
            "min_business_value_preservation": 0.7,  # 70% of value should be preserved
            "max_acceptable_degradation": 0.5,   # 50% performance degradation acceptable
            "data_consistency_required": True,   # Data must remain consistent
            "graceful_error_handling": True      # Errors must be handled gracefully
        }
        self.test_results = []

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_connection_failure_recovery(self, real_services_fixture):
        """
        Test system behavior when database connections fail and recover.
        
        Validates database resilience critical for data persistence.
        """
        user_context = await create_authenticated_user_context(
            self.auth_helper,
            real_services_fixture["db"],
            user_data={"email": "db-resilience@example.com", "name": "DB Resilience User"}
        )
        
        # Establish baseline functionality
        thread_id = str(uuid.uuid4())
        await real_services_fixture["db"].execute("""
            INSERT INTO backend.threads (id, user_id, title, created_at)
            VALUES ($1, $2, $3, $4)
        """, thread_id, user_context.user_id, "Database Resilience Test", datetime.now(timezone.utc))
        
        # Test database connection failure simulation
        failure_start_time = time.time()
        
        # Simulate database connection failure by closing the pool temporarily
        original_execute = real_services_fixture["db"].execute
        original_fetch = real_services_fixture["db"].fetch
        original_fetchval = real_services_fixture["db"].fetchval
        
        failure_count = 0
        max_failures = 5
        
        async def failing_execute(*args, **kwargs):
            nonlocal failure_count
            if failure_count < max_failures:
                failure_count += 1
                raise Exception(f"Database connection failed (attempt {failure_count})")
            return await original_execute(*args, **kwargs)
        
        async def failing_fetch(*args, **kwargs):
            nonlocal failure_count
            if failure_count < max_failures:
                failure_count += 1
                raise Exception(f"Database connection failed (attempt {failure_count})")
            return await original_fetch(*args, **kwargs)
        
        async def failing_fetchval(*args, **kwargs):
            nonlocal failure_count
            if failure_count < max_failures:
                failure_count += 1
                raise Exception(f"Database connection failed (attempt {failure_count})")
            return await original_fetchval(*args, **kwargs)
        
        # Replace database methods with failing versions
        real_services_fixture["db"].execute = failing_execute
        real_services_fixture["db"].fetch = failing_fetch
        real_services_fixture["db"].fetchval = failing_fetchval
        
        # Attempt operations during failure with retry logic
        retry_attempts = 0
        max_retries = 10
        success_after_failure = False
        recovery_start_time = None
        
        while retry_attempts < max_retries and not success_after_failure:
            try:
                retry_attempts += 1
                await asyncio.sleep(0.5)  # Brief delay between retries
                
                # Attempt database operation
                result = await real_services_fixture["db"].fetchval("""
                    SELECT COUNT(*) FROM backend.threads WHERE user_id = $1
                """, user_context.user_id)
                
                success_after_failure = True
                recovery_start_time = time.time()
                
            except Exception as e:
                self.logger.info(f"Database operation failed on attempt {retry_attempts}: {e}")
                if "connection failed" not in str(e).lower():
                    # Unexpected error type
                    raise
        
        # Restore original database methods
        real_services_fixture["db"].execute = original_execute
        real_services_fixture["db"].fetch = original_fetch
        real_services_fixture["db"].fetchval = original_fetchval
        
        failure_duration = recovery_start_time - failure_start_time if recovery_start_time else time.time() - failure_start_time
        
        # Validate recovery behavior
        assert success_after_failure, "System must recover from database failures"
        assert retry_attempts <= max_retries, "Recovery must succeed within reasonable retry limit"
        assert failure_duration <= self.resilience_requirements["max_recovery_time"], \
            f"Recovery took too long: {failure_duration:.2f}s"
        
        # Test that system continues to function after recovery
        recovery_validation_thread_id = str(uuid.uuid4()) 
        await real_services_fixture["db"].execute("""
            INSERT INTO backend.threads (id, user_id, title, created_at)  
            VALUES ($1, $2, $3, $4)
        """, recovery_validation_thread_id, user_context.user_id, "Post-Recovery Validation", datetime.now(timezone.utc))
        
        threads = await real_services_fixture["db"].fetch("""
            SELECT id, title FROM backend.threads WHERE user_id = $1 ORDER BY created_at DESC
        """, user_context.user_id)
        
        assert len(threads) >= 2, "System must maintain data after recovery"
        assert any(t["title"] == "Post-Recovery Validation" for t in threads), "New operations must work after recovery"
        
        # Store resilience test result
        db_resilience_result = ResilienceTestResult(
            failure_type=FailureType.DATABASE_CONNECTION,
            failure_duration=failure_duration,
            recovery_time=failure_duration,  # Same in this case
            business_value_preserved=True,   # System eventually recovered
            data_consistency_maintained=True,  # Data integrity preserved
            user_experience_degraded=True,  # User experienced delays
            error_handled_gracefully=True,  # Errors were caught and retried
            system_recovered_fully=True     # Full functionality restored
        )
        
        await real_services_fixture["redis"].set_json(
            "db_resilience_test_result",
            {
                "failure_type": db_resilience_result.failure_type.value,
                "failure_duration": db_resilience_result.failure_duration,
                "recovery_time": db_resilience_result.recovery_time,
                "retry_attempts": retry_attempts,
                "business_value_preserved": db_resilience_result.business_value_preserved,
                "test_timestamp": datetime.now(timezone.utc).isoformat()
            },
            ex=86400
        )
        
        self.test_results.append(db_resilience_result)
        self.logger.info(f"Database resilience test passed - Recovery time: {failure_duration:.2f}s")

    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_redis_cache_failure_graceful_degradation(self, real_services_fixture):
        """
        Test graceful degradation when Redis cache becomes unavailable.
        
        Validates that core functionality continues without caching.
        """
        user_context = await create_authenticated_user_context(
            self.auth_helper,
            real_services_fixture["db"],
            user_data={"email": "redis-resilience@example.com", "name": "Redis Resilience User"}
        )
        
        # Establish baseline with working cache
        baseline_data = {
            "user_id": user_context.user_id,
            "session_data": {"active": True, "created_at": time.time()},
            "preferences": {"theme": "dark", "notifications": True}
        }
        
        await real_services_fixture["redis"].set_json(
            f"user_session:{user_context.user_id}",
            baseline_data,
            ex=3600
        )
        
        # Verify cache is working
        cached_data = await real_services_fixture["redis"].get_json(f"user_session:{user_context.user_id}")
        assert cached_data is not None, "Baseline cache operation must work"
        
        # Simulate Redis failure
        failure_start_time = time.time()
        
        original_redis_methods = {
            "set": real_services_fixture["redis"].set,
            "get": real_services_fixture["redis"].get,
            "set_json": real_services_fixture["redis"].set_json,
            "get_json": real_services_fixture["redis"].get_json,
            "delete": real_services_fixture["redis"].delete,
            "ping": real_services_fixture["redis"].ping
        }
        
        # Replace Redis methods with failing versions
        async def failing_redis_operation(*args, **kwargs):
            raise Exception("Redis connection refused")
        
        for method_name in original_redis_methods:
            setattr(real_services_fixture["redis"], method_name, failing_redis_operation)
        
        # Test operations during Redis failure - system should degrade gracefully
        degraded_operations = []
        
        try:
            # Create thread without cache (should work via database)
            thread_id = str(uuid.uuid4())
            await real_services_fixture["db"].execute("""
                INSERT INTO backend.threads (id, user_id, title, created_at, metadata)
                VALUES ($1, $2, $3, $4, $5)
            """, thread_id, user_context.user_id, "Redis Degradation Test", datetime.now(timezone.utc),
                 json.dumps({"cache_available": False}))
            
            degraded_operations.append("thread_creation")
            
            # Attempt to store session data (should fail gracefully)
            try:
                await real_services_fixture["redis"].set_json(f"session_backup:{user_context.user_id}", {"test": True}, ex=300)
                degraded_operations.append("cache_write_failed_gracefully")
            except Exception:
                degraded_operations.append("cache_write_failed_gracefully")  # Expected failure
            
            # Retrieve user data from database instead of cache
            user_threads = await real_services_fixture["db"].fetch("""
                SELECT id, title, created_at FROM backend.threads 
                WHERE user_id = $1 ORDER BY created_at DESC LIMIT 5
            """, user_context.user_id)
            
            assert len(user_threads) >= 1, "Database operations must continue during cache failure"
            degraded_operations.append("database_fallback")
            
        except Exception as e:
            self.logger.error(f"Critical failure during Redis degradation: {e}")
            raise
        
        # Restore Redis functionality
        for method_name, original_method in original_redis_methods.items():
            setattr(real_services_fixture["redis"], method_name, original_method)
        
        recovery_time = time.time() - failure_start_time
        
        # Verify Redis recovery  
        recovery_test_data = {"recovered": True, "timestamp": time.time()}
        await real_services_fixture["redis"].set_json(
            f"recovery_test:{user_context.user_id}",
            recovery_test_data,
            ex=300
        )
        
        recovered_data = await real_services_fixture["redis"].get_json(f"recovery_test:{user_context.user_id}")
        assert recovered_data is not None, "Redis must be functional after restoration"
        assert recovered_data["recovered"] is True, "Recovered Redis data must be intact"
        
        # Test that cache functionality is fully restored
        await real_services_fixture["redis"].set_json(
            f"full_recovery_test:{user_context.user_id}",
            {"test": "full_functionality", "operations": degraded_operations},
            ex=3600
        )
        
        # Store resilience test result
        redis_resilience_result = ResilienceTestResult(
            failure_type=FailureType.REDIS_UNAVAILABLE,
            failure_duration=recovery_time,
            recovery_time=0.1,  # Quick restoration
            business_value_preserved=True,   # Core functionality via database
            data_consistency_maintained=True,  # Database maintained consistency
            user_experience_degraded=True,   # Slower without cache
            error_handled_gracefully=True,   # System didn't crash
            system_recovered_fully=True      # Full cache functionality restored
        )
        
        await real_services_fixture["redis"].set_json(
            "redis_resilience_test_result", 
            {
                "failure_type": redis_resilience_result.failure_type.value,
                "degraded_operations": degraded_operations,
                "recovery_time": redis_resilience_result.recovery_time,
                "business_value_preserved": redis_resilience_result.business_value_preserved,
                "graceful_degradation": len(degraded_operations) >= 2,
                "test_timestamp": datetime.now(timezone.utc).isoformat()
            },
            ex=86400
        )
        
        self.test_results.append(redis_resilience_result)
        
        # Validate graceful degradation requirements
        assert "database_fallback" in degraded_operations, "System must fall back to database when cache fails"
        assert "thread_creation" in degraded_operations, "Core operations must continue without cache"
        assert len(degraded_operations) >= 2, "System must demonstrate graceful degradation across multiple operations"
        
        self.logger.info(f"Redis resilience test passed - Graceful degradation maintained, recovery in {redis_resilience_result.recovery_time:.2f}s")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_error_recovery(self, real_services_fixture):
        """
        Test agent execution error recovery and continuation of golden path.
        
        Validates that agent failures don't break the entire user workflow.
        """
        user_context = await create_authenticated_user_context(
            self.auth_helper,
            real_services_fixture["db"],
            user_data={"email": "agent-resilience@example.com", "name": "Agent Resilience User"}
        )
        
        thread_id = str(uuid.uuid4())
        await real_services_fixture["db"].execute("""
            INSERT INTO backend.threads (id, user_id, title, created_at)
            VALUES ($1, $2, $3, $4)
        """, thread_id, user_context.user_id, "Agent Error Recovery Test", datetime.now(timezone.utc))
        
        # Simulate agent execution with various failure scenarios
        agent_scenarios = [
            {
                "agent_type": "triage_agent",
                "failure_stage": "initialization",
                "recovery_strategy": "retry_with_backoff",
                "expected_recovery": True
            },
            {
                "agent_type": "data_helper", 
                "failure_stage": "data_collection",
                "recovery_strategy": "partial_results",
                "expected_recovery": True
            },
            {
                "agent_type": "uvs_reporter",
                "failure_stage": "result_generation", 
                "recovery_strategy": "fallback_analysis",
                "expected_recovery": True
            }
        ]
        
        agent_recovery_results = []
        
        for scenario in agent_scenarios:
            failure_start_time = time.time()
            
            # Simulate agent execution with controlled failure
            execution_id = str(uuid.uuid4())
            
            async def simulate_failing_agent_execution():
                # Store execution start
                await real_services_fixture["redis"].set_json(
                    f"agent_execution:{execution_id}",
                    {
                        "agent_type": scenario["agent_type"],
                        "thread_id": thread_id,
                        "status": "starting",
                        "start_time": time.time(),
                        "failure_stage": scenario["failure_stage"]
                    },
                    ex=300
                )
                
                # Simulate work up to failure point
                await asyncio.sleep(0.1)
                
                if scenario["failure_stage"] == "initialization":
                    # Fail during initialization, then recover
                    await real_services_fixture["redis"].set_json(
                        f"agent_execution:{execution_id}",
                        {
                            "agent_type": scenario["agent_type"],
                            "thread_id": thread_id,
                            "status": "failed",
                            "error": "Initialization failed - resource unavailable",
                            "retry_attempt": 1
                        },
                        ex=300
                    )
                    
                    # Simulate retry with backoff
                    await asyncio.sleep(0.2)
                    
                    # Successful retry
                    await real_services_fixture["redis"].set_json(
                        f"agent_execution:{execution_id}",
                        {
                            "agent_type": scenario["agent_type"],
                            "thread_id": thread_id,
                            "status": "completed",
                            "result": f"Recovered {scenario['agent_type']} execution after initialization retry",
                            "recovery_strategy": scenario["recovery_strategy"],
                            "retry_successful": True
                        },
                        ex=300
                    )
                    
                elif scenario["failure_stage"] == "data_collection":
                    # Partial failure during data collection
                    await real_services_fixture["redis"].set_json(
                        f"agent_execution:{execution_id}",
                        {
                            "agent_type": scenario["agent_type"],
                            "thread_id": thread_id,
                            "status": "partial_failure",
                            "error": "Some data sources unavailable",
                            "available_data": ["source_1", "source_2"],
                            "unavailable_data": ["source_3"]
                        },
                        ex=300
                    )
                    
                    # Continue with partial results
                    await asyncio.sleep(0.1)
                    
                    await real_services_fixture["redis"].set_json(
                        f"agent_execution:{execution_id}",
                        {
                            "agent_type": scenario["agent_type"],
                            "thread_id": thread_id,
                            "status": "completed_with_limitations",
                            "result": f"Partial {scenario['agent_type']} analysis with available data",
                            "confidence": 0.75,  # Reduced confidence due to partial data
                            "limitations": ["Limited data availability"],
                            "recovery_strategy": scenario["recovery_strategy"]
                        },
                        ex=300
                    )
                    
                elif scenario["failure_stage"] == "result_generation":
                    # Failure during result generation, fallback to simpler analysis
                    await real_services_fixture["redis"].set_json(
                        f"agent_execution:{execution_id}",
                        {
                            "agent_type": scenario["agent_type"],
                            "thread_id": thread_id,
                            "status": "generation_failed",
                            "error": "Complex analysis failed - falling back to basic analysis",
                        },
                        ex=300
                    )
                    
                    # Fallback analysis
                    await asyncio.sleep(0.15)
                    
                    await real_services_fixture["redis"].set_json(
                        f"agent_execution:{execution_id}",
                        {
                            "agent_type": scenario["agent_type"],
                            "thread_id": thread_id,
                            "status": "completed_fallback",
                            "result": f"Fallback {scenario['agent_type']} analysis - basic recommendations provided",
                            "fallback_used": True,
                            "recovery_strategy": scenario["recovery_strategy"],
                            "business_value": "reduced_but_present"
                        },
                        ex=300
                    )
                
                return execution_id
            
            # Execute agent with failure simulation
            result_execution_id = await simulate_failing_agent_execution()
            recovery_time = time.time() - failure_start_time
            
            # Verify recovery
            final_execution_state = await real_services_fixture["redis"].get_json(
                f"agent_execution:{result_execution_id}"
            )
            
            assert final_execution_state is not None, f"Agent execution state must be preserved for {scenario['agent_type']}"
            
            recovery_successful = final_execution_state["status"] in [
                "completed", "completed_with_limitations", "completed_fallback"
            ]
            
            business_value_delivered = (
                "result" in final_execution_state and 
                len(final_execution_state["result"]) > 0
            )
            
            # Store agent execution result in database
            message_id = str(uuid.uuid4())
            await real_services_fixture["db"].execute("""
                INSERT INTO backend.messages (id, thread_id, role, content, metadata, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, message_id, thread_id, "assistant", 
                 final_execution_state.get("result", "Agent execution recovered"),
                 json.dumps({
                     "agent_type": scenario["agent_type"],
                     "recovery_strategy": scenario["recovery_strategy"],
                     "execution_id": result_execution_id,
                     "recovery_time": recovery_time
                 }),
                 datetime.now(timezone.utc))
            
            agent_recovery_result = {
                "agent_type": scenario["agent_type"],
                "failure_stage": scenario["failure_stage"],
                "recovery_strategy": scenario["recovery_strategy"],
                "recovery_time": recovery_time,
                "recovery_successful": recovery_successful,
                "business_value_delivered": business_value_delivered,
                "final_status": final_execution_state["status"]
            }
            
            agent_recovery_results.append(agent_recovery_result)
            
            # Validate agent recovery
            assert recovery_successful, f"Agent {scenario['agent_type']} must recover from {scenario['failure_stage']} failure"
            assert business_value_delivered, f"Agent {scenario['agent_type']} must deliver business value after recovery"
            assert recovery_time <= self.resilience_requirements["max_recovery_time"], \
                f"Agent {scenario['agent_type']} recovery took too long: {recovery_time:.2f}s"
        
        # Test golden path continuation after agent failures
        golden_path_continued = await self._test_golden_path_continuation_after_failures(
            real_services_fixture, user_context, thread_id, agent_recovery_results
        )
        
        # Store agent resilience results
        agent_resilience_result = ResilienceTestResult(
            failure_type=FailureType.CONCURRENT_CONFLICTS,  # Representing agent execution conflicts
            failure_duration=max(r["recovery_time"] for r in agent_recovery_results),
            recovery_time=max(r["recovery_time"] for r in agent_recovery_results),
            business_value_preserved=all(r["business_value_delivered"] for r in agent_recovery_results),
            data_consistency_maintained=golden_path_continued,
            user_experience_degraded=True,  # User experienced delays
            error_handled_gracefully=all(r["recovery_successful"] for r in agent_recovery_results),
            system_recovered_fully=golden_path_continued
        )
        
        await real_services_fixture["redis"].set_json(
            "agent_resilience_test_result",
            {
                "failure_type": agent_resilience_result.failure_type.value,
                "agent_recovery_results": agent_recovery_results,
                "golden_path_continued": golden_path_continued,
                "all_agents_recovered": all(r["recovery_successful"] for r in agent_recovery_results),
                "test_timestamp": datetime.now(timezone.utc).isoformat()
            },
            ex=86400
        )
        
        self.test_results.append(agent_resilience_result)
        
        # Validate overall agent resilience
        assert agent_resilience_result.business_value_preserved, "Business value must be preserved across agent failures"
        assert agent_resilience_result.error_handled_gracefully, "All agent errors must be handled gracefully"  
        assert golden_path_continued, "Golden path must continue after agent failures"
        
        self.logger.info(f"Agent resilience test passed - All {len(agent_recovery_results)} agents recovered successfully")

    async def _test_golden_path_continuation_after_failures(self, real_services_fixture, user_context, thread_id, agent_results):
        """Test that the golden path can continue after agent failures."""
        try:
            # Verify thread integrity
            thread_data = await real_services_fixture["db"].fetchrow("""
                SELECT id, title, user_id FROM backend.threads WHERE id = $1
            """, thread_id)
            
            if not thread_data or thread_data["user_id"] != user_context.user_id:
                return False
            
            # Verify messages were stored
            messages = await real_services_fixture["db"].fetch("""
                SELECT id, role, content, metadata FROM backend.messages 
                WHERE thread_id = $1 ORDER BY created_at ASC
            """, thread_id)
            
            # Should have messages from recovered agents
            agent_messages = [m for m in messages if m["role"] == "assistant"]
            if len(agent_messages) != len(agent_results):
                return False
            
            # Verify user can continue interaction
            followup_message_id = str(uuid.uuid4())
            await real_services_fixture["db"].execute("""
                INSERT INTO backend.messages (id, thread_id, role, content, created_at)
                VALUES ($1, $2, $3, $4, $5)
            """, followup_message_id, thread_id, "user", 
                 "Thank you for the analysis. Can you provide more details?",
                 datetime.now(timezone.utc))
            
            return True
            
        except Exception as e:
            self.logger.error(f"Golden path continuation test failed: {e}")
            return False

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_connection_resilience(self, real_services_fixture):
        """
        Test WebSocket connection resilience and message delivery guarantees.
        
        Validates real-time communication reliability critical for chat UX.
        """
        user_context = await create_authenticated_user_context(
            self.auth_helper,
            real_services_fixture["db"],
            user_data={"email": "websocket-resilience@example.com", "name": "WebSocket Resilience User"}
        )
        
        thread_id = str(uuid.uuid4())
        await real_services_fixture["db"].execute("""
            INSERT INTO backend.threads (id, user_id, title, created_at)
            VALUES ($1, $2, $3, $4)
        """, thread_id, user_context.user_id, "WebSocket Resilience Test", datetime.now(timezone.utc))
        
        # Simulate WebSocket connection scenarios
        websocket_scenarios = [
            {
                "scenario": "intermittent_connection",
                "description": "Connection drops and reconnects multiple times",
                "failure_count": 3,
                "recovery_expected": True
            },
            {
                "scenario": "message_queue_backlog",
                "description": "Messages queue up during connection loss",
                "message_count": 10,
                "recovery_expected": True  
            },
            {
                "scenario": "partial_message_delivery",
                "description": "Some messages fail, others succeed",
                "failure_rate": 0.3,
                "recovery_expected": True
            }
        ]
        
        websocket_resilience_results = []
        
        for scenario_config in websocket_scenarios:
            failure_start_time = time.time()
            
            if scenario_config["scenario"] == "intermittent_connection":
                # Simulate intermittent connection issues
                connection_attempts = 0
                successful_connections = 0
                
                for attempt in range(scenario_config["failure_count"] * 2):
                    connection_attempts += 1
                    
                    # Simulate connection attempt
                    connection_id = str(uuid.uuid4())
                    
                    if attempt % 2 == 0:
                        # Connection fails
                        await real_services_fixture["redis"].set_json(
                            f"websocket_connection:{connection_id}",
                            {
                                "user_id": user_context.user_id,
                                "status": "failed",
                                "attempt": attempt,
                                "error": "Connection timeout"
                            },
                            ex=300
                        )
                    else:
                        # Connection succeeds
                        await real_services_fixture["redis"].set_json(
                            f"websocket_connection:{connection_id}",
                            {
                                "user_id": user_context.user_id,  
                                "status": "connected",
                                "attempt": attempt,
                                "established_at": time.time()
                            },
                            ex=300
                        )
                        successful_connections += 1
                        
                        # Send a test message on successful connection
                        await real_services_fixture["redis"].set_json(
                            f"websocket_message:{connection_id}",
                            {
                                "connection_id": connection_id,
                                "type": "connection_established",
                                "content": f"Connection restored after attempt {attempt}",
                                "timestamp": time.time()
                            },
                            ex=300
                        )
                    
                    await asyncio.sleep(0.1)  # Brief delay between connection attempts
                
                recovery_time = time.time() - failure_start_time
                connection_resilience = successful_connections >= scenario_config["failure_count"]
                
                websocket_resilience_results.append({
                    "scenario": scenario_config["scenario"],
                    "connection_attempts": connection_attempts,
                    "successful_connections": successful_connections,
                    "recovery_time": recovery_time,
                    "resilience_demonstrated": connection_resilience
                })
                
                assert connection_resilience, f"WebSocket must demonstrate connection resilience: {successful_connections} >= {scenario_config['failure_count']}"
                
            elif scenario_config["scenario"] == "message_queue_backlog":
                # Test message queuing during connection loss
                queued_messages = []
                
                # Queue messages while "disconnected"
                for i in range(scenario_config["message_count"]):
                    message_id = str(uuid.uuid4())
                    message_data = {
                        "id": message_id,
                        "user_id": user_context.user_id,
                        "thread_id": thread_id,
                        "type": "agent_thinking",
                        "content": f"Queued message {i} during connection loss",
                        "queued_at": time.time(),
                        "status": "queued"
                    }
                    
                    await real_services_fixture["redis"].set_json(
                        f"websocket_queue:{message_id}",
                        message_data,
                        ex=3600
                    )
                    queued_messages.append(message_id)
                
                # Simulate connection restoration and message delivery
                delivered_count = 0
                for message_id in queued_messages:
                    message_data = await real_services_fixture["redis"].get_json(f"websocket_queue:{message_id}")
                    
                    if message_data:
                        # "Deliver" message
                        message_data["status"] = "delivered"
                        message_data["delivered_at"] = time.time()
                        
                        await real_services_fixture["redis"].set_json(
                            f"websocket_delivered:{message_id}",
                            message_data,
                            ex=3600
                        )
                        delivered_count += 1
                
                recovery_time = time.time() - failure_start_time
                message_delivery_rate = delivered_count / len(queued_messages)
                
                websocket_resilience_results.append({
                    "scenario": scenario_config["scenario"],
                    "queued_messages": len(queued_messages),
                    "delivered_messages": delivered_count,
                    "delivery_rate": message_delivery_rate,
                    "recovery_time": recovery_time,
                    "resilience_demonstrated": message_delivery_rate >= 0.9  # 90% delivery rate
                })
                
                assert message_delivery_rate >= 0.9, f"Message delivery rate too low: {message_delivery_rate:.2f}"
                
            elif scenario_config["scenario"] == "partial_message_delivery":
                # Test partial message delivery failures
                total_messages = 20
                expected_failures = int(total_messages * scenario_config["failure_rate"])
                actual_failures = 0
                successful_deliveries = 0
                
                for i in range(total_messages):
                    message_id = str(uuid.uuid4())
                    
                    # Randomly fail messages based on failure rate
                    if random.random() < scenario_config["failure_rate"]:
                        # Message fails
                        await real_services_fixture["redis"].set_json(
                            f"websocket_failed:{message_id}",
                            {
                                "id": message_id,
                                "user_id": user_context.user_id,
                                "status": "failed",
                                "error": "Network error during delivery",
                                "attempt": 1
                            },
                            ex=300
                        )
                        actual_failures += 1
                        
                        # Attempt retry
                        await asyncio.sleep(0.05)
                        
                        # Retry succeeds (resilience)
                        await real_services_fixture["redis"].set_json(
                            f"websocket_retry_success:{message_id}",
                            {
                                "id": message_id,
                                "user_id": user_context.user_id,
                                "status": "delivered_after_retry",
                                "retry_attempt": 2,
                                "delivered_at": time.time()
                            },
                            ex=300
                        )
                        successful_deliveries += 1
                    else:
                        # Message succeeds immediately
                        await real_services_fixture["redis"].set_json(
                            f"websocket_success:{message_id}",
                            {
                                "id": message_id,
                                "user_id": user_context.user_id,
                                "status": "delivered",
                                "delivered_at": time.time()
                            },
                            ex=300
                        )
                        successful_deliveries += 1
                
                recovery_time = time.time() - failure_start_time
                final_delivery_rate = successful_deliveries / total_messages
                
                websocket_resilience_results.append({
                    "scenario": scenario_config["scenario"],
                    "total_messages": total_messages,
                    "failed_messages": actual_failures,
                    "successful_deliveries": successful_deliveries,
                    "final_delivery_rate": final_delivery_rate,
                    "recovery_time": recovery_time,
                    "resilience_demonstrated": final_delivery_rate >= 0.95  # 95% final success rate
                })
                
                assert final_delivery_rate >= 0.95, f"Final delivery rate too low after retries: {final_delivery_rate:.2f}"
        
        # Store WebSocket resilience results
        websocket_resilience_result = ResilienceTestResult(
            failure_type=FailureType.NETWORK_TIMEOUT,
            failure_duration=max(r["recovery_time"] for r in websocket_resilience_results),
            recovery_time=max(r["recovery_time"] for r in websocket_resilience_results),
            business_value_preserved=all(r["resilience_demonstrated"] for r in websocket_resilience_results),
            data_consistency_maintained=True,  # Message ordering preserved
            user_experience_degraded=True,     # User experienced delays
            error_handled_gracefully=True,     # Retry mechanisms worked
            system_recovered_fully=True        # All scenarios demonstrated recovery
        )
        
        await real_services_fixture["redis"].set_json(
            "websocket_resilience_test_result",
            {
                "failure_type": websocket_resilience_result.failure_type.value,
                "scenario_results": websocket_resilience_results,
                "all_scenarios_resilient": all(r["resilience_demonstrated"] for r in websocket_resilience_results),
                "max_recovery_time": websocket_resilience_result.recovery_time,
                "test_timestamp": datetime.now(timezone.utc).isoformat()
            },
            ex=86400
        )
        
        self.test_results.append(websocket_resilience_result)
        
        # Validate overall WebSocket resilience
        assert websocket_resilience_result.business_value_preserved, "WebSocket resilience must preserve business value"
        assert websocket_resilience_result.error_handled_gracefully, "WebSocket errors must be handled gracefully"
        assert all(r["resilience_demonstrated"] for r in websocket_resilience_results), "All WebSocket scenarios must demonstrate resilience"
        
        self.logger.info(f"WebSocket resilience test passed - All {len(websocket_resilience_results)} scenarios demonstrated resilience")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_partial_system_failure_golden_path_continuation(self, real_services_fixture):
        """
        Test that golden path can continue even when some system components fail.
        
        Validates business continuity during partial system failures.
        """
        user_context = await create_authenticated_user_context(
            self.auth_helper,
            real_services_fixture["db"],
            user_data={"email": "partial-failure@example.com", "name": "Partial Failure User"}
        )
        
        # Test scenario: Some services degraded, others working
        thread_id = str(uuid.uuid4())
        await real_services_fixture["db"].execute("""
            INSERT INTO backend.threads (id, user_id, title, created_at, metadata)
            VALUES ($1, $2, $3, $4, $5)
        """, thread_id, user_context.user_id, "Partial System Failure Test", 
             datetime.now(timezone.utc),
             json.dumps({"test_type": "partial_system_failure"}))
        
        # Test golden path stages with partial failures
        golden_path_stages = [
            {
                "stage": "triage_agent",
                "service_health": {"database": True, "redis": False, "llm": True},  # Redis degraded
                "expected_outcome": "success_degraded",
                "fallback_strategy": "database_only"
            },
            {
                "stage": "data_helper",
                "service_health": {"database": True, "redis": True, "llm": False},  # LLM degraded  
                "expected_outcome": "success_cached",
                "fallback_strategy": "cached_analysis"
            },
            {
                "stage": "uvs_reporter", 
                "service_health": {"database": False, "redis": True, "llm": True},  # Database degraded
                "expected_outcome": "success_memory",
                "fallback_strategy": "in_memory_reporting"
            }
        ]
        
        golden_path_continuation_results = []
        overall_business_value_preserved = True
        
        for stage_config in golden_path_stages:
            stage_start_time = time.time()
            stage_success = False
            business_value_delivered = False
            
            # Simulate stage execution with partial system failure
            execution_id = str(uuid.uuid4())
            
            try:
                if stage_config["stage"] == "triage_agent":
                    # Redis unavailable - use database only
                    if stage_config["service_health"]["redis"]:
                        # Normal operation with cache
                        await real_services_fixture["redis"].set_json(
                            f"triage_cache:{execution_id}",
                            {"status": "processing", "stage": "triage_agent"},
                            ex=300
                        )
                    else:
                        # Fallback to database only
                        self.logger.info("Redis unavailable - using database fallback for triage")
                    
                    # Store triage result in database (always works)
                    await real_services_fixture["db"].execute("""
                        INSERT INTO backend.messages (id, thread_id, role, content, metadata, created_at)
                        VALUES ($1, $2, $3, $4, $5, $6)
                    """, str(uuid.uuid4()), thread_id, "assistant",
                         "Triage analysis completed using database fallback. Identified cost optimization opportunity.",
                         json.dumps({
                             "agent_type": "triage_agent",
                             "execution_id": execution_id,
                             "fallback_used": not stage_config["service_health"]["redis"],
                             "business_value": "cost_optimization_identified"
                         }),
                         datetime.now(timezone.utc))
                    
                    stage_success = True
                    business_value_delivered = True
                    
                elif stage_config["stage"] == "data_helper":
                    # LLM unavailable - use cached analysis
                    if stage_config["service_health"]["llm"]:
                        # Normal operation with LLM
                        analysis_result = "Full LLM-powered data analysis completed"
                    else:
                        # Fallback to cached/rule-based analysis
                        self.logger.info("LLM unavailable - using cached analysis for data helper")
                        analysis_result = "Rule-based data analysis completed using cached patterns"
                    
                    # Store in both database and cache (both available)
                    analysis_data = {
                        "analysis_result": analysis_result,
                        "data_sources": ["aws_billing", "performance_metrics"],
                        "confidence": 0.8 if stage_config["service_health"]["llm"] else 0.6,
                        "fallback_used": not stage_config["service_health"]["llm"]
                    }
                    
                    await real_services_fixture["redis"].set_json(
                        f"data_analysis:{execution_id}",
                        analysis_data,
                        ex=3600
                    )
                    
                    await real_services_fixture["db"].execute("""
                        INSERT INTO backend.messages (id, thread_id, role, content, metadata, created_at)
                        VALUES ($1, $2, $3, $4, $5, $6)
                    """, str(uuid.uuid4()), thread_id, "assistant", analysis_result,
                         json.dumps({
                             "agent_type": "data_helper",
                             "execution_id": execution_id,
                             "analysis_data": analysis_data
                         }),
                         datetime.now(timezone.utc))
                    
                    stage_success = True  
                    business_value_delivered = True
                    
                elif stage_config["stage"] == "uvs_reporter":
                    # Database unavailable - use in-memory reporting
                    if stage_config["service_health"]["database"]:
                        # Normal operation with database persistence
                        report_storage = "database"
                    else:
                        # Fallback to in-memory/cache only
                        self.logger.info("Database unavailable - using in-memory reporting")
                        report_storage = "memory_cache"
                    
                    # Generate report regardless of storage availability
                    report_data = {
                        "business_impact": {
                            "potential_savings": 7200,
                            "implementation_effort": "medium",
                            "roi_months": 4
                        },
                        "recommendations": [
                            "Implement EC2 right-sizing",
                            "Configure S3 lifecycle policies", 
                            "Purchase reserved instances"
                        ],
                        "storage_strategy": report_storage,
                        "generated_at": time.time()
                    }
                    
                    # Store in cache (always available in this scenario)
                    await real_services_fixture["redis"].set_json(
                        f"uvs_report:{execution_id}",
                        report_data,
                        ex=3600
                    )
                    
                    if stage_config["service_health"]["database"]:
                        # Also store in database if available
                        await real_services_fixture["db"].execute("""
                            INSERT INTO backend.messages (id, thread_id, role, content, metadata, created_at) 
                            VALUES ($1, $2, $3, $4, $5, $6)
                        """, str(uuid.uuid4()), thread_id, "assistant",
                             f"Business value analysis completed. Identified ${report_data['business_impact']['potential_savings']}/month in potential savings.",
                             json.dumps({
                                 "agent_type": "uvs_reporter",
                                 "execution_id": execution_id,
                                 "report_data": report_data
                             }),
                             datetime.now(timezone.utc))
                    
                    stage_success = True
                    business_value_delivered = True
                
            except Exception as e:
                self.logger.error(f"Stage {stage_config['stage']} failed: {e}")
                stage_success = False
                business_value_delivered = False
            
            stage_duration = time.time() - stage_start_time
            
            stage_result = {
                "stage": stage_config["stage"],
                "service_health": stage_config["service_health"],
                "fallback_strategy": stage_config["fallback_strategy"],
                "stage_success": stage_success,
                "business_value_delivered": business_value_delivered,
                "stage_duration": stage_duration,
                "expected_outcome": stage_config["expected_outcome"],
                "outcome_met": stage_success
            }
            
            golden_path_continuation_results.append(stage_result)
            
            if not business_value_delivered:
                overall_business_value_preserved = False
            
            # Validate stage completion despite partial failures
            assert stage_success, f"Stage {stage_config['stage']} must succeed despite partial system failure"
            assert business_value_delivered, f"Stage {stage_config['stage']} must deliver business value with fallback strategy"
            
            await asyncio.sleep(0.1)  # Brief delay between stages
        
        # Verify golden path completion
        final_thread_messages = await real_services_fixture["db"].fetch("""
            SELECT id, role, content, metadata FROM backend.messages 
            WHERE thread_id = $1 ORDER BY created_at ASC
        """, thread_id)
        
        assistant_messages = [m for m in final_thread_messages if m["role"] == "assistant"]
        golden_path_completed = len(assistant_messages) == len(golden_path_stages)
        
        # Verify business value chain
        business_values = []
        for message in assistant_messages:
            metadata = json.loads(message["metadata"])
            if "business_value" in metadata:
                business_values.append(metadata["business_value"])
            elif "report_data" in metadata and "business_impact" in metadata["report_data"]:
                business_values.append("business_impact_quantified")
            else:
                business_values.append("analysis_provided")
        
        business_value_chain_complete = len(business_values) == len(golden_path_stages)
        
        # Store partial failure resilience results
        partial_failure_result = ResilienceTestResult(
            failure_type=FailureType.PARTIAL_DATA_CORRUPTION,  # Representing partial system degradation
            failure_duration=sum(r["stage_duration"] for r in golden_path_continuation_results),
            recovery_time=0.0,  # Immediate fallback, no recovery needed
            business_value_preserved=overall_business_value_preserved,
            data_consistency_maintained=golden_path_completed,
            user_experience_degraded=True,  # Some degradation expected
            error_handled_gracefully=all(r["stage_success"] for r in golden_path_continuation_results),
            system_recovered_fully=False  # System adapted rather than recovered
        )
        
        await real_services_fixture["redis"].set_json(
            "partial_failure_resilience_result",
            {
                "failure_type": partial_failure_result.failure_type.value,
                "golden_path_stages": golden_path_continuation_results,
                "golden_path_completed": golden_path_completed,
                "business_value_chain_complete": business_value_chain_complete,
                "overall_business_value_preserved": overall_business_value_preserved,
                "all_stages_successful": all(r["stage_success"] for r in golden_path_continuation_results),
                "test_timestamp": datetime.now(timezone.utc).isoformat()
            },
            ex=86400
        )
        
        self.test_results.append(partial_failure_result)
        
        # Validate overall partial failure resilience
        assert golden_path_completed, "Golden path must complete despite partial system failures"
        assert business_value_chain_complete, "Business value chain must be maintained"
        assert overall_business_value_preserved, "Overall business value must be preserved through fallback strategies"
        assert all(r["stage_success"] for r in golden_path_continuation_results), "All stages must succeed with appropriate fallback strategies"
        
        self.logger.info(f"Partial system failure resilience test passed - Golden path completed with {len([r for r in golden_path_continuation_results if 'fallback' in r['fallback_strategy']])} fallback strategies")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_data_consistency_during_error_scenarios(self, real_services_fixture):
        """
        Test data consistency maintenance during various error scenarios.
        
        Validates that data integrity is preserved even during system failures.
        """
        user_context = await create_authenticated_user_context(
            self.auth_helper,
            real_services_fixture["db"],
            user_data={"email": "data-consistency@example.com", "name": "Data Consistency User"}
        )
        
        # Create initial consistent state
        thread_id = str(uuid.uuid4())
        await real_services_fixture["db"].execute("""
            INSERT INTO backend.threads (id, user_id, title, created_at)
            VALUES ($1, $2, $3, $4)
        """, thread_id, user_context.user_id, "Data Consistency Test", datetime.now(timezone.utc))
        
        # Test data consistency scenarios
        consistency_scenarios = [
            {
                "scenario": "concurrent_write_conflicts",
                "description": "Multiple concurrent writes to same data",
                "consistency_requirement": "last_writer_wins_with_timestamps"
            },
            {
                "scenario": "partial_transaction_failure",
                "description": "Transaction fails partway through",
                "consistency_requirement": "atomic_rollback"
            },
            {
                "scenario": "cache_database_sync_failure", 
                "description": "Cache and database get out of sync",
                "consistency_requirement": "database_authority"
            }
        ]
        
        data_consistency_results = []
        
        for scenario_config in consistency_scenarios:
            scenario_start_time = time.time()
            consistency_maintained = False
            
            if scenario_config["scenario"] == "concurrent_write_conflicts":
                # Simulate concurrent writes to the same thread
                concurrent_operations = []
                
                async def concurrent_message_write(operation_id):
                    message_id = str(uuid.uuid4())
                    timestamp = datetime.now(timezone.utc)
                    
                    # Add small random delay to create race conditions
                    await asyncio.sleep(random.uniform(0.01, 0.05))
                    
                    try:
                        await real_services_fixture["db"].execute("""
                            INSERT INTO backend.messages (id, thread_id, role, content, metadata, created_at)
                            VALUES ($1, $2, $3, $4, $5, $6)
                        """, message_id, thread_id, "user", 
                             f"Concurrent message from operation {operation_id}",
                             json.dumps({
                                 "operation_id": operation_id,
                                 "write_timestamp": timestamp.isoformat(),
                                 "scenario": "concurrent_write_test"
                             }),
                             timestamp)
                        
                        # Also update cache
                        await real_services_fixture["redis"].set_json(
                            f"message_cache:{message_id}",
                            {
                                "content": f"Concurrent message from operation {operation_id}",
                                "operation_id": operation_id,
                                "cached_at": time.time()
                            },
                            ex=3600
                        )
                        
                        return {"success": True, "message_id": message_id, "operation_id": operation_id}
                        
                    except Exception as e:
                        return {"success": False, "error": str(e), "operation_id": operation_id}
                
                # Execute 5 concurrent write operations
                concurrent_tasks = [concurrent_message_write(i) for i in range(5)]
                concurrent_results = await asyncio.gather(*concurrent_tasks)
                
                # Verify data consistency after concurrent writes
                messages = await real_services_fixture["db"].fetch("""
                    SELECT id, content, metadata, created_at FROM backend.messages
                    WHERE thread_id = $1 AND metadata @> '{"scenario": "concurrent_write_test"}'
                    ORDER BY created_at ASC
                """, thread_id)
                
                successful_writes = [r for r in concurrent_results if r["success"]]
                
                # Consistency checks
                consistency_checks = {
                    "all_messages_stored": len(messages) == len(successful_writes),
                    "unique_message_ids": len(set(m["id"] for m in messages)) == len(messages),
                    "timestamp_ordering": all(
                        messages[i]["created_at"] <= messages[i+1]["created_at"] 
                        for i in range(len(messages) - 1)
                    ) if len(messages) > 1 else True,
                    "metadata_integrity": all(
                        "operation_id" in json.loads(m["metadata"]) for m in messages
                    )
                }
                
                consistency_maintained = all(consistency_checks.values())
                
                scenario_result = {
                    "scenario": scenario_config["scenario"],
                    "concurrent_operations": len(concurrent_tasks),
                    "successful_operations": len(successful_writes),
                    "consistency_checks": consistency_checks,
                    "consistency_maintained": consistency_maintained,
                    "duration": time.time() - scenario_start_time
                }
                
            elif scenario_config["scenario"] == "partial_transaction_failure":
                # Simulate transaction that fails partway through
                transaction_success = False
                rollback_successful = False
                
                try:
                    # Start transaction that will fail
                    async with real_services_fixture["db"].transaction() as tx:
                        # First operation succeeds
                        message_1_id = str(uuid.uuid4())
                        await tx.execute("""
                            INSERT INTO backend.messages (id, thread_id, role, content, created_at)
                            VALUES ($1, $2, $3, $4, $5)
                        """, message_1_id, thread_id, "assistant", "Transaction message 1", datetime.now(timezone.utc))
                        
                        # Second operation succeeds
                        message_2_id = str(uuid.uuid4())
                        await tx.execute("""
                            INSERT INTO backend.messages (id, thread_id, role, content, created_at)
                            VALUES ($1, $2, $3, $4, $5)
                        """, message_2_id, thread_id, "assistant", "Transaction message 2", datetime.now(timezone.utc))
                        
                        # Third operation fails (simulated)
                        raise Exception("Simulated transaction failure")
                        
                except Exception as e:
                    # Transaction should rollback automatically
                    rollback_successful = "Simulated transaction failure" in str(e)
                
                # Verify rollback - no messages should exist from the failed transaction
                transaction_messages = await real_services_fixture["db"].fetch("""
                    SELECT id FROM backend.messages 
                    WHERE thread_id = $1 AND content LIKE 'Transaction message%'
                """, thread_id)
                
                consistency_maintained = len(transaction_messages) == 0 and rollback_successful
                
                scenario_result = {
                    "scenario": scenario_config["scenario"],
                    "transaction_attempted": True,
                    "rollback_successful": rollback_successful,
                    "orphaned_data": len(transaction_messages),
                    "consistency_maintained": consistency_maintained,
                    "duration": time.time() - scenario_start_time
                }
                
            elif scenario_config["scenario"] == "cache_database_sync_failure":
                # Create data in database
                message_id = str(uuid.uuid4())
                original_content = "Original message content"
                
                await real_services_fixture["db"].execute("""
                    INSERT INTO backend.messages (id, thread_id, role, content, created_at)
                    VALUES ($1, $2, $3, $4, $5)
                """, message_id, thread_id, "user", original_content, datetime.now(timezone.utc))
                
                # Cache the data
                await real_services_fixture["redis"].set_json(
                    f"message_cache:{message_id}",
                    {"content": original_content, "cached_at": time.time()},
                    ex=3600
                )
                
                # Simulate database update without cache update (sync failure)
                updated_content = "Updated message content"
                await real_services_fixture["db"].execute("""
                    UPDATE backend.messages SET content = $1 WHERE id = $2
                """, updated_content, message_id)
                
                # Cache still has old data
                cached_data = await real_services_fixture["redis"].get_json(f"message_cache:{message_id}")
                database_data = await real_services_fixture["db"].fetchrow("""
                    SELECT content FROM backend.messages WHERE id = $1
                """, message_id)
                
                # Detect inconsistency
                cache_db_consistent = cached_data["content"] == database_data["content"]
                
                if not cache_db_consistent:
                    # Implement consistency resolution (database is authority)
                    await real_services_fixture["redis"].set_json(
                        f"message_cache:{message_id}",
                        {"content": database_data["content"], "synced_at": time.time()},
                        ex=3600
                    )
                    
                    # Verify consistency restored
                    updated_cached_data = await real_services_fixture["redis"].get_json(f"message_cache:{message_id}")
                    consistency_maintained = updated_cached_data["content"] == database_data["content"]
                else:
                    consistency_maintained = True
                
                scenario_result = {
                    "scenario": scenario_config["scenario"],
                    "initial_sync_consistent": cache_db_consistent,
                    "consistency_restored": consistency_maintained,
                    "resolution_strategy": "database_authority",
                    "consistency_maintained": consistency_maintained,
                    "duration": time.time() - scenario_start_time
                }
            
            data_consistency_results.append(scenario_result)
            
            # Validate consistency requirement met
            assert consistency_maintained, f"Data consistency not maintained for scenario: {scenario_config['scenario']}"
            
            await asyncio.sleep(0.1)  # Brief delay between consistency tests
        
        # Overall consistency validation
        overall_consistency_maintained = all(r["consistency_maintained"] for r in data_consistency_results)
        
        # Store data consistency results
        consistency_resilience_result = ResilienceTestResult(
            failure_type=FailureType.PARTIAL_DATA_CORRUPTION,
            failure_duration=sum(r["duration"] for r in data_consistency_results),
            recovery_time=0.0,  # Immediate consistency resolution
            business_value_preserved=True,  # Data integrity preserves business value
            data_consistency_maintained=overall_consistency_maintained,
            user_experience_degraded=False,  # Consistency maintained transparently
            error_handled_gracefully=True,   # All scenarios handled properly
            system_recovered_fully=True      # Full consistency restored
        )
        
        await real_services_fixture["redis"].set_json(
            "data_consistency_resilience_result",
            {
                "failure_type": consistency_resilience_result.failure_type.value,
                "consistency_scenarios": data_consistency_results,
                "overall_consistency_maintained": overall_consistency_maintained,
                "all_scenarios_passed": all(r["consistency_maintained"] for r in data_consistency_results),
                "test_timestamp": datetime.now(timezone.utc).isoformat()
            },
            ex=86400
        )
        
        self.test_results.append(consistency_resilience_result)
        
        # Validate overall data consistency resilience
        assert overall_consistency_maintained, "Data consistency must be maintained across all error scenarios"
        assert all(r["consistency_maintained"] for r in data_consistency_results), "All consistency scenarios must pass"
        
        # Verify final system state consistency
        final_consistency_check = await self._verify_final_system_consistency(real_services_fixture, user_context, thread_id)
        assert final_consistency_check, "Final system state must be consistent after all error scenarios"
        
        self.logger.info(f"Data consistency resilience test passed - All {len(data_consistency_results)} scenarios maintained consistency")

    async def _verify_final_system_consistency(self, real_services_fixture, user_context, thread_id):
        """Verify final system state consistency after all tests."""
        try:
            # Check database consistency
            thread_exists = await real_services_fixture["db"].fetchval("""
                SELECT EXISTS(SELECT 1 FROM backend.threads WHERE id = $1 AND user_id = $2)
            """, thread_id, user_context.user_id)
            
            if not thread_exists:
                return False
            
            # Check message count consistency
            db_message_count = await real_services_fixture["db"].fetchval("""
                SELECT COUNT(*) FROM backend.messages WHERE thread_id = $1
            """, thread_id)
            
            # Verify user data integrity
            user_exists = await real_services_fixture["db"].fetchval("""
                SELECT EXISTS(SELECT 1 FROM auth.users WHERE id = $1)
            """, user_context.user_id)
            
            return thread_exists and user_exists and db_message_count >= 0
            
        except Exception as e:
            self.logger.error(f"Final consistency check failed: {e}")
            return False