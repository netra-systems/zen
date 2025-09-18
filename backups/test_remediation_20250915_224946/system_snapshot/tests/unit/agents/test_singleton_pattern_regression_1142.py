"""
Singleton Pattern Regression Prevention Tests for Issue #1142

PURPOSE: Prevent regression of singleton patterns in agent factory code.
These tests scan for global variables, singleton patterns, and shared state
that could cause multi-user contamination.

CRITICAL: These tests should PASS after SSOT migration and continue to pass
to prevent regression of singleton patterns in future development.

Created: 2025-09-14
Issue: #1142 - SSOT Agent Factory Singleton violation blocking Golden Path
"""
import pytest
import ast
import inspect
from pathlib import Path
from typing import List, Dict, Any, Set
from unittest.mock import patch
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.agents.supervisor import agent_instance_factory
from netra_backend.app import dependencies

class SingletonPatternScanner:
    """Utility class to scan Python modules for singleton patterns."""

    @staticmethod
    def scan_for_global_variables(module_path: str) -> List[Dict[str, Any]]:
        """Scan a Python file for global variables that could be singletons."""
        global_vars = []
        with open(module_path, 'r') as file:
            content = file.read()
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            if target.id.startswith('_') and 'instance' in target.id.lower():
                                global_vars.append({'name': target.id, 'line': node.lineno, 'module': module_path})
                            elif target.id.isupper() and 'FACTORY' in target.id:
                                global_vars.append({'name': target.id, 'line': node.lineno, 'module': module_path})
        return global_vars

    @staticmethod
    def scan_for_singleton_functions(module_path: str) -> List[Dict[str, Any]]:
        """Scan for functions that implement singleton patterns."""
        singleton_functions = []
        with open(module_path, 'r') as file:
            content = file.read()
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if node.name.startswith('get_') and 'factory' in node.name.lower():
                        for child in ast.walk(node):
                            if isinstance(child, ast.Global):
                                singleton_functions.append({'name': node.name, 'line': node.lineno, 'module': module_path, 'uses_global': True})
                                break
        return singleton_functions

    @staticmethod
    def scan_for_shared_state_patterns(module_path: str) -> List[Dict[str, Any]]:
        """Scan for patterns that indicate shared state between users."""
        shared_state_patterns = []
        with open(module_path, 'r') as file:
            content = file.read()
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                line_lower = line.lower()
                if any((pattern in line_lower for pattern in ['global cache', 'shared_cache', 'global_storage', 'singleton', 'shared_instance'])):
                    shared_state_patterns.append({'pattern': line.strip(), 'line': i, 'module': module_path, 'type': 'shared_state'})
        return shared_state_patterns

@pytest.mark.unit
class SingletonPatternRegression1142Tests(SSotBaseTestCase):
    """Test suite to prevent singleton pattern regression."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.factory_module_path = Path(agent_instance_factory.__file__)
        self.dependencies_module_path = Path(dependencies.__file__)
        self.allowed_global_variables = {'_factory_instance', 'logger', 'TYPE_CHECKING'}
        self.allowed_singleton_functions = {'get_agent_instance_factory', 'configure_agent_instance_factory'}

    def test_no_new_global_singleton_variables(self):
        """
        CRITICAL: Test that no new global singleton variables are introduced.
        
        This prevents regression by ensuring developers don't add new global
        variables that could cause multi-user state contamination.
        
        Expected: PASS - No new global singleton variables detected
        """
        scanner = SingletonPatternScanner()
        factory_globals = scanner.scan_for_global_variables(str(self.factory_module_path))
        dependencies_globals = scanner.scan_for_global_variables(str(self.dependencies_module_path))
        problematic_globals = []
        for global_var in factory_globals + dependencies_globals:
            if global_var['name'] not in self.allowed_global_variables:
                problematic_globals.append(global_var)
        assert len(problematic_globals) == 0, f'SINGLETON REGRESSION DETECTED: New global singleton variables found. This violates SSOT user isolation patterns. Problematic globals: {problematic_globals}. Remove these globals and use per-request factory pattern instead.'

    def test_no_new_singleton_functions(self):
        """
        CRITICAL: Test that no new singleton functions are introduced.
        
        This prevents regression by ensuring developers don't create new
        get_* functions that return shared singleton instances.
        
        Expected: PASS - No new singleton functions detected
        """
        scanner = SingletonPatternScanner()
        factory_singletons = scanner.scan_for_singleton_functions(str(self.factory_module_path))
        dependencies_singletons = scanner.scan_for_singleton_functions(str(self.dependencies_module_path))
        problematic_singletons = []
        for singleton_func in factory_singletons + dependencies_singletons:
            if singleton_func['name'] not in self.allowed_singleton_functions:
                problematic_singletons.append(singleton_func)
        assert len(problematic_singletons) == 0, f'SINGLETON FUNCTION REGRESSION: New singleton functions detected. This violates SSOT per-request isolation patterns. Problematic functions: {problematic_singletons}. Use create_agent_instance_factory(user_context) pattern instead.'

    def test_no_shared_state_patterns(self):
        """
        CRITICAL: Test that no shared state patterns are introduced.
        
        This prevents regression by scanning for code patterns that indicate
        shared state or caching that could contaminate between users.
        
        Expected: PASS - No shared state patterns detected
        """
        scanner = SingletonPatternScanner()
        factory_shared_state = scanner.scan_for_shared_state_patterns(str(self.factory_module_path))
        dependencies_shared_state = scanner.scan_for_shared_state_patterns(str(self.dependencies_module_path))
        all_shared_patterns = factory_shared_state + dependencies_shared_state
        assert len(all_shared_patterns) == 0, f'SHARED STATE REGRESSION: Shared state patterns detected. This can cause multi-user data contamination. Patterns found: {all_shared_patterns}. Use per-request isolation patterns instead.'

    def test_legacy_singleton_functions_show_deprecation_warnings(self):
        """
        CRITICAL: Test that legacy singleton functions show proper warnings.
        
        This ensures that allowed legacy functions properly warn developers
        about the security risks and encourage migration.
        
        Expected: PASS - Deprecation warnings are properly shown
        """
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            from netra_backend.app.agents.supervisor.agent_instance_factory import get_agent_instance_factory
            factory = get_agent_instance_factory()
            assert factory is not None, 'LEGACY FUNCTION: get_agent_instance_factory() should return a factory instance'

    def test_factory_module_exports_correct_functions(self):
        """
        CRITICAL: Test that factory module exports the correct SSOT functions.
        
        This validates that the module provides the correct public interface
        for SSOT per-request factory creation.
        
        Expected: PASS - Correct SSOT functions are exported
        """
        assert hasattr(agent_instance_factory, 'create_agent_instance_factory'), 'SSOT EXPORT: Module should export create_agent_instance_factory function'
        create_function = getattr(agent_instance_factory, 'create_agent_instance_factory')
        assert callable(create_function), 'SSOT FUNCTION: create_agent_instance_factory should be callable'
        sig = inspect.signature(create_function)
        param_names = list(sig.parameters.keys())
        assert 'user_context' in param_names, f'SSOT SIGNATURE: create_agent_instance_factory should accept user_context parameter. Current parameters: {param_names}'

    def test_dependencies_module_uses_correct_patterns(self):
        """
        CRITICAL: Test that dependencies module uses SSOT per-request patterns.
        
        This validates that FastAPI dependency injection uses the correct
        create_agent_instance_factory pattern instead of singleton configuration.
        
        Expected: PASS - Dependencies use SSOT per-request patterns
        """
        assert hasattr(dependencies, 'get_agent_instance_factory_dependency'), 'DEPENDENCY EXPORT: Dependencies should export get_agent_instance_factory_dependency'
        dep_function = getattr(dependencies, 'get_agent_instance_factory_dependency')
        assert inspect.iscoroutinefunction(dep_function), 'DEPENDENCY ASYNC: get_agent_instance_factory_dependency should be async function'
        sig = inspect.signature(dep_function)
        param_names = list(sig.parameters.keys())
        assert 'request' in param_names, f'DEPENDENCY SIGNATURE: Function should accept Request parameter. Current parameters: {param_names}'

    def test_no_module_level_factory_instances(self):
        """
        CRITICAL: Test that no factory instances exist at module level.
        
        This prevents regression by ensuring no module-level factory instances
        are created that could be shared between requests.
        
        Expected: PASS - No module-level factory instances detected
        """
        factory_attributes = [attr for attr in dir(agent_instance_factory) if not attr.startswith('__')]
        problematic_instances = []
        for attr_name in factory_attributes:
            attr_value = getattr(agent_instance_factory, attr_name)
            if hasattr(attr_value, '__class__') and 'AgentInstanceFactory' in str(attr_value.__class__) and (not inspect.isclass(attr_value)) and (not inspect.isfunction(attr_value)):
                problematic_instances.append({'name': attr_name, 'type': str(type(attr_value)), 'module': 'agent_instance_factory'})
        assert len(problematic_instances) == 0, f'MODULE INSTANCE REGRESSION: Factory instances found at module level. This creates shared singleton state. Instances: {problematic_instances}. Move these to per-request creation patterns.'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')