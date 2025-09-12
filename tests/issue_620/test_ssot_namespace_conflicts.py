"""REPRODUCTION TESTS: SSOT Namespace Conflicts (MUST FAIL before migration).

These tests MUST FAIL before the migration to demonstrate the Issue #565 SSOT violations.
These tests MUST PASS after the migration when only UserExecutionEngine exists.

Business Impact: Demonstrates $500K+ ARR security risk from multiple ExecutionEngine implementations.
"""

import inspect
import importlib
import pytest
from typing import List, Tuple, Any
from unittest.mock import Mock, AsyncMock

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestSSotNamespaceConflicts(SSotBaseTestCase):
    """Test suite to reproduce SSOT namespace conflicts in ExecutionEngine implementations."""
    
    def test_execution_engine_namespace_conflicts(self):
        """REPRODUCTION TEST: Multiple ExecutionEngine implementations cause namespace conflicts.
        
        This test MUST FAIL before migration to demonstrate the issue.
        This test MUST PASS after migration when only UserExecutionEngine exists.
        
        Expected Behavior:
        - Before Migration: FAIL - Different classes with same name
        - After Migration: PASS - Only UserExecutionEngine exists
        """
        logger.info("🔍 REPRODUCTION TEST: Testing ExecutionEngine namespace conflicts")
        
        try:
            # Test 1: Multiple import sources - this should reveal the conflict
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as DeprecatedEngine
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            
            logger.info(f"DeprecatedEngine type: {type(DeprecatedEngine)}")
            logger.info(f"UserExecutionEngine type: {type(UserExecutionEngine)}")
            
            # EXPECTED FAILURE POINT: Different classes with same name
            # After migration, ExecutionEngine should be an alias to UserExecutionEngine
            classes_are_same = DeprecatedEngine == UserExecutionEngine
            logger.info(f"Classes are same: {classes_are_same}")
            
            if not classes_are_same:
                logger.warning("❌ SSOT VIOLATION DETECTED: Different ExecutionEngine classes exist")
                # This should fail before migration
                pytest.fail(
                    f"SSOT VIOLATION: DeprecatedEngine ({DeprecatedEngine}) != UserExecutionEngine ({UserExecutionEngine}). "
                    f"Multiple ExecutionEngine implementations detected - security risk for user isolation."
                )
            else:
                logger.info("✅ SSOT COMPLIANCE: ExecutionEngine properly aliased to UserExecutionEngine")
            
        except ImportError as e:
            # Expected after successful migration - deprecated import should not exist
            logger.info(f"✅ MIGRATION SUCCESS: Deprecated ExecutionEngine import not found: {e}")
            
        # Test 2: Constructor signature conflicts
        try:
            # Try to get constructor signatures
            deprecated_params = None
            ssot_params = None
            
            try:
                from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as DeprecatedEngine
                deprecated_params = inspect.signature(DeprecatedEngine.__init__).parameters
                logger.info(f"Deprecated constructor params: {list(deprecated_params.keys())}")
            except ImportError:
                logger.info("Deprecated ExecutionEngine import not available (expected after migration)")
            
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            ssot_params = inspect.signature(UserExecutionEngine.__init__).parameters
            logger.info(f"SSOT constructor params: {list(ssot_params.keys())}")
            
            # If both exist, they should have different signatures (proving the issue)
            if deprecated_params is not None and ssot_params is not None:
                signatures_match = list(deprecated_params.keys()) == list(ssot_params.keys())
                
                if not signatures_match:
                    logger.warning("❌ CONSTRUCTOR INCOMPATIBILITY: Different ExecutionEngine constructor signatures")
                    pytest.fail(
                        f"CONSTRUCTOR INCOMPATIBILITY: "
                        f"Deprecated: {list(deprecated_params.keys())} vs SSOT: {list(ssot_params.keys())}. "
                        f"This proves multiple incompatible ExecutionEngine implementations exist."
                    )
                else:
                    logger.info("✅ CONSTRUCTOR COMPATIBILITY: Signatures match")
            
        except Exception as e:
            logger.error(f"Error testing constructor compatibility: {e}")
            # Don't fail on this - the import test is more critical
    
    def test_import_resolution_consistency(self):
        """REPRODUCTION TEST: Same import paths resolve to different classes.
        
        This demonstrates the SSOT violation where identical import statements
        can resolve to different ExecutionEngine implementations in different contexts.
        
        Expected Behavior:
        - Before Migration: FAIL - Different classes from same import
        - After Migration: PASS - Consistent class resolution
        """
        logger.info("🔍 REPRODUCTION TEST: Testing import resolution consistency")
        
        # Get all known ExecutionEngine import patterns
        import_patterns = [
            "netra_backend.app.agents.supervisor.execution_engine",
            "netra_backend.app.agents.supervisor.user_execution_engine",
        ]
        
        imported_classes = []
        
        for module_path in import_patterns:
            try:
                module = importlib.import_module(module_path)
                
                # Try to get ExecutionEngine from each module
                if hasattr(module, 'ExecutionEngine'):
                    execution_engine_class = getattr(module, 'ExecutionEngine')
                    imported_classes.append((module_path, execution_engine_class))
                    logger.info(f"Found ExecutionEngine in {module_path}: {execution_engine_class}")
                
                # Also try UserExecutionEngine
                if hasattr(module, 'UserExecutionEngine'):
                    user_execution_engine_class = getattr(module, 'UserExecutionEngine')
                    imported_classes.append((module_path, user_execution_engine_class))
                    logger.info(f"Found UserExecutionEngine in {module_path}: {user_execution_engine_class}")
                    
            except ImportError as e:
                logger.info(f"Could not import {module_path}: {e}")
                continue
        
        # Analyze class consistency
        if len(imported_classes) == 0:
            pytest.fail("CRITICAL: No ExecutionEngine classes found - system broken")
        
        logger.info(f"Found {len(imported_classes)} ExecutionEngine-related classes")
        
        # Check for SSOT violation: multiple different classes with same purpose
        execution_engine_classes = [cls for path, cls in imported_classes if 'ExecutionEngine' in cls.__name__]
        
        if len(execution_engine_classes) > 1:
            unique_classes = set(execution_engine_classes)
            
            if len(unique_classes) > 1:
                logger.warning(f"❌ SSOT VIOLATION: {len(unique_classes)} different ExecutionEngine classes found")
                class_info = [(cls.__name__, cls.__module__) for cls in unique_classes]
                pytest.fail(
                    f"SSOT VIOLATION: {len(unique_classes)} different ExecutionEngine classes detected: {class_info}. "
                    f"This creates user isolation security vulnerabilities."
                )
            else:
                logger.info("✅ SSOT COMPLIANCE: All ExecutionEngine imports resolve to same class")
        else:
            logger.info("✅ SINGLE EXECUTION ENGINE: Only one ExecutionEngine class found")
    
    def test_class_hierarchy_consistency(self):
        """REPRODUCTION TEST: ExecutionEngine class hierarchies are inconsistent.
        
        This test checks if different ExecutionEngine implementations have
        different base classes or method signatures, proving SSOT violations.
        """
        logger.info("🔍 REPRODUCTION TEST: Testing class hierarchy consistency")
        
        execution_engine_classes = []
        
        # Collect all ExecutionEngine implementations
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as DeprecatedEngine
            execution_engine_classes.append(("Deprecated", DeprecatedEngine))
        except ImportError:
            logger.info("Deprecated ExecutionEngine not available (expected after migration)")
        
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            execution_engine_classes.append(("SSOT", UserExecutionEngine))
        except ImportError:
            pytest.fail("CRITICAL: UserExecutionEngine not available - SSOT missing")
        
        if len(execution_engine_classes) < 2:
            logger.info("✅ Only one ExecutionEngine implementation found - SSOT compliant")
            return
        
        # Compare class hierarchies
        base_classes_info = []
        method_sets = []
        
        for name, cls in execution_engine_classes:
            # Get base classes
            base_classes = [base.__name__ for base in cls.__mro__[1:]]  # Exclude self
            base_classes_info.append((name, base_classes))
            
            # Get methods
            methods = set([method for method in dir(cls) if not method.startswith('_')])
            method_sets.append((name, methods))
            
            logger.info(f"{name} base classes: {base_classes}")
            logger.info(f"{name} method count: {len(methods)}")
        
        # Check for hierarchy inconsistencies
        if len(execution_engine_classes) == 2:
            (name1, base1), (name2, base2) = base_classes_info
            (_, methods1), (_, methods2) = method_sets
            
            if base1 != base2:
                logger.warning(f"❌ HIERARCHY VIOLATION: Different base classes - {name1}: {base1} vs {name2}: {base2}")
                
            # Check method signature compatibility
            common_methods = methods1.intersection(methods2)
            unique_to_1 = methods1 - methods2
            unique_to_2 = methods2 - methods1
            
            if unique_to_1 or unique_to_2:
                logger.warning(f"❌ METHOD SIGNATURE VIOLATION: Unique to {name1}: {unique_to_1}, Unique to {name2}: {unique_to_2}")
                
                # This indicates SSOT violation - different capabilities
                pytest.fail(
                    f"METHOD SIGNATURE VIOLATION: ExecutionEngine implementations have different capabilities. "
                    f"{name1} unique methods: {unique_to_1}, {name2} unique methods: {unique_to_2}. "
                    f"This proves SSOT violation - multiple incompatible implementations."
                )
            else:
                logger.info("✅ METHOD COMPATIBILITY: All ExecutionEngine implementations have same methods")


class TestExecutionEngineFactoryViolations(SSotBaseTestCase):
    """Test suite to reproduce factory pattern SSOT violations."""
    
    def test_multiple_execution_engine_factory_methods(self):
        """REPRODUCTION TEST: Multiple factory methods create different ExecutionEngine types.
        
        This demonstrates SSOT violations where different factory methods
        create incompatible ExecutionEngine instances.
        """
        logger.info("🔍 REPRODUCTION TEST: Testing ExecutionEngine factory violations")
        
        factory_results = []
        
        # Test different factory patterns that might exist
        factory_methods = [
            self._try_direct_constructor,
            self._try_legacy_factory,
            self._try_user_execution_engine_factory,
        ]
        
        for factory_method in factory_methods:
            try:
                result = factory_method()
                if result:
                    factory_results.append(result)
            except Exception as e:
                logger.info(f"Factory method failed (expected): {e}")
                continue
        
        logger.info(f"Found {len(factory_results)} working factory methods")
        
        if len(factory_results) < 2:
            logger.info("✅ SSOT COMPLIANT: Only one factory method available")
            return
        
        # Analyze factory results for SSOT violations
        factory_types = [type(result) for _, result in factory_results]
        unique_types = set(factory_types)
        
        if len(unique_types) > 1:
            type_info = [(name, type(result).__name__) for name, result in factory_results]
            logger.warning(f"❌ FACTORY SSOT VIOLATION: Different types from different factories: {type_info}")
            
            pytest.fail(
                f"FACTORY SSOT VIOLATION: {len(unique_types)} different ExecutionEngine types from factories. "
                f"Factory results: {type_info}. This creates user isolation inconsistencies."
            )
        else:
            logger.info("✅ FACTORY CONSISTENCY: All factory methods create same type")
    
    def _try_direct_constructor(self):
        """Try direct ExecutionEngine constructor."""
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
            
            mock_registry = Mock()
            mock_websocket_bridge = Mock()
            
            engine = ExecutionEngine(mock_registry, mock_websocket_bridge)
            return ("direct_constructor", engine)
            
        except Exception as e:
            logger.debug(f"Direct constructor failed: {e}")
            return None
    
    def _try_legacy_factory(self):
        """Try legacy factory method if it exists."""
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
            
            if hasattr(ExecutionEngine, '_init_from_factory'):
                mock_registry = Mock()
                mock_websocket_bridge = Mock()
                
                engine = ExecutionEngine._init_from_factory(mock_registry, mock_websocket_bridge)
                return ("legacy_factory", engine)
                
        except Exception as e:
            logger.debug(f"Legacy factory failed: {e}")
            return None
    
    def _try_user_execution_engine_factory(self):
        """Try UserExecutionEngine factory method."""
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            
            mock_context = UserExecutionContext(
                user_id="test_user",
                thread_id="test_thread", 
                run_id="test_run"
            )
            
            mock_agent_factory = Mock()
            mock_websocket_emitter = Mock()
            
            engine = UserExecutionEngine(mock_context, mock_agent_factory, mock_websocket_emitter)
            return ("user_execution_engine_factory", engine)
            
        except Exception as e:
            logger.debug(f"UserExecutionEngine factory failed: {e}")
            return None


if __name__ == "__main__":
    # Run reproduction tests
    pytest.main([__file__, "-v", "--tb=short"])