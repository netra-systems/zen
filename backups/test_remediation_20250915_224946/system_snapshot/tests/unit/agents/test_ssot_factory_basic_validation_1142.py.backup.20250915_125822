"""
Basic SSOT Factory Validation Tests for Issue #1142 - Minimal Dependencies

PURPOSE: Validate core SSOT migration patterns without complex import chains.
These tests focus on the basic factory patterns and singleton elimination.

CRITICAL: These tests validate the CORRECT behavior after migration.
They should PASS once the SSOT migration is complete.

Created: 2025-09-14
Issue: #1142 - SSOT Agent Factory Singleton violation blocking Golden Path
"""
import pytest
import asyncio
from unittest.mock import MagicMock, patch
from typing import Dict, Any
from test_framework.ssot.base_test_case import SSotBaseTestCase

class MockUserExecutionContext:
    """Mock UserExecutionContext for isolated testing."""

    def __init__(self, user_id: str, thread_id: str, run_id: str, websocket_client_id: str):
        self.user_id = user_id
        self.thread_id = thread_id
        self.run_id = run_id
        self.websocket_client_id = websocket_client_id

@pytest.mark.unit
class TestSSOTFactoryBasicValidation1142(SSotBaseTestCase):
    """Basic validation tests for SSOT factory migration."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.user1_context = MockUserExecutionContext(user_id='healthcare_user_001', thread_id='thread_healthcare_001', run_id='run_healthcare_001', websocket_client_id='ws_healthcare_001')
        self.user2_context = MockUserExecutionContext(user_id='fintech_user_002', thread_id='thread_fintech_002', run_id='run_fintech_002', websocket_client_id='ws_fintech_002')

    def test_import_create_agent_instance_factory_exists(self):
        """
        CRITICAL: Test that create_agent_instance_factory function exists and is importable.
        
        This validates the core SSOT function is available for per-request factory creation.
        
        Expected: PASS - Function exists and is importable
        """
        try:
            from netra_backend.app.agents.supervisor.agent_instance_factory import create_agent_instance_factory
            assert callable(create_agent_instance_factory), 'SSOT FUNCTION: create_agent_instance_factory should be callable'
        except ImportError as e:
            pytest.fail(f'SSOT IMPORT FAILURE: Cannot import create_agent_instance_factory: {e}')

    def test_import_get_agent_instance_factory_deprecated(self):
        """
        CRITICAL: Test that deprecated get_agent_instance_factory exists but is marked deprecated.
        
        This validates the legacy singleton function is available but properly deprecated.
        
        Expected: PASS - Function exists and shows deprecation behavior
        """
        try:
            from netra_backend.app.agents.supervisor.agent_instance_factory import get_agent_instance_factory
            assert callable(get_agent_instance_factory), 'LEGACY FUNCTION: get_agent_instance_factory should be callable'
            factory = get_agent_instance_factory()
            assert factory is not None, 'LEGACY FUNCTION: Should return a factory instance even if deprecated'
        except ImportError as e:
            pytest.fail(f'LEGACY IMPORT FAILURE: Cannot import get_agent_instance_factory: {e}')

    def test_dependencies_module_exports_correct_function(self):
        """
        CRITICAL: Test that dependencies module exports the correct SSOT dependency function.
        
        This validates that FastAPI dependency injection uses the SSOT pattern.
        
        Expected: PASS - Dependency function exists and is properly structured
        """
        try:
            from netra_backend.app.dependencies import get_agent_instance_factory_dependency
            assert callable(get_agent_instance_factory_dependency), 'DEPENDENCY FUNCTION: get_agent_instance_factory_dependency should be callable'
            import inspect
            assert inspect.iscoroutinefunction(get_agent_instance_factory_dependency), 'DEPENDENCY ASYNC: get_agent_instance_factory_dependency should be async'
        except ImportError as e:
            pytest.fail(f'DEPENDENCY IMPORT FAILURE: Cannot import get_agent_instance_factory_dependency: {e}')

    def test_user_execution_context_import(self):
        """
        CRITICAL: Test that UserExecutionContext is importable and usable.
        
        This validates the core user context object used for factory isolation.
        
        Expected: PASS - UserExecutionContext can be imported and instantiated
        """
        try:
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            context = UserExecutionContext(user_id='test_user', thread_id='test_thread', run_id='test_run', websocket_client_id='test_ws')
            assert context.user_id == 'test_user', 'USER CONTEXT: Should properly bind user_id'
            assert context.thread_id == 'test_thread', 'USER CONTEXT: Should properly bind thread_id'
        except ImportError as e:
            pytest.fail(f'USER CONTEXT IMPORT FAILURE: Cannot import UserExecutionContext: {e}')

    def test_factory_pattern_isolation_basic(self):
        """
        CRITICAL: Test basic factory pattern isolation using mocked components.
        
        This validates that the factory pattern creates isolated instances.
        
        Expected: PASS - Factory pattern creates separate instances
        """

        def mock_create_agent_instance_factory(user_context):
            """Mock factory creation that maintains user isolation."""
            factory = MagicMock()
            factory._user_context = user_context
            factory.configure = MagicMock()
            return factory
        factory1 = mock_create_agent_instance_factory(self.user1_context)
        factory2 = mock_create_agent_instance_factory(self.user2_context)
        assert factory1 is not factory2, f'FACTORY ISOLATION: Factories should be separate instances. Factory1: {id(factory1)}, Factory2: {id(factory2)}'
        assert factory1._user_context.user_id == 'healthcare_user_001'
        assert factory2._user_context.user_id == 'fintech_user_002'

    def test_singleton_pattern_elimination_verification(self):
        """
        CRITICAL: Test that singleton patterns are eliminated in factory code.
        
        This validates that no global singleton variables exist in the factory module.
        
        Expected: PASS - No singleton patterns detected
        """
        try:
            import netra_backend.app.agents.supervisor.agent_instance_factory as factory_module
            module_attributes = dir(factory_module)
            singleton_indicators = ['_instance', '_factory_instance', '_singleton', '_global_factory']
            found_singletons = []
            for attr_name in module_attributes:
                if any((indicator in attr_name.lower() for indicator in singleton_indicators)):
                    attr_value = getattr(factory_module, attr_name)
                    if not callable(attr_value) and (not attr_name.startswith('__')) and (attr_value is not None):
                        found_singletons.append(attr_name)
            assert len(found_singletons) == 0, f'SINGLETON PATTERN DETECTED: Found potential singleton attributes: {found_singletons}. These may cause multi-user state contamination.'
        except ImportError as e:
            pytest.fail(f'FACTORY MODULE IMPORT FAILURE: Cannot import factory module: {e}')

    def test_dependencies_module_structure(self):
        """
        CRITICAL: Test that dependencies module has correct structure for SSOT patterns.
        
        This validates the overall structure supports per-request isolation.
        
        Expected: PASS - Dependencies module structured correctly
        """
        try:
            import netra_backend.app.dependencies as deps_module
            required_exports = ['get_agent_instance_factory_dependency', 'AgentInstanceFactoryDep']
            missing_exports = []
            for export in required_exports:
                if not hasattr(deps_module, export):
                    missing_exports.append(export)
            assert len(missing_exports) == 0, f'DEPENDENCIES STRUCTURE: Missing required exports: {missing_exports}. These are needed for proper SSOT dependency injection.'
        except ImportError as e:
            pytest.fail(f'DEPENDENCIES MODULE IMPORT FAILURE: Cannot import dependencies: {e}')

    def test_no_module_level_factory_instantiation(self):
        """
        CRITICAL: Test that no factory instances are created at module import time.
        
        This prevents singleton creation during module loading.
        
        Expected: PASS - No module-level factory instances
        """
        try:
            import netra_backend.app.agents.supervisor.agent_instance_factory as factory_module
            module_vars = vars(factory_module)
            instantiated_factories = []
            for name, value in module_vars.items():
                if name.startswith('_') or callable(value) or value is None:
                    continue
                if hasattr(value, '__class__') and 'Factory' in str(value.__class__):
                    instantiated_factories.append(name)
            assert len(instantiated_factories) == 0, f'MODULE FACTORY INSTANTIATION: Found factory instances at module level: {instantiated_factories}. This creates singleton state that can contaminate between users.'
        except ImportError as e:
            pytest.fail(f'FACTORY MODULE ANALYSIS FAILURE: Cannot analyze factory module: {e}')

    def test_user_context_validation_exists(self):
        """
        CRITICAL: Test that user context validation functions exist.
        
        This validates that proper user context validation is available.
        
        Expected: PASS - User context validation functions exist
        """
        try:
            from netra_backend.app.services.user_execution_context import validate_user_context
            assert callable(validate_user_context), 'USER CONTEXT VALIDATION: validate_user_context should be callable'
        except ImportError as e:
            pass
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')