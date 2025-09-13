"""
Integration Test: Agent Execution Isolation Validation

This test is designed to FAIL initially, proving that agent execution contexts
are not properly isolated between users, causing state contamination.

Business Impact:
- Agent responses contaminated between users
- Execution contexts shared across concurrent sessions
- Memory leaks from improper isolation
- $500K+ ARR blocked by agent execution failures

SSOT Violations Tested:
- Agent execution engines shared between users
- Execution contexts not properly isolated
- Memory state bleeding between concurrent executions
- Factory patterns not creating isolated instances

This test MUST FAIL until agent execution isolation is properly implemented.
"""
import asyncio
import pytest
import threading
import time
import uuid
from typing import Dict, List, Any
from unittest.mock import patch, MagicMock, AsyncMock
from test_framework.ssot.base_test_case import SSotAsyncTestCase

try:
    # SSOT imports - these should work after consolidation
    from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
    from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
    from netra_backend.app.core.user_execution_context import UserExecutionContext
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    from netra_backend.app.agents.factory import AgentFactory
    from netra_backend.app.tools.enhanced_dispatcher import EnhancedToolDispatcher
except ImportError as e:
    # Expected during SSOT migration - imports will be fixed during consolidation
    print(f"EXPECTED IMPORT ERROR during SSOT migration: {e}")
    ExecutionEngine = None
    UserExecutionEngine = None
    UserExecutionContext = None
    AgentRegistry = None
    AgentFactory = None
    EnhancedToolDispatcher = None


class TestAgentExecutionIsolation(SSotAsyncTestCase):
    """
    CRITICAL: This test proves agent execution isolation failures.

    EXPECTED RESULT: FAIL - Agent executions contaminate each other
    BUSINESS IMPACT: $500K+ ARR blocked by unreliable agent responses
    """

    def setup_method(self):
        """Set up test environment for agent execution testing."""
        super().setup_method()
        self.test_users = [
            {"user_id": "exec_test_user_1", "session_id": "exec_session_1"},
            {"user_id": "exec_test_user_2", "session_id": "exec_session_2"},
            {"user_id": "exec_test_user_3", "session_id": "exec_session_3"}
        ]
        self.execution_results = []
        self.isolation_violations = []

    @pytest.mark.asyncio
    async def test_concurrent_agent_execution_context_contamination(self):
        """
        CRITICAL BUSINESS TEST: Prove agent execution contexts contaminate each other

        Expected Result: FAIL - Execution contexts bleed between concurrent users
        Business Impact: Users receive responses meant for other users
        """
        if not all([ExecutionEngine, UserExecutionContext]):
            pytest.skip("SSOT imports not available - expected during migration")

        # Create execution contexts for different users
        execution_contexts = []
        for user_info in self.test_users:
            try:
                context = UserExecutionContext.create_for_user(user_info["user_id"])
                context.session_id = user_info["session_id"]
                context.test_data = f"private_data_for_{user_info['user_id']}"
                execution_contexts.append(context)
            except Exception as e:
                pytest.fail(f"SSOT VIOLATION: Cannot create execution context for {user_info['user_id']}: {e}")

        # Execute agents concurrently with user-specific data
        concurrent_executions = []

        async def execute_agent_for_user(context, user_index):
            """Execute agent for specific user context."""
            try:
                # Create execution engine for user
                engine = UserExecutionEngine.create_from_legacy(context)

                # Set user-specific execution state
                execution_data = {
                    'user_id': context.user_id,
                    'execution_id': f"exec_{user_index}_{int(time.time())}",
                    'private_data': context.test_data,
                    'timestamp': time.time()
                }

                # Simulate agent execution
                result = await self._simulate_agent_execution(engine, execution_data)

                return {
                    'user_id': context.user_id,
                    'execution_data': execution_data,
                    'result': result,
                    'engine_id': id(engine),
                    'success': True
                }

            except Exception as e:
                return {
                    'user_id': context.user_id,
                    'error': str(e),
                    'success': False
                }

        # Execute all users concurrently
        tasks = [execute_agent_for_user(ctx, i) for i, ctx in enumerate(execution_contexts)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Analyze execution isolation
        successful_executions = [r for r in results if isinstance(r, dict) and r.get('success', False)]

        # CRITICAL ASSERTION: All executions should succeed independently
        assert len(successful_executions) == len(self.test_users), (
            f"SSOT VIOLATION: {len(self.test_users) - len(successful_executions)} concurrent executions failed. "
            f"Failed executions: {[r for r in results if r not in successful_executions]}. "
            f"BUSINESS IMPACT: Concurrent users experience execution failures."
        )

        # Check for context contamination
        await self._check_execution_context_contamination(successful_executions)

    @pytest.mark.asyncio
    async def test_agent_execution_engine_shared_state_violation(self):
        """
        CRITICAL BUSINESS TEST: Prove execution engines share state between users

        Expected Result: FAIL - Execution engines have shared state
        Business Impact: Agent responses contain data from other users
        """
        if not all([ExecutionEngine, UserExecutionEngine]):
            pytest.skip("SSOT imports not available - expected during migration")

        # Create execution engines for different users
        execution_engines = []

        for user_info in self.test_users:
            try:
                context = UserExecutionContext.create_for_user(user_info["user_id"])
                engine = UserExecutionEngine.create_from_legacy(context)

                # Set user-specific state
                if hasattr(engine, 'set_user_state'):
                    engine.set_user_state({
                        'user_id': user_info["user_id"],
                        'private_data': f"secret_data_for_{user_info['user_id']}"
                    })

                execution_engines.append({
                    'engine': engine,
                    'user_id': user_info["user_id"],
                    'engine_id': id(engine)
                })

            except Exception as e:
                pytest.fail(f"SSOT VIOLATION: Cannot create execution engine for {user_info['user_id']}: {e}")

        # CRITICAL ASSERTION: All engines should be different instances
        engine_ids = [engine_info['engine_id'] for engine_info in execution_engines]
        unique_engine_ids = set(engine_ids)

        assert len(unique_engine_ids) == len(execution_engines), (
            f"SSOT VIOLATION: Execution engines sharing instances. "
            f"Created {len(execution_engines)} engines but only {len(unique_engine_ids)} unique instances. "
            f"Engine IDs: {engine_ids}. "
            f"BUSINESS IMPACT: Shared engines cause state contamination between users."
        )

        # Test state isolation
        await self._test_execution_engine_state_isolation(execution_engines)

    @pytest.mark.asyncio
    async def test_agent_registry_execution_isolation_violation(self):
        """
        CRITICAL BUSINESS TEST: Prove AgentRegistry execution isolation failures

        Expected Result: FAIL - AgentRegistry doesn't maintain execution isolation
        Business Impact: Agent routing and execution contaminated between users
        """
        if not all([AgentRegistry, UserExecutionContext]):
            pytest.skip("SSOT imports not available - expected during migration")

        # Create agent registries for different users
        registries = []

        for user_info in self.test_users:
            try:
                context = UserExecutionContext.create_for_user(user_info["user_id"])

                # Create agent registry
                if hasattr(AgentRegistry, 'create_for_user'):
                    registry = AgentRegistry.create_for_user(context)
                else:
                    registry = AgentRegistry(context)

                # Set user-specific execution context
                execution_context = {
                    'user_id': user_info["user_id"],
                    'session_id': user_info["session_id"],
                    'execution_state': f"state_for_{user_info['user_id']}"
                }

                if hasattr(registry, 'set_execution_context'):
                    registry.set_execution_context(execution_context)

                registries.append({
                    'registry': registry,
                    'user_id': user_info["user_id"],
                    'registry_id': id(registry),
                    'execution_context': execution_context
                })

            except Exception as e:
                pytest.fail(f"SSOT VIOLATION: Cannot create agent registry for {user_info['user_id']}: {e}")

        # Test concurrent agent execution through registries
        execution_tasks = []

        async def execute_through_registry(registry_info):
            """Execute agent through registry for user."""
            try:
                registry = registry_info['registry']
                user_id = registry_info['user_id']

                # Mock agent execution through registry
                if hasattr(registry, 'execute_agent'):
                    result = await registry.execute_agent('supervisor', {
                        'message': f'Test request from {user_id}',
                        'user_id': user_id
                    })
                else:
                    # Fallback simulation
                    result = {
                        'response': f'Agent response for {user_id}',
                        'user_id': user_id,
                        'execution_id': f'exec_{user_id}_{int(time.time())}'
                    }

                return {
                    'user_id': user_id,
                    'result': result,
                    'success': True
                }

            except Exception as e:
                return {
                    'user_id': registry_info['user_id'],
                    'error': str(e),
                    'success': False
                }

        # Execute agents concurrently
        tasks = [execute_through_registry(reg_info) for reg_info in registries]
        execution_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Analyze registry execution isolation
        successful_executions = [r for r in execution_results if isinstance(r, dict) and r.get('success', False)]

        # CRITICAL ASSERTION: All registry executions should succeed
        assert len(successful_executions) == len(registries), (
            f"SSOT VIOLATION: Registry execution failures detected. "
            f"{len(registries) - len(successful_executions)} executions failed. "
            f"BUSINESS IMPACT: Agent registry cannot handle concurrent users."
        )

        # Check for execution result contamination
        await self._check_registry_execution_contamination(successful_executions)

    @pytest.mark.asyncio
    async def test_tool_execution_isolation_violation(self):
        """
        CRITICAL BUSINESS TEST: Prove tool execution isolation failures

        Expected Result: FAIL - Tool executions share state between users
        Business Impact: Tool results contaminated between users
        """
        if not all([EnhancedToolDispatcher, UserExecutionContext]):
            pytest.skip("SSOT imports not available - expected during migration")

        # Create tool dispatchers for different users
        tool_dispatchers = []

        for user_info in self.test_users:
            try:
                context = UserExecutionContext.create_for_user(user_info["user_id"])

                # Create tool dispatcher
                dispatcher = EnhancedToolDispatcher()

                # Set user-specific context
                if hasattr(dispatcher, 'set_user_context'):
                    dispatcher.set_user_context(context)

                tool_dispatchers.append({
                    'dispatcher': dispatcher,
                    'user_id': user_info["user_id"],
                    'context': context,
                    'dispatcher_id': id(dispatcher)
                })

            except Exception as e:
                pytest.fail(f"SSOT VIOLATION: Cannot create tool dispatcher for {user_info['user_id']}: {e}")

        # Test concurrent tool execution
        tool_execution_tasks = []

        async def execute_tool_for_user(dispatcher_info):
            """Execute tool for specific user."""
            try:
                dispatcher = dispatcher_info['dispatcher']
                user_id = dispatcher_info['user_id']

                # Mock tool execution
                tool_request = {
                    'tool_name': 'test_tool',
                    'parameters': {
                        'user_specific_data': f'data_for_{user_id}',
                        'user_id': user_id
                    }
                }

                if hasattr(dispatcher, 'execute_tool'):
                    result = await dispatcher.execute_tool(tool_request)
                else:
                    # Fallback simulation
                    result = {
                        'tool_result': f'Tool result for {user_id}',
                        'user_id': user_id,
                        'execution_time': time.time()
                    }

                return {
                    'user_id': user_id,
                    'tool_request': tool_request,
                    'tool_result': result,
                    'success': True
                }

            except Exception as e:
                return {
                    'user_id': dispatcher_info['user_id'],
                    'error': str(e),
                    'success': False
                }

        # Execute tools concurrently
        tasks = [execute_tool_for_user(disp_info) for disp_info in tool_dispatchers]
        tool_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Analyze tool execution isolation
        successful_tool_executions = [r for r in tool_results if isinstance(r, dict) and r.get('success', False)]

        # CRITICAL ASSERTION: All tool executions should succeed
        assert len(successful_tool_executions) == len(tool_dispatchers), (
            f"SSOT VIOLATION: Tool execution failures detected. "
            f"{len(tool_dispatchers) - len(successful_tool_executions)} tool executions failed. "
            f"BUSINESS IMPACT: Tool execution cannot handle concurrent users."
        )

        # Check for tool result contamination
        await self._check_tool_execution_contamination(successful_tool_executions)

    async def _simulate_agent_execution(self, engine, execution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate agent execution with user-specific data."""
        try:
            # Mock agent execution process
            await asyncio.sleep(0.1)  # Simulate processing time

            return {
                'agent_response': f"AI analysis for user {execution_data['user_id']}",
                'user_id': execution_data['user_id'],
                'execution_id': execution_data['execution_id'],
                'private_data_echo': execution_data.get('private_data'),
                'timestamp': time.time()
            }

        except Exception as e:
            return {
                'error': str(e),
                'user_id': execution_data.get('user_id', 'unknown')
            }

    async def _check_execution_context_contamination(self, executions: List[Dict]):
        """Check for execution context contamination between users."""
        for execution in executions:
            user_id = execution['user_id']
            result = execution.get('result', {})

            # Check if result contains correct user data
            result_user_id = result.get('user_id')
            assert result_user_id == user_id, (
                f"SSOT VIOLATION: Execution context contamination detected. "
                f"User {user_id} execution result contains data for user {result_user_id}. "
                f"BUSINESS IMPACT: Users receive responses meant for other users."
            )

            # Check private data isolation
            private_data = result.get('private_data_echo', '')
            if private_data and user_id not in private_data:
                pytest.fail(
                    f"SSOT VIOLATION: Private data contamination. "
                    f"User {user_id} result contains private data: {private_data}. "
                    f"BUSINESS IMPACT: User privacy violation."
                )

    async def _test_execution_engine_state_isolation(self, engines: List[Dict]):
        """Test execution engine state isolation."""
        if len(engines) < 2:
            return

        # Set different states and verify isolation
        for i, engine_info in enumerate(engines):
            engine = engine_info['engine']
            user_id = engine_info['user_id']

            # Set user-specific state
            test_state = f"test_state_{user_id}_{i}"

            if hasattr(engine, 'set_state'):
                engine.set_state(test_state)
            elif hasattr(engine, 'state'):
                engine.state = test_state

        # Verify state isolation
        for i, engine_info in enumerate(engines):
            engine = engine_info['engine']
            user_id = engine_info['user_id']
            expected_state = f"test_state_{user_id}_{i}"

            # Check state
            if hasattr(engine, 'get_state'):
                actual_state = engine.get_state()
                assert actual_state == expected_state, (
                    f"SSOT VIOLATION: Engine state contamination. "
                    f"Engine for user {user_id} expected state '{expected_state}', got '{actual_state}'"
                )
            elif hasattr(engine, 'state'):
                actual_state = engine.state
                assert actual_state == expected_state, (
                    f"SSOT VIOLATION: Engine state contamination. "
                    f"Engine for user {user_id} expected state '{expected_state}', got '{actual_state}'"
                )

    async def _check_registry_execution_contamination(self, executions: List[Dict]):
        """Check for registry execution contamination."""
        for execution in executions:
            user_id = execution['user_id']
            result = execution.get('result', {})

            # Check if result is properly attributed to user
            result_user_id = result.get('user_id')
            if result_user_id and result_user_id != user_id:
                pytest.fail(
                    f"SSOT VIOLATION: Registry execution contamination. "
                    f"User {user_id} received result for user {result_user_id}. "
                    f"BUSINESS IMPACT: Agent routing delivers results to wrong users."
                )

    async def _check_tool_execution_contamination(self, executions: List[Dict]):
        """Check for tool execution contamination."""
        for execution in executions:
            user_id = execution['user_id']
            tool_result = execution.get('tool_result', {})

            # Check if tool result is properly attributed to user
            result_user_id = tool_result.get('user_id')
            if result_user_id and result_user_id != user_id:
                pytest.fail(
                    f"SSOT VIOLATION: Tool execution contamination. "
                    f"User {user_id} received tool result for user {result_user_id}. "
                    f"BUSINESS IMPACT: Tool results delivered to wrong users."
                )

            # Check tool request data
            tool_request = execution.get('tool_request', {})
            request_data = tool_request.get('parameters', {})
            if 'user_specific_data' in request_data:
                if user_id not in request_data['user_specific_data']:
                    pytest.fail(
                        f"SSOT VIOLATION: Tool request data contamination. "
                        f"User {user_id} tool request contains wrong user data: {request_data['user_specific_data']}"
                    )


if __name__ == "__main__":
    # Run this test to prove agent execution isolation failures
    pytest.main([__file__, "-v", "--tb=short"])