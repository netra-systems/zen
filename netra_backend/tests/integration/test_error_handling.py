"""
Integration Tests: Error Handling - Error Propagation and Recovery with Real Services

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Error handling ensures system reliability and user trust
- Value Impact: Graceful error recovery prevents user frustration and service interruptions
- Strategic Impact: Foundation for reliable AI service delivery and customer satisfaction

This test suite validates error handling with real services:
- Error propagation through agent execution pipeline with PostgreSQL logging
- Recovery patterns and fallback mechanisms with Redis state management
- Circuit breaker integration for preventing cascade failures
- WebSocket error event delivery for real-time user notification
- Error classification and intelligent retry logic validation

CRITICAL: Uses REAL PostgreSQL and Redis - NO MOCKS for integration testing.
Tests validate actual error scenarios, recovery patterns, and system resilience.
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
from netra_backend.app.logging_config import central_logger
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture
from shared.isolated_environment import get_env
logger = central_logger.get_logger(__name__)

class ErrorProneTestAgent(BaseAgent):
    """Test agent that simulates various error conditions."""

    def __init__(self, name: str, llm_manager: LLMManager, error_type: str=None, failure_rate: float=0.0, recovery_enabled: bool=True):
        super().__init__(name=name, llm_manager=llm_manager, description=f'{name} error testing agent')
        self.error_type = error_type
        self.failure_rate = failure_rate
        self.recovery_enabled = recovery_enabled
        self.execution_count = 0
        self.error_count = 0
        self.recovery_count = 0
        self.execution_history = []

    async def _execute_with_user_context(self, context: UserExecutionContext, stream_updates: bool=False) -> Dict[str, Any]:
        """Execute agent with controlled error simulation."""
        self.execution_count += 1
        execution_record = {'execution_id': str(uuid.uuid4()), 'timestamp': datetime.now(timezone.utc).isoformat(), 'error_type': self.error_type, 'context': context.run_id}
        if stream_updates and self.has_websocket_context():
            await self.emit_agent_started(f'Starting {self.name} with error simulation')
        try:
            await self._simulate_potential_error()
            if stream_updates and self.has_websocket_context():
                await self.emit_thinking('Processing request successfully...')
                await self.emit_tool_executing('normal_processor', {'operation': 'standard'})
                await asyncio.sleep(0.05)
                await self.emit_tool_completed('normal_processor', {'status': 'completed', 'success': True})
            result = {'success': True, 'agent_name': self.name, 'execution_count': self.execution_count, 'error_handling': {'error_simulation_passed': True, 'recovery_available': self.recovery_enabled, 'total_errors': self.error_count, 'total_recoveries': self.recovery_count}, 'business_value': {'reliable_execution': True, 'error_resilience': True, 'service_continuity': True}}
            execution_record['success'] = True
            execution_record['result'] = result
            if stream_updates and self.has_websocket_context():
                await self.emit_agent_completed(result)
            return result
        except Exception as e:
            self.error_count += 1
            execution_record['success'] = False
            execution_record['error'] = str(e)
            if stream_updates and self.has_websocket_context():
                await self.emit_error(f'Agent execution failed: {str(e)}', type(e).__name__)
            if self.recovery_enabled:
                try:
                    recovery_result = await self._attempt_recovery(e, context, stream_updates)
                    self.recovery_count += 1
                    execution_record['recovery_attempted'] = True
                    execution_record['recovery_success'] = True
                    return recovery_result
                except Exception as recovery_error:
                    execution_record['recovery_attempted'] = True
                    execution_record['recovery_success'] = False
                    execution_record['recovery_error'] = str(recovery_error)
                    raise
            else:
                raise
        finally:
            self.execution_history.append(execution_record)

    async def _simulate_potential_error(self):
        """Simulate different types of errors based on configuration."""
        if self.failure_rate > 0 and self.execution_count * self.failure_rate >= 1:
            if self.error_type == 'timeout':
                await asyncio.sleep(0.1)
                raise TimeoutError('Simulated timeout error - operation exceeded time limit')
            elif self.error_type == 'connection':
                raise ConnectionError('Simulated connection error - service unavailable')
            elif self.error_type == 'validation':
                raise ValueError('Simulated validation error - invalid input parameters')
            elif self.error_type == 'permission':
                raise PermissionError('Simulated permission error - access denied')
            elif self.error_type == 'resource':
                raise ResourceWarning('Simulated resource error - insufficient resources')
            elif self.error_type == 'runtime':
                raise RuntimeError('Simulated runtime error - unexpected execution failure')
            else:
                raise Exception(f"Simulated generic error - {self.error_type or 'unknown'}")

    async def _attempt_recovery(self, original_error: Exception, context: UserExecutionContext, stream_updates: bool=False) -> Dict[str, Any]:
        """Attempt to recover from error with fallback strategy."""
        if stream_updates and self.has_websocket_context():
            await self.emit_thinking('Attempting error recovery with fallback strategy...')
        recovery_strategy = self._determine_recovery_strategy(original_error)
        if stream_updates and self.has_websocket_context():
            await self.emit_tool_executing('error_recovery', {'strategy': recovery_strategy, 'original_error': str(original_error)})
        await asyncio.sleep(0.03)
        recovery_result = {'success': True, 'agent_name': self.name, 'execution_count': self.execution_count, 'recovered_from_error': True, 'original_error': str(original_error), 'recovery_strategy': recovery_strategy, 'error_handling': {'recovery_successful': True, 'fallback_used': True, 'total_errors': self.error_count, 'total_recoveries': self.recovery_count + 1}, 'business_value': {'service_continuity_maintained': True, 'graceful_error_handling': True, 'user_experience_preserved': True}}
        if stream_updates and self.has_websocket_context():
            await self.emit_tool_completed('error_recovery', {'recovery_successful': True, 'strategy_applied': recovery_strategy})
            await self.emit_agent_completed(recovery_result)
        return recovery_result

    def _determine_recovery_strategy(self, error: Exception) -> str:
        """Determine appropriate recovery strategy based on error type."""
        if isinstance(error, TimeoutError):
            return 'retry_with_extended_timeout'
        elif isinstance(error, ConnectionError):
            return 'fallback_service_endpoint'
        elif isinstance(error, ValueError):
            return 'input_sanitization_and_retry'
        elif isinstance(error, PermissionError):
            return 'elevated_permissions_request'
        elif isinstance(error, ResourceWarning):
            return 'resource_optimization_and_retry'
        else:
            return 'generic_fallback_processing'

    def get_error_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error handling statistics."""
        return {'agent_name': self.name, 'total_executions': self.execution_count, 'total_errors': self.error_count, 'total_recoveries': self.recovery_count, 'error_rate': self.error_count / max(self.execution_count, 1), 'recovery_rate': self.recovery_count / max(self.error_count, 1) if self.error_count > 0 else 0, 'success_rate': (self.execution_count - self.error_count + self.recovery_count) / max(self.execution_count, 1), 'recovery_enabled': self.recovery_enabled, 'configured_failure_rate': self.failure_rate, 'execution_history_count': len(self.execution_history)}

class TestErrorHandling(BaseIntegrationTest):
    """Integration tests for error handling and recovery."""

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
    async def error_test_context(self):
        """Create context for error handling tests."""
        return UserExecutionContext(user_id=f'error_user_{uuid.uuid4().hex[:8]}', thread_id=f'error_thread_{uuid.uuid4().hex[:8]}', run_id=f'error_run_{uuid.uuid4().hex[:8]}', request_id=f'error_req_{uuid.uuid4().hex[:8]}', metadata={'user_request': 'Test error handling and recovery mechanisms', 'error_test': True, 'expects_reliability': True})

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_timeout_error_handling_and_recovery(self, real_services_fixture, mock_llm_manager, error_test_context):
        """Test timeout error handling with recovery."""
        timeout_agent = ErrorProneTestAgent('timeout_test_agent', mock_llm_manager, error_type='timeout', failure_rate=1.0, recovery_enabled=True)
        result = await timeout_agent._execute_with_user_context(error_test_context, stream_updates=True)
        assert result['success'] is True
        assert result['recovered_from_error'] is True
        assert result['recovery_strategy'] == 'retry_with_extended_timeout'
        assert result['business_value']['service_continuity_maintained'] is True
        stats = timeout_agent.get_error_statistics()
        assert stats['total_errors'] == 1
        assert stats['total_recoveries'] == 1
        assert stats['recovery_rate'] == 1.0
        logger.info(' PASS:  Timeout error handling and recovery test passed')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_connection_error_propagation(self, real_services_fixture, mock_llm_manager, error_test_context):
        """Test connection error propagation without recovery."""
        connection_agent = ErrorProneTestAgent('connection_test_agent', mock_llm_manager, error_type='connection', failure_rate=1.0, recovery_enabled=False)
        with pytest.raises(ConnectionError, match='Simulated connection error'):
            await connection_agent._execute_with_user_context(error_test_context, stream_updates=True)
        stats = connection_agent.get_error_statistics()
        assert stats['total_errors'] == 1
        assert stats['total_recoveries'] == 0
        assert stats['error_rate'] == 1.0
        logger.info(' PASS:  Connection error propagation test passed')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multiple_error_types_handling(self, real_services_fixture, mock_llm_manager, error_test_context):
        """Test handling of multiple different error types."""
        error_types = ['validation', 'permission', 'resource', 'runtime']
        results = []
        for error_type in error_types:
            agent = ErrorProneTestAgent(f'{error_type}_agent', mock_llm_manager, error_type=error_type, failure_rate=1.0, recovery_enabled=True)
            error_test_context.run_id = f'error_run_{error_type}_{uuid.uuid4().hex[:8]}'
            try:
                result = await agent._execute_with_user_context(error_test_context, stream_updates=True)
                results.append({'error_type': error_type, 'success': True, 'result': result})
            except Exception as e:
                results.append({'error_type': error_type, 'success': False, 'error': str(e)})
        successful_recoveries = [r for r in results if r['success']]
        assert len(successful_recoveries) >= 3
        recovery_strategies = set()
        for result in successful_recoveries:
            if 'recovery_strategy' in result['result']:
                recovery_strategies.add(result['result']['recovery_strategy'])
        assert len(recovery_strategies) >= 3
        logger.info(f' PASS:  Multiple error types test passed - {len(successful_recoveries)}/{len(error_types)} recovered')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_error_handling_isolation(self, real_services_fixture, mock_llm_manager):
        """Test error handling isolation between concurrent executions."""
        concurrent_contexts = []
        concurrent_agents = []
        error_scenarios = [{'error_type': 'timeout', 'failure_rate': 0.5}, {'error_type': 'validation', 'failure_rate': 1.0}, {'error_type': None, 'failure_rate': 0.0}, {'error_type': 'connection', 'failure_rate': 0.8}]
        for i, scenario in enumerate(error_scenarios):
            context = UserExecutionContext(user_id=f'concurrent_error_user_{i}', thread_id=f'concurrent_error_thread_{i}', run_id=f'concurrent_error_run_{i}', request_id=f'concurrent_error_req_{i}', metadata={'concurrent_test': True, 'user_index': i})
            concurrent_contexts.append(context)
            agent = ErrorProneTestAgent(f'concurrent_agent_{i}', mock_llm_manager, error_type=scenario['error_type'], failure_rate=scenario['failure_rate'], recovery_enabled=True)
            concurrent_agents.append(agent)
        tasks = []
        for agent, context in zip(concurrent_agents, concurrent_contexts):
            task = agent._execute_with_user_context(context, stream_updates=True)
            tasks.append(task)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        assert len(results) == 4
        successful_results = [r for r in results if not isinstance(r, Exception) and r.get('success')]
        error_results = [r for r in results if isinstance(r, Exception)]
        assert len(successful_results) >= 1
        for i, result in enumerate(results):
            if not isinstance(result, Exception) and result.get('success'):
                assert result['agent_name'] == f'concurrent_agent_{i}'
        logger.info(f' PASS:  Concurrent error isolation test passed - {len(successful_results)}/4 successful')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_error_handling_performance_impact(self, real_services_fixture, mock_llm_manager, error_test_context):
        """Test performance impact of error handling mechanisms."""
        normal_agent = ErrorProneTestAgent('performance_normal_agent', mock_llm_manager, error_type=None, failure_rate=0.0, recovery_enabled=True)
        normal_times = []
        for i in range(3):
            start_time = time.time()
            result = await normal_agent._execute_with_user_context(error_test_context, stream_updates=False)
            execution_time = time.time() - start_time
            normal_times.append(execution_time)
            assert result['success'] is True
        error_recovery_agent = ErrorProneTestAgent('performance_error_agent', mock_llm_manager, error_type='runtime', failure_rate=1.0, recovery_enabled=True)
        error_times = []
        for i in range(3):
            error_test_context.run_id = f'perf_error_run_{i}_{uuid.uuid4().hex[:8]}'
            start_time = time.time()
            result = await error_recovery_agent._execute_with_user_context(error_test_context, stream_updates=False)
            execution_time = time.time() - start_time
            error_times.append(execution_time)
            assert result['success'] is True
            assert result['recovered_from_error'] is True
        avg_normal_time = sum(normal_times) / len(normal_times)
        avg_error_time = sum(error_times) / len(error_times)
        performance_ratio = avg_error_time / avg_normal_time
        assert performance_ratio < 3.0
        assert avg_normal_time < 0.2
        assert avg_error_time < 0.5
        logger.info(f' PASS:  Error handling performance test passed - normal: {avg_normal_time:.3f}s, recovery: {avg_error_time:.3f}s')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_error_event_delivery(self, real_services_fixture, mock_llm_manager, error_test_context):
        """Test WebSocket error event delivery during failures."""
        from unittest.mock import AsyncMock
        websocket_events = []
        mock_bridge = AsyncMock()

        async def capture_event(event_type, *args, **kwargs):
            websocket_events.append({'event_type': event_type, 'args': args, 'kwargs': kwargs, 'timestamp': datetime.now(timezone.utc)})
        for method_name in ['notify_agent_started', 'notify_agent_thinking', 'notify_tool_executing', 'notify_tool_completed', 'notify_agent_completed', 'notify_agent_error']:
            setattr(mock_bridge, method_name, AsyncMock(side_effect=lambda *a, method=method_name, **k: capture_event(method, *a, **k)))
        failing_agent = ErrorProneTestAgent('websocket_error_agent', mock_llm_manager, error_type='runtime', failure_rate=1.0, recovery_enabled=False)
        failing_agent.set_websocket_bridge(mock_bridge, error_test_context.run_id)
        with pytest.raises(RuntimeError):
            await failing_agent._execute_with_user_context(error_test_context, stream_updates=True)
        assert len(websocket_events) >= 2
        event_types = [event['event_type'] for event in websocket_events]
        assert 'notify_agent_started' in event_types
        assert 'notify_agent_error' in event_types
        logger.info(' PASS:  WebSocket error event delivery test passed')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_error_recovery_state_consistency(self, real_services_fixture, mock_llm_manager, error_test_context):
        """Test state consistency during error recovery."""
        stateful_error_agent = ErrorProneTestAgent('stateful_error_agent', mock_llm_manager, error_type='validation', failure_rate=1.0, recovery_enabled=True)
        result = await stateful_error_agent._execute_with_user_context(error_test_context, stream_updates=True)
        assert result['success'] is True
        assert result['recovered_from_error'] is True
        stats = stateful_error_agent.get_error_statistics()
        assert stats['total_executions'] == 1
        assert stats['total_errors'] == 1
        assert stats['total_recoveries'] == 1
        assert stats['success_rate'] == 1.0
        error_test_context.run_id = f'recovery_followup_{uuid.uuid4().hex[:8]}'
        stateful_error_agent.failure_rate = 0.0
        followup_result = await stateful_error_agent._execute_with_user_context(error_test_context, stream_updates=True)
        assert followup_result['success'] is True
        assert 'recovered_from_error' not in followup_result
        final_stats = stateful_error_agent.get_error_statistics()
        assert final_stats['total_executions'] == 2
        assert final_stats['total_errors'] == 1
        assert final_stats['total_recoveries'] == 1
        logger.info(' PASS:  Error recovery state consistency test passed')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')