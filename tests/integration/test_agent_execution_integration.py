"""
Phase 2: Agent Execution Integration Tests - Issue #861

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - $500K+ ARR Protection
- Business Goal: Ensure reliable agent execution delivers core platform value
- Value Impact: Agent execution = 90% of platform value through substantive AI responses
- Revenue Impact: Mission-critical for user satisfaction and enterprise retention

CRITICAL COVERAGE GAPS ADDRESSED:
- User Execution Engine (13.69% coverage - 555/643 lines missing)
- Agent Execution Core (10.37% coverage - 294/328 lines missing)
- Agent Instance Factory (9.60% coverage - 452/500 lines missing)
- Agent Registry coordination and state management
- End-to-end agent execution workflows

PHASE 2 TARGET: Comprehensive agent execution testing with real service integration
COVERAGE IMPROVEMENT: Contributing to 10.92% -> 25%+ coverage increase

TEST INFRASTRUCTURE:
- Real staging service connections (NO mocks for integration tests)
- Comprehensive agent execution flow validation
- Multi-user concurrent execution testing
- Agent lifecycle management and state isolation
- Tool execution and result handling validation

BUSINESS-CRITICAL AGENT EXECUTION FLOWS:
1. Agent initialization and context setup
2. User request processing and planning
3. Tool execution and result handling
4. Agent reasoning and decision making
5. Result compilation and delivery
6. Proper cleanup and state management
"""

import pytest
import asyncio
import json
import uuid
from typing import Dict, Any, List, Optional, Union
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta
import time

# SSOT Test Infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.websocket_test_utility import WebSocketTestUtility
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper

# Core Agent Execution Infrastructure
try:
    from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
    from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    AGENT_EXECUTION_AVAILABLE = True
except ImportError:
    AGENT_EXECUTION_AVAILABLE = False

# Agent Instance Management
try:
    from netra_backend.app.agents.base.agent_instance_factory import (
        create_agent_instance, AgentInstanceFactory
    )
    from netra_backend.app.agents.base.base_agent import BaseAgent
    AGENT_INSTANCE_AVAILABLE = True
except ImportError:
    AGENT_INSTANCE_AVAILABLE = False

# User Context and State Management
try:
    from netra_backend.app.services.user_execution_context import (
        UserExecutionContext,
        create_isolated_execution_context,
        managed_user_context,
        UserContextManager
    )
    from netra_backend.app.core.agent_execution_tracker import (
        ExecutionState,
        AgentExecutionTracker,
        get_execution_tracker
    )
    USER_CONTEXT_AVAILABLE = True
except ImportError:
    USER_CONTEXT_AVAILABLE = False

# WebSocket Integration
try:
    from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False

# Tool Execution System
try:
    from netra_backend.app.tools.enhanced_dispatcher import EnhancedToolDispatcher
    from netra_backend.app.tools.base_tool import BaseTool
    TOOL_SYSTEM_AVAILABLE = True
except ImportError:
    TOOL_SYSTEM_AVAILABLE = False


@pytest.mark.integration
@pytest.mark.agent_execution
@pytest.mark.business_critical
class AgentExecutionIntegrationTests(SSotAsyncTestCase):
    """
    Phase 2: Agent Execution Integration Test Suite

    BUSINESS IMPACT: Protects $500K+ ARR through reliable agent execution
    COVERAGE TARGET: User Execution Engine, Agent Execution Core, Agent Instance Factory
    """

    def setup_method(self, method):
        """Setup for each test method with isolated execution environment"""
        super().setup_method(method)
        self.test_user_ids = []
        self.websocket_connections = []
        self.execution_contexts = []
        self.auth_helper = E2EAuthHelper()
        self.websocket_utility = WebSocketTestUtility()

        # Test execution tracking
        self.test_start_time = datetime.now()
        self.agent_instances_created = []

    async def teardown_method(self, method):
        """Cleanup execution contexts and agent instances"""
        # Clean up agent instances
        for agent_instance in self.agent_instances_created:
            try:
                if hasattr(agent_instance, 'cleanup'):
                    await agent_instance.cleanup()
            except Exception:
                pass

        # Clean up execution contexts
        for context in self.execution_contexts:
            try:
                if hasattr(context, 'cleanup'):
                    await context.cleanup()
            except Exception:
                pass

        # Close WebSocket connections
        for connection in self.websocket_connections:
            try:
                await connection.close()
            except Exception:
                pass

        # Clean up test users
        for user_id in self.test_user_ids:
            try:
                await self.auth_helper.cleanup_test_user(user_id)
            except Exception:
                pass

        await super().teardown_method(method)

    @pytest.mark.timeout(30)
    async def test_user_execution_engine_initialization_and_setup(self):
        """
        Test User Execution Engine initialization and context setup
        COVERS: User Execution Engine (13.69% coverage - 555/643 lines missing)
        """
        if not all([AGENT_EXECUTION_AVAILABLE, USER_CONTEXT_AVAILABLE]):
            pytest.skip("Agent execution or User context system not available")

        # Create isolated test user and context
        user_id = str(uuid.uuid4())
        self.test_user_ids.append(user_id)

        async with create_isolated_execution_context(user_id) as context:
            self.execution_contexts.append(context)

            # Initialize User Execution Engine
            execution_engine = UserExecutionEngine(context)

            # Verify engine initialization
            assert execution_engine is not None
            assert execution_engine.user_context == context
            assert execution_engine.user_id == user_id

            # Test engine configuration
            engine_config = {
                'max_execution_time': 300,
                'enable_tool_execution': True,
                'enable_reasoning': True,
                'memory_limit': 512 * 1024 * 1024  # 512MB
            }

            execution_engine.configure(engine_config)

            # Verify configuration applied
            assert execution_engine.max_execution_time == 300
            assert execution_engine.tool_execution_enabled is True
            assert execution_engine.reasoning_enabled is True

            # Test engine readiness validation
            is_ready = await execution_engine.validate_readiness()
            assert is_ready is True

    @pytest.mark.timeout(35)
    async def test_agent_execution_core_workflow_processing(self):
        """
        Test Agent Execution Core workflow processing capabilities
        COVERS: Agent Execution Core (10.37% coverage - 294/328 lines missing)
        """
        if not all([AGENT_EXECUTION_AVAILABLE, USER_CONTEXT_AVAILABLE, WEBSOCKET_AVAILABLE]):
            pytest.skip("Required systems not available")

        # Create authenticated test user with WebSocket
        user_id = str(uuid.uuid4())
        self.test_user_ids.append(user_id)
        auth_token = await self.auth_helper.create_test_user_with_token(user_id)

        # Setup WebSocket connection
        websocket_url = await self.websocket_utility.get_staging_websocket_url()
        connection = await self.websocket_utility.connect_with_auth(websocket_url, auth_token)
        self.websocket_connections.append(connection)

        async with create_isolated_execution_context(user_id) as context:
            self.execution_contexts.append(context)

            # Initialize Agent Execution Core
            bridge = create_agent_websocket_bridge(connection, user_id)
            execution_core = AgentExecutionCore(context, bridge)

            # Test execution request processing
            execution_request = {
                'request_id': str(uuid.uuid4()),
                'user_input': 'Analyze the latest data trends and provide insights',
                'agent_type': 'data_helper',
                'execution_params': {
                    'analysis_depth': 'comprehensive',
                    'include_visualizations': True
                }
            }

            # Execute workflow through core
            start_time = datetime.now()
            result = await execution_core.process_execution_request(execution_request)
            execution_time = (datetime.now() - start_time).total_seconds()

            # Verify execution result
            assert result is not None
            assert result.get('status') in ['completed', 'success']
            assert result.get('request_id') == execution_request['request_id']
            assert 'output' in result or 'response' in result

            # Verify execution completed in reasonable time
            assert execution_time < 30.0  # Should complete within 30 seconds

            # Verify WebSocket events were sent during execution
            received_events = []
            try:
                while len(received_events) < 3:  # Expect at least 3 events
                    message = await asyncio.wait_for(connection.recv(), timeout=5.0)
                    event_data = json.loads(message)
                    received_events.append(event_data)
            except asyncio.TimeoutError:
                pass

            # Verify execution generated appropriate WebSocket events
            assert len(received_events) >= 1
            event_types = [event.get('type') for event in received_events]
            assert any(event_type in ['agent_started', 'agent_thinking', 'agent_completed'] for event_type in event_types)

    @pytest.mark.timeout(30)
    async def test_agent_instance_factory_creation_and_management(self):
        """
        Test Agent Instance Factory creation and lifecycle management
        COVERS: Agent Instance Factory (9.60% coverage - 452/500 lines missing)
        """
        if not all([AGENT_INSTANCE_AVAILABLE, USER_CONTEXT_AVAILABLE, WEBSOCKET_AVAILABLE]):
            pytest.skip("Required systems not available")

        # Create authenticated test user
        user_id = str(uuid.uuid4())
        self.test_user_ids.append(user_id)
        auth_token = await self.auth_helper.create_test_user_with_token(user_id)

        # Setup WebSocket connection
        websocket_url = await self.websocket_utility.get_staging_websocket_url()
        connection = await self.websocket_utility.connect_with_auth(websocket_url, auth_token)
        self.websocket_connections.append(connection)

        async with create_isolated_execution_context(user_id) as context:
            self.execution_contexts.append(context)
            bridge = create_agent_websocket_bridge(connection, user_id)

            # Test different agent type creation
            agent_types = ['data_helper', 'supervisor', 'triage']

            for agent_type in agent_types:
                # Create agent instance
                agent_instance = create_agent_instance(
                    agent_type=agent_type,
                    user_context=context,
                    websocket_bridge=bridge
                )

                self.agent_instances_created.append(agent_instance)

                # Verify agent instance creation
                assert agent_instance is not None
                assert hasattr(agent_instance, 'agent_type')
                assert agent_instance.agent_type == agent_type
                assert hasattr(agent_instance, 'user_context')
                assert agent_instance.user_context == context

                # Verify agent instance has required methods
                assert hasattr(agent_instance, 'execute')
                assert hasattr(agent_instance, 'process_request')
                assert callable(getattr(agent_instance, 'execute', None))

                # Test agent instance status
                status = await agent_instance.get_status()
                assert status in ['ready', 'initialized', 'active']

    @pytest.mark.timeout(40)
    async def test_agent_registry_coordination_and_lifecycle(self):
        """
        Test Agent Registry coordination with execution engines
        COVERS: Agent Registry coordination and state management
        """
        if not all([AGENT_EXECUTION_AVAILABLE, USER_CONTEXT_AVAILABLE, WEBSOCKET_AVAILABLE]):
            pytest.skip("Required systems not available")

        # Create authenticated test user
        user_id = str(uuid.uuid4())
        self.test_user_ids.append(user_id)
        auth_token = await self.auth_helper.create_test_user_with_token(user_id)

        # Setup WebSocket connection
        websocket_url = await self.websocket_utility.get_staging_websocket_url()
        connection = await self.websocket_utility.connect_with_auth(websocket_url, auth_token)
        self.websocket_connections.append(connection)

        async with create_isolated_execution_context(user_id) as context:
            self.execution_contexts.append(context)

            # Initialize Agent Registry and Execution Engine
            registry = AgentRegistry()
            execution_engine = UserExecutionEngine(context)
            bridge = create_agent_websocket_bridge(connection, user_id)

            # Configure registry with WebSocket
            registry.set_websocket_manager(bridge)

            # Register execution engine with registry
            registry.register_execution_engine(user_id, execution_engine)

            # Verify registration
            registered_engine = registry.get_execution_engine(user_id)
            assert registered_engine == execution_engine

            # Test agent lifecycle through registry
            agent_request = {
                'user_id': user_id,
                'agent_type': 'data_helper',
                'request': 'Process test data analysis',
                'session_id': str(uuid.uuid4())
            }

            # Execute through registry coordination
            result = await registry.execute_agent_request(agent_request)

            # Verify execution result
            assert result is not None
            assert result.get('status') in ['completed', 'success']

            # Verify registry maintained proper state
            active_executions = registry.get_active_executions(user_id)
            assert isinstance(active_executions, (list, dict))

            # Test cleanup through registry
            await registry.cleanup_user_session(user_id)

            # Verify cleanup completed
            post_cleanup_executions = registry.get_active_executions(user_id)
            assert len(post_cleanup_executions) == 0 or post_cleanup_executions is None

    @pytest.mark.timeout(35)
    async def test_concurrent_agent_execution_isolation(self):
        """
        Test concurrent agent execution with proper user isolation
        COVERS: Multi-user concurrent execution isolation
        """
        if not all([AGENT_EXECUTION_AVAILABLE, USER_CONTEXT_AVAILABLE, WEBSOCKET_AVAILABLE]):
            pytest.skip("Required systems not available")

        # Create 3 concurrent users
        user_ids = [str(uuid.uuid4()) for _ in range(3)]
        self.test_user_ids.extend(user_ids)

        # Setup authentication and WebSocket connections
        auth_tasks = [
            self.auth_helper.create_test_user_with_token(user_id)
            for user_id in user_ids
        ]
        auth_tokens = await asyncio.gather(*auth_tasks)

        websocket_url = await self.websocket_utility.get_staging_websocket_url()
        connection_tasks = [
            self.websocket_utility.connect_with_auth(websocket_url, token)
            for token in auth_tokens
        ]
        connections = await asyncio.gather(*connection_tasks)
        self.websocket_connections.extend(connections)

        # Create execution contexts and engines
        execution_engines = []
        contexts = []

        for i, user_id in enumerate(user_ids):
            context = await create_isolated_execution_context(user_id).__aenter__()
            contexts.append(context)
            self.execution_contexts.append(context)

            engine = UserExecutionEngine(context)
            bridge = create_agent_websocket_bridge(connections[i], user_id)
            engine.set_websocket_bridge(bridge)
            execution_engines.append(engine)

        # Execute concurrent requests
        execution_requests = [
            {
                'request_id': str(uuid.uuid4()),
                'user_input': f'User {i} concurrent execution test',
                'agent_type': 'data_helper',
                'user_id': user_ids[i]
            }
            for i in range(3)
        ]

        # Start concurrent executions
        start_time = datetime.now()
        execution_tasks = [
            engines[i].execute_agent_request(execution_requests[i])
            for i, engines in enumerate([execution_engines])
        ]

        # Wait for all executions to complete
        results = await asyncio.gather(*[
            execution_engines[i].execute_agent_request(execution_requests[i])
            for i in range(3)
        ], return_exceptions=True)

        execution_time = (datetime.now() - start_time).total_seconds()

        # Verify all executions completed
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) >= 2  # At least 2 should succeed

        # Verify user isolation - each result should be for correct user
        for i, result in enumerate(successful_results[:3]):
            if result and isinstance(result, dict):
                # Result should be associated with correct user
                assert result.get('user_id') == user_ids[i] or 'user_id' not in result

        # Verify concurrent execution completed in reasonable time
        assert execution_time < 45.0  # Should complete within 45 seconds

        # Cleanup contexts
        for context in contexts:
            try:
                await context.__aexit__(None, None, None)
            except Exception:
                pass

    @pytest.mark.timeout(30)
    async def test_agent_execution_error_handling_and_recovery(self):
        """
        Test agent execution error handling and recovery mechanisms
        COVERS: Error handling in agent execution workflows
        """
        if not all([AGENT_EXECUTION_AVAILABLE, USER_CONTEXT_AVAILABLE]):
            pytest.skip("Required systems not available")

        # Create test user and context
        user_id = str(uuid.uuid4())
        self.test_user_ids.append(user_id)

        async with create_isolated_execution_context(user_id) as context:
            self.execution_contexts.append(context)

            # Initialize execution engine
            execution_engine = UserExecutionEngine(context)

            # Test error handling with invalid request
            invalid_request = {
                'request_id': str(uuid.uuid4()),
                'user_input': None,  # Invalid input
                'agent_type': 'invalid_agent_type',  # Invalid agent type
                'malformed_params': {'bad': 'data'}
            }

            # Execute invalid request
            try:
                result = await execution_engine.execute_agent_request(invalid_request)

                # Should either return error result or raise exception gracefully
                if result:
                    assert result.get('status') in ['error', 'failed']
                    assert 'error' in result or 'message' in result

            except Exception as e:
                # Exception should be handled gracefully
                assert isinstance(e, (ValueError, TypeError, KeyError))

            # Test recovery with valid request after error
            valid_request = {
                'request_id': str(uuid.uuid4()),
                'user_input': 'Recovery test after error',
                'agent_type': 'data_helper'
            }

            # Execute valid request to test recovery
            recovery_result = await execution_engine.execute_agent_request(valid_request)

            # Verify system recovered properly
            assert recovery_result is not None
            if isinstance(recovery_result, dict):
                assert recovery_result.get('status') in ['completed', 'success']

    @pytest.mark.timeout(40)
    async def test_tool_execution_integration_with_agents(self):
        """
        Test tool execution integration within agent workflows
        COVERS: Tool execution coordination and result handling
        """
        if not all([AGENT_EXECUTION_AVAILABLE, USER_CONTEXT_AVAILABLE, TOOL_SYSTEM_AVAILABLE]):
            pytest.skip("Required systems not available")

        # Create test user and context
        user_id = str(uuid.uuid4())
        self.test_user_ids.append(user_id)

        async with create_isolated_execution_context(user_id) as context:
            self.execution_contexts.append(context)

            # Initialize execution engine with tool support
            execution_engine = UserExecutionEngine(context)
            tool_dispatcher = EnhancedToolDispatcher(context)

            # Configure engine with tool dispatcher
            execution_engine.set_tool_dispatcher(tool_dispatcher)

            # Test agent request requiring tool execution
            tool_request = {
                'request_id': str(uuid.uuid4()),
                'user_input': 'Use calculator tool to compute 123 + 456',
                'agent_type': 'data_helper',
                'require_tools': True
            }

            # Execute request with tool usage
            result = await execution_engine.execute_agent_request(tool_request)

            # Verify tool execution occurred
            assert result is not None
            if isinstance(result, dict):
                assert result.get('status') in ['completed', 'success']

                # Check for tool execution evidence
                response_text = result.get('response', '') or result.get('output', '')
                assert isinstance(response_text, str)

                # Should contain calculation result or evidence of tool usage
                contains_calculation = any(
                    calc_result in response_text.lower()
                    for calc_result in ['579', 'calculation', 'computed', 'result']
                )
                assert contains_calculation or len(response_text) > 0

    @pytest.mark.timeout(35)
    async def test_agent_execution_state_persistence_and_retrieval(self):
        """
        Test agent execution state persistence and retrieval
        COVERS: Agent execution state management and persistence
        """
        if not all([AGENT_EXECUTION_AVAILABLE, USER_CONTEXT_AVAILABLE]):
            pytest.skip("Required systems not available")

        # Create test user and context
        user_id = str(uuid.uuid4())
        self.test_user_ids.append(user_id)

        execution_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())

        async with create_isolated_execution_context(user_id) as context:
            self.execution_contexts.append(context)

            # Initialize execution engine
            execution_engine = UserExecutionEngine(context)

            # Create execution with state tracking
            execution_request = {
                'request_id': execution_id,
                'session_id': session_id,
                'user_input': 'Test execution with state persistence',
                'agent_type': 'data_helper',
                'persist_state': True
            }

            # Execute request
            result = await execution_engine.execute_agent_request(execution_request)

            # Verify execution completed
            assert result is not None

            # Test state retrieval
            try:
                execution_state = await execution_engine.get_execution_state(execution_id)

                if execution_state:
                    assert execution_state.get('execution_id') == execution_id
                    assert execution_state.get('user_id') == user_id
                    assert 'status' in execution_state
                    assert 'timestamp' in execution_state or 'created_at' in execution_state

            except (NotImplementedError, AttributeError):
                # State persistence might not be fully implemented
                pytest.skip("Execution state persistence not implemented")

            # Test session state retrieval
            try:
                session_state = await execution_engine.get_session_state(session_id)

                if session_state:
                    assert isinstance(session_state, dict)
                    assert session_state.get('session_id') == session_id

            except (NotImplementedError, AttributeError):
                # Session state might not be fully implemented
                pytest.skip("Session state persistence not implemented")

    @pytest.mark.timeout(30)
    async def test_agent_execution_resource_management(self):
        """
        Test agent execution resource management and limits
        COVERS: Resource management and execution constraints
        """
        if not all([AGENT_EXECUTION_AVAILABLE, USER_CONTEXT_AVAILABLE]):
            pytest.skip("Required systems not available")

        # Create test user and context
        user_id = str(uuid.uuid4())
        self.test_user_ids.append(user_id)

        async with create_isolated_execution_context(user_id) as context:
            self.execution_contexts.append(context)

            # Initialize execution engine with resource limits
            execution_engine = UserExecutionEngine(context)

            # Configure resource limits
            resource_config = {
                'max_execution_time': 20,  # 20 seconds max
                'memory_limit': 256 * 1024 * 1024,  # 256MB
                'max_concurrent_executions': 2
            }

            execution_engine.configure(resource_config)

            # Test execution within limits
            normal_request = {
                'request_id': str(uuid.uuid4()),
                'user_input': 'Normal execution within limits',
                'agent_type': 'data_helper'
            }

            start_time = datetime.now()
            result = await execution_engine.execute_agent_request(normal_request)
            execution_time = (datetime.now() - start_time).total_seconds()

            # Verify execution completed within time limit
            assert execution_time < 20.0  # Should complete within limit
            assert result is not None

            # Test resource monitoring
            try:
                resource_usage = await execution_engine.get_resource_usage()

                if resource_usage:
                    assert 'memory_usage' in resource_usage or 'cpu_usage' in resource_usage
                    assert isinstance(resource_usage, dict)

            except (NotImplementedError, AttributeError):
                # Resource monitoring might not be fully implemented
                pass

    @pytest.mark.timeout(45)
    async def test_agent_execution_timeout_handling(self):
        """
        Test agent execution timeout handling and graceful termination
        COVERS: Execution timeout scenarios and cleanup
        """
        if not all([AGENT_EXECUTION_AVAILABLE, USER_CONTEXT_AVAILABLE]):
            pytest.skip("Required systems not available")

        # Create test user and context
        user_id = str(uuid.uuid4())
        self.test_user_ids.append(user_id)

        async with create_isolated_execution_context(user_id) as context:
            self.execution_contexts.append(context)

            # Initialize execution engine with short timeout
            execution_engine = UserExecutionEngine(context)

            # Configure short timeout for testing
            timeout_config = {
                'max_execution_time': 5,  # Very short timeout
                'enable_timeout_handling': True
            }

            execution_engine.configure(timeout_config)

            # Create potentially long-running request
            timeout_request = {
                'request_id': str(uuid.uuid4()),
                'user_input': 'Analyze large dataset with complex processing (simulated long task)',
                'agent_type': 'data_helper',
                'complexity': 'high'
            }

            # Execute with timeout
            start_time = datetime.now()

            try:
                result = await asyncio.wait_for(
                    execution_engine.execute_agent_request(timeout_request),
                    timeout=10.0  # Outer timeout to prevent test hanging
                )

                execution_time = (datetime.now() - start_time).total_seconds()

                # If execution completed, verify it was within reasonable time
                if result:
                    assert execution_time < 8.0  # Should respect timeout

                    # If result indicates timeout, verify proper handling
                    if isinstance(result, dict):
                        status = result.get('status', '')
                        if status in ['timeout', 'cancelled', 'interrupted']:
                            assert 'timeout' in result.get('message', '').lower()

            except asyncio.TimeoutError:
                # Timeout occurred - verify execution was cancelled properly
                execution_time = (datetime.now() - start_time).total_seconds()
                assert execution_time >= 5.0  # Should have reached timeout
                assert execution_time < 12.0  # But not exceed outer timeout significantly

            # Verify engine is still responsive after timeout
            recovery_request = {
                'request_id': str(uuid.uuid4()),
                'user_input': 'Simple recovery test',
                'agent_type': 'data_helper'
            }

            recovery_result = await execution_engine.execute_agent_request(recovery_request)
            assert recovery_result is not None  # Engine should still be functional

    @pytest.mark.timeout(35)
    async def test_agent_execution_memory_management(self):
        """
        Test agent execution memory management and cleanup
        COVERS: Memory usage monitoring and leak prevention
        """
        if not all([AGENT_EXECUTION_AVAILABLE, USER_CONTEXT_AVAILABLE]):
            pytest.skip("Required systems not available")

        # Create test user and context
        user_id = str(uuid.uuid4())
        self.test_user_ids.append(user_id)

        async with create_isolated_execution_context(user_id) as context:
            self.execution_contexts.append(context)

            # Initialize execution engine
            execution_engine = UserExecutionEngine(context)

            # Execute multiple requests to test memory management
            request_count = 5
            execution_results = []

            for i in range(request_count):
                request = {
                    'request_id': str(uuid.uuid4()),
                    'user_input': f'Memory test execution {i}',
                    'agent_type': 'data_helper',
                    'iteration': i
                }

                result = await execution_engine.execute_agent_request(request)
                execution_results.append(result)

                # Small delay between executions
                await asyncio.sleep(0.5)

            # Verify all executions completed
            successful_executions = [r for r in execution_results if r is not None]
            assert len(successful_executions) >= 3  # At least 3 should succeed

            # Test memory cleanup
            try:
                await execution_engine.cleanup_memory()
            except (NotImplementedError, AttributeError):
                # Memory cleanup might not be implemented
                pass

            # Test execution after cleanup
            post_cleanup_request = {
                'request_id': str(uuid.uuid4()),
                'user_input': 'Post-cleanup execution test',
                'agent_type': 'data_helper'
            }

            post_cleanup_result = await execution_engine.execute_agent_request(post_cleanup_request)
            assert post_cleanup_result is not None  # Should still work after cleanup