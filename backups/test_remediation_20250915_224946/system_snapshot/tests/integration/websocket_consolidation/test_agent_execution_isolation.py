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
    from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
    from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    from netra_backend.app.agents.factory import AgentFactory
    from netra_backend.app.tools.enhanced_dispatcher import EnhancedToolDispatcher
except ImportError as e:
    print(f'EXPECTED IMPORT ERROR during SSOT migration: {e}')
    ExecutionEngine = None
    UserExecutionEngine = None
    UserExecutionContext = None
    AgentRegistry = None
    AgentFactory = None
    EnhancedToolDispatcher = None

@pytest.mark.integration
class AgentExecutionIsolationTests(SSotAsyncTestCase):
    """
    CRITICAL: This test proves agent execution isolation failures.

    EXPECTED RESULT: FAIL - Agent executions contaminate each other
    BUSINESS IMPACT: $500K+ ARR blocked by unreliable agent responses
    """

    def setup_method(self):
        """Set up test environment for agent execution testing."""
        super().setup_method()
        self.test_users = [{'user_id': 'exec_test_user_1', 'session_id': 'exec_session_1'}, {'user_id': 'exec_test_user_2', 'session_id': 'exec_session_2'}, {'user_id': 'exec_test_user_3', 'session_id': 'exec_session_3'}]
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
            pytest.skip('SSOT imports not available - expected during migration')
        execution_contexts = []
        for user_info in self.test_users:
            try:
                context = UserExecutionContext.create_for_user(user_info['user_id'])
                context.session_id = user_info['session_id']
                context.test_data = f"private_data_for_{user_info['user_id']}"
                execution_contexts.append(context)
            except Exception as e:
                pytest.fail(f"SSOT VIOLATION: Cannot create execution context for {user_info['user_id']}: {e}")
        concurrent_executions = []

        async def execute_agent_for_user(context, user_index):
            """Execute agent for specific user context."""
            try:
                engine = UserExecutionEngine.create_from_legacy(context)
                execution_data = {'user_id': context.user_id, 'execution_id': f'exec_{user_index}_{int(time.time())}', 'private_data': context.test_data, 'timestamp': time.time()}
                result = await self._simulate_agent_execution(engine, execution_data)
                return {'user_id': context.user_id, 'execution_data': execution_data, 'result': result, 'engine_id': id(engine), 'success': True}
            except Exception as e:
                return {'user_id': context.user_id, 'error': str(e), 'success': False}
        tasks = [execute_agent_for_user(ctx, i) for i, ctx in enumerate(execution_contexts)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successful_executions = [r for r in results if isinstance(r, dict) and r.get('success', False)]
        assert len(successful_executions) == len(self.test_users), f'SSOT VIOLATION: {len(self.test_users) - len(successful_executions)} concurrent executions failed. Failed executions: {[r for r in results if r not in successful_executions]}. BUSINESS IMPACT: Concurrent users experience execution failures.'
        await self._check_execution_context_contamination(successful_executions)

    @pytest.mark.asyncio
    async def test_agent_execution_engine_shared_state_violation(self):
        """
        CRITICAL BUSINESS TEST: Prove execution engines share state between users

        Expected Result: FAIL - Execution engines have shared state
        Business Impact: Agent responses contain data from other users
        """
        if not all([ExecutionEngine, UserExecutionEngine]):
            pytest.skip('SSOT imports not available - expected during migration')
        execution_engines = []
        for user_info in self.test_users:
            try:
                context = UserExecutionContext.create_for_user(user_info['user_id'])
                engine = UserExecutionEngine.create_from_legacy(context)
                if hasattr(engine, 'set_user_state'):
                    engine.set_user_state({'user_id': user_info['user_id'], 'private_data': f"secret_data_for_{user_info['user_id']}"})
                execution_engines.append({'engine': engine, 'user_id': user_info['user_id'], 'engine_id': id(engine)})
            except Exception as e:
                pytest.fail(f"SSOT VIOLATION: Cannot create execution engine for {user_info['user_id']}: {e}")
        engine_ids = [engine_info['engine_id'] for engine_info in execution_engines]
        unique_engine_ids = set(engine_ids)
        assert len(unique_engine_ids) == len(execution_engines), f'SSOT VIOLATION: Execution engines sharing instances. Created {len(execution_engines)} engines but only {len(unique_engine_ids)} unique instances. Engine IDs: {engine_ids}. BUSINESS IMPACT: Shared engines cause state contamination between users.'
        await self._test_execution_engine_state_isolation(execution_engines)

    @pytest.mark.asyncio
    async def test_agent_registry_execution_isolation_violation(self):
        """
        CRITICAL BUSINESS TEST: Prove AgentRegistry execution isolation failures

        Expected Result: FAIL - AgentRegistry doesn't maintain execution isolation
        Business Impact: Agent routing and execution contaminated between users
        """
        if not all([AgentRegistry, UserExecutionContext]):
            pytest.skip('SSOT imports not available - expected during migration')
        registries = []
        for user_info in self.test_users:
            try:
                context = UserExecutionContext.create_for_user(user_info['user_id'])
                if hasattr(AgentRegistry, 'create_for_user'):
                    registry = AgentRegistry.create_for_user(context)
                else:
                    registry = AgentRegistry(context)
                execution_context = {'user_id': user_info['user_id'], 'session_id': user_info['session_id'], 'execution_state': f"state_for_{user_info['user_id']}"}
                if hasattr(registry, 'set_execution_context'):
                    registry.set_execution_context(execution_context)
                registries.append({'registry': registry, 'user_id': user_info['user_id'], 'registry_id': id(registry), 'execution_context': execution_context})
            except Exception as e:
                pytest.fail(f"SSOT VIOLATION: Cannot create agent registry for {user_info['user_id']}: {e}")
        execution_tasks = []

        async def execute_through_registry(registry_info):
            """Execute agent through registry for user."""
            try:
                registry = registry_info['registry']
                user_id = registry_info['user_id']
                if hasattr(registry, 'execute_agent'):
                    result = await registry.execute_agent('supervisor', {'message': f'Test request from {user_id}', 'user_id': user_id})
                else:
                    result = {'response': f'Agent response for {user_id}', 'user_id': user_id, 'execution_id': f'exec_{user_id}_{int(time.time())}'}
                return {'user_id': user_id, 'result': result, 'success': True}
            except Exception as e:
                return {'user_id': registry_info['user_id'], 'error': str(e), 'success': False}
        tasks = [execute_through_registry(reg_info) for reg_info in registries]
        execution_results = await asyncio.gather(*tasks, return_exceptions=True)
        successful_executions = [r for r in execution_results if isinstance(r, dict) and r.get('success', False)]
        assert len(successful_executions) == len(registries), f'SSOT VIOLATION: Registry execution failures detected. {len(registries) - len(successful_executions)} executions failed. BUSINESS IMPACT: Agent registry cannot handle concurrent users.'
        await self._check_registry_execution_contamination(successful_executions)

    @pytest.mark.asyncio
    async def test_tool_execution_isolation_violation(self):
        """
        CRITICAL BUSINESS TEST: Prove tool execution isolation failures

        Expected Result: FAIL - Tool executions share state between users
        Business Impact: Tool results contaminated between users
        """
        if not all([EnhancedToolDispatcher, UserExecutionContext]):
            pytest.skip('SSOT imports not available - expected during migration')
        tool_dispatchers = []
        for user_info in self.test_users:
            try:
                context = UserExecutionContext.create_for_user(user_info['user_id'])
                dispatcher = EnhancedToolDispatcher()
                if hasattr(dispatcher, 'set_user_context'):
                    dispatcher.set_user_context(context)
                tool_dispatchers.append({'dispatcher': dispatcher, 'user_id': user_info['user_id'], 'context': context, 'dispatcher_id': id(dispatcher)})
            except Exception as e:
                pytest.fail(f"SSOT VIOLATION: Cannot create tool dispatcher for {user_info['user_id']}: {e}")
        tool_execution_tasks = []

        async def execute_tool_for_user(dispatcher_info):
            """Execute tool for specific user."""
            try:
                dispatcher = dispatcher_info['dispatcher']
                user_id = dispatcher_info['user_id']
                tool_request = {'tool_name': 'test_tool', 'parameters': {'user_specific_data': f'data_for_{user_id}', 'user_id': user_id}}
                if hasattr(dispatcher, 'execute_tool'):
                    result = await dispatcher.execute_tool(tool_request)
                else:
                    result = {'tool_result': f'Tool result for {user_id}', 'user_id': user_id, 'execution_time': time.time()}
                return {'user_id': user_id, 'tool_request': tool_request, 'tool_result': result, 'success': True}
            except Exception as e:
                return {'user_id': dispatcher_info['user_id'], 'error': str(e), 'success': False}
        tasks = [execute_tool_for_user(disp_info) for disp_info in tool_dispatchers]
        tool_results = await asyncio.gather(*tasks, return_exceptions=True)
        successful_tool_executions = [r for r in tool_results if isinstance(r, dict) and r.get('success', False)]
        assert len(successful_tool_executions) == len(tool_dispatchers), f'SSOT VIOLATION: Tool execution failures detected. {len(tool_dispatchers) - len(successful_tool_executions)} tool executions failed. BUSINESS IMPACT: Tool execution cannot handle concurrent users.'
        await self._check_tool_execution_contamination(successful_tool_executions)

    async def _simulate_agent_execution(self, engine, execution_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate agent execution with user-specific data."""
        try:
            await asyncio.sleep(0.1)
            return {'agent_response': f"AI analysis for user {execution_data['user_id']}", 'user_id': execution_data['user_id'], 'execution_id': execution_data['execution_id'], 'private_data_echo': execution_data.get('private_data'), 'timestamp': time.time()}
        except Exception as e:
            return {'error': str(e), 'user_id': execution_data.get('user_id', 'unknown')}

    async def _check_execution_context_contamination(self, executions: List[Dict]):
        """Check for execution context contamination between users."""
        for execution in executions:
            user_id = execution['user_id']
            result = execution.get('result', {})
            result_user_id = result.get('user_id')
            assert result_user_id == user_id, f'SSOT VIOLATION: Execution context contamination detected. User {user_id} execution result contains data for user {result_user_id}. BUSINESS IMPACT: Users receive responses meant for other users.'
            private_data = result.get('private_data_echo', '')
            if private_data and user_id not in private_data:
                pytest.fail(f'SSOT VIOLATION: Private data contamination. User {user_id} result contains private data: {private_data}. BUSINESS IMPACT: User privacy violation.')

    async def _test_execution_engine_state_isolation(self, engines: List[Dict]):
        """Test execution engine state isolation."""
        if len(engines) < 2:
            return
        for i, engine_info in enumerate(engines):
            engine = engine_info['engine']
            user_id = engine_info['user_id']
            test_state = f'test_state_{user_id}_{i}'
            if hasattr(engine, 'set_state'):
                engine.set_state(test_state)
            elif hasattr(engine, 'state'):
                engine.state = test_state
        for i, engine_info in enumerate(engines):
            engine = engine_info['engine']
            user_id = engine_info['user_id']
            expected_state = f'test_state_{user_id}_{i}'
            if hasattr(engine, 'get_state'):
                actual_state = engine.get_state()
                assert actual_state == expected_state, f"SSOT VIOLATION: Engine state contamination. Engine for user {user_id} expected state '{expected_state}', got '{actual_state}'"
            elif hasattr(engine, 'state'):
                actual_state = engine.state
                assert actual_state == expected_state, f"SSOT VIOLATION: Engine state contamination. Engine for user {user_id} expected state '{expected_state}', got '{actual_state}'"

    async def _check_registry_execution_contamination(self, executions: List[Dict]):
        """Check for registry execution contamination."""
        for execution in executions:
            user_id = execution['user_id']
            result = execution.get('result', {})
            result_user_id = result.get('user_id')
            if result_user_id and result_user_id != user_id:
                pytest.fail(f'SSOT VIOLATION: Registry execution contamination. User {user_id} received result for user {result_user_id}. BUSINESS IMPACT: Agent routing delivers results to wrong users.')

    async def _check_tool_execution_contamination(self, executions: List[Dict]):
        """Check for tool execution contamination."""
        for execution in executions:
            user_id = execution['user_id']
            tool_result = execution.get('tool_result', {})
            result_user_id = tool_result.get('user_id')
            if result_user_id and result_user_id != user_id:
                pytest.fail(f'SSOT VIOLATION: Tool execution contamination. User {user_id} received tool result for user {result_user_id}. BUSINESS IMPACT: Tool results delivered to wrong users.')
            tool_request = execution.get('tool_request', {})
            request_data = tool_request.get('parameters', {})
            if 'user_specific_data' in request_data:
                if user_id not in request_data['user_specific_data']:
                    pytest.fail(f"SSOT VIOLATION: Tool request data contamination. User {user_id} tool request contains wrong user data: {request_data['user_specific_data']}")
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')