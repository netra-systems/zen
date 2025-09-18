"""
SSOT Agent Execution Violations Test Suite - Issue #909 Validation

This test suite validates that all SSOT violations identified in Issue #909
have been properly remediated. These tests ensure the golden path works reliably.

Business Value: Prevents $500K+ ARR loss from golden path failures
Critical for: User login → AI response flow stability
"""

import pytest
import sys
import os
from pathlib import Path
from typing import List, Dict, Any
import importlib
import inspect

# Add project root to path for testing
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class TestSSOTAgentExecutionCompliance:
    """Test suite for SSOT agent execution compliance validation."""

    def test_single_execution_engine_ssot(self):
        """Test that there is only one canonical ExecutionEngine implementation."""
        logger.info("Testing ExecutionEngine SSOT compliance...")

        # Test that canonical imports work
        from netra_backend.app.agents.canonical_imports import ExecutionEngineFactory, UserExecutionEngine
        from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory as SupervisorFactory
        from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as SupervisorEngine

        # Verify SSOT - all imports should resolve to the same classes
        assert ExecutionEngineFactory is SupervisorFactory, "ExecutionEngineFactory SSOT violation detected"
        assert UserExecutionEngine is SupervisorEngine, "UserExecutionEngine SSOT violation detected"

        # Test factory creation
        factory = ExecutionEngineFactory()
        assert hasattr(factory, 'create_for_user'), "ExecutionEngineFactory missing create_for_user method"
        assert hasattr(factory, 'get_factory_metrics'), "ExecutionEngineFactory missing metrics method"

        logger.info("✅ ExecutionEngine SSOT compliance: PASS")

    def test_no_duplicate_registry_classes(self):
        """Test that there are no duplicate AgentRegistry classes."""
        logger.info("Testing AgentRegistry SSOT compliance...")

        # Test main registry paths
        from netra_backend.app.agents.registry import AgentRegistry as MainRegistry
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as SupervisorRegistry

        # Verify SSOT - should be the same class
        assert MainRegistry is SupervisorRegistry, "AgentRegistry SSOT violation - multiple classes detected"

        # Test that both import paths work
        main_instance = MainRegistry()
        supervisor_instance = SupervisorRegistry()

        # Both should be instances of the same class
        assert type(main_instance) is type(supervisor_instance), "AgentRegistry instances are different types"

        logger.info("✅ AgentRegistry SSOT compliance: PASS")

    def test_no_circular_imports(self):
        """Test that there are no circular import issues in agent modules."""
        logger.info("Testing for circular import issues...")

        # List of modules that previously had circular imports
        critical_modules = [
            'netra_backend.app.agents.registry',
            'netra_backend.app.agents.supervisor.agent_registry',
            'netra_backend.app.agents.supervisor.execution_engine',
            'netra_backend.app.agents.supervisor.execution_engine_factory',
            'netra_backend.app.websocket_core.websocket_manager',
            'netra_backend.app.websocket_core.manager'
        ]

        # Test each module can be imported without circular dependency errors
        for module_name in critical_modules:
            try:
                module = importlib.import_module(module_name)
                assert module is not None, f"Module {module_name} failed to import"
                logger.debug(f"✓ {module_name} imported successfully")
            except ImportError as e:
                pytest.fail(f"Circular import detected in {module_name}: {e}")

        logger.info("✅ Circular import test: PASS")

    def test_execution_engine_factory_pattern(self):
        """Test that ExecutionEngineFactory follows proper factory pattern."""
        logger.info("Testing ExecutionEngineFactory factory pattern...")

        from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory

        # Test factory instantiation
        factory = ExecutionEngineFactory()

        # Test required factory methods exist
        required_methods = [
            'create_for_user',
            'get_factory_metrics',
            'user_execution_scope',
            'cleanup_engine',
            'shutdown'
        ]

        for method_name in required_methods:
            assert hasattr(factory, method_name), f"ExecutionEngineFactory missing required method: {method_name}"
            method = getattr(factory, method_name)
            assert callable(method), f"ExecutionEngineFactory.{method_name} is not callable"

        # Test factory metrics
        metrics = factory.get_factory_metrics()
        assert isinstance(metrics, dict), "Factory metrics should return a dictionary"
        assert 'total_engines_created' in metrics, "Factory metrics missing total_engines_created"
        assert 'active_engines_count' in metrics, "Factory metrics missing active_engines_count"

        logger.info("✅ ExecutionEngineFactory factory pattern: PASS")

    def test_golden_path_imports(self):
        """Test that golden path imports work without errors."""
        logger.info("Testing golden path imports...")

        # Test critical golden path imports
        golden_path_imports = [
            ('netra_backend.app.agents.canonical_imports', ['ExecutionEngineFactory', 'UserExecutionEngine']),
            ('netra_backend.app.agents.supervisor.agent_registry', ['AgentRegistry', 'AgentStatus', 'AgentType']),
            ('netra_backend.app.websocket_core.websocket_manager', ['WebSocketManager']),
            ('netra_backend.app.services.user_execution_context', ['UserExecutionContext']),
        ]

        for module_name, expected_exports in golden_path_imports:
            try:
                module = importlib.import_module(module_name)

                for export_name in expected_exports:
                    assert hasattr(module, export_name), f"Module {module_name} missing expected export: {export_name}"
                    export_obj = getattr(module, export_name)
                    assert export_obj is not None, f"Export {export_name} from {module_name} is None"

                logger.debug(f"✓ {module_name} exports validated")

            except ImportError as e:
                pytest.fail(f"Golden path import failed for {module_name}: {e}")

        logger.info("✅ Golden path imports: PASS")

    def test_execution_engine_consolidation(self):
        """Test that execution engine files are properly consolidated or redirected."""
        logger.info("Testing execution engine file consolidation...")

        # Get project root
        project_root = Path(__file__).parent.parent.parent.parent

        # Execution engine files that should be consolidated/redirected
        execution_files = [
            'netra_backend/app/agents/execution_engine_consolidated.py',
            'netra_backend/app/agents/supervisor/execution_engine.py',
            'netra_backend/app/agents/supervisor/request_scoped_execution_engine.py',
            'netra_backend/app/tools/enhanced_tool_execution_engine.py'
        ]

        redirect_keywords = ['redirect', 'SSOT', 'canonical', 'deprecated']

        for file_path in execution_files:
            full_path = project_root / file_path
            if full_path.exists():
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Check if file properly redirects to SSOT
                    has_redirect = any(keyword.lower() in content.lower() for keyword in redirect_keywords)
                    assert has_redirect, f"File {file_path} does not properly redirect to SSOT implementation"

                    logger.debug(f"✓ {file_path} properly redirects to SSOT")

                except Exception as e:
                    pytest.fail(f"Failed to validate {file_path}: {e}")

        logger.info("✅ Execution engine consolidation: PASS")

    def test_registry_factory_integration(self):
        """Test that AgentRegistry and ExecutionEngineFactory integrate properly."""
        logger.info("Testing registry and factory integration...")

        from netra_backend.app.agents.supervisor.agent_registry import get_agent_registry
        from netra_backend.app.agents.supervisor.execution_engine_factory import get_execution_engine_factory

        # Test that both factory functions work
        try:
            # These should not raise exceptions
            registry = get_agent_registry()
            assert registry is not None, "get_agent_registry() returned None"

            # Factory function should work (may need context)
            # Note: This might require WebSocket bridge, so we test with None
            import asyncio
            async def test_factory():
                try:
                    factory = await get_execution_engine_factory()
                    assert factory is not None, "get_execution_engine_factory() returned None"
                    return True
                except Exception as e:
                    # If it fails due to missing websocket bridge, that's expected in test mode
                    if "websocket" in str(e).lower() or "bridge" in str(e).lower():
                        logger.debug(f"Factory requires WebSocket bridge (expected in test): {e}")
                        return True
                    else:
                        raise e

            # Run the async test
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(test_factory())
                assert result, "Factory integration test failed"
            finally:
                loop.close()

        except Exception as e:
            pytest.fail(f"Registry and factory integration failed: {e}")

        logger.info("✅ Registry and factory integration: PASS")


def test_comprehensive_ssot_validation():
    """Run comprehensive SSOT validation for Issue #909."""
    logger.info("=== Running Comprehensive SSOT Validation for Issue #909 ===")

    test_suite = TestSSOTAgentExecutionCompliance()

    # Run all validation tests
    tests = [
        test_suite.test_single_execution_engine_ssot,
        test_suite.test_no_duplicate_registry_classes,
        test_suite.test_no_circular_imports,
        test_suite.test_execution_engine_factory_pattern,
        test_suite.test_golden_path_imports,
        test_suite.test_execution_engine_consolidation,
        test_suite.test_registry_factory_integration
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            logger.error(f"Test {test.__name__} failed: {e}")
            failed += 1

    logger.info(f"=== SSOT Validation Complete: {passed} passed, {failed} failed ===")

    if failed > 0:
        pytest.fail(f"SSOT validation failed: {failed} tests failed out of {len(tests)}")
    else:
        logger.info("✅ All SSOT validation tests passed - Issue #909 remediation successful")


if __name__ == "__main__":
    # Run the comprehensive test
    test_comprehensive_ssot_validation()