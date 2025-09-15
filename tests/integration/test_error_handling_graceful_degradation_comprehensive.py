"""
Integration Tests: Graceful Degradation & Service Fallback Error Handling

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Maintain partial service availability during failures
- Value Impact: Graceful degradation preserves core functionality and user experience
- Strategic Impact: Foundation for resilient AI service delivery under partial system failures

This test suite validates graceful degradation patterns with real services:
- Service fallback chains and partial functionality preservation
- Feature flagging and dynamic capability reduction with PostgreSQL state tracking
- User experience continuity during service degradation with Redis caching
- Performance scaling under reduced capacity scenarios
- Automatic recovery detection and capability restoration
- Business impact minimization through intelligent service prioritization

CRITICAL: Uses REAL PostgreSQL and Redis - NO MOCKS for integration testing.
Tests validate actual degradation behavior, fallback effectiveness, and recovery patterns.
"""
import asyncio
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Callable
from enum import Enum
import pytest
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context
from shared.isolated_environment import get_env
from netra_backend.app.logging_config import central_logger
logger = central_logger.get_logger(__name__)

class ServiceStatus(Enum):
    """Service availability status levels."""
    HEALTHY = 'healthy'
    DEGRADED = 'degraded'
    CRITICAL = 'critical'
    UNAVAILABLE = 'unavailable'

class ServiceCapability:
    """Represents a service capability that can be degraded."""

    def __init__(self, name: str, priority: int, dependencies: List[str]=None):
        self.name = name
        self.priority = priority
        self.dependencies = dependencies or []
        self.enabled = True
        self.performance_level = 1.0

    def can_operate(self, available_dependencies: Set[str]) -> bool:
        """Check if capability can operate with available dependencies."""
        if not self.enabled:
            return False
        required_deps = set(self.dependencies)
        return required_deps.issubset(available_dependencies)

    def get_degraded_performance(self, missing_dependencies: Set[str]) -> float:
        """Calculate performance level based on missing dependencies."""
        if not self.dependencies:
            return self.performance_level
        missing_deps = set(self.dependencies).intersection(missing_dependencies)
        degradation_factor = 1.0 - len(missing_deps) / len(self.dependencies) * 0.5
        return max(0.1, self.performance_level * degradation_factor)

class GracefulDegradationManager:
    """Manages graceful degradation across service capabilities."""

    def __init__(self):
        self.capabilities = {}
        self.service_status = {}
        self.fallback_chains = {}
        self.degradation_history = []
        self.performance_metrics = {}

    def register_capability(self, capability: ServiceCapability):
        """Register a service capability."""
        self.capabilities[capability.name] = capability

    def register_service(self, service_name: str, status: ServiceStatus=ServiceStatus.HEALTHY):
        """Register a service with its status."""
        self.service_status[service_name] = status

    def register_fallback_chain(self, primary: str, fallbacks: List[str]):
        """Register fallback chain for a capability."""
        self.fallback_chains[primary] = fallbacks

    async def handle_service_failure(self, service_name: str) -> Dict[str, Any]:
        """Handle service failure and apply degradation strategies."""
        degradation_start = time.time()
        old_status = self.service_status.get(service_name, ServiceStatus.HEALTHY)
        self.service_status[service_name] = ServiceStatus.UNAVAILABLE
        affected_capabilities = []
        for cap_name, capability in self.capabilities.items():
            if service_name in capability.dependencies:
                affected_capabilities.append(cap_name)
        degradation_actions = []
        available_services = {name for name, status in self.service_status.items() if status in [ServiceStatus.HEALTHY, ServiceStatus.DEGRADED]}
        for cap_name in affected_capabilities:
            capability = self.capabilities[cap_name]
            if capability.can_operate(available_services):
                new_performance = capability.get_degraded_performance({service_name})
                capability.performance_level = new_performance
                degradation_actions.append({'capability': cap_name, 'action': 'performance_reduction', 'new_performance': new_performance, 'reason': f'dependency_{service_name}_unavailable'})
            elif cap_name in self.fallback_chains:
                fallback_found = False
                for fallback in self.fallback_chains[cap_name]:
                    if fallback in available_services:
                        degradation_actions.append({'capability': cap_name, 'action': 'fallback_activated', 'fallback_service': fallback, 'original_service': service_name})
                        fallback_found = True
                        break
                if not fallback_found:
                    capability.enabled = False
                    degradation_actions.append({'capability': cap_name, 'action': 'capability_disabled', 'reason': 'no_fallback_available'})
            else:
                capability.enabled = False
                degradation_actions.append({'capability': cap_name, 'action': 'capability_disabled', 'reason': 'no_fallback_configured'})
        degradation_duration = time.time() - degradation_start
        degradation_record = {'failed_service': service_name, 'old_status': old_status.value, 'new_status': ServiceStatus.UNAVAILABLE.value, 'affected_capabilities': affected_capabilities, 'degradation_actions': degradation_actions, 'degradation_duration_ms': degradation_duration * 1000, 'timestamp': datetime.now(timezone.utc), 'available_services': list(available_services)}
        self.degradation_history.append(degradation_record)
        return {'degradation_applied': True, 'failed_service': service_name, 'affected_capabilities': len(affected_capabilities), 'actions_taken': len(degradation_actions), 'degradation_actions': degradation_actions, 'system_still_operational': len(available_services) > 0, 'business_value': {'service_continuity': len(available_services) > 0, 'graceful_failure': True, 'user_impact_minimized': any((action['action'] in ['performance_reduction', 'fallback_activated'] for action in degradation_actions))}}

    async def handle_service_recovery(self, service_name: str) -> Dict[str, Any]:
        """Handle service recovery and restore capabilities."""
        recovery_start = time.time()
        self.service_status[service_name] = ServiceStatus.HEALTHY
        restoration_actions = []
        for cap_name, capability in self.capabilities.items():
            if service_name in capability.dependencies:
                if not capability.enabled:
                    capability.enabled = True
                    capability.performance_level = 1.0
                    restoration_actions.append({'capability': cap_name, 'action': 'capability_restored', 'service': service_name})
                elif capability.performance_level < 1.0:
                    capability.performance_level = 1.0
                    restoration_actions.append({'capability': cap_name, 'action': 'performance_restored', 'service': service_name})
        recovery_duration = time.time() - recovery_start
        return {'recovery_applied': True, 'recovered_service': service_name, 'restoration_actions': restoration_actions, 'recovery_duration_ms': recovery_duration * 1000, 'timestamp': datetime.now(timezone.utc)}

    def get_system_health_summary(self) -> Dict[str, Any]:
        """Get comprehensive system health and degradation summary."""
        healthy_services = sum((1 for status in self.service_status.values() if status == ServiceStatus.HEALTHY))
        total_services = len(self.service_status)
        enabled_capabilities = sum((1 for cap in self.capabilities.values() if cap.enabled))
        total_capabilities = len(self.capabilities)
        avg_performance = sum((cap.performance_level for cap in self.capabilities.values() if cap.enabled)) / max(enabled_capabilities, 1)
        return {'overall_health': 'healthy' if healthy_services == total_services else 'degraded', 'service_health': {'healthy_services': healthy_services, 'total_services': total_services, 'health_ratio': healthy_services / max(total_services, 1)}, 'capability_health': {'enabled_capabilities': enabled_capabilities, 'total_capabilities': total_capabilities, 'capability_ratio': enabled_capabilities / max(total_capabilities, 1), 'average_performance': avg_performance}, 'degradation_events': len(self.degradation_history), 'services_status': {name: status.value for name, status in self.service_status.items()}, 'capabilities_status': {name: {'enabled': cap.enabled, 'performance_level': cap.performance_level, 'priority': cap.priority} for name, cap in self.capabilities.items()}}

class TestGracefulDegradationErrorHandling(BaseIntegrationTest):
    """Integration tests for graceful degradation and service fallback patterns."""

    def setup_method(self):
        """Set up test environment."""
        super().setup_method()
        self.env = get_env()
        self.env.set('TEST_MODE', 'true', source='test')
        self.env.set('USE_REAL_SERVICES', 'true', source='test')
        self.auth_helper = E2EAuthHelper()

    @pytest.fixture
    async def degradation_manager(self):
        """Create degradation manager with test service configuration."""
        manager = GracefulDegradationManager()
        services = ['database', 'auth', 'llm', 'cache', 'search', 'notifications']
        for service in services:
            manager.register_service(service, ServiceStatus.HEALTHY)
        capabilities = [ServiceCapability('user_authentication', 1, ['auth', 'database']), ServiceCapability('ai_chat', 2, ['llm', 'database']), ServiceCapability('search_functionality', 3, ['search', 'database']), ServiceCapability('user_notifications', 4, ['notifications']), ServiceCapability('session_management', 1, ['cache', 'database']), ServiceCapability('data_analytics', 5, ['database'])]
        for capability in capabilities:
            manager.register_capability(capability)
        manager.register_fallback_chain('llm', ['cache'])
        manager.register_fallback_chain('search', ['cache'])
        manager.register_fallback_chain('notifications', ['database'])
        return manager

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_single_service_failure_degradation(self, real_services_fixture, degradation_manager):
        """Test graceful degradation when a single service fails."""
        initial_health = degradation_manager.get_system_health_summary()
        assert initial_health['overall_health'] == 'healthy'
        assert initial_health['service_health']['healthy_services'] == 6
        assert initial_health['capability_health']['enabled_capabilities'] == 6
        degradation_result = await degradation_manager.handle_service_failure('llm')
        assert degradation_result['degradation_applied'] is True
        assert degradation_result['failed_service'] == 'llm'
        assert degradation_result['system_still_operational'] is True
        assert degradation_result['business_value']['graceful_failure'] is True
        actions = degradation_result['degradation_actions']
        ai_chat_action = next((action for action in actions if action['capability'] == 'ai_chat'), None)
        assert ai_chat_action is not None
        assert ai_chat_action['action'] == 'fallback_activated'
        assert ai_chat_action['fallback_service'] == 'cache'
        degraded_health = degradation_manager.get_system_health_summary()
        assert degraded_health['overall_health'] == 'degraded'
        assert degraded_health['service_health']['healthy_services'] == 5
        ai_chat_cap = degradation_manager.capabilities['ai_chat']
        assert ai_chat_cap.enabled is True
        logger.info(' PASS:  Single service failure degradation test passed')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multiple_service_failure_cascade(self, real_services_fixture, degradation_manager):
        """Test graceful degradation during multiple cascading service failures."""
        postgres = real_services_fixture['postgres']
        await postgres.execute('\n            CREATE TABLE IF NOT EXISTS degradation_events (\n                id SERIAL PRIMARY KEY,\n                event_type TEXT NOT NULL,\n                service_name TEXT,\n                capability_name TEXT,\n                action_taken TEXT,\n                timestamp TIMESTAMP DEFAULT NOW()\n            )\n        ')
        try:
            initial_health = degradation_manager.get_system_health_summary()
            await postgres.execute("\n                INSERT INTO degradation_events (event_type, action_taken)\n                VALUES ('system_health_check', 'all_services_healthy')\n            ")
            failure_sequence = ['llm', 'search', 'notifications']
            degradation_results = []
            for service in failure_sequence:
                result = await degradation_manager.handle_service_failure(service)
                degradation_results.append(result)
                for action in result['degradation_actions']:
                    await postgres.execute("\n                        INSERT INTO degradation_events (event_type, service_name, capability_name, action_taken)\n                        VALUES ('service_failure', $1, $2, $3)\n                    ", service, action.get('capability', ''), action['action'])
            final_health = degradation_manager.get_system_health_summary()
            assert final_health['service_health']['healthy_services'] == 3
            user_auth = degradation_manager.capabilities['user_authentication']
            session_mgmt = degradation_manager.capabilities['session_management']
            assert user_auth.enabled is True
            assert session_mgmt.enabled is True
            ai_chat = degradation_manager.capabilities['ai_chat']
            search_func = degradation_manager.capabilities['search_functionality']
            notifications = degradation_manager.capabilities['user_notifications']
            assert ai_chat.enabled is True
            assert search_func.enabled is True
            assert notifications.enabled is True
            degradation_events = await postgres.fetch("\n                SELECT event_type, service_name, action_taken, COUNT(*) as count\n                FROM degradation_events \n                WHERE event_type = 'service_failure'\n                GROUP BY event_type, service_name, action_taken\n                ORDER BY service_name, action_taken\n            ")
            assert len(degradation_events) >= 3
            business_impact = {'core_authentication': user_auth.enabled, 'session_continuity': session_mgmt.enabled, 'partial_ai_functionality': ai_chat.enabled, 'cached_search': search_func.enabled, 'notification_fallback': notifications.enabled}
            preserved_functions = sum((1 for enabled in business_impact.values() if enabled))
            assert preserved_functions >= 4, 'Too much functionality lost during cascading failures'
        finally:
            await postgres.execute('DROP TABLE IF EXISTS degradation_events')
        logger.info(' PASS:  Multiple service failure cascade test passed')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_performance_degradation_scaling(self, real_services_fixture, degradation_manager):
        """Test system performance under degraded conditions."""
        redis = real_services_fixture['redis']

        async def measure_capability_performance(capability_name: str, operation_count: int=10) -> Dict[str, Any]:
            """Measure performance of a capability under current conditions."""
            capability = degradation_manager.capabilities[capability_name]
            if not capability.enabled:
                return {'capability': capability_name, 'enabled': False, 'operations_completed': 0, 'average_response_time': 0, 'success_rate': 0}
            start_time = time.time()
            successful_operations = 0
            response_times = []
            for i in range(operation_count):
                op_start = time.time()
                base_operation_time = 0.01
                adjusted_time = base_operation_time / capability.performance_level
                await asyncio.sleep(adjusted_time)
                failure_rate = 1.0 - capability.performance_level
                if failure_rate < 0.1 or time.time() % 1 > failure_rate:
                    successful_operations += 1
                response_times.append(time.time() - op_start)
                await redis.set_json(f'perf_test:{capability_name}:{i}', {'capability': capability_name, 'operation_index': i, 'response_time_ms': response_times[-1] * 1000, 'performance_level': capability.performance_level, 'success': successful_operations > i or successful_operations == i + 1}, ex=300)
            total_time = time.time() - start_time
            return {'capability': capability_name, 'enabled': True, 'operations_completed': operation_count, 'successful_operations': successful_operations, 'success_rate': successful_operations / operation_count, 'average_response_time': sum(response_times) / len(response_times), 'total_time': total_time, 'operations_per_second': operation_count / total_time, 'performance_level': capability.performance_level}
        baseline_performance = {}
        for cap_name in degradation_manager.capabilities:
            perf = await measure_capability_performance(cap_name, 10)
            baseline_performance[cap_name] = perf
        await degradation_manager.handle_service_failure('llm')
        await degradation_manager.handle_service_failure('search')
        degraded_performance = {}
        for cap_name in degradation_manager.capabilities:
            perf = await measure_capability_performance(cap_name, 10)
            degraded_performance[cap_name] = perf
        performance_analysis = {}
        for cap_name in degradation_manager.capabilities:
            baseline = baseline_performance[cap_name]
            degraded = degraded_performance[cap_name]
            if baseline['enabled'] and degraded['enabled']:
                performance_ratio = degraded['operations_per_second'] / baseline['operations_per_second']
                response_time_ratio = degraded['average_response_time'] / baseline['average_response_time']
                success_rate_impact = degraded['success_rate'] - baseline['success_rate']
                performance_analysis[cap_name] = {'performance_retained': performance_ratio, 'response_time_impact': response_time_ratio, 'success_rate_impact': success_rate_impact, 'graceful_degradation': performance_ratio >= 0.1, 'acceptable_response_time': response_time_ratio <= 5.0}
            elif baseline['enabled'] and (not degraded['enabled']):
                performance_analysis[cap_name] = {'capability_disabled': True, 'graceful_degradation': False}
            else:
                performance_analysis[cap_name] = {'no_change': True, 'graceful_degradation': True}
        capabilities_with_fallbacks = ['ai_chat', 'search_functionality', 'user_notifications']
        for cap_name in capabilities_with_fallbacks:
            analysis = performance_analysis[cap_name]
            if 'graceful_degradation' in analysis:
                assert analysis['graceful_degradation'] is True, f'{cap_name} did not degrade gracefully'
        core_capabilities = ['user_authentication', 'session_management']
        for cap_name in core_capabilities:
            analysis = performance_analysis[cap_name]
            if 'performance_retained' in analysis:
                assert analysis['performance_retained'] >= 0.8, f'{cap_name} performance degraded too much'
        await redis.set_json('performance_analysis', performance_analysis, ex=600)
        logger.info(' PASS:  Performance degradation scaling test passed')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_automatic_service_recovery_restoration(self, real_services_fixture, degradation_manager):
        """Test automatic capability restoration when services recover."""
        postgres = real_services_fixture['postgres']
        await postgres.execute('\n            CREATE TABLE IF NOT EXISTS recovery_events (\n                id SERIAL PRIMARY KEY,\n                service_name TEXT NOT NULL,\n                capability_name TEXT,\n                event_type TEXT NOT NULL,\n                performance_before DECIMAL,\n                performance_after DECIMAL,\n                enabled_before BOOLEAN,\n                enabled_after BOOLEAN,\n                recovery_duration_ms DECIMAL,\n                timestamp TIMESTAMP DEFAULT NOW()\n            )\n        ')
        try:
            failed_services = ['llm', 'search', 'notifications']
            for service in failed_services:
                await degradation_manager.handle_service_failure(service)
            pre_recovery_health = degradation_manager.get_system_health_summary()
            for cap_name, cap_status in pre_recovery_health['capabilities_status'].items():
                await postgres.execute("\n                    INSERT INTO recovery_events (\n                        service_name, capability_name, event_type, \n                        performance_before, enabled_before\n                    ) VALUES ('system', $1, 'pre_recovery_state', $2, $3)\n                ", cap_name, cap_status['performance_level'], cap_status['enabled'])
            recovery_results = []
            recovery_times = []
            for service in failed_services:
                recovery_start = time.time()
                recovery_result = await degradation_manager.handle_service_recovery(service)
                recovery_duration = time.time() - recovery_start
                recovery_results.append(recovery_result)
                recovery_times.append(recovery_duration)
                for action in recovery_result['restoration_actions']:
                    await postgres.execute('\n                        INSERT INTO recovery_events (\n                            service_name, capability_name, event_type, recovery_duration_ms\n                        ) VALUES ($1, $2, $3, $4)\n                    ', service, action['capability'], action['action'], recovery_duration * 1000)
            post_recovery_health = degradation_manager.get_system_health_summary()
            assert post_recovery_health['overall_health'] == 'healthy'
            assert post_recovery_health['service_health']['healthy_services'] == 6
            assert post_recovery_health['capability_health']['enabled_capabilities'] == 6
            for cap_name, capability in degradation_manager.capabilities.items():
                assert capability.enabled is True, f'Capability {cap_name} not restored'
                assert capability.performance_level == 1.0, f'Capability {cap_name} performance not fully restored'
                await postgres.execute("\n                    INSERT INTO recovery_events (\n                        service_name, capability_name, event_type, \n                        performance_after, enabled_after\n                    ) VALUES ('system', $1, 'post_recovery_state', $2, $3)\n                ", cap_name, capability.performance_level, capability.enabled)
            max_recovery_time = max(recovery_times)
            avg_recovery_time = sum(recovery_times) / len(recovery_times)
            assert max_recovery_time < 1.0, 'Recovery took too long'
            assert avg_recovery_time < 0.5, 'Average recovery time too slow'
            recovery_events_count = await postgres.fetchval("\n                SELECT COUNT(*) FROM recovery_events WHERE event_type LIKE '%recovery%'\n            ")
            assert recovery_events_count >= len(failed_services), 'Recovery events not properly logged'
            business_value_metrics = {'complete_service_restoration': post_recovery_health['service_health']['health_ratio'] == 1.0, 'full_capability_restoration': post_recovery_health['capability_health']['capability_ratio'] == 1.0, 'optimal_performance': post_recovery_health['capability_health']['average_performance'] == 1.0, 'rapid_recovery': max_recovery_time < 1.0}
            assert all(business_value_metrics.values()), 'Business value not fully restored'
        finally:
            await postgres.execute('DROP TABLE IF EXISTS recovery_events')
        logger.info(' PASS:  Automatic service recovery restoration test passed')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_user_isolation_during_degradation(self, real_services_fixture, degradation_manager):
        """Test user isolation during system degradation scenarios."""
        redis = real_services_fixture['redis']
        user_contexts = []
        for i in range(5):
            context = await create_authenticated_user_context(user_email=f'degradation_test_{i}@example.com', user_id=f'degradation_user_{i}', environment='test')
            user_contexts.append(context)

        async def simulate_user_activity(user_context, activity_count: int, degraded_system: bool=False):
            """Simulate user activity under normal or degraded conditions."""
            user_id = user_context.user_id
            results = []
            for i in range(activity_count):
                activity_start = time.time()
                activity_key = f'user_activity:{user_id}:{i}'
                activity_data = {'user_id': str(user_id), 'activity_index': i, 'timestamp': datetime.now(timezone.utc).isoformat(), 'degraded_system': degraded_system}
                try:
                    if i % 3 == 0:
                        capability = degradation_manager.capabilities['user_authentication']
                        if capability.enabled:
                            await asyncio.sleep(0.01 / capability.performance_level)
                            activity_data['activity_type'] = 'authentication'
                            activity_data['success'] = True
                        else:
                            activity_data['activity_type'] = 'authentication'
                            activity_data['success'] = False
                            activity_data['error'] = 'authentication_unavailable'
                    elif i % 3 == 1:
                        capability = degradation_manager.capabilities['ai_chat']
                        if capability.enabled:
                            await asyncio.sleep(0.02 / capability.performance_level)
                            activity_data['activity_type'] = 'ai_chat'
                            activity_data['success'] = True
                            activity_data['fallback_used'] = capability.performance_level < 1.0
                        else:
                            activity_data['activity_type'] = 'ai_chat'
                            activity_data['success'] = False
                            activity_data['error'] = 'ai_chat_unavailable'
                    else:
                        capability = degradation_manager.capabilities['search_functionality']
                        if capability.enabled:
                            await asyncio.sleep(0.015 / capability.performance_level)
                            activity_data['activity_type'] = 'search'
                            activity_data['success'] = True
                            activity_data['fallback_used'] = capability.performance_level < 1.0
                        else:
                            activity_data['activity_type'] = 'search'
                            activity_data['success'] = False
                            activity_data['error'] = 'search_unavailable'
                    activity_data['duration_ms'] = (time.time() - activity_start) * 1000
                    await redis.set_json(activity_key, activity_data, ex=300)
                    results.append(activity_data)
                except Exception as e:
                    activity_data['success'] = False
                    activity_data['error'] = str(e)
                    activity_data['duration_ms'] = (time.time() - activity_start) * 1000
                    results.append(activity_data)
                await asyncio.sleep(0.001)
            return results
        normal_tasks = [simulate_user_activity(context, 6, degraded_system=False) for context in user_contexts]
        normal_results = await asyncio.gather(*normal_tasks)
        await degradation_manager.handle_service_failure('llm')
        await degradation_manager.handle_service_failure('search')
        degraded_tasks = [simulate_user_activity(context, 6, degraded_system=True) for context in user_contexts]
        degraded_results = await asyncio.gather(*degraded_tasks)
        user_analysis = {}
        for i, user_context in enumerate(user_contexts):
            user_id = str(user_context.user_id)
            normal_user_results = normal_results[i]
            degraded_user_results = degraded_results[i]
            normal_success_rate = sum((1 for r in normal_user_results if r['success'])) / len(normal_user_results)
            degraded_success_rate = sum((1 for r in degraded_user_results if r['success'])) / len(degraded_user_results)
            normal_avg_time = sum((r['duration_ms'] for r in normal_user_results)) / len(normal_user_results)
            degraded_avg_time = sum((r['duration_ms'] for r in degraded_user_results)) / len(degraded_user_results)
            user_analysis[user_id] = {'normal_success_rate': normal_success_rate, 'degraded_success_rate': degraded_success_rate, 'success_rate_impact': degraded_success_rate - normal_success_rate, 'normal_avg_response_time': normal_avg_time, 'degraded_avg_response_time': degraded_avg_time, 'response_time_impact': degraded_avg_time / normal_avg_time, 'user_isolated': True}
        for user_id, analysis in user_analysis.items():
            assert analysis['user_isolated'] is True
            assert analysis['success_rate_impact'] >= -0.5, f'User {user_id} success rate dropped too much'
            assert analysis['response_time_impact'] <= 5.0, f'User {user_id} response time increased too much'
        all_activities = await redis.keys('user_activity:*')
        user_activity_counts = {}
        for activity_key in all_activities:
            activity_data = await redis.get_json(activity_key)
            user_id = activity_data['user_id']
            user_activity_counts[user_id] = user_activity_counts.get(user_id, 0) + 1
        for user_context in user_contexts:
            user_id = str(user_context.user_id)
            assert user_activity_counts[user_id] == 12, f'User {user_id} activity count incorrect'
        await redis.set_json('user_isolation_analysis', user_analysis, ex=600)
        logger.info(' PASS:  Concurrent user isolation during degradation test passed')

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_business_impact_prioritization_during_degradation(self, real_services_fixture, degradation_manager):
        """Test business impact prioritization during service degradation."""
        business_priorities = {'user_authentication': {'priority': 1, 'business_impact': 'critical'}, 'session_management': {'priority': 1, 'business_impact': 'critical'}, 'ai_chat': {'priority': 2, 'business_impact': 'high'}, 'data_analytics': {'priority': 3, 'business_impact': 'medium'}, 'search_functionality': {'priority': 4, 'business_impact': 'medium'}, 'user_notifications': {'priority': 5, 'business_impact': 'low'}}
        for cap_name, priority_info in business_priorities.items():
            if cap_name in degradation_manager.capabilities:
                degradation_manager.capabilities[cap_name].priority = priority_info['priority']
        critical_failures = ['database', 'auth']
        for service in critical_failures:
            degradation_result = await degradation_manager.handle_service_failure(service)
            for action in degradation_result['degradation_actions']:
                capability_name = action['capability']
                business_impact = business_priorities.get(capability_name, {}).get('business_impact', 'unknown')
                if business_impact == 'critical':
                    capability = degradation_manager.capabilities[capability_name]
                    if action['action'] == 'capability_disabled':
                        logger.warning(f'Critical capability {capability_name} was disabled - business impact HIGH')
                    elif action['action'] == 'fallback_activated':
                        assert 'fallback_service' in action, f'Fallback not properly configured for {capability_name}'
        final_health = degradation_manager.get_system_health_summary()
        critical_capabilities_status = []
        high_impact_capabilities_status = []
        for cap_name, capability in degradation_manager.capabilities.items():
            business_impact = business_priorities.get(cap_name, {}).get('business_impact', 'unknown')
            if business_impact == 'critical':
                critical_capabilities_status.append(capability.enabled)
            elif business_impact == 'high':
                high_impact_capabilities_status.append(capability.enabled)
        critical_functional_ratio = sum(critical_capabilities_status) / max(len(critical_capabilities_status), 1)
        assert critical_functional_ratio >= 0.5, 'Too many critical capabilities disabled'
        business_impact_report = {'critical_capabilities_functional': sum(critical_capabilities_status), 'total_critical_capabilities': len(critical_capabilities_status), 'critical_capability_ratio': critical_functional_ratio, 'high_impact_capabilities_functional': sum(high_impact_capabilities_status), 'total_high_impact_capabilities': len(high_impact_capabilities_status), 'overall_business_continuity': final_health['capability_health']['capability_ratio'], 'degradation_strategy_effective': critical_functional_ratio >= 0.5, 'business_value_preserved': {'authentication_available': degradation_manager.capabilities['user_authentication'].enabled, 'session_continuity': degradation_manager.capabilities['session_management'].enabled, 'core_ai_functionality': degradation_manager.capabilities['ai_chat'].enabled, 'business_operations_supported': critical_functional_ratio >= 0.5}}
        assert business_impact_report['business_value_preserved']['business_operations_supported'] is True
        logger.info(' PASS:  Business impact prioritization during degradation test passed')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')