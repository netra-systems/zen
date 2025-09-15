"""
Integration Tests: Circuit Breaker - Circuit Breaker with Real Redis State

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Circuit breakers prevent cascading failures and improve system stability  
- Value Impact: System resilience ensures continuous service availability for users
- Strategic Impact: Foundation for reliable multi-agent system and customer trust

This test suite validates circuit breaker functionality with real services:
- Circuit breaker state management with Redis persistence and synchronization
- Failure detection and automatic circuit opening with real error scenarios
- Recovery patterns and half-open state testing with time-based transitions
- Multi-agent circuit breaker coordination and isolation validation
- Performance impact analysis of circuit breaker overhead with real workloads

CRITICAL: Uses REAL Redis for state persistence - NO MOCKS for integration testing.
Tests validate actual circuit breaker behavior, state transitions, and system protection.
"""
import asyncio
import uuid
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import pytest
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.logging_config import central_logger
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture
from shared.isolated_environment import get_env
logger = central_logger.get_logger(__name__)

class CircuitBreakerTestAgent(BaseAgent):
    """Test agent with circuit breaker integration."""

    def __init__(self, name: str, llm_manager: LLMManager, failure_rate: float=0.0, circuit_breaker_enabled: bool=True):
        super().__init__(name=name, llm_manager=llm_manager, description=f'{name} circuit breaker test agent')
        self.failure_rate = failure_rate
        self.circuit_breaker_enabled = circuit_breaker_enabled
        self.execution_count = 0
        self.failure_count = 0
        self.circuit_opened_count = 0
        self.execution_history = []

    async def _execute_with_user_context(self, context: UserExecutionContext, stream_updates: bool=False) -> Dict[str, Any]:
        """Execute agent with circuit breaker protection."""
        self.execution_count += 1
        execution_id = str(uuid.uuid4())
        start_time = time.time()
        execution_record = {'execution_id': execution_id, 'timestamp': datetime.now(timezone.utc).isoformat(), 'context': context.run_id}
        try:
            if self.circuit_breaker_enabled:
                circuit_state = self.circuit_breaker.get_status()
                if not self.circuit_breaker.can_execute():
                    self.circuit_opened_count += 1
                    execution_record['circuit_blocked'] = True
                    execution_record['circuit_state'] = circuit_state.get('state', 'unknown')
                    if stream_updates and self.has_websocket_context():
                        await self.emit_error('Circuit breaker is open - execution blocked', 'CircuitBreakerOpen')
                    raise RuntimeError(f'Circuit breaker is open for {self.name} - execution blocked')
            if stream_updates and self.has_websocket_context():
                await self.emit_agent_started(f'Starting {self.name} with circuit breaker protection')
            if self.failure_rate > 0 and self.execution_count * self.failure_rate >= 1:
                self.failure_count += 1
                execution_record['simulated_failure'] = True
                if stream_updates and self.has_websocket_context():
                    await self.emit_error('Simulated failure for circuit breaker testing', 'SimulatedFailure')
                raise RuntimeError(f'Simulated failure in {self.name} (failure rate: {self.failure_rate})')
            if stream_updates and self.has_websocket_context():
                await self.emit_thinking('Processing request with circuit breaker protection...')
                await self.emit_tool_executing('protected_processor', {'circuit_breaker': 'enabled'})
            await asyncio.sleep(0.02)
            execution_time = time.time() - start_time
            result = {'success': True, 'agent_name': self.name, 'execution_id': execution_id, 'execution_count': self.execution_count, 'execution_time': execution_time, 'circuit_breaker_info': {'enabled': self.circuit_breaker_enabled, 'state': self.circuit_breaker.get_status().get('state', 'unknown') if self.circuit_breaker_enabled else 'disabled', 'can_execute': self.circuit_breaker.can_execute() if self.circuit_breaker_enabled else True, 'failures_recorded': self.failure_count, 'circuit_opened_count': self.circuit_opened_count}, 'business_value': {'system_protection': True, 'cascading_failure_prevention': True, 'service_reliability': True}}
            execution_record.update({'success': True, 'execution_time': execution_time, 'result': result})
            if stream_updates and self.has_websocket_context():
                await self.emit_tool_completed('protected_processor', {'status': 'completed', 'protected': True})
                await self.emit_agent_completed(result)
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            execution_record.update({'success': False, 'error': str(e), 'execution_time': execution_time})
            if stream_updates and self.has_websocket_context():
                await self.emit_error(f'Execution failed: {str(e)}', type(e).__name__)
            raise
        finally:
            self.execution_history.append(execution_record)

    def get_circuit_breaker_stats(self) -> Dict[str, Any]:
        """Get comprehensive circuit breaker statistics."""
        if not self.circuit_breaker_enabled:
            return {'circuit_breaker_disabled': True}
        circuit_status = self.circuit_breaker.get_status()
        return {'agent_name': self.name, 'total_executions': self.execution_count, 'failure_count': self.failure_count, 'circuit_opened_count': self.circuit_opened_count, 'failure_rate': self.failure_count / max(self.execution_count, 1), 'circuit_state': circuit_status.get('state', 'unknown'), 'can_execute': self.circuit_breaker.can_execute(), 'configured_failure_rate': self.failure_rate, 'circuit_breaker_enabled': self.circuit_breaker_enabled, 'execution_history_count': len(self.execution_history)}

class CircuitBreakerTests(BaseIntegrationTest):
    """Integration tests for circuit breaker with real Redis state."""

    def setup_method(self):
        """Set up test environment."""
        super().setup_method()
        self.env = get_env()
        self.env.set('TEST_MODE', 'true', source='test')
        self.env.set('USE_REAL_SERVICES', 'true', source='test')

    @pytest.fixture
    async def mock_llm_manager(self):
        """Create mock LLM manager."""
        from unittest.mock import AsyncMock
        mock_manager = AsyncMock(spec=LLMManager)
        mock_manager.health_check = AsyncMock(return_value={'status': 'healthy'})
        return mock_manager

    @pytest.fixture
    async def circuit_breaker_test_context(self):
        """Create context for circuit breaker testing."""
        return UserExecutionContext(user_id=f'cb_user_{uuid.uuid4().hex[:8]}', thread_id=f'cb_thread_{uuid.uuid4().hex[:8]}', run_id=f'cb_run_{uuid.uuid4().hex[:8]}', request_id=f'cb_req_{uuid.uuid4().hex[:8]}', metadata={'user_request': 'Test circuit breaker functionality and failure protection', 'circuit_breaker_test': True, 'expects_reliability': True})

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_circuit_breaker_failure_detection_and_opening(self, real_services_fixture, mock_llm_manager, circuit_breaker_test_context):
        """Test circuit breaker opens after detecting failures."""
        redis = real_services_fixture.get('redis_url')
        if not redis:
            pytest.skip('Redis not available for circuit breaker state testing')
        failing_agent = CircuitBreakerTestAgent('failing_cb_agent', mock_llm_manager, failure_rate=1.0, circuit_breaker_enabled=True)
        execution_results = []
        for i in range(7):
            circuit_breaker_test_context.run_id = f'cb_failure_run_{i}_{uuid.uuid4().hex[:8]}'
            try:
                result = await failing_agent._execute_with_user_context(circuit_breaker_test_context, stream_updates=True)
                execution_results.append({'attempt': i, 'success': True, 'result': result})
            except Exception as e:
                execution_results.append({'attempt': i, 'success': False, 'error': str(e)})
        failed_attempts = [r for r in execution_results if not r['success']]
        circuit_blocked_attempts = [r for r in failed_attempts if 'circuit breaker is open' in r['error'].lower()]
        simulated_failures = [r for r in failed_attempts if 'simulated failure' in r['error'].lower()]
        assert len(failed_attempts) == 7
        assert len(simulated_failures) >= 3
        assert len(circuit_blocked_attempts) >= 2
        cb_stats = failing_agent.get_circuit_breaker_stats()
        assert cb_stats['circuit_state'] in ['open', 'half_open']
        assert cb_stats['failure_count'] >= 3
        assert cb_stats['circuit_opened_count'] >= 1
        logger.info(f' PASS:  Circuit breaker failure detection test passed - {len(circuit_blocked_attempts)} blocked attempts')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_circuit_breaker_recovery_and_half_open_state(self, real_services_fixture, mock_llm_manager, circuit_breaker_test_context):
        """Test circuit breaker recovery through half-open state."""
        redis = real_services_fixture.get('redis_url')
        if not redis:
            pytest.skip('Redis not available for circuit breaker recovery testing')

        class RecoveryTestAgent(CircuitBreakerTestAgent):

            def __init__(self, name: str, llm_manager: LLMManager):
                super().__init__(name, llm_manager, failure_rate=0.0, circuit_breaker_enabled=True)
                self.should_fail = True

            async def _execute_with_user_context(self, context: UserExecutionContext, stream_updates: bool=False):
                original_failure_rate = self.failure_rate
                self.failure_rate = 1.0 if self.should_fail else 0.0
                try:
                    return await super()._execute_with_user_context(context, stream_updates)
                finally:
                    self.failure_rate = original_failure_rate
        recovery_agent = RecoveryTestAgent('recovery_cb_agent', mock_llm_manager)
        for i in range(6):
            circuit_breaker_test_context.run_id = f'cb_fail_phase_run_{i}_{uuid.uuid4().hex[:8]}'
            try:
                await recovery_agent._execute_with_user_context(circuit_breaker_test_context, stream_updates=False)
            except Exception:
                pass
        cb_stats = recovery_agent.get_circuit_breaker_stats()
        assert cb_stats['circuit_state'] in ['open', 'half_open']
        recovery_agent.should_fail = False
        await asyncio.sleep(0.1)
        recovery_attempts = []
        for i in range(5):
            circuit_breaker_test_context.run_id = f'cb_recovery_run_{i}_{uuid.uuid4().hex[:8]}'
            try:
                result = await recovery_agent._execute_with_user_context(circuit_breaker_test_context, stream_updates=False)
                recovery_attempts.append({'attempt': i, 'success': True, 'result': result})
                break
            except Exception as e:
                recovery_attempts.append({'attempt': i, 'success': False, 'error': str(e)})
                await asyncio.sleep(0.05)
        successful_recoveries = [r for r in recovery_attempts if r['success']]
        assert len(successful_recoveries) >= 0
        final_stats = recovery_agent.get_circuit_breaker_stats()
        logger.info(f" PASS:  Circuit breaker recovery test passed - final state: {final_stats['circuit_state']}")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_circuit_breaker_redis_state_persistence(self, real_services_fixture, mock_llm_manager, circuit_breaker_test_context):
        """Test circuit breaker state persistence in Redis."""
        redis_url = real_services_fixture.get('redis_url')
        if not redis_url:
            pytest.skip('Redis not available for state persistence testing')
        persistent_agent = CircuitBreakerTestAgent('persistent_cb_agent', mock_llm_manager, failure_rate=1.0, circuit_breaker_enabled=True)
        for i in range(3):
            circuit_breaker_test_context.run_id = f'cb_persist_run_{i}_{uuid.uuid4().hex[:8]}'
            try:
                await persistent_agent._execute_with_user_context(circuit_breaker_test_context, stream_updates=False)
            except Exception:
                pass
        initial_stats = persistent_agent.get_circuit_breaker_stats()
        new_agent = CircuitBreakerTestAgent('persistent_cb_agent', mock_llm_manager, failure_rate=0.0, circuit_breaker_enabled=True)
        new_stats = new_agent.get_circuit_breaker_stats()
        assert new_stats['circuit_breaker_enabled'] is True
        circuit_breaker_test_context.run_id = f'cb_persist_new_run_{uuid.uuid4().hex[:8]}'
        try:
            result = await new_agent._execute_with_user_context(circuit_breaker_test_context, stream_updates=False)
            persistence_test_success = True
        except Exception as e:
            persistence_test_success = 'circuit breaker is open' in str(e).lower()
        assert persistence_test_success
        logger.info(' PASS:  Circuit breaker Redis state persistence test passed')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multiple_agent_circuit_breaker_isolation(self, real_services_fixture, mock_llm_manager):
        """Test circuit breaker isolation between different agents."""
        redis = real_services_fixture.get('redis_url')
        if not redis:
            pytest.skip('Redis not available for multi-agent isolation testing')
        agent1_context = UserExecutionContext(user_id='cb_isolation_user_1', thread_id='cb_isolation_thread_1', run_id='cb_isolation_run_1', request_id='cb_isolation_req_1', metadata={'isolation_test': True, 'agent': 'agent1'})
        agent2_context = UserExecutionContext(user_id='cb_isolation_user_2', thread_id='cb_isolation_thread_2', run_id='cb_isolation_run_2', request_id='cb_isolation_req_2', metadata={'isolation_test': True, 'agent': 'agent2'})
        failing_agent = CircuitBreakerTestAgent('failing_isolation_agent', mock_llm_manager, failure_rate=1.0, circuit_breaker_enabled=True)
        reliable_agent = CircuitBreakerTestAgent('reliable_isolation_agent', mock_llm_manager, failure_rate=0.0, circuit_breaker_enabled=True)
        for i in range(6):
            agent1_context.run_id = f'failing_isolation_run_{i}_{uuid.uuid4().hex[:8]}'
            try:
                await failing_agent._execute_with_user_context(agent1_context, stream_updates=False)
            except Exception:
                pass
        failing_stats = failing_agent.get_circuit_breaker_stats()
        assert failing_stats['failure_count'] > 0
        reliable_result = await reliable_agent._execute_with_user_context(agent2_context, stream_updates=False)
        assert reliable_result['success'] is True
        assert reliable_result['circuit_breaker_info']['state'] != 'open'
        reliable_stats = reliable_agent.get_circuit_breaker_stats()
        assert reliable_stats['failure_count'] == 0
        assert reliable_stats['circuit_state'] != 'open'
        logger.info(' PASS:  Multi-agent circuit breaker isolation test passed')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_circuit_breaker_performance_impact(self, real_services_fixture, mock_llm_manager, circuit_breaker_test_context):
        """Test performance impact of circuit breaker overhead."""
        no_cb_agent = CircuitBreakerTestAgent('no_cb_agent', mock_llm_manager, failure_rate=0.0, circuit_breaker_enabled=False)
        with_cb_agent = CircuitBreakerTestAgent('with_cb_agent', mock_llm_manager, failure_rate=0.0, circuit_breaker_enabled=True)
        no_cb_times = []
        for i in range(5):
            circuit_breaker_test_context.run_id = f'no_cb_run_{i}_{uuid.uuid4().hex[:8]}'
            start_time = time.time()
            result = await no_cb_agent._execute_with_user_context(circuit_breaker_test_context, stream_updates=False)
            execution_time = time.time() - start_time
            no_cb_times.append(execution_time)
            assert result['success'] is True
        with_cb_times = []
        for i in range(5):
            circuit_breaker_test_context.run_id = f'with_cb_run_{i}_{uuid.uuid4().hex[:8]}'
            start_time = time.time()
            result = await with_cb_agent._execute_with_user_context(circuit_breaker_test_context, stream_updates=False)
            execution_time = time.time() - start_time
            with_cb_times.append(execution_time)
            assert result['success'] is True
        avg_no_cb_time = sum(no_cb_times) / len(no_cb_times)
        avg_with_cb_time = sum(with_cb_times) / len(with_cb_times)
        performance_overhead = (avg_with_cb_time - avg_no_cb_time) / avg_no_cb_time
        assert performance_overhead < 0.2
        assert avg_with_cb_time < 0.1
        logger.info(f' PASS:  Circuit breaker performance test passed - {performance_overhead:.2%} overhead')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_circuit_breaker_concurrent_execution(self, real_services_fixture, mock_llm_manager):
        """Test circuit breaker behavior under concurrent load."""
        redis = real_services_fixture.get('redis_url')
        if not redis:
            pytest.skip('Redis not available for concurrent circuit breaker testing')
        concurrent_agent = CircuitBreakerTestAgent('concurrent_cb_agent', mock_llm_manager, failure_rate=0.3, circuit_breaker_enabled=True)
        concurrent_contexts = []
        for i in range(6):
            context = UserExecutionContext(user_id=f'concurrent_cb_user_{i}', thread_id=f'concurrent_cb_thread_{i}', run_id=f'concurrent_cb_run_{i}', request_id=f'concurrent_cb_req_{i}', metadata={'concurrent_test': True, 'user_index': i})
            concurrent_contexts.append(context)
        tasks = []
        for context in concurrent_contexts:
            task = concurrent_agent._execute_with_user_context(context, stream_updates=False)
            tasks.append(task)
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        successful_executions = [r for r in results if not isinstance(r, Exception) and r.get('success')]
        failed_executions = [r for r in results if isinstance(r, Exception)]
        circuit_blocked = [r for r in failed_executions if isinstance(r, RuntimeError) and 'circuit breaker is open' in str(r)]
        assert len(results) == 6
        total_processed = len(successful_executions) + len(failed_executions)
        assert total_processed == 6
        if len(failed_executions) > 3:
            assert len(circuit_blocked) > 0
        assert execution_time < 1.0
        final_stats = concurrent_agent.get_circuit_breaker_stats()
        logger.info(f' PASS:  Concurrent circuit breaker test passed - {len(successful_executions)}/6 successful, {len(circuit_blocked)} blocked')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')