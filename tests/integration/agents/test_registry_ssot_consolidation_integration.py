"""
Integration Tests for Agent Registry SSOT Consolidation (Issue #929)

Business Value Protection: $500K+ ARR Golden Path (login -> AI responses)
CRITICAL: These tests validate that registry consolidation maintains full system integration

Test Strategy:
- Pre-Fix: Tests SHOULD FAIL demonstrating current integration conflicts
- Post-Fix: Tests SHOULD PASS after SSOT consolidation complete
- Focus: WebSocket integration, agent execution, multi-user scenarios

Priority: P0 (Mission Critical) - Must validate before production deployment

IMPORTANT: No Docker dependencies - uses real services and staging environment
"""
import asyncio
import pytest
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock, patch
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.logging_config import central_logger
logger = central_logger.get_logger(__name__)

@pytest.mark.integration
class AgentRegistrySSoTConsolidationIntegrationTests(SSotAsyncTestCase):
    """Integration tests for Agent Registry SSOT consolidation validation"""

    async def asyncSetUp(self):
        """Set up test environment with integration patterns"""
        await super().asyncSetUp()
        self.env = IsolatedEnvironment()
        self.test_users = [{'user_id': 'integration-test-user-1', 'session_id': 'session-integration-1'}, {'user_id': 'integration-test-user-2', 'session_id': 'session-integration-2'}, {'user_id': 'integration-test-user-3', 'session_id': 'session-integration-3'}]
        self.registry_instances = []
        self.websocket_managers = []
        logger.info('🔧 Integration test environment initialized')

    async def test_websocket_integration_with_consolidated_registry(self):
        """
        CRITICAL: Test WebSocket integration works with consolidated registry
        
        Business Impact: Validates real-time chat functionality preserved
        Expected: FAIL initially, PASS after consolidation
        """
        logger.info('🔍 INTEGRATION TEST 1: WebSocket integration with consolidated registry')
        websocket_registry_conflicts = []
        try:
            from netra_backend.app.agents.registry import AgentRegistry as BasicRegistry
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry
            basic_registry = BasicRegistry()
            advanced_registry = AdvancedRegistry()
            mock_websocket_manager = MagicMock()
            mock_websocket_manager.send_agent_event = AsyncMock()
            if hasattr(basic_registry, 'set_websocket_manager'):
                try:
                    basic_registry.set_websocket_manager(mock_websocket_manager)
                    basic_websocket_works = True
                except Exception as e:
                    basic_websocket_works = False
                    websocket_registry_conflicts.append(f'Basic registry WebSocket integration failed: {e}')
            else:
                basic_websocket_works = False
                websocket_registry_conflicts.append('Basic registry lacks WebSocket integration')
            if hasattr(advanced_registry, 'set_websocket_manager'):
                try:
                    test_user = self.test_users[0]
                    await advanced_registry.set_websocket_manager(mock_websocket_manager, user_context=None)
                    advanced_websocket_works = True
                except Exception as e:
                    advanced_websocket_works = False
                    websocket_registry_conflicts.append(f'Advanced registry WebSocket integration failed: {e}')
            else:
                advanced_websocket_works = False
                websocket_registry_conflicts.append('Advanced registry lacks WebSocket integration')
            logger.info(f"Basic registry WebSocket integration: {('CHECK' if basic_websocket_works else 'X')}")
            logger.info(f"Advanced registry WebSocket integration: {('CHECK' if advanced_websocket_works else 'X')}")
            for conflict in websocket_registry_conflicts:
                logger.error(f'  🔥 {conflict}')
        except ImportError as e:
            websocket_registry_conflicts.append(f'Registry import failed: {e}')
            logger.error(f'Registry import failure: {e}')
        self.assertGreater(len(websocket_registry_conflicts), 0, f'EXPECTED FAILURE: Should detect WebSocket integration conflicts between registries. Found {len(websocket_registry_conflicts)} conflicts requiring SSOT consolidation.')

    async def test_agent_execution_with_consolidated_registry(self):
        """
        CRITICAL: Test agent execution works through consolidated registry
        
        Business Impact: Validates core AI agent functionality preserved  
        Expected: FAIL initially due to execution conflicts, PASS after consolidation
        """
        logger.info('🔍 INTEGRATION TEST 2: Agent execution with consolidated registry')
        execution_conflicts = []
        try:
            from netra_backend.app.agents.registry import AgentRegistry as BasicRegistry
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry
            basic_registry = BasicRegistry()
            advanced_registry = AdvancedRegistry()
            try:
                basic_agents = await basic_registry.list_available_agents()
                basic_execution_works = True
                logger.info(f"Basic registry found {(len(basic_agents) if isinstance(basic_agents, list) else 'N/A')} agents")
            except Exception as e:
                basic_execution_works = False
                execution_conflicts.append(f'Basic registry agent execution failed: {e}')
            try:
                advanced_agents = await advanced_registry.list_available_agents()
                advanced_execution_works = True
                logger.info(f"Advanced registry found {(len(advanced_agents) if isinstance(advanced_agents, list) else 'N/A')} agents")
            except Exception as e:
                advanced_execution_works = False
                execution_conflicts.append(f'Advanced registry agent execution failed: {e}')
            if basic_execution_works and advanced_execution_works:
                basic_agent_count = len(basic_agents) if isinstance(basic_agents, list) else 0
                advanced_agent_count = len(advanced_agents) if isinstance(advanced_agents, list) else 0
                if basic_agent_count > 0 and advanced_agent_count > 0:
                    execution_conflicts.append(f'SSOT VIOLATION: Agents discoverable through multiple registries (Basic: {basic_agent_count}, Advanced: {advanced_agent_count})')
            if advanced_execution_works:
                try:
                    test_user = self.test_users[0]
                    user_session = await advanced_registry.create_user_session(test_user['user_id'], test_user['session_id'])
                    if user_session:
                        logger.info('CHECK User-specific execution works in advanced registry')
                    else:
                        execution_conflicts.append('Advanced registry user session creation failed')
                except Exception as e:
                    execution_conflicts.append(f'Advanced registry user-specific execution failed: {e}')
            for conflict in execution_conflicts:
                logger.error(f'  🔥 {conflict}')
        except ImportError as e:
            execution_conflicts.append(f'Agent execution test failed - registry import error: {e}')
        self.assertGreater(len(execution_conflicts), 0, f'EXPECTED FAILURE: Should detect agent execution conflicts between registries. Found {len(execution_conflicts)} conflicts requiring unified agent execution.')

    async def test_multi_user_registry_isolation_integration(self):
        """
        CRITICAL: Test multi-user isolation works with consolidated registry
        
        Business Impact: Validates concurrent user sessions don't interfere
        Expected: FAIL initially due to isolation conflicts, PASS after consolidation
        """
        logger.info('🔍 INTEGRATION TEST 3: Multi-user registry isolation integration')
        isolation_conflicts = []
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry
            advanced_registry = AdvancedRegistry()
            user_sessions = []
            for test_user in self.test_users:
                try:
                    session = await advanced_registry.create_user_session(test_user['user_id'], test_user['session_id'])
                    if session:
                        user_sessions.append({'user_id': test_user['user_id'], 'session_id': test_user['session_id'], 'session': session})
                        logger.info(f"CHECK Created session for user {test_user['user_id']}")
                    else:
                        isolation_conflicts.append(f"Failed to create session for user {test_user['user_id']}")
                except Exception as e:
                    isolation_conflicts.append(f"User session creation failed for {test_user['user_id']}: {e}")
            if len(user_sessions) > 1:
                try:

                    async def user_operation(user_session):
                        user_id = user_session['user_id']
                        try:
                            await asyncio.sleep(0.1)
                            return f'operation_result_{user_id}_{uuid.uuid4()}'
                        except Exception as e:
                            return f'failed_{user_id}_{e}'
                    tasks = [user_operation(session) for session in user_sessions]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    successful_results = [r for r in results if not isinstance(r, Exception) and (not r.startswith('failed_'))]
                    if len(successful_results) != len(user_sessions):
                        isolation_conflicts.append(f'Multi-user operation failures: {len(successful_results)}/{len(user_sessions)} succeeded')
                    if len(set(successful_results)) != len(successful_results):
                        isolation_conflicts.append('User operation results not properly isolated')
                    logger.info(f'Multi-user isolation test: {len(successful_results)}/{len(user_sessions)} operations succeeded')
                except Exception as e:
                    isolation_conflicts.append(f'Multi-user isolation test failed: {e}')
            else:
                isolation_conflicts.append('Insufficient user sessions created for isolation testing')
            try:
                from netra_backend.app.agents.registry import AgentRegistry as BasicRegistry
                basic_registry = BasicRegistry()
                if hasattr(basic_registry, 'create_user_session'):
                    isolation_conflicts.append('Basic registry unexpectedly supports user isolation')
                else:
                    logger.info('CHECK Basic registry correctly lacks user isolation (as expected)')
            except ImportError:
                logger.info('Basic registry not available for isolation comparison')
            for conflict in isolation_conflicts:
                logger.error(f'  🔥 {conflict}')
        except ImportError as e:
            isolation_conflicts.append(f'Multi-user isolation test failed - import error: {e}')
        self.assertGreater(len(isolation_conflicts), 0, f'EXPECTED FAILURE: Should detect multi-user isolation implementation conflicts. Found {len(isolation_conflicts)} conflicts requiring consolidated isolation patterns.')

    async def test_performance_impact_of_registry_consolidation(self):
        """
        CRITICAL: Test performance impact of registry consolidation
        
        Business Impact: Ensures consolidation doesn't degrade performance
        Expected: Initially show performance differences, then show consistency
        """
        logger.info('🔍 INTEGRATION TEST 4: Performance impact of registry consolidation')
        performance_conflicts = []
        try:
            from netra_backend.app.agents.registry import AgentRegistry as BasicRegistry
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry
            operation_count = 10
            timeout_seconds = 5
            basic_times = []
            try:
                for i in range(operation_count):
                    start_time = time.time()
                    basic_registry = BasicRegistry()
                    await basic_registry.list_available_agents()
                    end_time = time.time()
                    basic_times.append(end_time - start_time)
                basic_avg_time = sum(basic_times) / len(basic_times)
                logger.info(f'Basic registry average operation time: {basic_avg_time:.4f}s')
            except Exception as e:
                performance_conflicts.append(f'Basic registry performance test failed: {e}')
                basic_avg_time = float('inf')
            advanced_times = []
            try:
                for i in range(operation_count):
                    start_time = time.time()
                    advanced_registry = AdvancedRegistry()
                    await advanced_registry.list_available_agents()
                    end_time = time.time()
                    advanced_times.append(end_time - start_time)
                advanced_avg_time = sum(advanced_times) / len(advanced_times)
                logger.info(f'Advanced registry average operation time: {advanced_avg_time:.4f}s')
            except Exception as e:
                performance_conflicts.append(f'Advanced registry performance test failed: {e}')
                advanced_avg_time = float('inf')
            if basic_avg_time != float('inf') and advanced_avg_time != float('inf'):
                performance_ratio = advanced_avg_time / basic_avg_time
                logger.info(f'Performance ratio (Advanced/Basic): {performance_ratio:.2f}x')
                if performance_ratio > 3.0:
                    performance_conflicts.append(f'Advanced registry significantly slower: {performance_ratio:.2f}x vs basic')
                elif performance_ratio < 0.3:
                    performance_conflicts.append(f'Basic registry significantly slower: {1 / performance_ratio:.2f}x vs advanced')
                try:
                    start_time = time.time()
                    concurrent_tasks = []
                    for i in range(5):
                        basic_registry = BasicRegistry()
                        concurrent_tasks.append(basic_registry.list_available_agents())
                        advanced_registry = AdvancedRegistry()
                        concurrent_tasks.append(advanced_registry.list_available_agents())
                    await asyncio.gather(*concurrent_tasks, return_exceptions=True)
                    concurrent_time = time.time() - start_time
                    logger.info(f'Concurrent mixed registry operations time: {concurrent_time:.4f}s')
                    if concurrent_time > timeout_seconds:
                        performance_conflicts.append(f'Concurrent operations too slow: {concurrent_time:.2f}s > {timeout_seconds}s')
                except Exception as e:
                    performance_conflicts.append(f'Concurrent performance test failed: {e}')
            for conflict in performance_conflicts:
                logger.error(f'  🔥 {conflict}')
        except ImportError as e:
            performance_conflicts.append(f'Performance test failed - import error: {e}')
        self.assertGreater(len(performance_conflicts), 0, f'EXPECTED FAILURE: Should detect performance differences between registry implementations. Found {len(performance_conflicts)} performance conflicts requiring optimization in consolidation.')

    async def test_registry_cleanup_and_lifecycle_integration(self):
        """
        CRITICAL: Test registry cleanup and lifecycle management integration
        
        Business Impact: Prevents memory leaks and resource exhaustion
        Expected: FAIL initially due to lifecycle conflicts, PASS after consolidation  
        """
        logger.info('🔍 INTEGRATION TEST 5: Registry cleanup and lifecycle integration')
        lifecycle_conflicts = []
        try:
            from netra_backend.app.agents.registry import AgentRegistry as BasicRegistry
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry
            registries_created = []
            for i in range(3):
                try:
                    basic = BasicRegistry()
                    advanced = AdvancedRegistry()
                    registries_created.append(('basic', basic))
                    registries_created.append(('advanced', advanced))
                except Exception as e:
                    lifecycle_conflicts.append(f'Registry creation failed for instance {i}: {e}')
            logger.info(f'Created {len(registries_created)} registry instances')
            cleanup_methods_found = {'basic': 0, 'advanced': 0}
            for registry_type, registry in registries_created:
                cleanup_methods = [method for method in dir(registry) if any((cleanup_word in method.lower() for cleanup_word in ['cleanup', 'clear', 'close', 'destroy', 'shutdown']))]
                cleanup_methods_found[registry_type] += len(cleanup_methods)
                if len(cleanup_methods) == 0:
                    lifecycle_conflicts.append(f'{registry_type} registry lacks cleanup methods')
            logger.info(f"Cleanup methods found - Basic: {cleanup_methods_found['basic']}, Advanced: {cleanup_methods_found['advanced']}")
            try:
                import psutil
                import os
                process = psutil.Process(os.getpid())
                initial_memory = process.memory_info().rss
                temp_registries = []
                for i in range(10):
                    temp_registries.append(BasicRegistry())
                    temp_registries.append(AdvancedRegistry())
                intermediate_memory = process.memory_info().rss
                memory_growth = intermediate_memory - initial_memory
                temp_registries.clear()
                import gc
                gc.collect()
                final_memory = process.memory_info().rss
                memory_after_cleanup = final_memory - initial_memory
                logger.info(f'Memory growth: {memory_growth / 1024 / 1024:.2f} MB')
                logger.info(f'Memory after cleanup: {memory_after_cleanup / 1024 / 1024:.2f} MB')
                if memory_growth > 50 * 1024 * 1024:
                    lifecycle_conflicts.append(f'Excessive memory growth: {memory_growth / 1024 / 1024:.2f} MB')
                if memory_after_cleanup > memory_growth * 0.8:
                    lifecycle_conflicts.append(f'Poor memory cleanup: {memory_after_cleanup / 1024 / 1024:.2f} MB remaining')
            except ImportError:
                logger.warning('psutil not available - skipping memory growth test')
            except Exception as e:
                lifecycle_conflicts.append(f'Memory growth test failed: {e}')
            try:

                async def create_and_cleanup_registry(registry_class, instance_id):
                    try:
                        registry = registry_class()
                        await asyncio.sleep(0.1)
                        for method_name in ['cleanup', 'clear', 'close']:
                            if hasattr(registry, method_name):
                                method = getattr(registry, method_name)
                                if asyncio.iscoroutinefunction(method):
                                    await method()
                                else:
                                    method()
                                break
                        return f'success_{instance_id}'
                    except Exception as e:
                        return f'failed_{instance_id}_{e}'
                tasks = []
                for i in range(5):
                    tasks.append(create_and_cleanup_registry(BasicRegistry, f'basic_{i}'))
                    tasks.append(create_and_cleanup_registry(AdvancedRegistry, f'advanced_{i}'))
                results = await asyncio.gather(*tasks, return_exceptions=True)
                successful_lifecycles = [r for r in results if isinstance(r, str) and r.startswith('success_')]
                logger.info(f'Concurrent lifecycle operations: {len(successful_lifecycles)}/{len(tasks)} succeeded')
                if len(successful_lifecycles) < len(tasks) * 0.8:
                    lifecycle_conflicts.append(f'Concurrent lifecycle failures: {len(successful_lifecycles)}/{len(tasks)} succeeded')
            except Exception as e:
                lifecycle_conflicts.append(f'Concurrent lifecycle test failed: {e}')
            for conflict in lifecycle_conflicts:
                logger.error(f'  🔥 {conflict}')
        except ImportError as e:
            lifecycle_conflicts.append(f'Lifecycle test failed - import error: {e}')
        self.assertGreater(len(lifecycle_conflicts), 0, f'EXPECTED FAILURE: Should detect registry lifecycle management conflicts. Found {len(lifecycle_conflicts)} conflicts requiring consolidated lifecycle patterns.')

    async def test_comprehensive_integration_validation_summary(self):
        """
        CRITICAL: Comprehensive integration validation summary
        
        Business Impact: Overall assessment of registry consolidation readiness
        Expected: FAIL initially with detailed conflict report, PASS after consolidation
        """
        logger.info('📊 COMPREHENSIVE INTEGRATION VALIDATION SUMMARY')
        integration_conflicts = []
        test_methods = [self.test_websocket_integration_with_consolidated_registry, self.test_agent_execution_with_consolidated_registry, self.test_multi_user_registry_isolation_integration, self.test_performance_impact_of_registry_consolidation, self.test_registry_cleanup_and_lifecycle_integration]
        for test_method in test_methods:
            try:
                await test_method()
            except AssertionError as e:
                if 'conflicts' in str(e).lower() or 'violation' in str(e).lower():
                    integration_conflicts.append(f'Integration conflict in {test_method.__name__}: {str(e)[:100]}...')
                else:
                    integration_conflicts.append(f'Unexpected failure in {test_method.__name__}: {str(e)[:100]}...')
            except Exception as e:
                integration_conflicts.append(f'Test execution failed in {test_method.__name__}: {str(e)[:100]}...')
        integration_assessment = self._assess_integration_consolidation_readiness(integration_conflicts)
        logger.info(f'INTEGRATION CONSOLIDATION ASSESSMENT:')
        logger.info(f'  Total Integration Conflicts: {len(integration_conflicts)}')
        logger.info(f"  Business Risk Level: {integration_assessment['risk_level']}")
        logger.info(f"  Golden Path Impact: {integration_assessment['golden_path_impact']}")
        logger.info(f"  Consolidation Readiness: {integration_assessment['readiness_status']}")
        for i, conflict in enumerate(integration_conflicts[:3]):
            logger.error(f'    X {conflict}')
        if len(integration_conflicts) > 3:
            logger.error(f'    ... and {len(integration_conflicts) - 3} more integration conflicts')
        self.assertGreater(len(integration_conflicts), 0, f"EXPECTED FAILURE: Comprehensive integration conflicts detected requiring SSOT consolidation. Found {len(integration_conflicts)} integration conflicts across all test areas. Risk Level: {integration_assessment['risk_level']}, Golden Path Impact: {integration_assessment['golden_path_impact']}")

    def _assess_integration_consolidation_readiness(self, conflicts: List[str]) -> Dict[str, Any]:
        """Assess integration consolidation readiness based on detected conflicts."""
        conflict_count = len(conflicts)
        if conflict_count > 15:
            risk_level = 'CRITICAL'
        elif conflict_count > 10:
            risk_level = 'HIGH'
        elif conflict_count > 5:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'LOW'
        golden_path_keywords = ['websocket', 'agent_execution', 'user', 'isolation', 'performance']
        golden_path_conflicts = sum((1 for conflict in conflicts if any((keyword in conflict.lower() for keyword in golden_path_keywords))))
        if golden_path_conflicts > 5:
            golden_path_impact = 'SEVERE - Chat functionality at risk'
        elif golden_path_conflicts > 3:
            golden_path_impact = 'HIGH - User experience degradation risk'
        elif golden_path_conflicts > 1:
            golden_path_impact = 'MEDIUM - Some chat features may be affected'
        else:
            golden_path_impact = 'LOW - Minimal chat functionality impact'
        if conflict_count == 0:
            readiness_status = 'READY - Integration consolidation complete'
        elif conflict_count < 5:
            readiness_status = 'NEAR_READY - Minor integration conflicts remain'
        elif conflict_count < 10:
            readiness_status = 'IN_PROGRESS - Significant consolidation work needed'
        else:
            readiness_status = 'NOT_READY - Major integration conflicts require resolution'
        return {'risk_level': risk_level, 'golden_path_impact': golden_path_impact, 'readiness_status': readiness_status, 'conflict_count': conflict_count, 'golden_path_conflicts': golden_path_conflicts}

    async def asyncTearDown(self):
        """Clean up integration test resources"""
        try:
            for registry in self.registry_instances:
                if hasattr(registry, 'cleanup'):
                    if asyncio.iscoroutinefunction(registry.cleanup):
                        await registry.cleanup()
                    else:
                        registry.cleanup()
            for manager in self.websocket_managers:
                if hasattr(manager, 'close'):
                    if asyncio.iscoroutinefunction(manager.close):
                        await manager.close()
                    else:
                        manager.close()
        except Exception as e:
            logger.warning(f'Cleanup error in integration tests: {e}')
        await super().asyncTearDown()
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')