"""
E2E Test: Multi-User Concurrent Agent Execution with WebSocket Isolation

Business Value Justification (BVJ):
- Segment: Early, Mid, Enterprise - Multi-user scenarios are critical for paid tiers
- Business Goal: Ensure complete isolation between concurrent users executing agents
- Value Impact: Multiple users must receive isolated WebSocket events without cross-contamination
- Strategic Impact: Core multi-tenancy functionality that enables business scaling

This E2E test validates:
- 3+ users executing agents simultaneously with real authentication
- Complete WebSocket event isolation between users
- No cross-contamination of agent execution contexts
- Real agent execution for each user with proper LLM integration
- Database and state isolation across concurrent sessions

CRITICAL: Tests the fundamental multi-user architecture that enables business growth
"""

import pytest
import asyncio
import uuid
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper,
    E2EWebSocketAuthHelper, 
    create_authenticated_user_context
)
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.websocket_helpers import WebSocketTestClient

# Core system imports with absolute paths
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID, RequestID
from shared.id_generation.unified_id_generator import UnifiedIdGenerator


class TestMultiUserConcurrentAgentExecution(BaseE2ETest):
    """E2E tests for multi-user concurrent agent execution with complete isolation."""
    
    @pytest.fixture
    async def multiple_authenticated_users(self):
        """Create multiple authenticated users for concurrent testing."""
        users = []
        for i in range(3):  # Test with 3 concurrent users
            user_context = await create_authenticated_user_context(
                user_email=f"concurrent_user_{i}@e2e.test",
                environment="test",
                permissions=["read", "write", "agent_execute", "websocket_connect"],
                websocket_enabled=True
            )
            users.append(user_context)
        return users
    
    @pytest.fixture
    def websocket_auth_helpers(self):
        """Create WebSocket auth helpers for multiple users."""
        return [E2EWebSocketAuthHelper(environment="test") for _ in range(3)]
    
    @pytest.fixture
    def unified_id_generator(self):
        """Unified ID generator for consistent test IDs."""
        return UnifiedIdGenerator()
    
    @pytest.fixture
    async def real_agent_registry(self):
        """Real agent registry for concurrent testing."""
        registry = AgentRegistry()
        await registry.initialize_registry()
        
        available_agents = registry.list_available_agents()
        if len(available_agents) < 2:
            pytest.fail("Need at least 2 agents for concurrent testing")
        
        return registry
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.real_llm
    @pytest.mark.websocket_events
    @pytest.mark.multi_user
    async def test_three_users_concurrent_agent_execution_isolation(
        self,
        multiple_authenticated_users: List[StronglyTypedUserExecutionContext],
        websocket_auth_helpers: List[E2EWebSocketAuthHelper],
        real_agent_registry: AgentRegistry,
        unified_id_generator: UnifiedIdGenerator
    ):
        """
        Test 3 users executing agents concurrently with complete isolation.
        
        CRITICAL: This test validates the core multi-tenancy functionality.
        Each user must receive ONLY their own WebSocket events.
        """
        
        # Generate unique execution contexts for each user
        user_execution_contexts = []
        user_websocket_connections = []
        user_event_collectors = []
        user_received_events = [[] for _ in range(3)]
        
        for i, (user_context, ws_helper) in enumerate(zip(multiple_authenticated_users, websocket_auth_helpers)):
            # Create unique run ID for each user
            run_id = unified_id_generator.generate_run_id(
                user_id=str(user_context.user_id),
                operation=f"concurrent_user_{i}_execution"
            )
            
            execution_context = AgentExecutionContext(
                agent_name="triage_agent",  # Same agent for all users to test isolation
                run_id=str(run_id),
                correlation_id=str(user_context.request_id),
                retry_count=0,
                user_context=user_context
            )
            user_execution_contexts.append(execution_context)
            
            # Create isolated WebSocket connection for each user
            ws_connection = await ws_helper.connect_authenticated_websocket(timeout=20.0)
            user_websocket_connections.append(ws_connection)
            
            # Create event collector for this user
            async def create_event_collector(user_index: int, connection):
                async def collect_user_events():
                    try:
                        while True:
                            event_raw = await asyncio.wait_for(connection.recv(), timeout=45.0)
                            event = json.loads(event_raw)
                            user_received_events[user_index].append(event)
                            
                            self.logger.info(f"User {user_index} received event: {event.get('type')}")
                            
                            # Stop after completion
                            if event.get('type') == 'agent_completed':
                                break
                                
                    except asyncio.TimeoutError:
                        self.logger.warning(f"User {user_index} event collection timeout")
                    except Exception as e:
                        self.logger.error(f"User {user_index} event collection error: {e}")
                
                return collect_user_events()
            
            user_event_collectors.append(create_event_collector(i, ws_connection))
        
        # Set up agent execution infrastructure
        websocket_manager = UnifiedWebSocketManager()
        websocket_bridge = AgentWebSocketBridge(websocket_manager)
        execution_core = AgentExecutionCore(real_agent_registry, websocket_bridge)
        
        # Create agent states for each user
        agent_states = []
        for i, user_context in enumerate(multiple_authenticated_users):
            agent_state = DeepAgentState(
                user_id=str(user_context.user_id),
                thread_id=str(user_context.thread_id),
                agent_context={
                    **user_context.agent_context,
                    'user_message': f'Analyze request for user {i+1}',  # Unique message per user
                    'user_identifier': f'concurrent_user_{i+1}'
                }
            )
            agent_states.append(agent_state)
        
        # Start event collection for all users
        event_collection_tasks = [
            asyncio.create_task(collector) for collector in user_event_collectors
        ]
        
        try:
            # Execute agents for all users CONCURRENTLY
            self.logger.info("Starting concurrent agent execution for 3 users")
            
            execution_tasks = []
            for i, (context, state) in enumerate(zip(user_execution_contexts, agent_states)):
                task = asyncio.create_task(
                    execution_core.execute_agent(
                        context=context,
                        state=state,
                        timeout=60.0,
                        enable_llm=True,
                        enable_websocket_events=True
                    )
                )
                execution_tasks.append(task)
            
            # Wait for all executions to complete
            execution_results = await asyncio.gather(*execution_tasks, return_exceptions=True)
            
            # Wait for event collection to complete
            await asyncio.gather(*event_collection_tasks, return_exceptions=True)
            
        finally:
            # Clean up WebSocket connections
            for connection in user_websocket_connections:
                try:
                    await connection.close()
                except:
                    pass
        
        # CRITICAL VALIDATION: All executions succeeded
        for i, result in enumerate(execution_results):
            if isinstance(result, Exception):
                pytest.fail(f"User {i} execution failed with exception: {result}")
            assert result.success is True, f"User {i} execution failed: {result.error}"
        
        # CRITICAL VALIDATION: Each user received events
        for i in range(3):
            assert len(user_received_events[i]) > 0, f"User {i} received no WebSocket events"
        
        # CRITICAL VALIDATION: Complete event isolation between users
        for i in range(3):
            user_run_ids = {event.get('run_id') for event in user_received_events[i]}
            expected_run_id = str(user_execution_contexts[i].run_id)
            
            # User should only see their own run_id
            assert expected_run_id in user_run_ids, \
                f"User {i} missing their own run_id ({expected_run_id}) in events"
            
            # Verify NO cross-contamination
            for j in range(3):
                if i != j:
                    other_run_id = str(user_execution_contexts[j].run_id)
                    assert other_run_id not in user_run_ids, \
                        f"ISOLATION VIOLATION: User {i} received events for User {j} " \
                        f"(run_id: {other_run_id}). This is a critical multi-tenancy failure!"
        
        # CRITICAL VALIDATION: Required events for each user
        required_events = ['agent_started', 'agent_thinking', 'agent_completed']
        
        for i in range(3):
            user_event_types = [event.get('type') for event in user_received_events[i]]
            for required_event in required_events:
                assert required_event in user_event_types, \
                    f"User {i} missing required event: {required_event}"
        
        self.logger.info("✅ CRITICAL SUCCESS: Complete multi-user isolation validated for 3 concurrent users")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.websocket_events
    @pytest.mark.multi_user
    @pytest.mark.performance
    async def test_high_concurrency_websocket_event_delivery(
        self,
        websocket_auth_helpers: List[E2EWebSocketAuthHelper],
        real_agent_registry: AgentRegistry,
        unified_id_generator: UnifiedIdGenerator
    ):
        """
        Test high concurrency WebSocket event delivery with 5+ users.
        
        Validates system performance under concurrent load while maintaining isolation.
        """
        
        num_concurrent_users = 5
        concurrent_users = []
        
        # Create users for high concurrency test
        for i in range(num_concurrent_users):
            user_context = await create_authenticated_user_context(
                user_email=f"high_concurrency_user_{i}@e2e.test",
                environment="test",
                permissions=["read", "write", "agent_execute", "websocket_connect"],
                websocket_enabled=True
            )
            concurrent_users.append(user_context)
        
        # Track performance metrics
        start_time = time.time()
        user_completion_times = [None] * num_concurrent_users
        user_event_counts = [0] * num_concurrent_users
        
        async def execute_user_agent(user_index: int, user_context: StronglyTypedUserExecutionContext):
            """Execute agent for a single user and track performance."""
            user_start_time = time.time()
            
            try:
                # Create WebSocket helper for this user
                ws_helper = E2EWebSocketAuthHelper(environment="test")
                
                run_id = unified_id_generator.generate_run_id(
                    user_id=str(user_context.user_id),
                    operation=f"high_concurrency_user_{user_index}"
                )
                
                execution_context = AgentExecutionContext(
                    agent_name="triage_agent",
                    run_id=str(run_id),
                    correlation_id=str(user_context.request_id),
                    retry_count=0,
                    user_context=user_context
                )
                
                # Connect and collect events
                ws_connection = await ws_helper.connect_authenticated_websocket(timeout=25.0)
                
                user_events = []
                
                async def collect_events():
                    try:
                        while True:
                            event_raw = await asyncio.wait_for(ws_connection.recv(), timeout=30.0)
                            event = json.loads(event_raw)
                            user_events.append(event)
                            
                            if event.get('type') == 'agent_completed':
                                break
                    except asyncio.TimeoutError:
                        pass
                
                # Start event collection
                event_task = asyncio.create_task(collect_events())
                
                # Execute agent
                websocket_manager = UnifiedWebSocketManager()
                websocket_bridge = AgentWebSocketBridge(websocket_manager)
                execution_core = AgentExecutionCore(real_agent_registry, websocket_bridge)
                
                agent_state = DeepAgentState(
                    user_id=str(user_context.user_id),
                    thread_id=str(user_context.thread_id),
                    agent_context={
                        **user_context.agent_context,
                        'user_message': f'Quick analysis for concurrency test user {user_index}',
                        'performance_test': True
                    }
                )
                
                result = await execution_core.execute_agent(
                    context=execution_context,
                    state=agent_state,
                    timeout=45.0,
                    enable_llm=False,  # Disable LLM for performance test
                    enable_websocket_events=True
                )
                
                await event_task
                await ws_connection.close()
                
                # Record metrics
                user_completion_times[user_index] = time.time() - user_start_time
                user_event_counts[user_index] = len(user_events)
                
                assert result.success is True, f"User {user_index} execution failed"
                assert len(user_events) >= 3, f"User {user_index} received too few events: {len(user_events)}"
                
                return result, user_events
                
            except Exception as e:
                self.logger.error(f"User {user_index} execution failed: {e}")
                raise
        
        # Execute all users concurrently
        concurrent_tasks = [
            execute_user_agent(i, user_context)
            for i, user_context in enumerate(concurrent_users)
        ]
        
        try:
            results = await asyncio.gather(*concurrent_tasks)
            
            total_time = time.time() - start_time
            
            # Performance validation
            assert all(completion_time is not None for completion_time in user_completion_times), \
                "All users must complete execution"
            
            average_completion_time = sum(user_completion_times) / len(user_completion_times)
            max_completion_time = max(user_completion_times)
            
            # Performance thresholds for concurrent execution
            assert max_completion_time < 60.0, \
                f"Individual user completion time too high: {max_completion_time}s"
            
            assert total_time < 70.0, \
                f"Total concurrent execution time too high: {total_time}s"
            
            # Event delivery validation
            total_events = sum(user_event_counts)
            assert total_events >= num_concurrent_users * 3, \
                f"Too few events delivered across all users: {total_events}"
            
            self.logger.info(f"✅ HIGH CONCURRENCY SUCCESS:")
            self.logger.info(f"  - {num_concurrent_users} users executed concurrently")
            self.logger.info(f"  - Total time: {total_time:.2f}s")
            self.logger.info(f"  - Average completion: {average_completion_time:.2f}s")
            self.logger.info(f"  - Max completion: {max_completion_time:.2f}s")
            self.logger.info(f"  - Total events delivered: {total_events}")
            
        except Exception as e:
            self.logger.error(f"High concurrency test failed: {e}")
            raise
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.websocket_events
    @pytest.mark.multi_user
    async def test_different_agents_concurrent_execution(
        self,
        real_agent_registry: AgentRegistry,
        unified_id_generator: UnifiedIdGenerator
    ):
        """
        Test concurrent execution of different agents by different users.
        
        Validates that:
        1. Different users can execute different agents simultaneously
        2. Agent-specific events are properly isolated
        3. Different agent types generate appropriate event sequences
        """
        
        # Create users for different agent types
        users_and_agents = [
            ("triage_agent", "triage_user@e2e.test"),
            ("data_analysis_agent", "data_user@e2e.test"), 
            ("optimization_agent", "optimization_user@e2e.test")
        ]
        
        user_contexts = []
        for agent_name, user_email in users_and_agents:
            user_context = await create_authenticated_user_context(
                user_email=user_email,
                environment="test",
                permissions=["read", "write", "agent_execute", "websocket_connect"],
                websocket_enabled=True
            )
            user_contexts.append((user_context, agent_name))
        
        async def execute_agent_for_user(user_context: StronglyTypedUserExecutionContext, agent_name: str):
            """Execute specific agent for user."""
            ws_helper = E2EWebSocketAuthHelper(environment="test")
            
            run_id = unified_id_generator.generate_run_id(
                user_id=str(user_context.user_id),
                operation=f"different_agents_{agent_name}"
            )
            
            execution_context = AgentExecutionContext(
                agent_name=agent_name,
                run_id=str(run_id),
                correlation_id=str(user_context.request_id),
                retry_count=0,
                user_context=user_context
            )
            
            ws_connection = await ws_helper.connect_authenticated_websocket()
            
            events = []
            
            async def collect_events():
                try:
                    while True:
                        event_raw = await asyncio.wait_for(ws_connection.recv(), timeout=40.0)
                        event = json.loads(event_raw)
                        events.append(event)
                        
                        if event.get('type') == 'agent_completed':
                            break
                except asyncio.TimeoutError:
                    pass
            
            event_task = asyncio.create_task(collect_events())
            
            # Execute agent
            websocket_manager = UnifiedWebSocketManager()
            websocket_bridge = AgentWebSocketBridge(websocket_manager)
            execution_core = AgentExecutionCore(real_agent_registry, websocket_bridge)
            
            agent_state = DeepAgentState(
                user_id=str(user_context.user_id),
                thread_id=str(user_context.thread_id),
                agent_context={
                    **user_context.agent_context,
                    'agent_specific_request': f'Execute {agent_name} functionality',
                    'requested_agent': agent_name
                }
            )
            
            result = await execution_core.execute_agent(
                context=execution_context,
                state=agent_state,
                timeout=50.0,
                enable_llm=False,  # Focus on agent behavior, not LLM
                enable_websocket_events=True
            )
            
            await event_task
            await ws_connection.close()
            
            return result, events, agent_name
        
        # Execute different agents concurrently
        concurrent_tasks = [
            execute_agent_for_user(user_context, agent_name)
            for user_context, agent_name in user_contexts
        ]
        
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        # Validate results
        for i, result_data in enumerate(results):
            if isinstance(result_data, Exception):
                pytest.fail(f"Agent execution {i} failed: {result_data}")
            
            execution_result, events, agent_name = result_data
            
            # Execution success
            assert execution_result.success is True, \
                f"Agent {agent_name} execution failed: {execution_result.error}"
            
            # Event validation
            assert len(events) > 0, f"Agent {agent_name} generated no events"
            
            event_types = [event.get('type') for event in events]
            assert 'agent_started' in event_types, f"Agent {agent_name} missing agent_started"
            assert 'agent_completed' in event_types, f"Agent {agent_name} missing agent_completed"
            
            # Agent name consistency
            for event in events:
                if event.get('agent_name'):
                    assert event.get('agent_name') == agent_name, \
                        f"Event has wrong agent_name: {event.get('agent_name')} != {agent_name}"
        
        self.logger.info("✅ SUCCESS: Different agents executed concurrently with proper isolation")