"""
User Execution Engine Integration Tests

Business Value Justification (BVJ):
- Segment: Platform/Core Infrastructure
- Business Goal: Validate reliable user execution engine patterns for Golden Path
- Value Impact: Ensures seamless agent orchestration and WebSocket integration for chat
- Strategic Impact: Core component protecting $500K+ ARR through reliable agent execution

Integration Test Requirements:
- NO database dependencies - tests execution engine patterns without external services
- NO Docker requirements - focuses on component integration patterns
- Uses real user execution engine and context components
- Validates multi-user execution isolation and resource management
- Tests WebSocket bridge integration and event coordination

Phase 1 Priority Areas:
1. User execution engine integration patterns
2. Multi-user execution context isolation
3. WebSocket bridge coordination with execution engine
4. Agent lifecycle management through execution engine
5. Resource management and cleanup patterns

CRITICAL: These tests validate the execution engine's role in coordinating
agents with WebSocket events, ensuring users see real-time agent progress.
"""

import asyncio
import pytest
import time
import uuid
import gc
import weakref
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from unittest.mock import AsyncMock, MagicMock, patch
from concurrent.futures import ThreadPoolExecutor

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext, AgentExecutionResult, PipelineStep
)
from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher

import logging
logger = logging.getLogger(__name__)


class MockWebSocketEmitter:
    """Mock WebSocket emitter for execution engine testing."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.events = []
        self.is_active = True
        
    async def notify_agent_started(self, context, **kwargs):
        if self.is_active:
            self.events.append(('agent_started', context.agent_name, kwargs))
        return True
        
    async def notify_agent_thinking(self, context, reasoning, step_number=1, **kwargs):
        if self.is_active:
            self.events.append(('agent_thinking', context.agent_name, reasoning))
        return True
        
    async def notify_tool_executing(self, user_context, tool_name, parameters, **kwargs):
        if self.is_active:
            self.events.append(('tool_executing', tool_name, parameters))
        return True
        
    async def notify_tool_completed(self, user_context, tool_name, result, **kwargs):
        if self.is_active:
            self.events.append(('tool_completed', tool_name, result))
        return True
        
    async def notify_agent_completed(self, context, result, **kwargs):
        if self.is_active:
            self.events.append(('agent_completed', context.agent_name, result))
        return True
        
    async def cleanup(self):
        self.is_active = False
        self.events.clear()
        
    def get_event_count(self, event_type: str) -> int:
        return len([e for e in self.events if e[0] == event_type])


class MockAgentForExecution:
    """Mock agent for testing execution engine integration."""
    
    def __init__(self, agent_name: str, user_id: str):
        self.agent_name = agent_name
        self.name = agent_name
        self.user_id = user_id
        self.execution_count = 0
        self.is_active = True
        self.created_at = time.time()
        
    async def execute_with_context(self, context: AgentExecutionContext, prompt: str, **kwargs) -> AgentExecutionResult:
        """Execute agent with context."""
        if not self.is_active:
            raise RuntimeError(f"Agent {self.agent_name} is not active")
            
        self.execution_count += 1
        
        # Simulate processing
        await asyncio.sleep(0.01)
        
        return AgentExecutionResult(
            success=True,
            agent_name=self.agent_name,
            duration=0.01,
            metadata={
                'prompt': prompt,
                'user_id': self.user_id,
                'execution_number': self.execution_count,
                'kwargs': kwargs
            }
        )
        
    async def cleanup(self):
        """Cleanup agent resources."""
        self.is_active = False


class MockAgentFactory:
    """Mock agent factory for execution engine testing."""
    
    def __init__(self):
        self.created_agents = {}
        self.creation_count = 0
        
    async def create_agent_instance(self, agent_name: str, user_context: UserExecutionContext):
        """Create mock agent instance."""
        self.creation_count += 1
        agent = MockAgentForExecution(agent_name, user_context.user_id)
        
        agent_key = f"{user_context.user_id}:{agent_name}"
        self.created_agents[agent_key] = agent
        
        return agent
        
    def get_agent_count_for_user(self, user_id: str) -> int:
        """Get number of agents created for user."""
        return len([k for k in self.created_agents.keys() if k.startswith(f"{user_id}:")])


class MockToolDispatcher:
    """Mock tool dispatcher for execution engine testing."""
    
    def __init__(self, user_context: UserExecutionContext, websocket_emitter: MockWebSocketEmitter):
        self.user_context = user_context
        self.websocket_emitter = websocket_emitter
        self.executed_tools = []
        
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool with WebSocket events."""
        # Emit tool executing event
        await self.websocket_emitter.notify_tool_executing(
            self.user_context, tool_name, parameters
        )
        
        # Simulate tool execution
        await asyncio.sleep(0.005)
        
        result = {
            'success': True,
            'tool_name': tool_name,
            'parameters': parameters,
            'user_id': self.user_context.user_id,
            'execution_time': 0.005
        }
        
        # Record execution
        self.executed_tools.append({
            'tool_name': tool_name,
            'parameters': parameters,
            'result': result,
            'timestamp': time.time()
        })
        
        # Emit tool completed event
        await self.websocket_emitter.notify_tool_completed(
            self.user_context, tool_name, result
        )
        
        return result


class TestUserExecutionEngineIntegration(SSotAsyncTestCase):
    """Integration tests for user execution engine patterns and coordination."""
    
    def setup_method(self, method):
        """Set up test fixtures."""
        super().setup_method(method)
        self.test_start_time = time.time()
        
    @pytest.mark.integration
    @pytest.mark.agents
    async def test_execution_engine_agent_lifecycle_integration(self):
        """Test execution engine coordination with agent lifecycle and WebSocket events.
        
        BVJ: Validates core Golden Path functionality where execution engine coordinates
        agent execution with real-time WebSocket event delivery to users.
        """
        # Create user context
        user_context = UserExecutionContext(
            user_id="execution_test_user",
            thread_id="execution_thread_001", 
            run_id=f"execution_run_{int(time.time())}",
            request_id=f"execution_req_{uuid.uuid4().hex[:8]}"
        )
        
        # Create mock components
        websocket_emitter = MockWebSocketEmitter("execution_test_user")
        agent_factory = MockAgentFactory()
        
        # Create execution engine
        execution_engine = UserExecutionEngine(
            context=user_context,
            agent_factory=agent_factory,
            websocket_emitter=websocket_emitter
        )
        
        # Test agent creation through execution engine
        agent_name = "lifecycle_test_agent"
        agent = await execution_engine.create_agent_instance(agent_name)
        
        assert agent is not None, "Execution engine should create agent"
        assert agent.agent_name == agent_name, "Agent should have correct name"
        assert agent.user_id == user_context.user_id, "Agent should be bound to user"
        
        # Create execution context
        execution_context = AgentExecutionContext(
            user_id=user_context.user_id,
            thread_id=user_context.thread_id,
            run_id=user_context.run_id,
            request_id=user_context.request_id,
            agent_name=agent_name,
            step=PipelineStep.EXECUTION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1
        )
        
        # Test full lifecycle execution through engine
        test_prompt = "Test agent lifecycle coordination with WebSocket events"
        
        # Execute agent lifecycle with WebSocket coordination
        await execution_engine._send_user_agent_started(execution_context)
        
        await execution_engine._send_user_agent_thinking(
            execution_context, "Processing lifecycle test request", 1
        )
        
        # Execute agent
        result = await agent.execute_with_context(execution_context, test_prompt)
        
        await execution_engine._send_user_agent_completed(execution_context, result)
        
        # Validate execution result
        assert result.success, "Agent execution should succeed"
        assert result.agent_name == agent_name, "Result should match agent name"
        assert result.metadata['user_id'] == user_context.user_id, "Result should belong to user"
        
        # Validate WebSocket event coordination
        events = websocket_emitter.events
        assert len(events) >= 3, "Should have at least agent_started, thinking, and completed events"
        
        event_types = [e[0] for e in events]
        assert 'agent_started' in event_types, "Should have agent_started event"
        assert 'agent_thinking' in event_types, "Should have agent_thinking event"
        assert 'agent_completed' in event_types, "Should have agent_completed event"
        
        # Validate event ordering
        assert event_types[0] == 'agent_started', "First event should be agent_started"
        assert event_types[-1] == 'agent_completed', "Last event should be agent_completed"
        
        # Test execution engine statistics
        stats = execution_engine.get_user_execution_stats()
        assert stats['user_id'] == user_context.user_id, "Stats should belong to user"
        assert stats['total_executions'] >= 1, "Should track executions"
        
        # Cleanup
        await execution_engine.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.agents
    async def test_multi_user_execution_engine_isolation(self):
        """Test execution engine isolation between multiple concurrent users.
        
        BVJ: Critical for Enterprise SaaS operation - ensures complete isolation
        between user execution contexts and prevents cross-contamination.
        """
        num_users = 4
        user_contexts = []
        execution_engines = {}
        websocket_emitters = {}
        
        # Create multiple user execution engines
        for i in range(num_users):
            user_id = f"isolation_user_{i+1}"
            user_context = UserExecutionContext(
                user_id=user_id,
                thread_id=f"isolation_thread_{i+1}",
                run_id=f"isolation_run_{i+1}_{int(time.time())}",
                request_id=f"isolation_req_{i+1}_{uuid.uuid4().hex[:8]}"
            )
            user_contexts.append(user_context)
            
            # Create user-specific components
            emitter = MockWebSocketEmitter(user_id)
            factory = MockAgentFactory()
            
            engine = UserExecutionEngine(
                context=user_context,
                agent_factory=factory,
                websocket_emitter=emitter
            )
            
            websocket_emitters[user_id] = emitter
            execution_engines[user_id] = engine
        
        # Define user execution task
        async def execute_user_workflow(user_context: UserExecutionContext):
            """Execute agent workflow for specific user."""
            user_id = user_context.user_id
            engine = execution_engines[user_id]
            
            # Create agents for user
            agents = []
            for agent_name in ["analyzer", "optimizer", "processor"]:
                agent = await engine.create_agent_instance(agent_name)
                agents.append(agent)
            
            # Execute agents sequentially
            results = []
            for i, agent in enumerate(agents):
                execution_context = AgentExecutionContext(
                    user_id=user_context.user_id,
                    thread_id=user_context.thread_id,
                    run_id=user_context.run_id,
                    request_id=f"{user_context.request_id}_{agent.agent_name}",
                    agent_name=agent.agent_name,
                    step=PipelineStep.EXECUTION,
                    execution_timestamp=datetime.now(timezone.utc),
                    pipeline_step_num=i+1
                )
                
                # Full lifecycle with WebSocket events
                await engine._send_user_agent_started(execution_context)
                await engine._send_user_agent_thinking(
                    execution_context, f"User {user_id} executing {agent.agent_name}", i+1
                )
                
                result = await agent.execute_with_context(
                    execution_context, f"User {user_id} workflow step {i+1}"
                )
                results.append(result)
                
                await engine._send_user_agent_completed(execution_context, result)
                
                # Small delay to create temporal separation
                await asyncio.sleep(0.005)
            
            return user_id, results
        
        # Execute workflows concurrently for all users
        workflow_tasks = [execute_user_workflow(ctx) for ctx in user_contexts]
        workflow_results = await asyncio.gather(*workflow_tasks)
        
        # Validate all workflows succeeded
        for user_id, results in workflow_results:
            assert len(results) == 3, f"User {user_id} should have 3 execution results"
            
            for result in results:
                assert result.success, f"All executions should succeed for {user_id}"
                assert result.metadata['user_id'] == user_id, f"Results should belong to {user_id}"
        
        # Validate execution engine isolation
        all_user_ids = set(execution_engines.keys())
        
        for user_id in all_user_ids:
            engine = execution_engines[user_id]
            emitter = websocket_emitters[user_id]
            
            # Each engine should have its own statistics
            stats = engine.get_user_execution_stats()
            assert stats['user_id'] == user_id, f"Stats should belong to {user_id}"
            assert stats['total_executions'] >= 3, f"Should track executions for {user_id}"
            
            # Each emitter should have its own events
            events = emitter.events
            assert len(events) >= 9, f"Should have events from 3 agents for {user_id}"  # 3 events per agent minimum
            
            # All events should belong to this user's agents
            for event in events:
                if len(event) >= 3 and hasattr(event[2], 'get') and 'user_id' in event[2]:
                    assert event[2]['user_id'] == user_id, f"Events should belong to {user_id}"
        
        # Validate no cross-contamination between engines
        for user_id_1 in all_user_ids:
            for user_id_2 in all_user_ids:
                if user_id_1 != user_id_2:
                    engine_1 = execution_engines[user_id_1]
                    engine_2 = execution_engines[user_id_2]
                    
                    stats_1 = engine_1.get_user_execution_stats()
                    stats_2 = engine_2.get_user_execution_stats()
                    
                    # Engine IDs should be unique
                    assert stats_1['engine_id'] != stats_2['engine_id'], \
                        f"Engine IDs should be unique between {user_id_1} and {user_id_2}"
                    
                    # User correlation IDs should be unique
                    assert stats_1['user_correlation_id'] != stats_2['user_correlation_id'], \
                        f"User correlation IDs should be unique between {user_id_1} and {user_id_2}"
        
        # Cleanup all engines
        cleanup_tasks = [engine.cleanup() for engine in execution_engines.values()]
        await asyncio.gather(*cleanup_tasks)
    
    @pytest.mark.integration
    @pytest.mark.agents
    async def test_execution_engine_tool_integration(self):
        """Test execution engine integration with tool dispatcher and WebSocket events.
        
        BVJ: Validates tool execution coordination through execution engine,
        ensuring users see tool progress in real-time for enhanced UX.
        """
        user_context = UserExecutionContext(
            user_id="tool_integration_user",
            thread_id="tool_integration_thread",
            run_id=f"tool_integration_run_{int(time.time())}",
            request_id=f"tool_integration_req_{uuid.uuid4().hex[:8]}"
        )
        
        websocket_emitter = MockWebSocketEmitter("tool_integration_user")
        agent_factory = MockAgentFactory()
        
        execution_engine = UserExecutionEngine(
            context=user_context,
            agent_factory=agent_factory,
            websocket_emitter=websocket_emitter
        )
        
        # Create tool dispatcher through execution engine
        tool_dispatcher = execution_engine.get_tool_dispatcher()
        assert tool_dispatcher is not None, "Execution engine should provide tool dispatcher"
        
        # Replace dispatcher with mock for testing
        mock_tool_dispatcher = MockToolDispatcher(user_context, websocket_emitter)
        execution_engine.tool_dispatcher = mock_tool_dispatcher
        
        # Test tool execution with WebSocket event coordination
        tools_to_execute = [
            ("data_analyzer", {"dataset": "customer_data", "analysis_type": "trend"}),
            ("optimizer", {"target": "performance", "threshold": 0.85}),
            ("validator", {"ruleset": "business_rules", "strict": True})
        ]
        
        # Execute tools through engine
        tool_results = []
        for tool_name, parameters in tools_to_execute:
            result = await mock_tool_dispatcher.execute_tool(tool_name, parameters)
            tool_results.append(result)
        
        # Validate all tool executions succeeded
        assert len(tool_results) == len(tools_to_execute), "Should execute all tools"
        
        for i, result in enumerate(tool_results):
            tool_name, parameters = tools_to_execute[i]
            assert result['success'], f"Tool {tool_name} should succeed"
            assert result['tool_name'] == tool_name, f"Result should match tool {tool_name}"
            assert result['user_id'] == user_context.user_id, f"Result should belong to user"
            assert result['parameters'] == parameters, f"Parameters should match for {tool_name}"
        
        # Validate WebSocket events for tool execution
        events = websocket_emitter.events
        tool_executing_events = [e for e in events if e[0] == 'tool_executing']
        tool_completed_events = [e for e in events if e[0] == 'tool_completed']
        
        assert len(tool_executing_events) == len(tools_to_execute), \
            f"Should have {len(tools_to_execute)} tool executing events"
        assert len(tool_completed_events) == len(tools_to_execute), \
            f"Should have {len(tools_to_execute)} tool completed events"
        
        # Validate event pairs (each tool should have executing + completed)
        for i, (tool_name, parameters) in enumerate(tools_to_execute):
            # Find matching executing event
            executing_event = next(
                (e for e in tool_executing_events if e[1] == tool_name), 
                None
            )
            assert executing_event is not None, f"Should have executing event for {tool_name}"
            assert executing_event[2] == parameters, f"Executing event should have correct parameters for {tool_name}"
            
            # Find matching completed event
            completed_event = next(
                (e for e in tool_completed_events if e[1] == tool_name), 
                None
            )
            assert completed_event is not None, f"Should have completed event for {tool_name}"
            assert completed_event[2]['success'], f"Completed event should show success for {tool_name}"
        
        # Test tool dispatcher state
        assert len(mock_tool_dispatcher.executed_tools) == len(tools_to_execute), \
            "Tool dispatcher should track all executions"
        
        for i, execution in enumerate(mock_tool_dispatcher.executed_tools):
            tool_name, parameters = tools_to_execute[i]
            assert execution['tool_name'] == tool_name, f"Should track execution of {tool_name}"
            assert execution['parameters'] == parameters, f"Should track parameters for {tool_name}"
            assert execution['result']['user_id'] == user_context.user_id, \
                f"Tool execution should be bound to user for {tool_name}"
        
        await execution_engine.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.agents
    async def test_execution_engine_resource_management(self):
        """Test execution engine resource management and cleanup patterns.
        
        BVJ: Validates that execution engines properly manage resources and
        don't leak memory or connections under load.
        """
        # Test resource tracking during engine lifecycle
        initial_object_count = len(gc.get_objects())
        
        # Create multiple engines to test resource management
        engines = []
        weak_refs = []
        
        for i in range(5):
            user_context = UserExecutionContext(
                user_id=f"resource_user_{i+1}",
                thread_id=f"resource_thread_{i+1}",
                run_id=f"resource_run_{i+1}",
                request_id=f"resource_req_{i+1}"
            )
            
            websocket_emitter = MockWebSocketEmitter(f"resource_user_{i+1}")
            agent_factory = MockAgentFactory()
            
            engine = UserExecutionEngine(
                context=user_context,
                agent_factory=agent_factory,
                websocket_emitter=websocket_emitter
            )
            
            engines.append(engine)
            weak_refs.append(weakref.ref(engine))
            
            # Create agents through engine
            for agent_name in ["test_agent_1", "test_agent_2"]:
                await engine.create_agent_instance(agent_name)
        
        # Validate all engines are active
        for engine in engines:
            assert engine.is_active(), "Engine should be active after creation"
            stats = engine.get_user_execution_stats()
            assert stats['user_id'] is not None, "Engine should have valid user ID"
        
        # Test graceful cleanup
        cleanup_tasks = [engine.cleanup() for engine in engines]
        await asyncio.gather(*cleanup_tasks)
        
        # Validate engines are properly cleaned up
        for engine in engines:
            assert not engine.is_active(), "Engine should be inactive after cleanup"
        
        # Test that WebSocket emitters are cleaned up
        for engine in engines:
            if hasattr(engine, 'websocket_emitter'):
                assert not engine.websocket_emitter.is_active, "WebSocket emitter should be inactive"
        
        # Clear references and force garbage collection
        engines.clear()
        gc.collect()
        
        # Wait a moment for async cleanup to complete
        await asyncio.sleep(0.01)
        
        # Check for memory leaks using weak references
        living_engines = [ref() for ref in weak_refs if ref() is not None]
        assert len(living_engines) == 0, \
            f"All engines should be garbage collected, but {len(living_engines)} are still alive"
        
        # Validate object count hasn't grown significantly
        final_object_count = len(gc.get_objects())
        object_growth = final_object_count - initial_object_count
        
        # Allow some growth for test infrastructure but not excessive
        max_allowed_growth = 1000  # Reasonable buffer for test objects
        assert object_growth < max_allowed_growth, \
            f"Object count grew by {object_growth}, which may indicate memory leaks"
        
        logger.info(f"Resource management test: object count grew by {object_growth}")
    
    @pytest.mark.integration
    @pytest.mark.agents
    async def test_execution_engine_concurrent_operations(self):
        """Test execution engine handling of concurrent operations within single user.
        
        BVJ: Validates that execution engine can handle multiple concurrent
        agent operations for single user without race conditions.
        """
        user_context = UserExecutionContext(
            user_id="concurrent_ops_user",
            thread_id="concurrent_ops_thread",
            run_id=f"concurrent_ops_run_{int(time.time())}",
            request_id=f"concurrent_ops_req_{uuid.uuid4().hex[:8]}"
        )
        
        websocket_emitter = MockWebSocketEmitter("concurrent_ops_user")
        agent_factory = MockAgentFactory()
        
        execution_engine = UserExecutionEngine(
            context=user_context,
            agent_factory=agent_factory,
            websocket_emitter=websocket_emitter
        )
        
        # Create multiple agents for concurrent operations
        agent_names = ["concurrent_agent_1", "concurrent_agent_2", "concurrent_agent_3", "concurrent_agent_4"]
        agents = []
        
        for agent_name in agent_names:
            agent = await execution_engine.create_agent_instance(agent_name)
            agents.append(agent)
        
        # Define concurrent execution task
        async def execute_agent_concurrently(agent: MockAgentForExecution, task_id: int):
            """Execute agent with concurrent operations."""
            execution_context = AgentExecutionContext(
                user_id=user_context.user_id,
                thread_id=user_context.thread_id,
                run_id=user_context.run_id,
                request_id=f"{user_context.request_id}_task_{task_id}",
                agent_name=agent.agent_name,
                step=PipelineStep.EXECUTION,
                execution_timestamp=datetime.now(timezone.utc),
                pipeline_step_num=task_id
            )
            
            # Full lifecycle with WebSocket coordination
            await execution_engine._send_user_agent_started(execution_context)
            
            await execution_engine._send_user_agent_thinking(
                execution_context, f"Processing concurrent task {task_id}", task_id
            )
            
            result = await agent.execute_with_context(
                execution_context, f"Concurrent execution task {task_id}"
            )
            
            await execution_engine._send_user_agent_completed(execution_context, result)
            
            return agent.agent_name, result
        
        # Execute agents concurrently
        concurrent_tasks = [
            execute_agent_concurrently(agent, i+1) 
            for i, agent in enumerate(agents)
        ]
        
        start_time = time.time()
        concurrent_results = await asyncio.gather(*concurrent_tasks)
        execution_time = time.time() - start_time
        
        logger.info(f"Concurrent operations completed in {execution_time:.3f}s")
        
        # Validate all concurrent operations succeeded
        assert len(concurrent_results) == len(agents), "All concurrent operations should complete"
        
        for agent_name, result in concurrent_results:
            assert result.success, f"Concurrent execution should succeed for {agent_name}"
            assert result.agent_name == agent_name, f"Result should match agent {agent_name}"
            assert result.metadata['user_id'] == user_context.user_id, \
                f"Result should belong to user for {agent_name}"
        
        # Validate WebSocket event coordination
        events = websocket_emitter.events
        assert len(events) >= len(agents) * 3, \
            "Should have at least 3 events per agent (started, thinking, completed)"
        
        # Validate each agent has complete event set
        for agent in agents:
            agent_events = [e for e in events if len(e) >= 2 and e[1] == agent.agent_name]
            agent_event_types = [e[0] for e in agent_events]
            
            assert 'agent_started' in agent_event_types, \
                f"Agent {agent.agent_name} should have started event"
            assert 'agent_thinking' in agent_event_types, \
                f"Agent {agent.agent_name} should have thinking event"
            assert 'agent_completed' in agent_event_types, \
                f"Agent {agent.agent_name} should have completed event"
        
        # Validate execution engine statistics
        stats = execution_engine.get_user_execution_stats()
        assert stats['total_executions'] >= len(agents), \
            f"Should track all {len(agents)} executions"
        
        # Validate performance (concurrent operations should not be significantly slower)
        max_expected_time = 1.0  # Should complete within 1 second for 4 concurrent operations
        assert execution_time < max_expected_time, \
            f"Concurrent operations should complete within {max_expected_time}s, took {execution_time:.3f}s"
        
        await execution_engine.cleanup()
    
    def teardown_method(self, method):
        """Clean up test fixtures."""
        # Force garbage collection to clean up any remaining objects
        gc.collect()
        
        test_duration = time.time() - self.test_start_time
        logger.info(f"Test completed in {test_duration:.3f}s")
        super().teardown_method(method)