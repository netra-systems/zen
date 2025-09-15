"""
Test 3: SSOT Import Validation for Agent Factory

PURPOSE: Validate imports in agent factory modules follow SSOT patterns.
ISSUE: #709 - Agent Factory Singleton Legacy remediation
SCOPE: SSOT import pattern validation and circular dependency prevention

EXPECTED BEHAVIOR:
- BEFORE REMEDIATION: Tests should FAIL (proving incorrect import patterns exist)
- AFTER REMEDIATION: Tests should PASS (proving SSOT import compliance)

Business Value: Platform/Internal - $500K+ ARR protection through proper module architecture
"""
import ast
import importlib
import inspect
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from unittest.mock import patch
import pytest
from test_framework.ssot.base_test_case import SSotAsyncTestCase

@pytest.mark.unit
class SSOTImportValidationAgentFactoryTests(SSotAsyncTestCase):
    """
    Test suite validating SSOT import patterns in agent factory modules.

    This test suite specifically targets Issue #709 by validating that:
    1. All imports in agent factory modules follow SSOT registry patterns
    2. No circular dependencies are introduced by remediation
    3. Import paths are valid and verified
    4. SSOT import consolidation is properly implemented

    CRITICAL: These tests should FAIL before remediation and PASS after.
    """

    def setup_method(self, method):
        """Setup for each test method."""
        super().setup_method(method)
        self._target_modules = ['netra_backend.app.agents.supervisor.agent_instance_factory', 'netra_backend.app.agents.supervisor.execution_engine_factory']
        self._ssot_import_patterns = {'user_execution_context': 'netra_backend.app.services.user_execution_context', 'websocket_bridge': 'netra_backend.app.services.agent_websocket_bridge', 'unified_emitter': 'netra_backend.app.websocket_core.unified_emitter', 'unified_manager': 'netra_backend.app.websocket_core.unified_manager', 'agent_registry': 'netra_backend.app.agents.supervisor.agent_registry', 'agent_class_registry': 'netra_backend.app.agents.supervisor.agent_class_registry', 'base_agent': 'netra_backend.app.agents.base_agent', 'logging': 'netra_backend.app.logging_config'}
        self._discovered_imports = {}
        self._import_violations = []
        self.record_metric('test_setup_completed', True)

    def teardown_method(self, method):
        """Cleanup after each test method."""
        modules_to_clear = []
        for module_name in sys.modules:
            if any((target in module_name for target in self._target_modules)):
                modules_to_clear.append(module_name)
        for module_name in modules_to_clear:
            if module_name in sys.modules:
                del sys.modules[module_name]
        super().teardown_method(method)

    def _parse_module_imports(self, module_path: str) -> Dict[str, List[str]]:
        """Parse Python module and extract all import statements."""
        try:
            with open(module_path, 'r', encoding='utf-8') as f:
                content = f.read()
            tree = ast.parse(content)
            imports = {'from_imports': [], 'direct_imports': [], 'import_violations': []}
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports['direct_imports'].append({'module': alias.name, 'alias': alias.asname, 'line': node.lineno})
                elif isinstance(node, ast.ImportFrom):
                    module_name = node.module or ''
                    for alias in node.names:
                        imports['from_imports'].append({'module': module_name, 'name': alias.name, 'alias': alias.asname, 'line': node.lineno, 'level': node.level})
            return imports
        except Exception as e:
            return {'error': str(e), 'from_imports': [], 'direct_imports': []}

    def _find_module_file(self, module_name: str) -> Optional[str]:
        """Find the file path for a given module name."""
        try:
            parts = module_name.split('.')
            base_path = Path.cwd()
            for part in parts[:-1]:
                base_path = base_path / part
            module_file = base_path / f'{parts[-1]}.py'
            if module_file.exists():
                return str(module_file)
            package_init = base_path / parts[-1] / '__init__.py'
            if package_init.exists():
                return str(package_init)
            return None
        except Exception:
            return None

    def test_agent_instance_factory_import_patterns(self):
        """
        CRITICAL TEST: Validate AgentInstanceFactory import patterns follow SSOT.

        This test should FAIL before Issue #709 remediation if imports don't
        follow SSOT patterns or contain circular dependencies.

        After remediation, this test should PASS by proving SSOT import compliance.
        """
        self.record_metric('test_started', 'test_agent_instance_factory_import_patterns')
        module_name = 'netra_backend.app.agents.supervisor.agent_instance_factory'
        module_file = self._find_module_file(module_name)
        if not module_file:
            pytest.skip(f'Cannot find module file for {module_name}')
        try:
            imports = self._parse_module_imports(module_file)
            self._discovered_imports[module_name] = imports
            if 'error' in imports:
                pytest.fail(f"Failed to parse imports from {module_name}: {imports['error']}")
            ssot_violations = []
            from_imports = imports['from_imports']
            user_context_imports = [imp for imp in from_imports if 'user_execution_context' in imp['module'].lower()]
            if not user_context_imports:
                ssot_violations.append('Missing UserExecutionContext import')
            else:
                for imp in user_context_imports:
                    expected_module = self._ssot_import_patterns['user_execution_context']
                    if imp['module'] != expected_module:
                        ssot_violations.append(f"UserExecutionContext wrong import: {imp['module']}, expected: {expected_module}")
            websocket_imports = [imp for imp in from_imports if 'websocket' in imp['module'].lower()]
            for imp in websocket_imports:
                module = imp['module']
                deprecated_patterns = ['websocket_core.manager', 'websocket_core.emitter', 'websocket_notifications']
                for deprecated in deprecated_patterns:
                    if deprecated in module:
                        ssot_violations.append(f"Deprecated WebSocket import: {module}, line {imp['line']}")
            forbidden_imports = ['os.environ', 'singleton', 'global_state']
            all_imports_text = ' '.join([imp['module'] + '.' + imp['name'] for imp in from_imports])
            for forbidden in forbidden_imports:
                if forbidden in all_imports_text.lower():
                    ssot_violations.append(f'Forbidden import pattern: {forbidden}')
            agent_registry_imports = [imp for imp in from_imports if 'agent_registry' in imp['module'].lower() or 'agent_class_registry' in imp['module'].lower()]
            for imp in agent_registry_imports:
                if 'supervisor' not in imp['module']:
                    ssot_violations.append(f"Agent registry import outside supervisor module: {imp['module']}, line {imp['line']}")
            logging_imports = [imp for imp in from_imports + imports['direct_imports'] if 'logging' in imp.get('module', '').lower() or imp.get('name', '').lower() == 'logging']
            central_logger_used = any(('logging_config' in imp.get('module', '') for imp in from_imports))
            if logging_imports and (not central_logger_used):
                ssot_violations.append('Uses direct logging import instead of central_logger')
            if ssot_violations:
                assert len(ssot_violations) == 0, f'SSOT IMPORT VIOLATIONS in {module_name}: {ssot_violations}. These indicate non-SSOT import patterns that need remediation.'
            self.record_metric('agent_factory_import_checks_passed', 5)
            self.record_metric('test_result', 'PASS')
        except AssertionError:
            self.record_metric('test_result', 'FAIL_EXPECTED_BEFORE_REMEDIATION')
            raise
        except Exception as e:
            self.record_metric('test_result', 'ERROR')
            pytest.fail(f'Unexpected error during import validation: {e}')

    def test_execution_engine_factory_import_patterns(self):
        """
        CRITICAL TEST: Validate ExecutionEngineFactory import patterns follow SSOT.

        This test should FAIL before Issue #709 remediation if imports contain
        circular dependencies or don't follow SSOT consolidation patterns.
        """
        self.record_metric('test_started', 'test_execution_engine_factory_import_patterns')
        module_name = 'netra_backend.app.agents.supervisor.execution_engine_factory'
        module_file = self._find_module_file(module_name)
        if not module_file:
            pytest.skip(f'Cannot find module file for {module_name}')
        try:
            imports = self._parse_module_imports(module_file)
            self._discovered_imports[module_name] = imports
            if 'error' in imports:
                pytest.fail(f"Failed to parse imports from {module_name}: {imports['error']}")
            from_imports = imports['from_imports']
            circular_dependency_imports = [imp for imp in from_imports if 'agent_instance_factory' in imp['module']]
            assert len(circular_dependency_imports) == 0, f'CIRCULAR DEPENDENCY VIOLATION: ExecutionEngineFactory imports AgentInstanceFactory. Circular imports: {circular_dependency_imports}. Expected: No circular dependencies between factory modules.'
            user_execution_engine_imports = [imp for imp in from_imports if 'user_execution_engine' in imp['module'].lower()]
            if user_execution_engine_imports:
                for imp in user_execution_engine_imports:
                    expected_pattern = 'netra_backend.app.agents.supervisor'
                    if expected_pattern not in imp['module']:
                        pytest.fail(f"SSOT IMPORT VIOLATION: UserExecutionEngine wrong import location: {imp['module']}. Expected: {expected_pattern} for SSOT compliance.")
            websocket_bridge_imports = [imp for imp in from_imports if 'websocket_bridge' in imp['module'].lower() or 'agent_websocket_bridge' in imp['name'].lower()]
            if websocket_bridge_imports:
                for imp in websocket_bridge_imports:
                    expected_module = self._ssot_import_patterns['websocket_bridge']
                    if imp['module'] != expected_module:
                        pytest.fail(f"SSOT IMPORT VIOLATION: WebSocket bridge wrong import: {imp['module']}. Expected: {expected_module} for SSOT compliance.")
            deprecation_imports = [imp for imp in from_imports + imports['direct_imports'] if 'warnings' in imp.get('module', '').lower() or imp.get('name', '') == 'warnings']
            if not deprecation_imports:
                pytest.fail(f'SSOT MIGRATION VIOLATION: ExecutionEngineFactory missing deprecation warnings. Expected: warnings import for deprecated factory notification.')
            type_checking_imports = [imp for imp in from_imports if imp['module'] == 'typing' and 'TYPE_CHECKING' in imp['name']]
            if not type_checking_imports:
                forward_ref_candidates = [imp for imp in from_imports if any((pattern in imp['module'] for pattern in ['agent_registry', 'websocket_bridge']))]
                if forward_ref_candidates:
                    pytest.fail(f'SSOT IMPORT VIOLATION: Missing TYPE_CHECKING for forward references. Forward reference candidates: {forward_ref_candidates}. Expected: TYPE_CHECKING pattern for proper import organization.')
            self.record_metric('execution_engine_factory_import_checks_passed', 6)
            self.record_metric('test_result', 'PASS')
        except AssertionError:
            self.record_metric('test_result', 'FAIL_EXPECTED_BEFORE_REMEDIATION')
            raise
        except Exception as e:
            self.record_metric('test_result', 'ERROR')
            pytest.fail(f'Unexpected error during execution engine import validation: {e}')

    def test_import_path_validity(self):
        """
        CRITICAL TEST: Validate all imports in factory modules are valid and accessible.

        This test verifies that all import paths actually work and don't
        result in ImportError or circular dependency issues.

        Expected to FAIL before remediation due to broken import paths.
        """
        self.record_metric('test_started', 'test_import_path_validity')
        import_test_results = {}
        for module_name in self._target_modules:
            try:
                module = importlib.import_module(module_name)
                import_test_results[module_name] = {'import_success': True, 'module_object': module, 'import_errors': []}
                expected_classes = {'agent_instance_factory': ['AgentInstanceFactory', 'get_agent_instance_factory'], 'execution_engine_factory': ['ExecutionEngineFactory', 'get_execution_engine_factory']}
                module_key = module_name.split('.')[-1]
                if module_key in expected_classes:
                    for class_name in expected_classes[module_key]:
                        if not hasattr(module, class_name):
                            import_test_results[module_name]['import_errors'].append(f'Missing expected class/function: {class_name}')
                if module_key == 'agent_instance_factory':
                    try:
                        factory_class = getattr(module, 'AgentInstanceFactory', None)
                        if factory_class:
                            factory_instance = factory_class()
                            import_test_results[module_name]['instantiation_success'] = True
                        else:
                            import_test_results[module_name]['import_errors'].append('AgentInstanceFactory class not accessible')
                    except Exception as e:
                        import_test_results[module_name]['import_errors'].append(f'Factory instantiation failed: {e}')
                elif module_key == 'execution_engine_factory':
                    try:
                        factory_class = getattr(module, 'ExecutionEngineFactory', None)
                        if factory_class:
                            factory_instance = factory_class()
                            import_test_results[module_name]['instantiation_success'] = True
                        else:
                            import_test_results[module_name]['import_errors'].append('ExecutionEngineFactory class not accessible')
                    except Exception as e:
                        import_test_results[module_name]['import_errors'].append(f'ExecutionEngineFactory instantiation failed: {e}')
            except ImportError as e:
                import_test_results[module_name] = {'import_success': False, 'import_error': str(e), 'import_errors': [f'Module import failed: {e}']}
            except Exception as e:
                import_test_results[module_name] = {'import_success': False, 'unexpected_error': str(e), 'import_errors': [f'Unexpected error: {e}']}
        failed_imports = [module for module, result in import_test_results.items() if not result.get('import_success', False)]
        if failed_imports:
            assert len(failed_imports) == 0, f'IMPORT PATH VIOLATIONS: Failed to import modules: {failed_imports}. Import results: {import_test_results}. This indicates broken import paths that need remediation.'
        modules_with_errors = [module for module, result in import_test_results.items() if result.get('import_errors', [])]
        if modules_with_errors:
            error_details = {module: import_test_results[module]['import_errors'] for module in modules_with_errors}
            assert len(modules_with_errors) == 0, f'IMPORT ERROR VIOLATIONS: Modules with import errors: {error_details}. These indicate accessibility issues that need remediation.'
        self.record_metric('modules_tested', len(self._target_modules))
        self.record_metric('import_path_checks_passed', 5)
        self.record_metric('test_result', 'PASS')

    def test_ssot_import_consolidation_compliance(self):
        """
        CRITICAL TEST: Validate SSOT import consolidation is properly implemented.

        This test verifies that imports follow the consolidated SSOT patterns
        and don't use legacy or deprecated import paths.

        Expected to FAIL before remediation due to non-consolidated imports.
        """
        self.record_metric('test_started', 'test_ssot_import_consolidation_compliance')
        consolidation_violations = []
        for module_name in self._target_modules:
            module_file = self._find_module_file(module_name)
            if not module_file:
                continue
            try:
                imports = self._parse_module_imports(module_file)
                legacy_patterns = {'old_websocket_manager': 'netra_backend.app.websocket_core.manager', 'old_websocket_emitter': 'netra_backend.app.websocket_core.emitter', 'deprecated_agent_registry': 'netra_backend.app.agents.registry', 'old_execution_context': 'netra_backend.app.agents.execution_context', 'legacy_factory': 'netra_backend.app.agents.factory'}
                for legacy_name, legacy_path in legacy_patterns.items():
                    legacy_imports = [imp for imp in imports['from_imports'] if imp['module'] == legacy_path]
                    if legacy_imports:
                        consolidation_violations.append(f'{module_name}: Uses legacy import {legacy_name}: {legacy_path}')
                required_unified_imports = {'unified_emitter': 'netra_backend.app.websocket_core.unified_emitter', 'unified_manager': 'netra_backend.app.websocket_core.unified_manager'}
                for unified_name, unified_path in required_unified_imports.items():
                    websocket_usage = any(('websocket' in imp['name'].lower() or 'emitter' in imp['name'].lower() for imp in imports['from_imports']))
                    if websocket_usage:
                        unified_imports = [imp for imp in imports['from_imports'] if imp['module'] == unified_path]
                        if not unified_imports:
                            old_websocket_imports = [imp for imp in imports['from_imports'] if 'websocket' in imp['module'] and 'unified' not in imp['module']]
                            if old_websocket_imports:
                                consolidation_violations.append(f'{module_name}: Uses non-unified WebSocket imports instead of {unified_path}')
                agent_registry_imports = [imp for imp in imports['from_imports'] if 'agent_registry' in imp['module'].lower()]
                for imp in agent_registry_imports:
                    if 'supervisor' not in imp['module']:
                        consolidation_violations.append(f"{module_name}: Agent registry import not from supervisor: {imp['module']}")
                direct_logging_imports = [imp for imp in imports['direct_imports'] if imp['module'] == 'logging']
                if direct_logging_imports:
                    central_logger_imports = [imp for imp in imports['from_imports'] if 'logging_config' in imp['module'] and 'central_logger' in imp['name']]
                    if not central_logger_imports:
                        consolidation_violations.append(f'{module_name}: Uses direct logging import without central_logger')
            except Exception as e:
                consolidation_violations.append(f'{module_name}: Failed to analyze imports: {e}')
        if consolidation_violations:
            assert len(consolidation_violations) == 0, f"SSOT CONSOLIDATION VIOLATIONS: {consolidation_violations}. These indicate imports that haven't been consolidated to SSOT patterns."
        self.record_metric('consolidation_checks_passed', 5)
        self.record_metric('test_result', 'PASS')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')