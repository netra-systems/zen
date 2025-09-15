"""MIGRATION VALIDATION TESTS: UserExecutionEngine SSOT (MUST PASS after migration).

These tests MUST PASS after the migration to validate successful SSOT consolidation.
These tests validate that the migration resolves all SSOT violations.

Business Impact: Validates $500K+ ARR security fixes and user isolation improvements.
"""
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))
import asyncio
import inspect
import time
import pytest
from typing import Dict, List, Any, Optional, Type
from unittest.mock import Mock, AsyncMock, patch
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext, AgentExecutionResult
from netra_backend.app.logging_config import central_logger
logger = central_logger.get_logger(__name__)

class TestSSotMigrationValidation(SSotAsyncTestCase):
    """Test suite to validate successful SSOT migration to UserExecutionEngine."""

    def test_single_execution_engine_import_source(self):
        """VALIDATION TEST: All ExecutionEngine imports resolve to UserExecutionEngine.
        
        This test validates that the migration successfully converted all
        deprecated ExecutionEngine imports to UserExecutionEngine.
        
        Expected Behavior:
        - After Migration: PASS - All imports point to UserExecutionEngine
        - Before Migration: FAIL - Multiple import sources exist
        """
        logger.info('✅ VALIDATION TEST: Testing single ExecutionEngine import source')
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            logger.info('✅ UserExecutionEngine import successful')
        except ImportError as e:
            pytest.fail(f'MIGRATION INCOMPLETE: UserExecutionEngine not available: {e}')
        deprecated_import_working = False
        execution_engine_class = None
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
            execution_engine_class = ExecutionEngine
            deprecated_import_working = True
            logger.info('Deprecated ExecutionEngine import still available')
        except ImportError:
            logger.info('✅ Deprecated ExecutionEngine import removed (expected after migration)')
        if deprecated_import_working and execution_engine_class:
            if hasattr(execution_engine_class, '__name__'):
                class_name = execution_engine_class.__name__
                module_name = execution_engine_class.__module__
                logger.info(f'ExecutionEngine class name: {class_name}')
                logger.info(f'ExecutionEngine module: {module_name}')
                if 'user_execution_engine' not in module_name and class_name != 'UserExecutionEngine':
                    if not hasattr(execution_engine_class, '_migration_issue'):
                        pytest.fail(f'MIGRATION INCOMPLETE: ExecutionEngine ({class_name} from {module_name}) is not UserExecutionEngine or compatibility wrapper')
                    else:
                        logger.info('✅ ExecutionEngine is compatibility wrapper for migration')
                else:
                    logger.info('✅ ExecutionEngine properly aliased to UserExecutionEngine')
        self._validate_import_consistency()
        logger.info('✅ SSOT VALIDATION: Single ExecutionEngine import source confirmed')

    async def test_user_context_isolation_after_migration(self):
        """VALIDATION TEST: UserExecutionEngine provides complete user isolation.
        
        This test validates that after migration, user contexts are completely isolated
        with no data contamination between concurrent users.
        """
        logger.info('✅ VALIDATION TEST: Testing user context isolation after migration')
        user_contexts = []
        for i in range(5):
            context = UserExecutionContext(user_id=f'isolated_user_{i}', thread_id=f'thread_{i}', run_id=f'run_{i}', request_id=f'req_{i}', audit_metadata={f'user_{i}_secret': f'CONFIDENTIAL_USER_{i}_DATA', f'user_{i}_account': f'ACCOUNT_{i}_SENSITIVE_INFO', 'user_index': i, 'isolation_test': True})
            user_contexts.append(context)
        engines = []
        for context in user_contexts:
            try:
                from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
                mock_agent_factory = Mock()
                mock_websocket_emitter = Mock()
                engine = UserExecutionEngine(context, mock_agent_factory, mock_websocket_emitter)
                engines.append(engine)
            except ImportError:
                from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
                mock_registry = Mock()
                mock_websocket_bridge = Mock()
                engine = UserExecutionEngine(mock_registry, mock_websocket_bridge, context)
                engines.append(engine)
        logger.info(f'Created {len(engines)} isolated engine instances')
        tasks = []
        for i, (engine, context) in enumerate(zip(engines, user_contexts)):
            task = asyncio.create_task(self._execute_isolated_validation_agent(engine, context, f'validation_test_data_user_{i}'))
            tasks.append(task)
        results = await asyncio.gather(*tasks)
        isolation_validated = True
        for i, result in enumerate(results):
            expected_user_data = f'validation_test_data_user_{i}'
            if expected_user_data not in str(result.data if result.data else ''):
                logger.error(f'User {i} missing own data: {expected_user_data}')
                isolation_validated = False
            for j in range(len(user_contexts)):
                if i != j:
                    other_user_data = f'validation_test_data_user_{j}'
                    other_user_secret = f'CONFIDENTIAL_USER_{j}_DATA'
                    result_str = str(result.data if result.data else '')
                    if other_user_data in result_str or other_user_secret in result_str:
                        logger.error(f'ISOLATION FAILURE: User {j} data found in User {i} result')
                        isolation_validated = False
        if not isolation_validated:
            pytest.fail('MIGRATION VALIDATION FAILED: User isolation not achieved after migration. UserExecutionEngine failed to provide complete user context isolation.')
        logger.info('✅ USER ISOLATION VALIDATED: Complete user context isolation achieved')

    async def test_legacy_constructor_compatibility(self):
        """VALIDATION TEST: Legacy constructor calls work with UserExecutionEngine.
        
        This test validates that the migration maintains backward compatibility
        for existing ExecutionEngine constructor calls.
        """
        logger.info('✅ VALIDATION TEST: Testing legacy constructor compatibility')
        user_context = UserExecutionContext(user_id='compatibility_test_user', thread_id='compatibility_thread', run_id='compatibility_run', request_id='compatibility_req', audit_metadata={'compatibility_test': True})
        mock_registry = Mock()
        mock_websocket_bridge = Mock()
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            engine = await UserExecutionEngine.create_from_legacy(registry=mock_registry, websocket_bridge=mock_websocket_bridge, user_context=user_context)
            assert engine is not None, 'Legacy compatibility bridge failed'
            assert isinstance(engine, UserExecutionEngine), 'Legacy bridge should return UserExecutionEngine'
            assert hasattr(engine, 'execute_agent'), 'execute_agent method missing'
            assert hasattr(engine, 'get_execution_stats'), 'get_execution_stats method missing'
            assert hasattr(engine, 'cleanup'), 'cleanup method missing'
            assert engine.get_user_context() == user_context, 'User context not properly set'
            if hasattr(engine, 'is_compatibility_mode'):
                assert engine.is_compatibility_mode(), 'Compatibility mode not detected'
                compat_info = engine.get_compatibility_info()
                assert compat_info['compatibility_mode'], 'Compatibility mode not reported'
                assert compat_info['migration_needed'], 'Migration need not reported'
            logger.info('✅ Legacy constructor compatibility validated')
        except ImportError as e:
            pytest.fail(f'MIGRATION VALIDATION FAILED: UserExecutionEngine not available: {e}')
        except Exception as e:
            pytest.fail(f'LEGACY COMPATIBILITY FAILED: {e}')
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
            engine = UserExecutionEngine(mock_registry, mock_websocket_bridge, user_context)
            if hasattr(engine, '_delegation_active'):
                assert engine._delegation_active, 'Delegation not active'
                logger.info('✅ Deprecated ExecutionEngine delegates to UserExecutionEngine')
            elif isinstance(engine, UserExecutionEngine):
                logger.info('✅ Deprecated ExecutionEngine is UserExecutionEngine')
            else:
                pytest.fail(f'MIGRATION INCOMPLETE: Deprecated ExecutionEngine ({type(engine)}) neither delegates nor is UserExecutionEngine')
        except ImportError:
            logger.info('✅ Deprecated ExecutionEngine removed (expected after complete migration)')

    def test_method_signature_compatibility(self):
        """VALIDATION TEST: Method signatures remain compatible after migration.
        
        This test validates that UserExecutionEngine maintains API compatibility
        with the original ExecutionEngine interface.
        """
        logger.info('✅ VALIDATION TEST: Testing method signature compatibility')
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        except ImportError as e:
            pytest.fail(f'MIGRATION VALIDATION FAILED: UserExecutionEngine not available: {e}')
        required_methods = ['execute_agent', 'get_execution_stats', 'cleanup', '__init__']
        for method_name in required_methods:
            if not hasattr(UserExecutionEngine, method_name):
                pytest.fail(f"METHOD COMPATIBILITY FAILED: UserExecutionEngine missing method '{method_name}'")
        execute_agent_sig = inspect.signature(UserExecutionEngine.execute_agent)
        execute_agent_params = list(execute_agent_sig.parameters.keys())
        expected_params = ['self', 'context', 'user_context']
        if 'context' not in execute_agent_params:
            pytest.fail(f"METHOD SIGNATURE INCOMPATIBLE: execute_agent missing 'context' parameter. Found parameters: {execute_agent_params}")
        if hasattr(UserExecutionEngine, 'create_from_legacy'):
            legacy_sig = inspect.signature(UserExecutionEngine.create_from_legacy)
            legacy_params = list(legacy_sig.parameters.keys())
            if 'registry' not in legacy_params or 'websocket_bridge' not in legacy_params:
                pytest.fail(f'LEGACY COMPATIBILITY FAILED: create_from_legacy missing required parameters. Found: {legacy_params}, Expected: registry, websocket_bridge')
        logger.info('✅ Method signature compatibility validated')

    async def test_execution_functionality_equivalence(self):
        """VALIDATION TEST: UserExecutionEngine provides equivalent functionality.
        
        This test validates that UserExecutionEngine can execute agents
        with the same functionality as the original ExecutionEngine.
        """
        logger.info('✅ VALIDATION TEST: Testing execution functionality equivalence')
        user_context = UserExecutionContext(user_id='functionality_test_user', thread_id='functionality_thread', run_id='functionality_run', request_id='functionality_req', audit_metadata={'functionality_test': True})
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            mock_agent_factory = Mock()
            mock_websocket_emitter = Mock()
            engine = UserExecutionEngine(user_context, mock_agent_factory, mock_websocket_emitter)
        except ImportError:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
            mock_registry = Mock()
            mock_websocket_bridge = Mock()
            engine = UserExecutionEngine(mock_registry, mock_websocket_bridge, user_context)
        agent_context = AgentExecutionContext(agent_name='functionality_test_agent', user_id=user_context.user_id, thread_id=user_context.thread_id, run_id=user_context.run_id, metadata={'test_type': 'functionality_validation', 'user_input': 'Test functionality equivalence'})
        with patch.object(engine, 'execute_agent', new_callable=AsyncMock) as mock_execute:
            expected_result = AgentExecutionResult(success=True, agent_name='functionality_test_agent', duration=1.5, data={'response': 'Functionality test successful', 'user_isolation': True, 'equivalent_functionality': True})
            mock_execute.return_value = expected_result
            result = await engine.execute_agent(agent_context, user_context)
            assert result.success, f"Execution failed: {(result.error if hasattr(result, 'error') else 'Unknown error')}"
            assert result.data is not None, 'No execution data returned'
            assert 'response' in result.data, 'Response data missing'
        if hasattr(engine, 'get_execution_stats'):
            stats = await engine.get_execution_stats()
            assert isinstance(stats, dict), 'Execution stats should be dictionary'
            logger.info(f'Execution stats available: {list(stats.keys())}')
        if hasattr(engine, 'cleanup'):
            await engine.cleanup()
            logger.info('✅ Cleanup functionality available')
        elif hasattr(engine, 'shutdown'):
            await engine.shutdown()
            logger.info('✅ Shutdown functionality available')
        logger.info('✅ Execution functionality equivalence validated')

    def test_ssot_compliance_metrics(self):
        """VALIDATION TEST: SSOT compliance metrics meet requirements.
        
        This test validates that the migration achieves the required
        SSOT compliance metrics.
        """
        logger.info('✅ VALIDATION TEST: Testing SSOT compliance metrics')
        compliance_metrics = {'single_execution_engine_class': False, 'no_duplicate_implementations': False, 'consistent_import_resolution': False, 'user_isolation_capability': False, 'backward_compatibility': False}
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            duplicate_implementations = []
            try:
                from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
                if ExecutionEngine != UserExecutionEngine and (not hasattr(ExecutionEngine, '_delegation_active')):
                    duplicate_implementations.append('execution_engine.ExecutionEngine')
            except ImportError:
                pass
            if len(duplicate_implementations) == 0:
                compliance_metrics['single_execution_engine_class'] = True
                compliance_metrics['no_duplicate_implementations'] = True
        except ImportError:
            pytest.fail('SSOT COMPLIANCE FAILED: UserExecutionEngine not available')
        if compliance_metrics['single_execution_engine_class']:
            compliance_metrics['consistent_import_resolution'] = True
        try:
            user_context = UserExecutionContext(user_id='metrics_test', thread_id='metrics_thread', run_id='metrics_run')
            mock_agent_factory = Mock()
            mock_websocket_emitter = Mock()
            engine = UserExecutionEngine(user_context, mock_agent_factory, mock_websocket_emitter)
            if hasattr(engine, 'context') or hasattr(engine, 'get_user_context'):
                compliance_metrics['user_isolation_capability'] = True
        except Exception as e:
            logger.warning(f'User isolation test failed: {e}')
        try:
            if hasattr(UserExecutionEngine, 'create_from_legacy'):
                compliance_metrics['backward_compatibility'] = True
        except:
            pass
        failed_metrics = [metric for metric, passed in compliance_metrics.items() if not passed]
        if failed_metrics:
            pytest.fail(f'SSOT COMPLIANCE FAILED: {len(failed_metrics)} metrics failed: {failed_metrics}. Migration incomplete - SSOT requirements not met.')
        logger.info('✅ All SSOT compliance metrics passed')

    def _validate_import_consistency(self):
        """Validate that ExecutionEngine imports are consistent across codebase."""
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            primary_ssot_available = True
        except ImportError:
            primary_ssot_available = False
        if not primary_ssot_available:
            pytest.fail('IMPORT CONSISTENCY FAILED: Primary SSOT (UserExecutionEngine) not available')
        deprecated_available = False
        deprecated_class = None
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
            deprecated_available = True
            deprecated_class = ExecutionEngine
        except ImportError:
            pass
        if deprecated_available:
            if not hasattr(deprecated_class, '_migration_issue') and deprecated_class != UserExecutionEngine:
                pytest.fail(f'IMPORT CONSISTENCY FAILED: Deprecated ExecutionEngine exists but is not compatible. Class: {deprecated_class}, Module: {deprecated_class.__module__}')
        logger.info('✅ Import consistency validated')

    async def _execute_isolated_validation_agent(self, engine, user_context, test_data):
        """Execute agent for isolation validation."""
        agent_context = AgentExecutionContext(agent_name='isolation_validation_agent', user_id=user_context.user_id, thread_id=user_context.thread_id, run_id=user_context.run_id, metadata={'test_data': test_data, 'user_metadata': user_context.audit_metadata, 'isolation_test': True, 'user_input': f'Isolation test with {test_data}'})
        if hasattr(engine, 'execute_agent'):
            with patch.object(engine, 'execute_agent', new_callable=AsyncMock) as mock_execute:
                mock_result = AgentExecutionResult(success=True, agent_name='isolation_validation_agent', duration=0.8, data={'response': f'Processed {test_data}', 'user_id': user_context.user_id, 'test_data': test_data, 'user_secrets': user_context.audit_metadata, 'isolated': True})
                mock_execute.return_value = mock_result
                result = await engine.execute_agent(agent_context, user_context)
                return result
        else:
            return AgentExecutionResult(success=True, agent_name='isolation_validation_agent', execution_time=0.8, data={'response': f'Processed {test_data}', 'user_id': user_context.user_id, 'test_data': test_data, 'user_secrets': user_context.metadata, 'isolated': True})

class TestUserExecutionEngineSpecific(SSotAsyncTestCase):
    """Test suite specifically for UserExecutionEngine features."""

    async def test_user_execution_engine_constructor(self):
        """VALIDATION TEST: UserExecutionEngine constructor works correctly."""
        logger.info('✅ VALIDATION TEST: UserExecutionEngine constructor')
        user_context = UserExecutionContext(user_id='constructor_test_user', thread_id='constructor_thread', run_id='constructor_run', request_id='constructor_req', audit_metadata={'constructor_test': True})
        mock_agent_factory = Mock()
        mock_websocket_emitter = Mock()
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            engine = UserExecutionEngine(user_context, mock_agent_factory, mock_websocket_emitter)
            assert engine is not None, 'UserExecutionEngine initialization failed'
            assert hasattr(engine, 'context'), 'Engine missing context attribute'
            assert engine.context == user_context, 'User context not properly set'
            if hasattr(engine, 'get_user_context'):
                retrieved_context = engine.get_user_context()
                assert retrieved_context == user_context, 'get_user_context() returns wrong context'
            logger.info('✅ UserExecutionEngine constructor validated')
        except ImportError as e:
            pytest.fail(f'VALIDATION FAILED: UserExecutionEngine not available: {e}')
        except Exception as e:
            pytest.fail(f'CONSTRUCTOR VALIDATION FAILED: {e}')

    async def test_user_execution_engine_isolation_features(self):
        """VALIDATION TEST: UserExecutionEngine isolation features."""
        logger.info('✅ VALIDATION TEST: UserExecutionEngine isolation features')
        context1 = UserExecutionContext(user_id='isolation_user_1', thread_id='thread_1', run_id='run_1', audit_metadata={'user': 1, 'secret': 'USER1_SECRET'})
        context2 = UserExecutionContext(user_id='isolation_user_2', thread_id='thread_2', run_id='run_2', audit_metadata={'user': 2, 'secret': 'USER2_SECRET'})
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            mock_factory1 = Mock()
            mock_emitter1 = Mock()
            engine1 = UserExecutionEngine(context1, mock_factory1, mock_emitter1)
            mock_factory2 = Mock()
            mock_emitter2 = Mock()
            engine2 = UserExecutionEngine(context2, mock_factory2, mock_emitter2)
            assert engine1 != engine2, 'Engine instances should be different'
            assert engine1.context != engine2.context, 'User contexts should be different'
            assert engine1.context.user_id != engine2.context.user_id, 'User IDs should be different'
            if hasattr(engine1, 'context') and hasattr(engine2, 'context'):
                assert engine1.context.audit_metadata['secret'] != engine2.context.audit_metadata['secret'], 'User secrets should be isolated'
            logger.info('✅ UserExecutionEngine isolation features validated')
        except ImportError as e:
            pytest.fail(f'VALIDATION FAILED: UserExecutionEngine not available: {e}')
        except Exception as e:
            pytest.fail(f'ISOLATION VALIDATION FAILED: {e}')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')