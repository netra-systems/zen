"""
Test AgentRegistry Production Usage Pattern Conflicts (Issue #914)

This test module demonstrates critical production usage pattern conflicts where
different parts of the codebase use different AgentRegistry implementations,
causing runtime failures and unpredictable behavior in Golden Path scenarios.

Business Value: Protects $500K+ ARR by identifying production code patterns that
cause import conflicts, runtime type errors, and inconsistent agent behavior
when different registry implementations are used across the system.

Test Category: Unit (no Docker required)
Purpose: Failing tests to demonstrate production usage conflict problems
"""
import ast
import importlib
import inspect
import sys
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple, Optional
from unittest.mock import Mock, patch
import pytest
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.logging.unified_logging_ssot import get_logger
logger = get_logger(__name__)

@pytest.mark.unit
class TestAgentRegistryProductionUsagePatternConflicts(SSotAsyncTestCase):
    """
    Test production usage pattern conflicts in AgentRegistry implementations.
    
    These tests are DESIGNED TO FAIL initially to demonstrate how different
    parts of production code use incompatible registry implementations,
    causing runtime failures and blocking Golden Path functionality.
    """

    def setup_method(self, method):
        """Setup test environment for production usage analysis."""
        self.basic_registry_module = 'netra_backend.app.agents.registry'
        self.advanced_registry_module = 'netra_backend.app.agents.supervisor.agent_registry'
        self.production_paths = [Path('netra_backend/app/agents'), Path('netra_backend/app/core'), Path('netra_backend/app/services'), Path('netra_backend/app/routes'), Path('netra_backend/app/websocket_core')]
        self.registry_import_patterns = ['from netra_backend.app.agents.registry import AgentRegistry', 'from netra_backend.app.agents.registry import agent_registry', 'from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry', 'from netra_backend.app.agents.supervisor.agent_registry import get_agent_registry']
        self.registry_usage_methods = ['list_available_agents', 'set_websocket_manager', 'get_agent', 'register_agent', 'create_agent', '_notify_agent_event']

    def test_conflicting_imports_in_production_modules(self):
        """
        TEST DESIGNED TO FAIL: Demonstrate conflicting registry imports in production code.
        
        This test scans production code to find modules that import from both
        registry implementations, causing unpredictable behavior.
        """
        conflicting_modules = []
        scan_results = {}
        try:
            for production_path in self.production_paths:
                if not production_path.exists():
                    continue
                for py_file in production_path.rglob('*.py'):
                    if py_file.name.startswith('test_') or 'test' in str(py_file):
                        continue
                    try:
                        with open(py_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        registry_imports = []
                        lines = content.splitlines()
                        for line_num, line in enumerate(lines, 1):
                            line = line.strip()
                            for pattern in self.registry_import_patterns:
                                if pattern in line:
                                    registry_imports.append({'line_num': line_num, 'import_line': line, 'pattern': pattern, 'module_type': 'basic' if 'agents.registry' in pattern and 'supervisor' not in pattern else 'advanced'})
                        if registry_imports:
                            scan_results[str(py_file)] = registry_imports
                            basic_imports = [imp for imp in registry_imports if imp['module_type'] == 'basic']
                            advanced_imports = [imp for imp in registry_imports if imp['module_type'] == 'advanced']
                            if basic_imports and advanced_imports:
                                conflicting_modules.append({'file': str(py_file), 'basic_imports': basic_imports, 'advanced_imports': advanced_imports, 'total_imports': len(registry_imports)})
                    except Exception as e:
                        logger.warning(f'Could not scan {py_file}: {e}')
            logger.error(f'Production registry import analysis:')
            logger.error(f"  Files scanned: {sum((len(list(path.rglob('*.py'))) for path in self.production_paths if path.exists()))}")
            logger.error(f'  Files with registry imports: {len(scan_results)}')
            logger.error(f'  Conflicting modules: {len(conflicting_modules)}')
            for file_path, imports in scan_results.items():
                logger.error(f'  {file_path}: {len(imports)} registry imports')
                for imp in imports:
                    logger.error(f"    Line {imp['line_num']}: {imp['import_line']} ({imp['module_type']})")
            if conflicting_modules:
                conflict_details = []
                for conflict in conflicting_modules:
                    basic_count = len(conflict['basic_imports'])
                    advanced_count = len(conflict['advanced_imports'])
                    detail = f"{conflict['file']}: {basic_count} basic + {advanced_count} advanced imports"
                    conflict_details.append(detail)
                self.fail(f"CRITICAL PRODUCTION IMPORT CONFLICTS: {len(conflicting_modules)} production modules import from both AgentRegistry implementations. This causes unpredictable runtime behavior where the same code path might use different registry classes depending on import order, leading to AttributeError exceptions and Golden Path failures that are hard to reproduce. $500K+ ARR chat functionality is at risk from these import conflicts. Conflicting modules: {'; '.join(conflict_details)}")
        except Exception as e:
            self.fail(f'Unexpected error during production import analysis: {e}')
        logger.info('No production import conflicts detected - SSOT compliance maintained')

    def test_runtime_method_call_failures_in_production(self):
        """
        TEST DESIGNED TO FAIL: Demonstrate runtime method call failures in production code.
        
        This test analyzes production code that calls registry methods and simulates
        failures when the wrong registry implementation is used.
        """
        import importlib
        method_call_failures = []
        production_usage_analysis = {}
        try:
            basic_module = importlib.import_module(self.basic_registry_module)
            advanced_module = importlib.import_module(self.advanced_registry_module)
            basic_registry_class = getattr(basic_module, 'AgentRegistry')
            advanced_registry_class = getattr(advanced_module, 'AgentRegistry')
            basic_instance = basic_registry_class()
            advanced_instance = advanced_registry_class()
            method_call_usage = {}
            for production_path in self.production_paths:
                if not production_path.exists():
                    continue
                for py_file in production_path.rglob('*.py'):
                    if py_file.name.startswith('test_') or 'test' in str(py_file):
                        continue
                    try:
                        with open(py_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        method_calls = []
                        lines = content.splitlines()
                        for line_num, line in enumerate(lines, 1):
                            line = line.strip()
                            for method_name in self.registry_usage_methods:
                                if f'.{method_name}(' in line or f'registry.{method_name}(' in line:
                                    method_calls.append({'line_num': line_num, 'method_name': method_name, 'code_line': line, 'file': str(py_file)})
                        if method_calls:
                            method_call_usage[str(py_file)] = method_calls
                    except Exception as e:
                        logger.warning(f'Could not scan {py_file} for method calls: {e}')
            for file_path, method_calls in method_call_usage.items():
                for call in method_calls:
                    method_name = call['method_name']
                    basic_has_method = hasattr(basic_instance, method_name)
                    advanced_has_method = hasattr(advanced_instance, method_name)
                    signature_compatible = True
                    signature_difference = None
                    if basic_has_method and advanced_has_method:
                        try:
                            basic_method = getattr(basic_instance, method_name)
                            advanced_method = getattr(advanced_instance, method_name)
                            basic_sig = inspect.signature(basic_method)
                            advanced_sig = inspect.signature(advanced_method)
                            if str(basic_sig) != str(advanced_sig):
                                signature_compatible = False
                                signature_difference = f'basic: {basic_sig}, advanced: {advanced_sig}'
                        except Exception as e:
                            signature_compatible = False
                            signature_difference = f'signature analysis failed: {e}'
                    if not basic_has_method or not advanced_has_method:
                        method_call_failures.append({'file': file_path, 'line': call['line_num'], 'method': method_name, 'code': call['code_line'], 'failure_type': 'method_missing', 'basic_has': basic_has_method, 'advanced_has': advanced_has_method})
                    elif not signature_compatible:
                        method_call_failures.append({'file': file_path, 'line': call['line_num'], 'method': method_name, 'code': call['code_line'], 'failure_type': 'signature_incompatible', 'signature_difference': signature_difference})
            production_usage_analysis = {'files_with_method_calls': len(method_call_usage), 'total_method_calls': sum((len(calls) for calls in method_call_usage.values())), 'method_failures': len(method_call_failures), 'unique_methods_called': set((call['method'] for failures in method_call_usage.values() for call in failures))}
            logger.error(f'Production method call analysis:')
            logger.error(f"  Files with method calls: {production_usage_analysis['files_with_method_calls']}")
            logger.error(f"  Total method calls: {production_usage_analysis['total_method_calls']}")
            logger.error(f"  Method failures: {production_usage_analysis['method_failures']}")
            logger.error(f"  Methods called: {production_usage_analysis['unique_methods_called']}")
            for failure in method_call_failures:
                if failure['failure_type'] == 'method_missing':
                    logger.error(f"  MISSING METHOD: {failure['file']}:{failure['line']} - {failure['method']} (basic:{failure['basic_has']}, advanced:{failure['advanced_has']})")
                elif failure['failure_type'] == 'signature_incompatible':
                    logger.error(f"  SIGNATURE MISMATCH: {failure['file']}:{failure['line']} - {failure['method']} ({failure['signature_difference']})")
            if method_call_failures:
                failure_summary = []
                missing_method_failures = [f for f in method_call_failures if f['failure_type'] == 'method_missing']
                signature_failures = [f for f in method_call_failures if f['failure_type'] == 'signature_incompatible']
                if missing_method_failures:
                    failure_summary.append(f'{len(missing_method_failures)} missing method calls')
                if signature_failures:
                    failure_summary.append(f'{len(signature_failures)} signature incompatibilities')
                self.fail(f"CRITICAL PRODUCTION METHOD CALL FAILURES: {len(method_call_failures)} method call issues detected in production code. When the wrong registry implementation is imported, these calls will fail with AttributeError or TypeError exceptions, causing unpredictable Golden Path failures that depend on import order and timing. This makes $500K+ ARR chat functionality unreliable and hard to debug. Method call issues: {'; '.join(failure_summary)}")
        except Exception as e:
            self.fail(f'Unexpected error during method call analysis: {e}')
        logger.info('All production method calls compatible across registries - SSOT compliance achieved')

    def test_factory_instantiation_pattern_inconsistencies(self):
        """
        TEST DESIGNED TO FAIL: Demonstrate factory instantiation pattern inconsistencies.
        
        This test shows how production code uses different patterns to create registry
        instances, some of which fail with different registry implementations.
        """
        import importlib
        instantiation_failures = []
        try:
            basic_module = importlib.import_module(self.basic_registry_module)
            advanced_module = importlib.import_module(self.advanced_registry_module)
            basic_registry_class = getattr(basic_module, 'AgentRegistry')
            advanced_registry_class = getattr(advanced_module, 'AgentRegistry')
            instantiation_patterns = [{'name': 'direct_instantiation', 'pattern': lambda cls: cls(), 'description': 'registry = AgentRegistry()'}, {'name': 'with_websocket_manager', 'pattern': lambda cls: cls() if not hasattr(cls, '__init__') or len(inspect.signature(cls.__init__).parameters) <= 1 else None, 'description': 'registry = AgentRegistry(websocket_manager=manager)'}, {'name': 'global_instance_access', 'pattern': lambda cls: getattr(cls.__module__, 'agent_registry', None) if hasattr(importlib.import_module(cls.__module__), 'agent_registry') else None, 'description': 'from module import agent_registry'}, {'name': 'factory_function', 'pattern': lambda cls: getattr(importlib.import_module(cls.__module__), 'get_agent_registry', lambda: None)() if hasattr(importlib.import_module(cls.__module__), 'get_agent_registry') else None, 'description': 'registry = get_agent_registry()'}]
            for pattern_info in instantiation_patterns:
                pattern_name = pattern_info['name']
                pattern_func = pattern_info['pattern']
                basic_result = None
                advanced_result = None
                basic_error = None
                advanced_error = None
                try:
                    if pattern_name == 'global_instance_access':
                        basic_result = pattern_func(basic_registry_class)
                    elif pattern_name == 'factory_function':
                        basic_result = pattern_func(basic_registry_class)
                    else:
                        basic_result = pattern_func(basic_registry_class)
                except Exception as e:
                    basic_error = str(e)
                try:
                    if pattern_name == 'global_instance_access':
                        advanced_result = pattern_func(advanced_registry_class)
                    elif pattern_name == 'factory_function':
                        advanced_result = pattern_func(advanced_registry_class)
                    else:
                        advanced_result = pattern_func(advanced_registry_class)
                except Exception as e:
                    advanced_error = str(e)
                basic_success = basic_result is not None and basic_error is None
                advanced_success = advanced_result is not None and advanced_error is None
                logger.error(f"Instantiation pattern '{pattern_name}':")
                logger.error(f"  Description: {pattern_info['description']}")
                logger.error(f'  Basic registry success: {basic_success}')
                if basic_error:
                    logger.error(f'  Basic registry error: {basic_error}')
                logger.error(f'  Advanced registry success: {advanced_success}')
                if advanced_error:
                    logger.error(f'  Advanced registry error: {advanced_error}')
                if basic_success != advanced_success:
                    instantiation_failures.append({'pattern': pattern_name, 'description': pattern_info['description'], 'basic_success': basic_success, 'advanced_success': advanced_success, 'basic_error': basic_error, 'advanced_error': advanced_error})
                elif basic_success and advanced_success:
                    if basic_result and advanced_result:
                        basic_methods = set((method for method in dir(basic_result) if not method.startswith('_') and callable(getattr(basic_result, method))))
                        advanced_methods = set((method for method in dir(advanced_result) if not method.startswith('_') and callable(getattr(advanced_result, method))))
                        method_differences = basic_methods.symmetric_difference(advanced_methods)
                        if method_differences:
                            instantiation_failures.append({'pattern': pattern_name, 'description': pattern_info['description'], 'basic_success': True, 'advanced_success': True, 'failure_type': 'interface_mismatch', 'method_differences': list(method_differences)})
            if instantiation_failures:
                failure_details = []
                for failure in instantiation_failures:
                    if failure.get('failure_type') == 'interface_mismatch':
                        detail = f"{failure['pattern']}: interface differs by {len(failure['method_differences'])} methods"
                    else:
                        basic_status = 'works' if failure['basic_success'] else 'fails'
                        advanced_status = 'works' if failure['advanced_success'] else 'fails'
                        detail = f"{failure['pattern']}: basic {basic_status}, advanced {advanced_status}"
                    failure_details.append(detail)
                self.fail(f"CRITICAL INSTANTIATION PATTERN INCONSISTENCY: {len(instantiation_failures)} instantiation patterns work inconsistently between registry implementations. Production code that works with one registry will fail with the other, causing unpredictable Golden Path failures that depend on which registry gets imported. This makes $500K+ ARR chat functionality unreliable and creates hard-to-debug runtime errors. Pattern inconsistencies: {'; '.join(failure_details)}")
        except Exception as e:
            self.fail(f'Unexpected error during instantiation pattern testing: {e}')
        logger.info('All instantiation patterns work consistently - SSOT compliance achieved')

    def test_websocket_integration_code_path_analysis(self):
        """
        TEST DESIGNED TO FAIL: Analyze WebSocket integration code paths for conflicts.
        
        This test examines how production code integrates registries with WebSocket
        systems and identifies patterns that fail with different implementations.
        """
        websocket_integration_failures = []
        try:
            websocket_integration_files = []
            for production_path in self.production_paths:
                if not production_path.exists():
                    continue
                for py_file in production_path.rglob('*.py'):
                    if py_file.name.startswith('test_') or 'test' in str(py_file):
                        continue
                    try:
                        with open(py_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        websocket_keywords = ['websocket', 'WebSocket', 'set_websocket_manager', 'websocket_bridge']
                        registry_keywords = ['AgentRegistry', 'agent_registry', 'registry']
                        has_websocket = any((keyword in content for keyword in websocket_keywords))
                        has_registry = any((keyword in content for keyword in registry_keywords))
                        if has_websocket and has_registry:
                            websocket_integration_files.append({'file': str(py_file), 'content_length': len(content), 'has_async_methods': 'async def' in content})
                    except Exception as e:
                        logger.warning(f'Could not scan {py_file} for WebSocket integration: {e}')
            logger.error(f'WebSocket integration analysis:')
            logger.error(f'  Files with WebSocket+registry integration: {len(websocket_integration_files)}')
            import importlib
            basic_module = importlib.import_module(self.basic_registry_module)
            advanced_module = importlib.import_module(self.advanced_registry_module)
            basic_registry_class = getattr(basic_module, 'AgentRegistry')
            advanced_registry_class = getattr(advanced_module, 'AgentRegistry')
            integration_patterns = [{'name': 'sync_websocket_setup', 'description': 'registry.set_websocket_manager(manager)', 'test_func': lambda registry, manager: registry.set_websocket_manager(manager) if hasattr(registry, 'set_websocket_manager') else None, 'is_async': False}, {'name': 'async_websocket_setup', 'description': 'await registry.set_websocket_manager(manager, user_context)', 'test_func': lambda registry, manager: asyncio.get_event_loop().run_until_complete(registry.set_websocket_manager(manager, Mock())) if hasattr(registry, 'set_websocket_manager') and asyncio.iscoroutinefunction(registry.set_websocket_manager) else None, 'is_async': True}, {'name': 'event_notification', 'description': 'registry._notify_agent_event(event)', 'test_func': lambda registry, event: registry._notify_agent_event(event) if hasattr(registry, '_notify_agent_event') else None, 'is_async': False}]
            for pattern in integration_patterns:
                pattern_name = pattern['name']
                basic_registry = basic_registry_class()
                advanced_registry = advanced_registry_class()
                mock_manager = Mock()
                mock_event = {'type': 'test_event'}
                basic_success = False
                advanced_success = False
                basic_error = None
                advanced_error = None
                try:
                    if pattern_name in ['sync_websocket_setup', 'async_websocket_setup']:
                        result = pattern['test_func'](basic_registry, mock_manager)
                        basic_success = True
                    else:
                        result = pattern['test_func'](basic_registry, mock_event)
                        basic_success = True
                except Exception as e:
                    basic_error = str(e)
                try:
                    if pattern_name in ['sync_websocket_setup', 'async_websocket_setup']:
                        result = pattern['test_func'](advanced_registry, mock_manager)
                        advanced_success = True
                    else:
                        result = pattern['test_func'](advanced_registry, mock_event)
                        advanced_success = True
                except Exception as e:
                    advanced_error = str(e)
                logger.error(f"WebSocket integration pattern '{pattern_name}':")
                logger.error(f"  Description: {pattern['description']}")
                logger.error(f'  Basic registry success: {basic_success}')
                if basic_error:
                    logger.error(f'  Basic registry error: {basic_error}')
                logger.error(f'  Advanced registry success: {advanced_success}')
                if advanced_error:
                    logger.error(f'  Advanced registry error: {advanced_error}')
                if basic_success != advanced_success:
                    websocket_integration_failures.append({'pattern': pattern_name, 'description': pattern['description'], 'basic_success': basic_success, 'advanced_success': advanced_success, 'basic_error': basic_error, 'advanced_error': advanced_error, 'is_async': pattern['is_async']})
            if websocket_integration_failures:
                failure_summary = []
                for failure in websocket_integration_failures:
                    basic_status = 'works' if failure['basic_success'] else 'fails'
                    advanced_status = 'works' if failure['advanced_success'] else 'fails'
                    async_marker = ' (async)' if failure['is_async'] else ''
                    summary = f"{failure['pattern']}{async_marker}: basic {basic_status}, advanced {advanced_status}"
                    failure_summary.append(summary)
                self.fail(f"CRITICAL WEBSOCKET INTEGRATION PATTERN FAILURE: {len(websocket_integration_failures)} WebSocket integration patterns work inconsistently between registry implementations. Production code that successfully integrates WebSocket events with one registry will fail with the other, causing the 5 critical agent events (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed) to be lost. This blocks $500K+ ARR Golden Path chat functionality by preventing real-time user feedback. Integration failures: {'; '.join(failure_summary)}")
        except Exception as e:
            self.fail(f'Unexpected error during WebSocket integration analysis: {e}')
        logger.info('All WebSocket integration patterns work consistently - Golden Path functionality enabled')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')