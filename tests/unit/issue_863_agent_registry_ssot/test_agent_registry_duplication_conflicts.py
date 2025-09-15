"""
Test Agent Registry Duplication Conflicts (Issue #863)

Reproduces the critical SSOT violation where 4 different AgentRegistry implementations
cause import conflicts, blocking Golden Path user flow and WebSocket events.

Business Value: Protects $500K+ ARR by identifying registry conflicts that prevent
users from getting AI responses through the chat interface.

Test Categories:
- Unit tests for registry conflict reproduction
- No Docker required - pure import and conflict testing
- Focus on failing tests to demonstrate the problem clearly
"""
import sys
import importlib
import inspect
from typing import Dict, List, Any, Set, Optional, Tuple
from pathlib import Path
import pytest
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.logging.unified_logging_ssot import get_logger
logger = get_logger(__name__)

@pytest.mark.unit
class TestAgentRegistryDuplicationConflicts(SSotAsyncTestCase):
    """
    Test suite to reproduce AgentRegistry SSOT violations blocking Golden Path.

    These tests are DESIGNED TO FAIL initially to demonstrate the registry conflict
    problem that prevents users from getting AI responses.
    """

    def setup_method(self, method):
        """Pytest setup method."""
        self._setup_test_data()

    def _setup_test_data(self):
        """Set up test data for registry conflict detection."""
        self.registry_paths = ['netra_backend.app.agents.registry', 'netra_backend.app.agents.supervisor.agent_registry', 'netra_backend.app.core.registry.universal_registry']
        self.conflicting_imports = ['AgentRegistry', 'agent_registry', 'get_agent_registry']
        self.websocket_integration_methods = ['set_websocket_manager', 'set_websocket_bridge', '_notify_agent_event']

    def test_agent_registry_import_path_conflicts(self):
        """
        TEST DESIGNED TO FAIL: Demonstrate registry import conflicts.

        This test reproduces the core issue - multiple AgentRegistry classes
        with different interfaces causing import resolution failures.
        """
        registry_classes = {}
        import_errors = []
        for path in self.registry_paths:
            try:
                module = importlib.import_module(path)
                if hasattr(module, 'AgentRegistry'):
                    registry_class = getattr(module, 'AgentRegistry')
                    registry_classes[path] = {'class': registry_class, 'module_path': path, 'methods': [m for m in dir(registry_class) if not m.startswith('_')], 'file_location': inspect.getfile(registry_class), 'line_count': len(inspect.getsource(registry_class).splitlines())}
                    logger.info(f"Found AgentRegistry in {path}: {registry_classes[path]['line_count']} lines")
            except ImportError as e:
                import_errors.append(f'Failed to import {path}: {e}')
                logger.error(f'Import error for {path}: {e}')
            except Exception as e:
                import_errors.append(f'Unexpected error importing {path}: {e}')
                logger.error(f'Unexpected error for {path}: {e}')
        if len(registry_classes) > 1:
            logger.error(f'SSOT VIOLATION: Found {len(registry_classes)} different AgentRegistry classes')
            for path, info in registry_classes.items():
                logger.error(f"  - {path}: {info['line_count']} lines at {info['file_location']}")
            method_conflicts = self._analyze_method_conflicts(registry_classes)
            if method_conflicts:
                logger.error(f'Method signature conflicts detected: {len(method_conflicts)}')
                for conflict in method_conflicts:
                    logger.error(f'  - {conflict}')
            self.fail(f'CRITICAL SSOT VIOLATION: Found {len(registry_classes)} different AgentRegistry implementations. This causes import conflicts blocking Golden Path user flow. Classes found: {list(registry_classes.keys())}')
        self.assertEqual(len(registry_classes), 1, 'Should have exactly ONE AgentRegistry implementation for SSOT compliance')

    def test_agent_registry_interface_consistency(self):
        """
        TEST DESIGNED TO FAIL: Demonstrate interface inconsistencies between registries.

        This test shows how different registry implementations have incompatible
        interfaces, preventing WebSocket bridge integration.
        """
        registry_classes = self._get_all_registry_classes()
        if len(registry_classes) <= 1:
            self.skipTest('Only one registry found - interface consistency not applicable')
        websocket_method_analysis = {}
        for path, registry_info in registry_classes.items():
            registry_class = registry_info['class']
            websocket_method_analysis[path] = {}
            for method_name in self.websocket_integration_methods:
                if hasattr(registry_class, method_name):
                    method = getattr(registry_class, method_name)
                    signature = inspect.signature(method)
                    websocket_method_analysis[path][method_name] = {'exists': True, 'signature': str(signature), 'parameters': list(signature.parameters.keys())}
                else:
                    websocket_method_analysis[path][method_name] = {'exists': False, 'signature': None, 'parameters': []}
        method_inconsistencies = []
        for method_name in self.websocket_integration_methods:
            signatures = {}
            for path in registry_classes.keys():
                method_info = websocket_method_analysis[path][method_name]
                if method_info['exists']:
                    signatures[path] = method_info['signature']
            if len(set(signatures.values())) > 1:
                method_inconsistencies.append({'method': method_name, 'signatures': signatures})
        logger.error(f'WebSocket integration method analysis:')
        for path, methods in websocket_method_analysis.items():
            logger.error(f'  Registry: {path}')
            for method_name, method_info in methods.items():
                if method_info['exists']:
                    logger.error(f"    - {method_name}: {method_info['signature']}")
                else:
                    logger.error(f'    - {method_name}: MISSING')
        if method_inconsistencies:
            inconsistency_details = []
            for inconsistency in method_inconsistencies:
                details = f"Method '{inconsistency['method']}' has different signatures: "
                details += '; '.join([f'{path}: {sig}' for path, sig in inconsistency['signatures'].items()])
                inconsistency_details.append(details)
            self.fail(f"CRITICAL INTERFACE INCONSISTENCY: WebSocket integration methods have incompatible signatures. This prevents proper WebSocket event delivery in Golden Path. Inconsistencies: {'; '.join(inconsistency_details)}")
        logger.info('All registry interfaces are consistent - SSOT compliance achieved')

    def test_global_agent_registry_instance_conflicts(self):
        """
        TEST DESIGNED TO FAIL: Demonstrate global instance conflicts.

        This test shows how different modules expose global 'agent_registry' instances
        that can conflict with each other, causing race conditions.
        """
        global_instances = {}
        for path in self.registry_paths:
            try:
                module = importlib.import_module(path)
                if hasattr(module, 'agent_registry'):
                    instance = getattr(module, 'agent_registry')
                    global_instances[path] = {'instance': instance, 'class_name': instance.__class__.__name__, 'class_module': instance.__class__.__module__, 'instance_id': id(instance), 'methods': [m for m in dir(instance) if not m.startswith('_')]}
                    logger.info(f"Found global agent_registry in {path}: {global_instances[path]['class_name']}")
            except ImportError as e:
                logger.warning(f'Could not import {path}: {e}')
            except Exception as e:
                logger.error(f'Error checking global instance in {path}: {e}')
        if len(global_instances) > 1:
            logger.error(f'RACE CONDITION RISK: Found {len(global_instances)} global agent_registry instances')
            for path, info in global_instances.items():
                logger.error(f"  - {path}: {info['class_name']} (id: {info['instance_id']})")
            class_names = {info['class_name'] for info in global_instances.values()}
            instance_ids = {info['instance_id'] for info in global_instances.values()}
            if len(class_names) > 1:
                conflict_type = f'Different classes: {class_names}'
            else:
                conflict_type = f'Same class but {len(instance_ids)} different instances'
            self.fail(f'CRITICAL GLOBAL INSTANCE CONFLICT: Multiple global agent_registry instances detected. This causes race conditions and unpredictable behavior in multi-user scenarios. Conflict type: {conflict_type}. Instances: {list(global_instances.keys())}')
        if len(global_instances) == 1:
            logger.info('Single global agent_registry instance found - no conflicts')
        else:
            logger.info('No global agent_registry instances found - using factory pattern only')

    def test_import_resolution_consistency(self):
        """
        TEST DESIGNED TO FAIL: Demonstrate inconsistent import resolution.

        This test shows how the same import statement can resolve to different
        classes depending on import order and context.
        """
        import_resolution_results = {}
        import_patterns = [('from netra_backend.app.agents.registry import AgentRegistry', 'AgentRegistry'), ('from netra_backend.app.agents.registry import agent_registry', 'agent_registry'), ('from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry', 'AgentRegistry'), ('from netra_backend.app.agents.supervisor.agent_registry import get_agent_registry', 'get_agent_registry')]
        for import_statement, name in import_patterns:
            try:
                namespace = {}
                exec(import_statement, namespace)
                if name in namespace:
                    imported_obj = namespace[name]
                    import_resolution_results[import_statement] = {'success': True, 'object_type': type(imported_obj).__name__, 'object_module': getattr(imported_obj, '__module__', 'unknown'), 'object_id': id(imported_obj), 'is_class': inspect.isclass(imported_obj), 'is_function': inspect.isfunction(imported_obj), 'is_instance': not inspect.isclass(imported_obj) and (not inspect.isfunction(imported_obj))}
                    logger.info(f'Import success: {import_statement} -> {imported_obj}')
                else:
                    import_resolution_results[import_statement] = {'success': False, 'error': f"Name '{name}' not found after import"}
            except Exception as e:
                import_resolution_results[import_statement] = {'success': False, 'error': str(e)}
                logger.error(f'Import failed: {import_statement} -> {e}')
        successful_imports = {k: v for k, v in import_resolution_results.items() if v.get('success')}
        failed_imports = {k: v for k, v in import_resolution_results.items() if not v.get('success')}
        logger.info(f'Import resolution analysis:')
        logger.info(f'  Successful imports: {len(successful_imports)}')
        logger.info(f'  Failed imports: {len(failed_imports)}')
        for import_stmt, result in import_resolution_results.items():
            if result.get('success'):
                logger.info(f"    ✅ {import_stmt} -> {result['object_type']} from {result['object_module']}")
            else:
                logger.error(f"    ❌ {import_stmt} -> {result['error']}")
        if failed_imports:
            failed_details = '; '.join([f"{stmt}: {result['error']}" for stmt, result in failed_imports.items()])
            self.fail(f'CRITICAL IMPORT RESOLUTION FAILURE: {len(failed_imports)} import patterns failed. This prevents reliable AgentRegistry usage across the codebase, blocking Golden Path. Failed imports: {failed_details}')
        agent_registry_classes = []
        for result in successful_imports.values():
            if result['is_class'] and 'AgentRegistry' in result['object_type']:
                agent_registry_classes.append(result)
        if len(agent_registry_classes) > 1:
            class_details = [f"{r['object_type']} from {r['object_module']}" for r in agent_registry_classes]
            self.fail(f'INCONSISTENT IMPORT RESOLUTION: AgentRegistry imports resolve to different classes. This causes unpredictable behavior in production. Classes: {class_details}')

    def _get_all_registry_classes(self) -> Dict[str, Dict[str, Any]]:
        """Helper to get all AgentRegistry classes for analysis."""
        registry_classes = {}
        for path in self.registry_paths:
            try:
                module = importlib.import_module(path)
                if hasattr(module, 'AgentRegistry'):
                    registry_class = getattr(module, 'AgentRegistry')
                    registry_classes[path] = {'class': registry_class, 'module_path': path, 'methods': [m for m in dir(registry_class) if not m.startswith('_')], 'file_location': inspect.getfile(registry_class)}
            except ImportError:
                continue
            except Exception as e:
                logger.warning(f'Error analyzing {path}: {e}')
                continue
        return registry_classes

    def _analyze_method_conflicts(self, registry_classes: Dict[str, Dict[str, Any]]) -> List[str]:
        """Analyze method signature conflicts between registry classes."""
        conflicts = []
        all_methods = set()
        for registry_info in registry_classes.values():
            all_methods.update(registry_info['methods'])
        for method_name in all_methods:
            signatures = {}
            for path, registry_info in registry_classes.items():
                if method_name in registry_info['methods']:
                    try:
                        method = getattr(registry_info['class'], method_name)
                        if callable(method):
                            signatures[path] = str(inspect.signature(method))
                    except Exception:
                        signatures[path] = 'SIGNATURE_ERROR'
            if len(set(signatures.values())) > 1:
                conflict_detail = f"Method '{method_name}' has different signatures: "
                conflict_detail += '; '.join([f'{path}: {sig}' for path, sig in signatures.items()])
                conflicts.append(conflict_detail)
        return conflicts

    def test_production_import_usage_patterns(self):
        """
        TEST DESIGNED TO FAIL: Analyze production import patterns for conflicts.

        This test scans production code to find actual import usage patterns
        and identifies where conflicts occur in real usage.
        """
        expected_patterns = ['from netra_backend.app.agents.registry import AgentRegistry', 'from netra_backend.app.agents.registry import agent_registry', 'from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry', 'from netra_backend.app.agents.supervisor.agent_registry import get_agent_registry']
        production_usage = self._scan_production_imports()
        conflicts_found = []
        for file_path, imports in production_usage.items():
            registry_modules_used = set()
            for import_line in imports:
                if 'agents.registry' in import_line:
                    if 'supervisor.agent_registry' in import_line:
                        registry_modules_used.add('supervisor.agent_registry')
                    elif 'agents.registry' in import_line:
                        registry_modules_used.add('agents.registry')
            if len(registry_modules_used) > 1:
                conflicts_found.append({'file': file_path, 'modules': list(registry_modules_used), 'imports': imports})
        logger.info(f'Production import analysis:')
        logger.info(f'  Files scanned: {len(production_usage)}')
        logger.info(f'  Conflicting files: {len(conflicts_found)}')
        for conflict in conflicts_found:
            logger.error(f"  Conflict in {conflict['file']}:")
            logger.error(f"    Uses modules: {conflict['modules']}")
            for import_line in conflict['imports']:
                logger.error(f'    Import: {import_line}')
        if conflicts_found:
            conflict_summary = '; '.join([f"{c['file']} uses {c['modules']}" for c in conflicts_found])
            self.fail(f'PRODUCTION IMPORT CONFLICTS: {len(conflicts_found)} files use conflicting registry imports. This causes runtime failures and blocks Golden Path functionality. Conflicts: {conflict_summary}')
        logger.info('No production import conflicts detected - SSOT compliance maintained')

    def _scan_production_imports(self) -> Dict[str, List[str]]:
        """Scan production Python files for registry import patterns."""
        production_usage = {}
        scan_paths = [Path('netra_backend/app'), Path('tests')]
        registry_keywords = ['agent_registry', 'AgentRegistry', 'get_agent_registry']
        for scan_path in scan_paths:
            if not scan_path.exists():
                continue
            for py_file in scan_path.rglob('*.py'):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        lines = content.splitlines()
                    registry_imports = []
                    for line_num, line in enumerate(lines, 1):
                        line = line.strip()
                        if (line.startswith('from ') or line.startswith('import ')) and any((keyword in line for keyword in registry_keywords)):
                            registry_imports.append(f'Line {line_num}: {line}')
                    if registry_imports:
                        production_usage[str(py_file)] = registry_imports
                except Exception as e:
                    logger.warning(f'Could not scan {py_file}: {e}')
                    continue
        return production_usage
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')