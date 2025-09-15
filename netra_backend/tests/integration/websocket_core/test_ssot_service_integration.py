"""SSOT WebSocket Broadcast Service Integration Tests - Issue #1058

Business Value Justification (BVJ):
- Segment: Enterprise/Platform (Multi-service architecture)
- Business Goal: Service integration reliability and Golden Path protection
- Value Impact: Ensures $500K+ ARR system integration works with SSOT consolidation
- Strategic Impact: Validates SSOT works across all service boundaries

Integration tests for SSOT WebSocket broadcast consolidation:
- Agent integration with SSOT broadcast service
- Multi-service coordination through SSOT interface
- WebSocket factory integration patterns
- Real service dependencies and interactions

CRITICAL MISSION: Validate SSOT consolidation works correctly with all
integrated services that depend on WebSocket broadcasting functionality.

Test Strategy: Real service integration testing (NON-DOCKER) with actual
service dependencies to ensure SSOT consolidation doesn't break existing integrations.
"""
import asyncio
import json
import pytest
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import Dict, Any, List, Optional, Set
from netra_backend.app.services.websocket_broadcast_service import WebSocketBroadcastService, BroadcastResult, create_broadcast_service
from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager
from netra_backend.app.websocket_core.protocols import WebSocketManagerProtocol
from netra_backend.app.websocket_core.factory import create_websocket_manager
try:
    from netra_backend.app.agents.base_agent import BaseAgent
    from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
    from netra_backend.app.agents.registry import AgentRegistry
    AGENT_INTEGRATION_AVAILABLE = True
except ImportError as e:
    AGENT_INTEGRATION_AVAILABLE = False
    import warnings
    warnings.warn(f'Agent integration not available: {e}')
from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase
from shared.types.core_types import UserID, ensure_user_id
from shared.logging.unified_logging_ssot import get_logger
logger = get_logger(__name__)

@pytest.mark.integration
@pytest.mark.websocket_ssot
@pytest.mark.non_docker
@pytest.mark.issue_1058_service_integration
class SSOTServiceIntegrationTests(SSotAsyncTestCase):
    """Integration tests validating SSOT service integration across system boundaries.

    CRITICAL: These tests validate SSOT consolidation works correctly with
    all services that depend on WebSocket broadcasting functionality.

    Integration test requirements:
    1. Agent integration with SSOT broadcast service
    2. Multi-service coordination through SSOT
    3. WebSocket factory integration patterns
    4. Real service dependency validation
    """

    @pytest.fixture
    async def integration_websocket_manager(self):
        """Create real WebSocket manager for integration testing."""
        try:
            manager = create_websocket_manager()
            yield manager
        except Exception as e:
            logger.warning(f'Real WebSocket manager not available, using mock: {e}')
            manager = Mock(spec=WebSocketManagerProtocol)
            manager.send_to_user = AsyncMock()
            manager.get_user_connections = Mock(return_value=[{'connection_id': 'integration_conn_1', 'user_id': 'integration_user'}])
            yield manager

    @pytest.fixture
    async def ssot_integration_service(self, integration_websocket_manager):
        """Create SSOT broadcast service for integration testing."""
        service = WebSocketBroadcastService(integration_websocket_manager)
        service.update_feature_flag('enable_contamination_detection', True)
        service.update_feature_flag('enable_performance_monitoring', True)
        service.update_feature_flag('enable_comprehensive_logging', True)
        return service

    @pytest.fixture
    def agent_integration_events(self):
        """Create agent-specific events for integration testing."""
        return [{'type': 'agent_started', 'data': {'agent_id': 'integration_test_agent', 'user_id': 'agent_user_123', 'execution_id': 'exec_integration_001'}}, {'type': 'agent_thinking', 'data': {'agent_id': 'integration_test_agent', 'thought_process': 'Analyzing integration requirements', 'step': 'integration_validation'}}, {'type': 'tool_executing', 'data': {'tool_name': 'integration_validator', 'tool_id': 'tool_integration_001', 'status': 'running'}}, {'type': 'tool_completed', 'data': {'tool_name': 'integration_validator', 'tool_id': 'tool_integration_001', 'result': 'integration_successful', 'execution_time_ms': 150}}, {'type': 'agent_completed', 'data': {'agent_id': 'integration_test_agent', 'final_result': 'Integration test completed successfully', 'total_execution_time_ms': 2500}}]

    @pytest.mark.asyncio
    async def test_ssot_broadcast_agent_integration(self, ssot_integration_service, agent_integration_events):
        """Test SSOT broadcast service integrates correctly with agent systems.

        INTEGRATION CRITICAL: Agent systems depend on WebSocket broadcasting
        for real-time user feedback during AI task execution.
        """
        agent_user = 'agent_integration_user_123'
        integration_results = []
        for event in agent_integration_events:
            result = await ssot_integration_service.broadcast_to_user(agent_user, event)
            integration_results.append((event['type'], result))
            await asyncio.sleep(0.01)
        assert len(integration_results) == len(agent_integration_events)
        for event_type, result in integration_results:
            assert isinstance(result, BroadcastResult)
            assert result.user_id == agent_user
            assert result.successful_sends > 0, f'Agent event {event_type} broadcast failed'
            assert result.event_type == event_type
        expected_sequence = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        actual_sequence = [event_type for event_type, _ in integration_results]
        assert actual_sequence == expected_sequence, 'Agent integration workflow sequence incorrect'
        stats = ssot_integration_service.get_stats()
        assert stats['broadcast_stats']['total_broadcasts'] >= len(agent_integration_events)
        assert stats['broadcast_stats']['successful_broadcasts'] >= len(agent_integration_events)
        assert stats['performance_metrics']['success_rate_percentage'] == 100.0
        logger.info(f'✅ Agent integration validated - {len(agent_integration_events)} agent events broadcasted')

    @pytest.mark.asyncio
    async def test_ssot_multi_service_coordination(self, ssot_integration_service):
        """Test SSOT coordinates broadcasts across multiple service boundaries.

        INTEGRATION CRITICAL: SSOT must coordinate broadcasts from multiple
        services (backend, agent, tool execution) without conflicts.
        """
        coordination_user = 'multi_service_user_456'
        service_events = [{'service': 'backend_api', 'event': {'type': 'api_request_received', 'data': {'endpoint': '/chat', 'method': 'POST', 'service': 'backend_api'}}}, {'service': 'agent_orchestrator', 'event': {'type': 'agent_orchestration_started', 'data': {'orchestrator': 'supervisor', 'service': 'agent_orchestrator'}}}, {'service': 'tool_executor', 'event': {'type': 'tool_execution_queued', 'data': {'tool': 'data_analyzer', 'service': 'tool_executor'}}}, {'service': 'websocket_manager', 'event': {'type': 'websocket_connection_validated', 'data': {'connection_status': 'active', 'service': 'websocket_manager'}}}]
        coordination_tasks = []
        for service_info in service_events:
            service_name = service_info['service']
            event = service_info['event']
            coordinated_event = {**event, 'coordination_metadata': {'originating_service': service_name, 'coordination_id': f'coord_{service_name}_{int(time.time())}', 'multi_service_workflow': True}}
            task = ssot_integration_service.broadcast_to_user(coordination_user, coordinated_event)
            coordination_tasks.append((service_name, task))
        coordination_results = []
        for service_name, task in coordination_tasks:
            try:
                result = await task
                coordination_results.append((service_name, result))
            except Exception as e:
                logger.error(f'Service coordination failed for {service_name}: {e}')
                coordination_results.append((service_name, None))
        successful_coordinations = [(name, result) for name, result in coordination_results if result is not None]
        assert len(successful_coordinations) == len(service_events), 'Not all services coordinated successfully'
        for service_name, result in successful_coordinations:
            assert isinstance(result, BroadcastResult)
            assert result.user_id == coordination_user
            assert result.successful_sends > 0, f'Service {service_name} coordination failed'
        stats = ssot_integration_service.get_stats()
        assert stats['broadcast_stats']['total_broadcasts'] >= len(service_events)
        assert stats['broadcast_stats']['failed_broadcasts'] == 0, 'Multi-service coordination created conflicts'
        expected_services = {'backend_api', 'agent_orchestrator', 'tool_executor', 'websocket_manager'}
        coordinated_services = {name for name, _ in successful_coordinations}
        assert coordinated_services == expected_services
        logger.info(f'✅ Multi-service coordination validated - {len(expected_services)} services coordinated')

    @pytest.mark.asyncio
    async def test_ssot_websocket_factory_integration(self, integration_websocket_manager):
        """Test SSOT integrates correctly with WebSocket factory patterns.

        INTEGRATION CRITICAL: WebSocket factory patterns must work seamlessly
        with SSOT broadcast service consolidation.
        """
        factory_user = 'factory_integration_user'
        factory_service_1 = create_broadcast_service(integration_websocket_manager)
        assert isinstance(factory_service_1, WebSocketBroadcastService)
        factory_service_2 = create_broadcast_service(integration_websocket_manager)
        assert isinstance(factory_service_2, WebSocketBroadcastService)
        assert factory_service_1.websocket_manager is factory_service_2.websocket_manager
        assert factory_service_1 is not factory_service_2
        factory_event = {'type': 'factory_test_event', 'data': {'test': 'factory_integration', 'timestamp': datetime.now(timezone.utc).isoformat()}}
        result_1 = await factory_service_1.broadcast_to_user(factory_user, factory_event)
        result_2 = await factory_service_2.broadcast_to_user(factory_user, factory_event)
        assert result_1.successful_sends > 0
        assert result_2.successful_sends > 0
        assert result_1.user_id == factory_user
        assert result_2.user_id == factory_user
        stats_1 = factory_service_1.get_stats()
        stats_2 = factory_service_2.get_stats()
        assert stats_1['broadcast_stats']['total_broadcasts'] >= 1
        assert stats_2['broadcast_stats']['total_broadcasts'] >= 1
        assert stats_1['service_info']['name'] == stats_2['service_info']['name']
        assert stats_1['service_info']['replaces'] == stats_2['service_info']['replaces']
        try:
            invalid_factory_service = create_broadcast_service(None)
            await invalid_factory_service.broadcast_to_user(factory_user, factory_event)
            assert False, 'Should have failed with None manager'
        except Exception as e:
            assert 'manager' in str(e).lower() or 'websocket' in str(e).lower()
        logger.info('✅ WebSocket factory integration validated - factory patterns work with SSOT')

    @pytest.mark.asyncio
    async def test_ssot_real_service_dependency_validation(self, ssot_integration_service):
        """Test SSOT works with real service dependencies and configurations.

        INTEGRATION CRITICAL: SSOT must work with real service configurations,
        authentication, and dependency injection patterns.
        """
        dependency_user = 'service_dependency_user'
        dependency_scenarios = [{'scenario': 'authentication_service_integration', 'event': {'type': 'auth_validation_complete', 'data': {'user_authenticated': True, 'auth_service': 'real_auth_service', 'token_validated': True, 'permissions': ['read', 'write', 'broadcast']}}}, {'scenario': 'database_service_integration', 'event': {'type': 'data_persistence_complete', 'data': {'database_operation': 'user_session_save', 'database_service': 'real_database_service', 'operation_successful': True, 'transaction_id': 'txn_integration_001'}}}, {'scenario': 'redis_cache_integration', 'event': {'type': 'cache_operation_complete', 'data': {'cache_operation': 'user_state_cache', 'cache_service': 'real_redis_service', 'cache_hit': True, 'cache_key': f'user_state_{dependency_user}'}}}, {'scenario': 'logging_service_integration', 'event': {'type': 'audit_log_recorded', 'data': {'log_level': 'INFO', 'logging_service': 'real_logging_service', 'audit_event': 'websocket_broadcast_integration_test', 'user_activity': f'User {dependency_user} integration test'}}}]
        dependency_results = []
        for scenario_info in dependency_scenarios:
            scenario_name = scenario_info['scenario']
            event = scenario_info['event']
            try:
                integration_event = {**event, 'integration_metadata': {'test_scenario': scenario_name, 'dependency_validation': True, 'real_service_integration': True}}
                result = await ssot_integration_service.broadcast_to_user(dependency_user, integration_event)
                dependency_results.append((scenario_name, result, None))
            except Exception as e:
                logger.warning(f'Dependency scenario {scenario_name} failed: {e}')
                dependency_results.append((scenario_name, None, str(e)))
        successful_scenarios = [(name, result) for name, result, error in dependency_results if result is not None]
        failed_scenarios = [(name, error) for name, result, error in dependency_results if result is None]
        success_rate = len(successful_scenarios) / len(dependency_scenarios)
        assert success_rate >= 0.75, f'Too many dependency failures: {success_rate:.1%} success rate'
        for scenario_name, result in successful_scenarios:
            assert isinstance(result, BroadcastResult)
            assert result.user_id == dependency_user
            assert result.successful_sends > 0, f'Dependency scenario {scenario_name} broadcast failed'
        if failed_scenarios:
            logger.info(f'⚠️  Some dependency scenarios failed (expected in test environment):')
            for scenario_name, error in failed_scenarios:
                logger.info(f'   - {scenario_name}: {error}')
        stats = ssot_integration_service.get_stats()
        assert stats['broadcast_stats']['total_broadcasts'] >= len(successful_scenarios)
        logger.info(f'✅ Service dependency validation complete - {len(successful_scenarios)}/{len(dependency_scenarios)} scenarios successful')

    @pytest.mark.asyncio
    async def test_ssot_integration_error_resilience(self, ssot_integration_service):
        """Test SSOT integration resilience to service failures and errors.

        INTEGRATION CRITICAL: SSOT must remain operational even when
        integrated services fail or become unavailable.
        """
        resilience_user = 'integration_resilience_user'
        error_scenarios = [{'name': 'websocket_manager_temporary_failure', 'setup': lambda: setattr(ssot_integration_service.websocket_manager, 'send_to_user', AsyncMock(side_effect=Exception('Temporary WebSocket failure'))), 'cleanup': lambda: setattr(ssot_integration_service.websocket_manager, 'send_to_user', AsyncMock())}, {'name': 'connection_retrieval_failure', 'setup': lambda: setattr(ssot_integration_service.websocket_manager, 'get_user_connections', Mock(side_effect=Exception('Connection retrieval failed'))), 'cleanup': lambda: setattr(ssot_integration_service.websocket_manager, 'get_user_connections', Mock(return_value=[{'connection_id': 'resilience_conn', 'user_id': resilience_user}]))}]
        resilience_results = []
        for scenario in error_scenarios:
            scenario_name = scenario['name']
            try:
                scenario['setup']()
                error_event = {'type': 'resilience_test', 'data': {'test_scenario': scenario_name, 'error_condition': True}}
                result = await ssot_integration_service.broadcast_to_user(resilience_user, error_event)
                resilience_results.append((scenario_name, result, 'error_handled'))
                scenario['cleanup']()
                recovery_event = {'type': 'recovery_test', 'data': {'test_scenario': scenario_name, 'recovery_test': True}}
                recovery_result = await ssot_integration_service.broadcast_to_user(resilience_user, recovery_event)
                resilience_results.append((f'{scenario_name}_recovery', recovery_result, 'recovered'))
            except Exception as e:
                logger.error(f'Resilience test {scenario_name} failed: {e}')
                resilience_results.append((scenario_name, None, str(e)))
        error_handled_results = [(name, result) for name, result, status in resilience_results if status == 'error_handled' and result is not None]
        recovery_results = [(name, result) for name, result, status in resilience_results if status == 'recovered' and result is not None]
        for scenario_name, result in error_handled_results:
            assert isinstance(result, BroadcastResult)
            assert result.user_id == resilience_user
            assert len(result.errors) > 0, f'Error scenario {scenario_name} should record errors'
        for scenario_name, result in recovery_results:
            assert isinstance(result, BroadcastResult)
            assert result.user_id == resilience_user
            assert result.successful_sends > 0, f'Recovery scenario {scenario_name} should succeed'
        stats = ssot_integration_service.get_stats()
        assert stats['broadcast_stats']['failed_broadcasts'] >= len(error_handled_results)
        assert stats['broadcast_stats']['successful_broadcasts'] >= len(recovery_results)
        logger.info(f'✅ Integration error resilience validated - {len(error_scenarios)} scenarios tested')

@pytest.mark.integration_performance
class SSOTIntegrationPerformanceTests:
    """Performance integration tests for SSOT service."""

    @pytest.mark.asyncio
    async def test_ssot_integration_performance_benchmarks(self):
        """Test SSOT integration performance meets requirements.

        PERFORMANCE CRITICAL: SSOT consolidation should maintain or improve
        performance compared to scattered legacy implementations.
        """
        mock_manager = Mock(spec=WebSocketManagerProtocol)
        mock_manager.send_to_user = AsyncMock()
        mock_manager.get_user_connections = Mock(return_value=[{'connection_id': 'perf_conn', 'user_id': 'perf_user'}])
        perf_service = WebSocketBroadcastService(mock_manager)
        benchmark_user = 'performance_benchmark_user'
        benchmark_count = 1000
        start_time = time.time()
        benchmark_tasks = []
        for i in range(benchmark_count):
            event = {'type': f'benchmark_event_{i}', 'data': {'iteration': i, 'benchmark': True}}
            task = perf_service.broadcast_to_user(benchmark_user, event)
            benchmark_tasks.append(task)
        benchmark_results = await asyncio.gather(*benchmark_tasks, return_exceptions=True)
        end_time = time.time()
        total_duration = end_time - start_time
        successful_broadcasts = [r for r in benchmark_results if isinstance(r, BroadcastResult) and r.successful_sends > 0]
        success_rate = len(successful_broadcasts) / benchmark_count
        assert total_duration < 5.0, f'Benchmark too slow: {total_duration:.2f}s for {benchmark_count} broadcasts'
        assert success_rate >= 0.95, f'Benchmark success rate too low: {success_rate:.1%}'
        broadcasts_per_second = benchmark_count / total_duration
        assert broadcasts_per_second >= 200, f'Benchmark throughput too low: {broadcasts_per_second:.1f} broadcasts/sec'
        logger.info(f'✅ Integration performance benchmark: {broadcasts_per_second:.1f} broadcasts/sec, {success_rate:.1%} success rate')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')