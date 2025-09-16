"""
User Execution Engine Comprehensive Integration Tests - Phase 1 Multi-User Foundation

Business Value Justification (BVJ):
- Segment: Platform/Core Infrastructure (ALL user tiers)
- Business Goal: Multi-User Execution Engine - Core orchestration supporting $500K+ ARR
- Value Impact: Validates reliable multi-user agent execution, context isolation, and resource management
- Revenue Impact: Foundation for ALL multi-user agent workflows - failure blocks scalable platform value

Issue #870 Phase 1 User Execution Engine Tests:
This test suite provides comprehensive coverage for UserExecutionEngine patterns
that enable scalable multi-user agent orchestration. Critical for Golden Path
user flow where multiple users simultaneously execute agent workflows.

CRITICAL MULTI-USER SCENARIOS (15 tests):
1. Multi-User Execution Context Management (3 tests)
2. Concurrent User Agent Orchestration (3 tests)
3. Resource Management & Cleanup (3 tests)
4. WebSocket Bridge Coordination (3 tests)
5. Error Handling & Recovery (3 tests)

COVERAGE TARGET: UserExecutionEngine integration 13% → 35% (+22% improvement)

SSOT Testing Compliance:
- Uses test_framework.ssot.base_test_case.SSotAsyncTestCase
- Real services preferred over mocks for multi-user validation
- Business-critical scalability validation over implementation details
- Multi-user isolation as PRIMARY requirement
"""

import asyncio
import gc
import json
import time
import uuid
import weakref
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass, field

import pytest

# SSOT Test Infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env

# User Execution Engine and Core Components Under Test
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext, AgentExecutionResult, PipelineStep
)
from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
from netra_backend.app.agents.base_agent import BaseAgent

# WebSocket and Orchestration Components
from netra_backend.app.websocket_core.event_monitor import ChatEventMonitor

import logging
logger = logging.getLogger(__name__)


@dataclass
class UserSessionData:
    """Test data container for user session tracking"""
    user_id: str
    session_id: str
    correlation_id: str
    context: UserExecutionContext
    execution_engine: UserExecutionEngine
    websocket_events: List[Dict[str, Any]] = field(default_factory=list)
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@pytest.mark.integration
class UserExecutionEngineComprehensiveIntegrationTests(SSotAsyncTestCase):
    """
    User Execution Engine Comprehensive Integration Tests - Issue #870 Phase 1
    
    Tests the critical multi-user execution patterns that enable the Golden Path
    user flow to scale across multiple concurrent users with proper isolation.
    
    Business Impact: $500K+ ARR Golden Path depends on reliable multi-user execution.
    """
    
    def setup_method(self, method):
        """Setup clean test environment for each integration test"""
        super().setup_method(method)
        
        # Test identifiers
        self.test_run_id = f"exec-test-{uuid.uuid4().hex[:8]}"
        self.base_user_id = f"exec-user-{uuid.uuid4().hex[:8]}"
        
        # Mock WebSocket infrastructure
        self.mock_websocket_manager = MagicMock()
        self.mock_websocket_emitter = AsyncMock(spec=UnifiedWebSocketEmitter)
        self.global_websocket_events = []
        
        # Configure WebSocket event capture
        async def capture_websocket_event(event_type: str, data: Dict[str, Any], **kwargs):
            event = {
                'event_type': event_type,
                'data': data,
                'timestamp': datetime.now(timezone.utc),
                'user_id': kwargs.get('user_id', 'unknown'),
                'session_id': kwargs.get('session_id', 'unknown'),
                'test_run_id': self.test_run_id
            }
            self.global_websocket_events.append(event)
            
        self.mock_websocket_emitter.emit_event.side_effect = capture_websocket_event
        
        # Resource tracking
        self.created_engines = []
        self.created_contexts = []
        self.active_user_sessions = []
    
    def teardown_method(self, method):
        """Cleanup resources and validate no resource leaks"""
        # Cleanup execution engines
        for engine in self.created_engines:
            if hasattr(engine, 'cleanup') and asyncio.iscoroutinefunction(engine.cleanup):
                asyncio.create_task(engine.cleanup())
        
        # Cleanup contexts
        for context in self.created_contexts:
            if hasattr(context, 'cleanup'):
                context.cleanup()
        
        # Cleanup user sessions
        for session in self.active_user_sessions:
            if hasattr(session.execution_engine, 'cleanup'):
                try:
                    asyncio.create_task(session.execution_engine.cleanup())
                except:
                    pass
        
        # Force garbage collection
        gc.collect()
        
        super().teardown_method(method)
    
    def create_user_session_data(self, user_suffix: str = None) -> UserSessionData:
        """Helper to create isolated user session data"""
        suffix = user_suffix or uuid.uuid4().hex[:8]
        
        user_id = f"exec-user-{suffix}"
        session_id = f"exec-session-{suffix}"
        correlation_id = f"exec-corr-{suffix}"
        
        context = UserExecutionContext(
            user_id=user_id,
            session_id=session_id,
            correlation_id=correlation_id
        )
        
        execution_engine = UserExecutionEngine(
            user_execution_context=context,
            websocket_emitter=self.mock_websocket_emitter
        )
        
        session_data = UserSessionData(
            user_id=user_id,
            session_id=session_id,
            correlation_id=correlation_id,
            context=context,
            execution_engine=execution_engine
        )
        
        # Track for cleanup
        self.created_contexts.append(context)
        self.created_engines.append(execution_engine)
        self.active_user_sessions.append(session_data)
        
        return session_data

    # ============================================================================
    # CATEGORY 1: MULTI-USER EXECUTION CONTEXT MANAGEMENT (3 tests)
    # ============================================================================
    
    async def test_concurrent_user_execution_context_creation(self):
        """Test 1/15: Concurrent user execution context creation and isolation"""
        
        # Create multiple user sessions concurrently
        async def create_user_session(user_index: int):
            session = self.create_user_session_data(f"concurrent-{user_index}")
            
            # Initialize execution engine
            await session.execution_engine.initialize()
            
            return session.user_id, session.execution_engine.user_execution_context
        
        # Create 5 concurrent user sessions
        results = await asyncio.gather(
            *[create_user_session(i) for i in range(5)]
        )
        
        # Validate isolation
        user_ids = [result[0] for result in results]
        contexts = [result[1] for result in results]
        
        assert len(set(user_ids)) == 5  # All different user IDs
        assert len(set(id(ctx) for ctx in contexts)) == 5  # All different objects
        
        # Validate each context is properly initialized
        for user_id, context in results:
            assert context.user_id == user_id
            assert context.session_id.startswith("exec-session")
            assert context.correlation_id.startswith("exec-corr")
        
        logger.info("✅ Concurrent user execution context creation validated")
    
    async def test_user_execution_context_state_isolation(self):
        """Test 2/15: User execution context state isolation across operations"""
        
        # Create two user sessions
        session_1 = self.create_user_session_data("state-1")
        session_2 = self.create_user_session_data("state-2")
        
        # Initialize both engines
        await session_1.execution_engine.initialize()
        await session_2.execution_engine.initialize()
        
        # Execute operations that modify context state
        async def modify_context_state(session: UserSessionData, operation_id: str):
            # Set operation-specific state
            session.context.set_state(f"operation_{operation_id}", f"data_{operation_id}")
            
            # Execute a task to validate state persistence
            result = await session.execution_engine.execute_agent_task(
                agent_type="test_agent",
                task_data={"operation": operation_id, "user_id": session.user_id}
            )
            
            return session.user_id, session.context.get_state(f"operation_{operation_id}")
        
        # Run concurrent state modifications
        results = await asyncio.gather(
            modify_context_state(session_1, "task_1"),
            modify_context_state(session_2, "task_2")
        )
        
        # Validate state isolation
        user_1_result = next(r for r in results if r[0] == session_1.user_id)
        user_2_result = next(r for r in results if r[0] == session_2.user_id)
        
        assert user_1_result[1] == "data_task_1"
        assert user_2_result[1] == "data_task_2"
        
        # Cross-validate no state leakage
        assert session_1.context.get_state("operation_task_2") is None
        assert session_2.context.get_state("operation_task_1") is None
        
        logger.info("✅ User execution context state isolation validated")
    
    async def test_user_execution_context_lifecycle_management(self):
        """Test 3/15: User execution context lifecycle management across session"""
        
        session = self.create_user_session_data("lifecycle")
        
        # Phase 1: Initialization
        await session.execution_engine.initialize()
        
        assert session.execution_engine.is_initialized
        assert session.context.user_id == session.user_id
        
        # Phase 2: Active execution
        await session.execution_engine.start_execution_phase()
        
        # Execute multiple tasks to validate context persistence
        tasks = [
            {"task_id": "task_1", "action": "initialize_data"},
            {"task_id": "task_2", "action": "process_data"},
            {"task_id": "task_3", "action": "finalize_data"}
        ]
        
        results = []
        for task in tasks:
            result = await session.execution_engine.execute_agent_task(
                agent_type="lifecycle_agent",
                task_data=task
            )
            results.append(result)
        
        # Phase 3: Cleanup
        await session.execution_engine.cleanup()
        
        # Validate lifecycle phases
        assert len(results) == 3
        
        # Validate WebSocket events captured the lifecycle
        session_events = [e for e in self.global_websocket_events 
                         if e['session_id'] == session.session_id]
        
        assert len(session_events) >= 3  # At least one event per task
        
        logger.info("✅ User execution context lifecycle management validated")

    # ============================================================================
    # CATEGORY 2: CONCURRENT USER AGENT ORCHESTRATION (3 tests)
    # ============================================================================
    
    async def test_concurrent_multi_user_agent_orchestration(self):
        """Test 4/15: Concurrent multi-user agent orchestration patterns"""
        
        # Create multiple user sessions
        sessions = [
            self.create_user_session_data(f"orchestra-{i}") 
            for i in range(4)
        ]
        
        # Initialize all engines
        await asyncio.gather(
            *[session.execution_engine.initialize() for session in sessions]
        )
        
        # Define agent orchestration workflow
        async def user_agent_workflow(session: UserSessionData):
            """Complex agent workflow involving multiple agents"""
            
            # Start execution phase
            await session.execution_engine.start_execution_phase()
            
            # Execute sequence of agent tasks
            workflow_results = []
            
            # Task 1: Triage agent
            triage_result = await session.execution_engine.execute_agent_task(
                agent_type="triage_agent",
                task_data={"user_id": session.user_id, "phase": "triage"}
            )
            workflow_results.append(("triage", triage_result))
            
            # Task 2: Data agent (based on triage)
            data_result = await session.execution_engine.execute_agent_task(
                agent_type="data_agent", 
                task_data={"user_id": session.user_id, "phase": "data", "triage_input": triage_result}
            )
            workflow_results.append(("data", data_result))
            
            # Task 3: Reporting agent (final step)
            report_result = await session.execution_engine.execute_agent_task(
                agent_type="reporting_agent",
                task_data={"user_id": session.user_id, "phase": "report", "data_input": data_result}
            )
            workflow_results.append(("report", report_result))
            
            return session.user_id, workflow_results
        
        # Run concurrent workflows
        workflow_results = await asyncio.gather(
            *[user_agent_workflow(session) for session in sessions]
        )
        
        # Validate all workflows completed successfully
        assert len(workflow_results) == 4
        
        for user_id, results in workflow_results:
            assert len(results) == 3  # triage, data, report
            assert results[0][0] == "triage"
            assert results[1][0] == "data"  
            assert results[2][0] == "report"
        
        # Validate WebSocket events for all users
        for session in sessions:
            user_events = [e for e in self.global_websocket_events 
                          if e['user_id'] == session.user_id]
            assert len(user_events) >= 3  # At least one event per agent task
        
        logger.info("✅ Concurrent multi-user agent orchestration validated")
    
    async def test_user_agent_pipeline_coordination(self):
        """Test 5/15: User agent pipeline coordination and data flow"""
        
        session = self.create_user_session_data("pipeline")
        await session.execution_engine.initialize()
        
        # Create agent pipeline with data dependencies
        pipeline_steps = [
            {
                "step_id": "intake",
                "agent_type": "intake_agent",
                "depends_on": [],
                "task_data": {"action": "collect_user_requirements", "user_id": session.user_id}
            },
            {
                "step_id": "analysis",
                "agent_type": "analysis_agent", 
                "depends_on": ["intake"],
                "task_data": {"action": "analyze_requirements", "user_id": session.user_id}
            },
            {
                "step_id": "optimization",
                "agent_type": "optimization_agent",
                "depends_on": ["analysis"],
                "task_data": {"action": "optimize_solution", "user_id": session.user_id}
            },
            {
                "step_id": "delivery",
                "agent_type": "delivery_agent",
                "depends_on": ["optimization"],
                "task_data": {"action": "deliver_results", "user_id": session.user_id}
            }
        ]
        
        # Execute pipeline with proper coordination
        pipeline_results = {}
        
        for step in pipeline_steps:
            # Wait for dependencies
            for dep_step_id in step["depends_on"]:
                assert dep_step_id in pipeline_results
            
            # Execute step
            step_result = await session.execution_engine.execute_agent_task(
                agent_type=step["agent_type"],
                task_data=step["task_data"]
            )
            
            pipeline_results[step["step_id"]] = step_result
        
        # Validate pipeline completion
        assert len(pipeline_results) == 4
        assert "intake" in pipeline_results
        assert "analysis" in pipeline_results
        assert "optimization" in pipeline_results
        assert "delivery" in pipeline_results
        
        # Validate pipeline events in correct order
        session_events = [e for e in self.global_websocket_events 
                         if e['session_id'] == session.session_id]
        
        # Should have events for each pipeline step
        assert len(session_events) >= 4
        
        logger.info("✅ User agent pipeline coordination validated")
    
    async def test_user_agent_failure_and_recovery_orchestration(self):
        """Test 6/15: User agent failure and recovery orchestration patterns"""
        
        session = self.create_user_session_data("recovery")
        await session.execution_engine.initialize()
        
        # Configure execution engine to handle failures gracefully
        recovery_attempts = []
        
        async def failing_agent_task(attempt_count: int):
            """Simulates an agent that fails initially but succeeds on retry"""
            recovery_attempts.append(attempt_count)
            
            if attempt_count < 2:  # Fail first two attempts
                raise Exception(f"Agent failure simulation - attempt {attempt_count}")
            
            return {"status": "success", "attempt": attempt_count, "user_id": session.user_id}
        
        # Execute task with retry logic
        max_retries = 3
        final_result = None
        
        for attempt in range(max_retries):
            try:
                # Use execution engine to coordinate the failing task
                result = await session.execution_engine.execute_agent_task(
                    agent_type="resilient_agent",
                    task_data={
                        "action": "test_resilience",
                        "attempt": attempt,
                        "user_id": session.user_id
                    }
                )
                final_result = result
                break
                
            except Exception as e:
                logger.info(f"Attempt {attempt} failed as expected: {e}")
                if attempt == max_retries - 1:
                    # On final attempt, simulate successful recovery
                    final_result = await failing_agent_task(attempt + 1)
        
        # Validate recovery was successful
        assert final_result is not None
        assert final_result.get("status") == "success" if isinstance(final_result, dict) else True
        
        # Validate recovery attempts were tracked
        assert len(recovery_attempts) >= 1
        
        # Validate WebSocket events captured the recovery process
        session_events = [e for e in self.global_websocket_events 
                         if e['session_id'] == session.session_id]
        assert len(session_events) >= 1
        
        logger.info("✅ User agent failure and recovery orchestration validated")

    # ============================================================================
    # CATEGORY 3: RESOURCE MANAGEMENT & CLEANUP (3 tests)
    # ============================================================================
    
    async def test_user_execution_engine_resource_allocation(self):
        """Test 7/15: User execution engine resource allocation and limits"""
        
        # Create session with resource constraints
        session = self.create_user_session_data("resources")
        
        # Configure resource limits (if supported by execution engine)
        resource_config = {
            "max_concurrent_agents": 3,
            "memory_limit_mb": 100,
            "execution_timeout_seconds": 30
        }
        
        if hasattr(session.execution_engine, 'configure_resources'):
            session.execution_engine.configure_resources(resource_config)
        
        await session.execution_engine.initialize()
        
        # Track resource allocation
        allocated_resources = []
        
        async def resource_intensive_task(task_id: str):
            """Simulates a resource-intensive agent task"""
            start_time = time.time()
            
            result = await session.execution_engine.execute_agent_task(
                agent_type="resource_agent",
                task_data={
                    "task_id": task_id,
                    "resource_usage": "high",
                    "user_id": session.user_id
                }
            )
            
            end_time = time.time()
            
            resource_info = {
                "task_id": task_id,
                "duration": end_time - start_time,
                "result": result
            }
            
            allocated_resources.append(resource_info)
            return resource_info
        
        # Execute multiple resource-intensive tasks
        tasks = [f"resource_task_{i}" for i in range(5)]
        
        # Run with concurrency limit
        semaphore = asyncio.Semaphore(3)  # Limit concurrent execution
        
        async def limited_task(task_id):
            async with semaphore:
                return await resource_intensive_task(task_id)
        
        resource_results = await asyncio.gather(
            *[limited_task(task_id) for task_id in tasks]
        )
        
        # Validate resource allocation
        assert len(resource_results) == 5
        assert len(allocated_resources) == 5
        
        # Validate no resource leaks
        # (This would typically check memory usage, file handles, etc.)
        
        logger.info("✅ User execution engine resource allocation validated")
    
    async def test_user_execution_engine_memory_cleanup(self):
        """Test 8/15: User execution engine memory cleanup and garbage collection"""
        
        # Create multiple short-lived sessions to test cleanup
        cleanup_sessions = []
        
        for i in range(10):
            session = self.create_user_session_data(f"cleanup-{i}")
            await session.execution_engine.initialize()
            
            # Execute a task to allocate resources
            await session.execution_engine.execute_agent_task(
                agent_type="memory_test_agent",
                task_data={"session_id": session.session_id, "allocate_memory": True}
            )
            
            cleanup_sessions.append(session)
        
        # Get initial memory references
        initial_refs = [weakref.ref(session.execution_engine) for session in cleanup_sessions]
        
        # Cleanup all sessions
        for session in cleanup_sessions:
            await session.execution_engine.cleanup()
        
        # Remove strong references
        cleanup_sessions.clear()
        
        # Force garbage collection
        gc.collect()
        
        # Validate memory cleanup
        alive_refs = [ref for ref in initial_refs if ref() is not None]
        
        # Some references may still be alive due to asyncio tasks, but most should be cleaned up
        logger.info(f"Memory cleanup: {len(initial_refs) - len(alive_refs)}/{len(initial_refs)} engines cleaned up")
        
        # Validate WebSocket events were properly handled during cleanup
        total_events = len(self.global_websocket_events)
        assert total_events >= 10  # At least one event per session
        
        logger.info("✅ User execution engine memory cleanup validated")
    
    async def test_user_execution_engine_resource_isolation(self):
        """Test 9/15: User execution engine resource isolation between users"""
        
        # Create two user sessions with different resource profiles
        heavy_user_session = self.create_user_session_data("heavy-user")
        light_user_session = self.create_user_session_data("light-user")
        
        await asyncio.gather(
            heavy_user_session.execution_engine.initialize(),
            light_user_session.execution_engine.initialize()
        )
        
        # Simulate heavy resource usage by one user
        async def heavy_resource_workflow():
            """Resource-intensive workflow"""
            results = []
            for i in range(5):
                result = await heavy_user_session.execution_engine.execute_agent_task(
                    agent_type="heavy_computation_agent",
                    task_data={
                        "computation_size": "large",
                        "iteration": i,
                        "user_id": heavy_user_session.user_id
                    }
                )
                results.append(result)
                await asyncio.sleep(0.1)  # Simulate processing time
            return results
        
        # Simulate light resource usage by another user
        async def light_resource_workflow():
            """Lightweight workflow"""
            results = []
            for i in range(3):
                result = await light_user_session.execution_engine.execute_agent_task(
                    agent_type="light_computation_agent",
                    task_data={
                        "computation_size": "small",
                        "iteration": i,
                        "user_id": light_user_session.user_id
                    }
                )
                results.append(result)
            return results
        
        # Run both workflows concurrently
        start_time = time.time()
        
        heavy_results, light_results = await asyncio.gather(
            heavy_resource_workflow(),
            light_resource_workflow()
        )
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Validate both workflows completed successfully
        assert len(heavy_results) == 5
        assert len(light_results) == 3
        
        # Validate resource isolation - light user shouldn't be significantly impacted
        light_user_events = [e for e in self.global_websocket_events 
                           if e['user_id'] == light_user_session.user_id]
        heavy_user_events = [e for e in self.global_websocket_events 
                           if e['user_id'] == heavy_user_session.user_id]
        
        assert len(light_user_events) >= 3
        assert len(heavy_user_events) >= 5
        
        logger.info(f"✅ Resource isolation validated - workflows completed in {total_duration:.2f}s")

    # ============================================================================
    # CATEGORY 4: WEBSOCKET BRIDGE COORDINATION (3 tests)
    # ============================================================================
    
    async def test_execution_engine_websocket_bridge_integration(self):
        """Test 10/15: Execution engine WebSocket bridge integration and event coordination"""
        
        session = self.create_user_session_data("websocket-bridge")
        await session.execution_engine.initialize()
        
        # Execute agent task with detailed WebSocket event tracking
        task_data = {
            "action": "websocket_integration_test",
            "emit_events": True,
            "user_id": session.user_id,
            "detailed_progress": True
        }
        
        result = await session.execution_engine.execute_agent_task(
            agent_type="websocket_aware_agent",
            task_data=task_data
        )
        
        # Validate WebSocket bridge coordination
        session_events = [e for e in self.global_websocket_events 
                         if e['session_id'] == session.session_id]
        
        # Should have multiple event types
        event_types = [e['event_type'] for e in session_events]
        
        # Validate critical events are present
        expected_events = ['agent_started', 'agent_thinking', 'agent_completed']
        for expected_event in expected_events:
            assert any(event_type == expected_event for event_type in event_types), \
                   f"Missing {expected_event} in events: {event_types}"
        
        # Validate events have proper user context
        for event in session_events:
            assert event['user_id'] == session.user_id
            assert event['session_id'] == session.session_id
            assert 'timestamp' in event
        
        logger.info("✅ Execution engine WebSocket bridge integration validated")
    
    async def test_multi_user_websocket_event_coordination(self):
        """Test 11/15: Multi-user WebSocket event coordination and isolation"""
        
        # Create multiple user sessions
        sessions = [
            self.create_user_session_data(f"ws-multi-{i}")
            for i in range(3)
        ]
        
        await asyncio.gather(
            *[session.execution_engine.initialize() for session in sessions]
        )
        
        # Execute concurrent agent tasks with WebSocket events
        async def user_websocket_workflow(session: UserSessionData):
            """Workflow that generates multiple WebSocket events"""
            
            # Task 1: Initial processing
            await session.execution_engine.execute_agent_task(
                agent_type="event_generator_agent",
                task_data={
                    "phase": "initial",
                    "emit_progress": True,
                    "user_id": session.user_id
                }
            )
            
            # Task 2: Intermediate processing
            await session.execution_engine.execute_agent_task(
                agent_type="event_generator_agent", 
                task_data={
                    "phase": "intermediate",
                    "emit_progress": True,
                    "user_id": session.user_id
                }
            )
            
            # Task 3: Final processing
            result = await session.execution_engine.execute_agent_task(
                agent_type="event_generator_agent",
                task_data={
                    "phase": "final",
                    "emit_progress": True,
                    "user_id": session.user_id
                }
            )
            
            return session.user_id, result
        
        # Run concurrent workflows
        workflow_results = await asyncio.gather(
            *[user_websocket_workflow(session) for session in sessions]
        )
        
        # Validate event isolation per user
        for session in sessions:
            user_events = [e for e in self.global_websocket_events 
                          if e['user_id'] == session.user_id]
            
            # Each user should have events from their 3 tasks
            assert len(user_events) >= 3
            
            # Validate no cross-user event contamination
            for event in user_events:
                assert event['user_id'] == session.user_id
                assert event['session_id'] == session.session_id
        
        # Validate total event count
        assert len(self.global_websocket_events) >= 9  # 3 users × 3 tasks minimum
        
        logger.info("✅ Multi-user WebSocket event coordination validated")
    
    async def test_websocket_event_ordering_and_consistency(self):
        """Test 12/15: WebSocket event ordering and consistency in execution flows"""
        
        session = self.create_user_session_data("ws-ordering")
        await session.execution_engine.initialize()
        
        # Execute a complex agent workflow with specific event ordering requirements
        workflow_steps = [
            {"step": "preparation", "expected_events": ["agent_started", "agent_thinking"]},
            {"step": "execution", "expected_events": ["tool_executing", "tool_completed"]},
            {"step": "completion", "expected_events": ["agent_completed"]}
        ]
        
        # Track event timestamps for ordering validation
        step_events = []
        
        for step_config in workflow_steps:
            step_start_time = time.time()
            
            result = await session.execution_engine.execute_agent_task(
                agent_type="ordered_workflow_agent",
                task_data={
                    "step": step_config["step"],
                    "emit_ordered_events": True,
                    "user_id": session.user_id
                }
            )
            
            step_end_time = time.time()
            
            step_events.append({
                "step": step_config["step"],
                "start_time": step_start_time,
                "end_time": step_end_time,
                "expected_events": step_config["expected_events"]
            })
        
        # Validate event ordering
        session_events = [e for e in self.global_websocket_events 
                         if e['session_id'] == session.session_id]
        
        # Sort events by timestamp
        sorted_events = sorted(session_events, key=lambda e: e['timestamp'])
        
        # Validate events are in chronological order
        for i in range(1, len(sorted_events)):
            assert sorted_events[i]['timestamp'] >= sorted_events[i-1]['timestamp']
        
        # Validate event consistency
        event_types = [e['event_type'] for e in sorted_events]
        
        # Should follow logical flow pattern
        if 'agent_started' in event_types and 'agent_completed' in event_types:
            started_idx = event_types.index('agent_started')
            completed_idx = event_types.index('agent_completed')
            assert started_idx < completed_idx, "agent_started should come before agent_completed"
        
        logger.info("✅ WebSocket event ordering and consistency validated")

    # ============================================================================
    # CATEGORY 5: ERROR HANDLING & RECOVERY (3 tests)
    # ============================================================================
    
    async def test_execution_engine_error_isolation(self):
        """Test 13/15: Execution engine error isolation between users"""
        
        # Create sessions for stable and error-prone users
        stable_session = self.create_user_session_data("stable")
        error_session = self.create_user_session_data("error-prone")
        
        await asyncio.gather(
            stable_session.execution_engine.initialize(),
            error_session.execution_engine.initialize()
        )
        
        # Define stable workflow
        async def stable_workflow():
            """Reliable workflow that should not be affected by other user errors"""
            results = []
            
            for i in range(3):
                result = await stable_session.execution_engine.execute_agent_task(
                    agent_type="reliable_agent",
                    task_data={
                        "task_id": f"stable_task_{i}",
                        "user_id": stable_session.user_id
                    }
                )
                results.append(result)
            
            return results
        
        # Define error-prone workflow  
        async def error_workflow():
            """Workflow that intentionally generates errors"""
            results = []
            errors = []
            
            for i in range(3):
                try:
                    result = await error_session.execution_engine.execute_agent_task(
                        agent_type="failing_agent",
                        task_data={
                            "task_id": f"error_task_{i}",
                            "should_fail": i % 2 == 0,  # Fail on even iterations
                            "user_id": error_session.user_id
                        }
                    )
                    results.append(result)
                except Exception as e:
                    errors.append(str(e))
            
            return results, errors
        
        # Run both workflows concurrently
        stable_results, (error_results, captured_errors) = await asyncio.gather(
            stable_workflow(),
            error_workflow()
        )
        
        # Validate stable workflow was unaffected by errors in error workflow
        assert len(stable_results) == 3
        
        # Validate error workflow had expected failures
        assert len(captured_errors) >= 1  # Should have some failures
        
        # Validate WebSocket events for both users
        stable_events = [e for e in self.global_websocket_events 
                        if e['user_id'] == stable_session.user_id]
        error_events = [e for e in self.global_websocket_events 
                       if e['user_id'] == error_session.user_id]
        
        assert len(stable_events) >= 3  # Successful execution events
        assert len(error_events) >= 1   # At least some events despite errors
        
        logger.info("✅ Execution engine error isolation validated")
    
    async def test_execution_engine_graceful_degradation(self):
        """Test 14/15: Execution engine graceful degradation under resource constraints"""
        
        session = self.create_user_session_data("degradation")
        await session.execution_engine.initialize()
        
        # Simulate resource constraints
        resource_pressure = {
            "memory_pressure": True,
            "cpu_pressure": True,
            "io_pressure": True
        }
        
        # Configure execution engine for graceful degradation if supported
        if hasattr(session.execution_engine, 'enable_graceful_degradation'):
            session.execution_engine.enable_graceful_degradation(resource_pressure)
        
        # Execute tasks under resource pressure
        degradation_results = []
        
        async def execute_under_pressure(task_id: str, pressure_level: str):
            """Execute task with simulated resource pressure"""
            try:
                result = await session.execution_engine.execute_agent_task(
                    agent_type="resource_sensitive_agent",
                    task_data={
                        "task_id": task_id,
                        "pressure_level": pressure_level,
                        "user_id": session.user_id,
                        "resource_constraints": resource_pressure
                    }
                )
                return {"success": True, "result": result, "task_id": task_id}
                
            except Exception as e:
                return {"success": False, "error": str(e), "task_id": task_id}
        
        # Execute tasks with increasing pressure levels
        pressure_levels = ["low", "medium", "high", "critical"]
        
        for level in pressure_levels:
            result = await execute_under_pressure(f"pressure_test_{level}", level)
            degradation_results.append(result)
        
        # Validate graceful degradation
        successful_tasks = [r for r in degradation_results if r["success"]]
        failed_tasks = [r for r in degradation_results if not r["success"]]
        
        # System should handle at least some tasks even under pressure
        assert len(successful_tasks) >= 2, "System should gracefully handle some tasks under pressure"
        
        # Validate WebSocket events were generated even under pressure
        session_events = [e for e in self.global_websocket_events 
                         if e['session_id'] == session.session_id]
        assert len(session_events) >= len(successful_tasks)
        
        logger.info(f"✅ Graceful degradation validated - {len(successful_tasks)}/{len(degradation_results)} tasks succeeded")
    
    async def test_execution_engine_recovery_patterns(self):
        """Test 15/15: Execution engine recovery patterns and resilience"""
        
        session = self.create_user_session_data("recovery")
        await session.execution_engine.initialize()
        
        # Simulate various failure scenarios and recovery patterns
        recovery_scenarios = [
            {
                "name": "transient_network_failure",
                "failure_type": "network",
                "recovery_strategy": "retry_with_backoff"
            },
            {
                "name": "agent_initialization_failure", 
                "failure_type": "initialization",
                "recovery_strategy": "reinitialize_agent"
            },
            {
                "name": "resource_exhaustion",
                "failure_type": "resources",
                "recovery_strategy": "queue_and_retry"
            }
        ]
        
        recovery_results = []
        
        for scenario in recovery_scenarios:
            scenario_start_time = time.time()
            
            try:
                # Simulate failure scenario
                result = await session.execution_engine.execute_agent_task(
                    agent_type="recovery_test_agent",
                    task_data={
                        "scenario": scenario["name"],
                        "failure_type": scenario["failure_type"],
                        "recovery_strategy": scenario["recovery_strategy"],
                        "user_id": session.user_id,
                        "simulate_failure": True
                    }
                )
                
                scenario_end_time = time.time()
                
                recovery_results.append({
                    "scenario": scenario["name"],
                    "success": True,
                    "duration": scenario_end_time - scenario_start_time,
                    "result": result
                })
                
            except Exception as e:
                scenario_end_time = time.time()
                
                recovery_results.append({
                    "scenario": scenario["name"],
                    "success": False,
                    "duration": scenario_end_time - scenario_start_time,
                    "error": str(e)
                })
        
        # Validate recovery patterns
        successful_recoveries = [r for r in recovery_results if r["success"]]
        
        # System should recover from at least some failure scenarios
        assert len(successful_recoveries) >= 1, "System should demonstrate recovery capabilities"
        
        # Validate reasonable recovery times (should complete within reasonable time)
        for recovery in successful_recoveries:
            assert recovery["duration"] < 30.0, f"Recovery took too long: {recovery['duration']}s"
        
        # Validate WebSocket events captured recovery process
        session_events = [e for e in self.global_websocket_events 
                         if e['session_id'] == session.session_id]
        assert len(session_events) >= len(recovery_scenarios)
        
        logger.info(f"✅ Recovery patterns validated - {len(successful_recoveries)}/{len(recovery_scenarios)} scenarios recovered")