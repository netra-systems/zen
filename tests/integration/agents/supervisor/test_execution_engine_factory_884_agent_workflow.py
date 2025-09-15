"""Phase 1 Integration Tests: Execution Engine Factory Agent Workflow (Issue #884)

CRITICAL BUSINESS VALUE: These tests reproduce agent workflow coordination failures
in execution engine factory patterns that cause incomplete agent executions and
Golden Path failures, protecting $500K+ ARR functionality.

EXPECTED BEHAVIOR: All tests in this file should INITIALLY FAIL to demonstrate
agent workflow integration issues. They will pass after SSOT consolidation.

Business Value Justification (BVJ):
- Segment: All Segments (Agent workflows are core business value)
- Business Goal: Ensure reliable agent execution for chat functionality
- Value Impact: Prevents incomplete agent responses, workflow failures
- Strategic Impact: Foundation for $500K+ ARR AI-powered user interactions

Test Philosophy:
- FAILING TESTS FIRST: These tests reproduce real agent workflow coordination issues
- REAL SERVICES: Tests use real agent infrastructure (NON-DOCKER)
- INTEGRATION FOCUS: Tests validate factory-agent workflow coordination
- GOLDEN PATH PROTECTION: Tests protect end-to-end agent execution
- BUSINESS VALUE VALIDATION: Tests ensure agents deliver meaningful results
"""
import pytest
import asyncio
import gc
import inspect
import json
import time
import uuid
import unittest
from datetime import datetime
from typing import Dict, List, Any, Optional
from unittest.mock import patch, MagicMock, AsyncMock
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.user_execution_context import UserExecutionContext

@pytest.mark.integration
class TestExecutionEngineFactoryAgentWorkflow884(SSotAsyncTestCase):
    """Phase 1 Integration Tests: Execution Engine Factory Agent Workflow

    These tests are designed to FAIL initially to demonstrate agent workflow
    coordination issues in factory patterns. They will pass after SSOT consolidation.
    """

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.test_users = []
        self.factory_instances = []
        self.created_contexts = []
        self.created_engines = []
        self.agent_workflow_failures = []
        self.factory_agent_mismatches = []
        self.execution_coordination_failures = []
        self.agent_execution_timeout = 30.0
        self.expected_agent_workflow_stages = ['agent_initialization', 'agent_execution', 'agent_completion', 'result_processing']

    async def asyncTearDown(self):
        """Clean up test resources."""
        for engine in self.created_engines:
            try:
                if hasattr(engine, 'cleanup'):
                    await engine.cleanup()
            except Exception:
                pass
        for context in self.created_contexts:
            try:
                if hasattr(context, 'cleanup'):
                    await context.cleanup()
            except Exception:
                pass
        for factory in self.factory_instances:
            try:
                if hasattr(factory, 'shutdown'):
                    await factory.shutdown()
            except Exception:
                pass
        gc.collect()
        await super().asyncTearDown()

    async def test_execution_engine_factory_agent_creation_coordination_failures(self):
        """FAILING TEST: Reproduce agent creation coordination failures with factory

        BVJ: All Segments - Ensures agents are created properly for chat functionality
        EXPECTED: FAIL - Factory/agent creation coordination should fail
        ISSUE: Factory and agent creation patterns have coordination conflicts
        """
        agent_creation_failures = []
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
            from netra_backend.app.agents.supervisor.agent_instance_factory import create_agent_instance_factory
        except ImportError as e:
            self.fail(f'Cannot import required classes - SSOT consolidation incomplete: {e}')
        try:
            factory = ExecutionEngineFactory(websocket_bridge=None)
            self.factory_instances.append(factory)
            test_context = UserExecutionContext(user_id='agent_creation_test_user', run_id=f'agent_creation_test_run_{int(time.time() * 1000)}', session_id='agent_creation_test_session', request_id='agent_creation_test_request')
            self.created_contexts.append(test_context)
            engine = await factory.create_for_user(test_context)
            self.created_engines.append(engine)
            if not hasattr(engine, '_agent_factory'):
                agent_creation_failures.append({'test': 'engine_agent_factory', 'failure_type': 'missing_agent_factory', 'description': 'Engine created without agent factory'})
            elif engine._agent_factory is None:
                agent_creation_failures.append({'test': 'engine_agent_factory', 'failure_type': 'null_agent_factory', 'description': 'Engine agent factory is None'})
            try:
                if hasattr(engine, '_agent_factory') and engine._agent_factory:
                    agent_types_to_test = ['supervisor_agent', 'data_helper_agent', 'triage_agent']
                    for agent_type in agent_types_to_test:
                        try:
                            agent = engine._agent_factory.get(agent_type)
                            if agent is None:
                                agent_creation_failures.append({'test': f'agent_creation_{agent_type}', 'failure_type': 'agent_creation_failed', 'agent_type': agent_type, 'description': f'Agent factory could not create {agent_type}'})
                        except Exception as e:
                            agent_creation_failures.append({'test': f'agent_creation_{agent_type}', 'failure_type': 'agent_creation_error', 'agent_type': agent_type, 'error': str(e), 'description': f'Error creating {agent_type}'})
            except Exception as e:
                agent_creation_failures.append({'test': 'agent_factory_usage', 'failure_type': 'agent_factory_error', 'error': str(e), 'description': 'Error using agent factory'})
            try:
                engine_context = engine.get_user_context()
                if engine_context.user_id != test_context.user_id:
                    agent_creation_failures.append({'test': 'agent_context_coordination', 'failure_type': 'context_mismatch', 'expected_user_id': test_context.user_id, 'actual_user_id': engine_context.user_id, 'description': 'Agent execution context does not match factory context'})
            except Exception as e:
                agent_creation_failures.append({'test': 'agent_context_coordination', 'failure_type': 'context_access_error', 'error': str(e), 'description': 'Could not access agent execution context'})
            await factory.cleanup_engine(engine)
        except Exception as e:
            agent_creation_failures.append({'test': 'factory_agent_coordination', 'failure_type': 'factory_creation_failure', 'error': str(e), 'description': 'Factory creation or basic coordination failed'})
        self.agent_workflow_failures.extend(agent_creation_failures)
        self.assertEqual(len(agent_creation_failures), 0, f'AGENT CREATION COORDINATION FAILURES: Found {len(agent_creation_failures)} agent creation coordination failures between factory and agents. Failures: {agent_creation_failures}. Agent creation coordination issues prevent proper AI functionality.')

    async def test_concurrent_agent_execution_coordination_race_conditions(self):
        """FAILING TEST: Reproduce race conditions in concurrent agent execution coordination

        BVJ: All Segments - Ensures reliable agent execution under concurrent load
        EXPECTED: FAIL - Concurrent agent execution should cause coordination failures
        ISSUE: Factory agent coordination fails under concurrent user load
        """
        execution_coordination_failures = []
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
        except ImportError as e:
            self.fail(f'Cannot import ExecutionEngineFactory - SSOT consolidation incomplete: {e}')
        factory = ExecutionEngineFactory(websocket_bridge=None)
        self.factory_instances.append(factory)
        num_concurrent_users = 5
        concurrent_execution_results = []

        async def simulate_agent_workflow_execution(user_index: int):
            """Simulate agent workflow execution for a user."""
            try:
                context = UserExecutionContext(user_id=f'concurrent_agent_user_{user_index}', run_id=f'concurrent_agent_run_{user_index}_{int(time.time() * 1000)}', session_id=f'concurrent_agent_session_{user_index}', request_id=f'concurrent_agent_request_{user_index}')
                self.created_contexts.append(context)
                start_time = time.time()
                engine = await factory.create_for_user(context)
                self.created_engines.append(engine)
                creation_time = (time.time() - start_time) * 1000
                if not hasattr(engine, '_agent_factory') or engine._agent_factory is None:
                    return {'user_index': user_index, 'success': False, 'failure_type': 'missing_agent_factory', 'creation_time': creation_time}
                workflow_stages = []
                for stage in self.expected_agent_workflow_stages:
                    try:
                        stage_start = time.time()
                        if stage == 'agent_initialization':
                            agent = engine._agent_factory.get('supervisor_agent')
                            if agent is None:
                                workflow_stages.append({'stage': stage, 'success': False, 'error': 'supervisor_agent creation failed'})
                                continue
                        elif stage == 'agent_execution':
                            await asyncio.sleep(0.1)
                        elif stage == 'agent_completion':
                            await asyncio.sleep(0.05)
                        elif stage == 'result_processing':
                            await asyncio.sleep(0.02)
                        stage_time = (time.time() - stage_start) * 1000
                        workflow_stages.append({'stage': stage, 'success': True, 'stage_time': stage_time})
                    except Exception as e:
                        workflow_stages.append({'stage': stage, 'success': False, 'error': str(e)})
                await factory.cleanup_engine(engine)
                total_time = (time.time() - start_time) * 1000
                return {'user_index': user_index, 'success': True, 'creation_time': creation_time, 'total_time': total_time, 'workflow_stages': workflow_stages}
            except Exception as e:
                return {'user_index': user_index, 'success': False, 'error': str(e), 'failure_type': 'execution_coordination_failure'}
        tasks = [simulate_agent_workflow_execution(i) for i in range(num_concurrent_users)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successful_executions = []
        failed_executions = []
        for result in results:
            if isinstance(result, dict):
                concurrent_execution_results.append(result)
                if result['success']:
                    successful_executions.append(result)
                else:
                    failed_executions.append(result)
            else:
                failed_executions.append({'user_index': 'unknown', 'success': False, 'error': str(result), 'failure_type': 'execution_exception'})
        for execution in successful_executions:
            workflow_stages = execution.get('workflow_stages', [])
            failed_stages = [stage for stage in workflow_stages if not stage.get('success', True)]
            if failed_stages:
                execution_coordination_failures.append({'user_index': execution['user_index'], 'failure_type': 'workflow_stage_failures', 'failed_stages': failed_stages, 'description': 'Agent workflow stages failed during concurrent execution'})
        if successful_executions:
            creation_times = [exec['creation_time'] for exec in successful_executions]
            total_times = [exec['total_time'] for exec in successful_executions]
            avg_creation_time = sum(creation_times) / len(creation_times)
            max_creation_time = max(creation_times)
            avg_total_time = sum(total_times) / len(total_times)
            max_total_time = max(total_times)
            if max_creation_time > avg_creation_time * 5:
                execution_coordination_failures.append({'failure_type': 'creation_timing_inconsistency', 'avg_creation_time': avg_creation_time, 'max_creation_time': max_creation_time, 'description': 'Agent creation timing varies significantly - possible race condition'})
            if max_total_time > avg_total_time * 3:
                execution_coordination_failures.append({'failure_type': 'execution_timing_inconsistency', 'avg_total_time': avg_total_time, 'max_total_time': max_total_time, 'description': 'Agent execution timing varies significantly - possible race condition'})
        self.execution_coordination_failures = execution_coordination_failures
        self.assertEqual(len(execution_coordination_failures), 0, f'EXECUTION COORDINATION FAILURES: Found {len(execution_coordination_failures)} agent execution coordination failures during concurrent operations. Failures: {execution_coordination_failures}. Execution coordination race conditions prevent reliable agent workflows.')
        failure_rate = len(failed_executions) / len(results) if results else 0
        max_acceptable_failure_rate = 0.2
        self.assertLess(failure_rate, max_acceptable_failure_rate, f'HIGH AGENT EXECUTION FAILURE RATE: {failure_rate:.1%} of concurrent agent executions failed (threshold: {max_acceptable_failure_rate:.1%}). Failed executions: {len(failed_executions)}, Total: {len(results)}. Agent execution reliability issues detected.')

    async def test_factory_agent_state_isolation_contamination(self):
        """FAILING TEST: Reproduce agent state contamination across factory instances

        BVJ: Enterprise - Ensures agent state isolation for data security
        EXPECTED: FAIL - Agent state should contaminate across factory instances
        ISSUE: Factory instances share agent state causing cross-user data leakage
        """
        agent_state_violations = []
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
        except ImportError as e:
            self.fail(f'Cannot import ExecutionEngineFactory - SSOT consolidation incomplete: {e}')
        num_factories = 3
        factory_instances = []
        agent_state_comparisons = []
        for i in range(num_factories):
            try:
                factory = ExecutionEngineFactory(websocket_bridge=None)
                factory_instances.append({'index': i, 'factory': factory})
                self.factory_instances.append(factory)
            except Exception as e:
                agent_state_violations.append({'factory_index': i, 'failure_type': 'factory_creation_failure', 'error': str(e)})
        for factory_info in factory_instances:
            try:
                context = UserExecutionContext(user_id=f"agent_state_user_{factory_info['index']}", run_id=f"agent_state_run_{factory_info['index']}_{int(time.time() * 1000)}", session_id=f"agent_state_session_{factory_info['index']}", request_id=f"agent_state_request_{factory_info['index']}")
                self.created_contexts.append(context)
                engine = await factory_info['factory'].create_for_user(context)
                self.created_engines.append(engine)
                if hasattr(engine, '_agent_factory') and engine._agent_factory:
                    agent_factory = engine._agent_factory
                    unique_state_data = {'factory_index': factory_info['index'], 'user_specific_data': f"factory_{factory_info['index']}_data_{uuid.uuid4().hex}", 'timestamp': time.time()}
                    try:
                        if hasattr(agent_factory, 'agent_class_registry'):
                            registry = agent_factory.agent_class_registry
                            if hasattr(registry, '_test_state'):
                                registry._test_state.update(unique_state_data)
                            else:
                                registry._test_state = unique_state_data.copy()
                        factory_info['agent_state'] = unique_state_data
                        factory_info['engine'] = engine
                        factory_info['agent_factory'] = agent_factory
                    except Exception as e:
                        agent_state_violations.append({'factory_index': factory_info['index'], 'failure_type': 'agent_state_setup_failure', 'error': str(e)})
                else:
                    agent_state_violations.append({'factory_index': factory_info['index'], 'failure_type': 'missing_agent_factory', 'description': 'Engine does not have agent factory'})
            except Exception as e:
                agent_state_violations.append({'factory_index': factory_info['index'], 'failure_type': 'factory_setup_failure', 'error': str(e)})
        for i, factory1 in enumerate(factory_instances):
            for j, factory2 in enumerate(factory_instances):
                if i != j and 'agent_factory' in factory1 and ('agent_factory' in factory2):
                    try:
                        if factory1['agent_factory'] is factory2['agent_factory']:
                            agent_state_violations.append({'factory1_index': i, 'factory2_index': j, 'violation_type': 'shared_agent_factory', 'description': 'Factories share the same agent factory instance'})
                        af1 = factory1['agent_factory']
                        af2 = factory2['agent_factory']
                        if hasattr(af1, 'agent_class_registry') and hasattr(af2, 'agent_class_registry'):
                            registry1 = af1.agent_class_registry
                            registry2 = af2.agent_class_registry
                            if registry1 is registry2:
                                agent_state_violations.append({'factory1_index': i, 'factory2_index': j, 'violation_type': 'shared_agent_registry', 'description': 'Factories share the same agent registry instance'})
                            if hasattr(registry1, '_test_state') and hasattr(registry2, '_test_state'):
                                state1 = registry1._test_state
                                state2 = registry2._test_state
                                if state1 is state2:
                                    agent_state_violations.append({'factory1_index': i, 'factory2_index': j, 'violation_type': 'shared_agent_state', 'description': 'Factories share the same agent state object'})
                                if isinstance(state1, dict) and isinstance(state2, dict):
                                    factory1_data = state1.get('user_specific_data', '')
                                    factory2_data = state2.get('user_specific_data', '')
                                    if factory1_data in str(state2) and factory1_data != factory2_data:
                                        agent_state_violations.append({'factory1_index': i, 'factory2_index': j, 'violation_type': 'cross_factory_data_contamination', 'contaminated_data': factory1_data, 'description': f'Factory {i} data found in Factory {j} agent state'})
                    except Exception as e:
                        agent_state_violations.append({'factory1_index': i, 'factory2_index': j, 'violation_type': 'state_comparison_failure', 'error': str(e)})
        for factory_info in factory_instances:
            if 'engine' in factory_info:
                try:
                    await factory_info['factory'].cleanup_engine(factory_info['engine'])
                except Exception:
                    pass
        self.factory_agent_mismatches = agent_state_violations
        self.assertEqual(len(agent_state_violations), 0, f'AGENT STATE CONTAMINATION DETECTED: Found {len(agent_state_violations)} instances of agent state contamination between factory instances. Violations: {agent_state_violations}. Agent state contamination violates user data isolation.')

    async def test_factory_agent_resource_management_coordination_failures(self):
        """FAILING TEST: Reproduce agent resource management coordination failures

        BVJ: Platform - Ensures proper agent resource management
        EXPECTED: FAIL - Agent resource coordination should fail with factory
        ISSUE: Factory and agent resource management are not properly coordinated
        """
        resource_coordination_failures = []
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
        except ImportError as e:
            self.fail(f'Cannot import ExecutionEngineFactory - SSOT consolidation incomplete: {e}')
        factory = ExecutionEngineFactory(websocket_bridge=None)
        self.factory_instances.append(factory)
        num_engines = 5
        created_engines = []
        resource_metrics = []
        try:
            for i in range(num_engines):
                context = UserExecutionContext(user_id=f'resource_test_user_{i}', run_id=f'resource_test_run_{i}_{int(time.time() * 1000)}', session_id=f'resource_test_session_{i}', request_id=f'resource_test_request_{i}')
                self.created_contexts.append(context)
                start_time = time.time()
                engine = await factory.create_for_user(context)
                creation_time = (time.time() - start_time) * 1000
                created_engines.append({'index': i, 'engine': engine, 'context': context, 'creation_time': creation_time})
                self.created_engines.append(engine)
                try:
                    factory_metrics = factory.get_factory_metrics()
                    resource_metrics.append({'engine_index': i, 'active_engines': factory_metrics.get('active_engines_count', 0), 'total_created': factory_metrics.get('total_engines_created', 0), 'creation_time': creation_time})
                    expected_active = i + 1
                    actual_active = factory_metrics.get('active_engines_count', 0)
                    if actual_active != expected_active:
                        resource_coordination_failures.append({'engine_index': i, 'failure_type': 'resource_tracking_mismatch', 'expected_active': expected_active, 'actual_active': actual_active, 'description': 'Factory resource tracking is inconsistent'})
                except Exception as e:
                    resource_coordination_failures.append({'engine_index': i, 'failure_type': 'resource_metrics_failure', 'error': str(e), 'description': 'Could not get factory resource metrics'})
            cleanup_failures = []
            for engine_info in created_engines:
                try:
                    cleanup_start = time.time()
                    await factory.cleanup_engine(engine_info['engine'])
                    cleanup_time = (time.time() - cleanup_start) * 1000
                    try:
                        post_cleanup_metrics = factory.get_factory_metrics()
                        cleanup_failures.append({'engine_index': engine_info['index'], 'cleanup_time': cleanup_time, 'post_cleanup_active': post_cleanup_metrics.get('active_engines_count', 0)})
                    except Exception as e:
                        resource_coordination_failures.append({'engine_index': engine_info['index'], 'failure_type': 'post_cleanup_metrics_failure', 'error': str(e)})
                except Exception as e:
                    resource_coordination_failures.append({'engine_index': engine_info['index'], 'failure_type': 'resource_cleanup_failure', 'error': str(e), 'description': 'Engine cleanup failed'})
            try:
                final_metrics = factory.get_factory_metrics()
                final_active = final_metrics.get('active_engines_count', 0)
                if final_active != 0:
                    resource_coordination_failures.append({'failure_type': 'resource_leak_detected', 'final_active_engines': final_active, 'description': 'Engines not properly cleaned up - resource leak detected'})
            except Exception as e:
                resource_coordination_failures.append({'failure_type': 'final_resource_check_failure', 'error': str(e)})
        except Exception as e:
            resource_coordination_failures.append({'failure_type': 'resource_management_test_failure', 'error': str(e), 'description': 'Resource management test setup failed'})
        self.assertEqual(len(resource_coordination_failures), 0, f'RESOURCE COORDINATION FAILURES: Found {len(resource_coordination_failures)} agent resource management coordination failures. Failures: {resource_coordination_failures}. Resource coordination issues cause memory leaks and instability.')

    def _log_test_failure_details(self, test_name: str, failure_details: Dict[str, Any]):
        """Log detailed test failure information for analysis."""
        print(f'\n=== EXECUTION ENGINE FACTORY AGENT WORKFLOW FAILURE: {test_name} ===')
        print(f'Timestamp: {datetime.now().isoformat()}')
        print(f'Business Impact: Incomplete agent responses, AI workflow failures - $500K+ ARR at risk')
        print(f'Issue: #884 Execution Engine Factory Agent Workflow Coordination Failures')
        print('\nFailure Details:')
        for key, value in failure_details.items():
            print(f'  {key}: {value}')
        print('\nAgent Workflow Impact:')
        print('- Incomplete Responses: Agents fail to complete workflows')
        print('- State Contamination: Cross-user agent state leakage')
        print('- Resource Leaks: Agent resources not properly managed')
        print('- Golden Path: End-to-end agent execution interrupted')
        print('\nNext Steps:')
        print('1. Fix factory/agent creation coordination')
        print('2. Ensure proper agent state isolation')
        print('3. Resolve agent execution race conditions')
        print('4. Implement proper agent resource management')
        print('5. Re-run tests to validate agent workflow coordination fixes')
        print('=' * 60)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')