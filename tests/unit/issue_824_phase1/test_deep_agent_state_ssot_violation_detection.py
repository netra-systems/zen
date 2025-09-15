"""Test DeepAgentState SSOT Violation Detection - Issue #871

CRITICAL: P0 DeepAgentState duplicate definitions blocking Golden Path.

These tests MUST FAIL initially to prove the SSOT violation exists:
1. Import conflict validation (should fail with current violation)
2. State compatibility verification (validate functional equivalence)
3. Golden Path independence (verify WebSocket independence)

Business Value: $500K+ ARR Golden Path protection through SSOT compliance.
Purpose: Detect duplicate DeepAgentState definitions preventing WebSocket reliability.

EXPECTED BEHAVIOR: All tests should FAIL initially, proving violation exists.
After remediation: All tests should PASS, confirming SSOT consolidation.
"""

import pytest
import sys
import importlib
import inspect
from typing import Dict, List, Set, Any, Optional, Type
from pathlib import Path

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


@pytest.mark.unit
class TestDeepAgentStateImportConflictValidation(SSotAsyncTestCase):
    """Test import conflict validation - MUST FAIL initially to prove violation exists."""

    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)

        # SSOT canonical source (should be the only one after remediation)
        self.canonical_import_path = "netra_backend.app.schemas.agent_models"
        self.canonical_class_name = "DeepAgentState"

        # DEPRECATED source (should cause conflicts - violation exists)
        self.deprecated_import_path = "netra_backend.app.agents.state"

        # Import paths that should resolve to same class (after remediation)
        self.import_paths_to_test = [
            f"{self.canonical_import_path}.{self.canonical_class_name}",
            f"{self.deprecated_import_path}.{self.canonical_class_name}",
        ]

    def _import_class_from_path(self, import_path: str) -> Optional[Type]:
        """Import a class from a given import path."""
        try:
            module_path, class_name = import_path.rsplit('.', 1)
            module = importlib.import_module(module_path)

            if hasattr(module, class_name):
                return getattr(module, class_name)
            else:
                logger.error(f"Class {class_name} not found in module {module_path}")
                return None
        except ImportError as e:
            logger.error(f"Failed to import {import_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error importing {import_path}: {e}")
            return None

    def test_deep_agent_state_import_conflict_detection(self):
        """
        TEST THAT MUST FAIL: Detect import conflicts between duplicate definitions.

        EXPECTED FAILURE: Should detect that two different DeepAgentState classes exist.
        This proves the SSOT violation exists and needs remediation.
        """
        logger.info("Testing DeepAgentState import conflict detection...")

        # Import both versions
        canonical_class = self._import_class_from_path(f"{self.canonical_import_path}.{self.canonical_class_name}")
        deprecated_class = self._import_class_from_path(f"{self.deprecated_import_path}.{self.canonical_class_name}")

        # Both should exist (proving violation)
        self.assertIsNotNone(canonical_class, "Canonical DeepAgentState should exist")
        self.assertIsNotNone(deprecated_class, "Deprecated DeepAgentState should exist")

        # CRITICAL TEST: These should be the SAME class after SSOT remediation
        # This test MUST FAIL initially, proving violation exists
        self.assertEqual(
            canonical_class,
            deprecated_class,
            f"SSOT VIOLATION DETECTED: DeepAgentState classes are different! "
            f"Canonical: {canonical_class} vs Deprecated: {deprecated_class}. "
            f"This proves duplicate definitions exist and need consolidation."
        )

        # Verify they have the same module path (should fail initially)
        canonical_module = canonical_class.__module__
        deprecated_module = deprecated_class.__module__

        self.assertEqual(
            canonical_module,
            deprecated_module,
            f"SSOT VIOLATION: DeepAgentState defined in multiple modules! "
            f"Canonical: {canonical_module} vs Deprecated: {deprecated_module}"
        )

    def test_deep_agent_state_single_source_validation(self):
        """
        TEST THAT MUST FAIL: Validate only one DeepAgentState definition exists.

        EXPECTED FAILURE: Should find multiple definitions, proving SSOT violation.
        """
        logger.info("Testing DeepAgentState single source validation...")

        # Search for all DeepAgentState definitions in the codebase
        definitions_found = []

        # Check canonical location
        try:
            canonical_module = importlib.import_module(self.canonical_import_path)
            if hasattr(canonical_module, self.canonical_class_name):
                canonical_class = getattr(canonical_module, self.canonical_class_name)
                definitions_found.append({
                    'module': self.canonical_import_path,
                    'class': canonical_class,
                    'file': inspect.getfile(canonical_class)
                })
        except Exception as e:
            logger.error(f"Error checking canonical source: {e}")

        # Check deprecated location
        try:
            deprecated_module = importlib.import_module(self.deprecated_import_path)
            if hasattr(deprecated_module, self.canonical_class_name):
                deprecated_class = getattr(deprecated_module, self.canonical_class_name)
                definitions_found.append({
                    'module': self.deprecated_import_path,
                    'class': deprecated_class,
                    'file': inspect.getfile(deprecated_class)
                })
        except Exception as e:
            logger.error(f"Error checking deprecated source: {e}")

        # Log all definitions found
        logger.info(f"DeepAgentState definitions found: {len(definitions_found)}")
        for i, definition in enumerate(definitions_found):
            logger.info(f"  {i+1}. Module: {definition['module']}, File: {definition['file']}")

        # CRITICAL ASSERTION: Should only be ONE definition (will fail initially)
        self.assertEqual(
            len(definitions_found),
            1,
            f"SSOT VIOLATION: Found {len(definitions_found)} DeepAgentState definitions! "
            f"Expected 1 (canonical only). Definitions: {[d['module'] for d in definitions_found]}. "
            f"This proves multiple definitions exist and violate SSOT principle."
        )

    def test_deep_agent_state_field_consistency_validation(self):
        """
        TEST THAT MUST FAIL: Validate field consistency between definitions.

        EXPECTED FAILURE: Should find field differences, proving inconsistent behavior.
        """
        logger.info("Testing DeepAgentState field consistency validation...")

        # Import both versions
        canonical_class = self._import_class_from_path(f"{self.canonical_import_path}.{self.canonical_class_name}")
        deprecated_class = self._import_class_from_path(f"{self.deprecated_import_path}.{self.canonical_class_name}")

        self.assertIsNotNone(canonical_class, "Canonical DeepAgentState should exist")
        self.assertIsNotNone(deprecated_class, "Deprecated DeepAgentState should exist")

        # Get field definitions from both classes
        canonical_fields = set(canonical_class.model_fields.keys()) if hasattr(canonical_class, 'model_fields') else set()
        deprecated_fields = set(deprecated_class.model_fields.keys()) if hasattr(deprecated_class, 'model_fields') else set()

        logger.info(f"Canonical fields: {sorted(canonical_fields)}")
        logger.info(f"Deprecated fields: {sorted(deprecated_fields)}")

        # Check for missing fields in canonical (fields only in deprecated)
        missing_in_canonical = deprecated_fields - canonical_fields
        if missing_in_canonical:
            logger.warning(f"Fields missing in canonical: {missing_in_canonical}")

        # Check for extra fields in canonical (fields only in canonical)
        extra_in_canonical = canonical_fields - deprecated_fields
        if extra_in_canonical:
            logger.warning(f"Extra fields in canonical: {extra_in_canonical}")

        # CRITICAL ASSERTION: Field sets should be identical for SSOT compliance
        # This test MUST FAIL initially if definitions are different
        self.assertEqual(
            canonical_fields,
            deprecated_fields,
            f"SSOT VIOLATION: DeepAgentState field definitions are inconsistent! "
            f"Missing in canonical: {missing_in_canonical}, "
            f"Extra in canonical: {extra_in_canonical}. "
            f"This proves definitions have different behaviors and violate SSOT."
        )


@pytest.mark.unit
class TestDeepAgentStateCompatibilityVerification(SSotAsyncTestCase):
    """Test state compatibility verification - MUST FAIL initially to prove differences exist."""

    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)
        self.canonical_import_path = "netra_backend.app.schemas.agent_models"
        self.deprecated_import_path = "netra_backend.app.agents.state"
        self.class_name = "DeepAgentState"

    def _create_test_state_data(self) -> Dict[str, Any]:
        """Create test state data for compatibility testing."""
        return {
            'user_request': 'test_request',
            'chat_thread_id': 'test_thread_123',
            'user_id': 'test_user_456',
        }

    def test_deep_agent_state_instantiation_compatibility(self):
        """
        TEST THAT MUST FAIL: Validate instantiation compatibility between definitions.

        EXPECTED FAILURE: Should find differences in how instances are created.
        """
        logger.info("Testing DeepAgentState instantiation compatibility...")

        # Import both classes
        canonical_module = importlib.import_module(self.canonical_import_path)
        deprecated_module = importlib.import_module(self.deprecated_import_path)

        canonical_class = getattr(canonical_module, self.class_name)
        deprecated_class = getattr(deprecated_module, self.class_name)

        test_data = self._create_test_state_data()

        # Try to create instances with same data
        canonical_instance = None
        deprecated_instance = None
        canonical_error = None
        deprecated_error = None

        try:
            canonical_instance = canonical_class(**test_data)
            logger.info(f"Canonical instance created: {type(canonical_instance)}")
        except Exception as e:
            canonical_error = str(e)
            logger.error(f"Canonical instantiation failed: {e}")

        try:
            deprecated_instance = deprecated_class(**test_data)
            logger.info(f"Deprecated instance created: {type(deprecated_instance)}")
        except Exception as e:
            deprecated_error = str(e)
            logger.error(f"Deprecated instantiation failed: {e}")

        # Both should be creatable with same data for compatibility
        self.assertIsNone(canonical_error, f"Canonical instantiation should succeed: {canonical_error}")
        self.assertIsNone(deprecated_error, f"Deprecated instantiation should succeed: {deprecated_error}")

        # CRITICAL TEST: Instances should have identical behavior
        # This may fail if they have different fields or validation rules
        if canonical_instance and deprecated_instance:
            canonical_dict = canonical_instance.model_dump() if hasattr(canonical_instance, 'model_dump') else dict(canonical_instance)
            deprecated_dict = deprecated_instance.model_dump() if hasattr(deprecated_instance, 'model_dump') else dict(deprecated_instance)

            # Compare the dictionaries (may fail if definitions are different)
            self.assertEqual(
                canonical_dict,
                deprecated_dict,
                f"COMPATIBILITY VIOLATION: Instances created from same data have different representations! "
                f"Canonical: {canonical_dict} vs Deprecated: {deprecated_dict}. "
                f"This proves definitions are functionally different."
            )

    def test_deep_agent_state_method_compatibility(self):
        """
        TEST THAT MUST FAIL: Validate method compatibility between definitions.

        EXPECTED FAILURE: Should find method differences between classes.
        """
        logger.info("Testing DeepAgentState method compatibility...")

        # Import both classes
        canonical_module = importlib.import_module(self.canonical_import_path)
        deprecated_module = importlib.import_module(self.deprecated_import_path)

        canonical_class = getattr(canonical_module, self.class_name)
        deprecated_class = getattr(deprecated_module, self.class_name)

        # Get methods from both classes
        canonical_methods = set(dir(canonical_class))
        deprecated_methods = set(dir(deprecated_class))

        # Filter to public methods (exclude private/magic methods)
        canonical_public = {m for m in canonical_methods if not m.startswith('_')}
        deprecated_public = {m for m in deprecated_methods if not m.startswith('_')}

        logger.info(f"Canonical public methods: {sorted(canonical_public)}")
        logger.info(f"Deprecated public methods: {sorted(deprecated_public)}")

        # Check for method differences
        missing_in_canonical = deprecated_public - canonical_public
        extra_in_canonical = canonical_public - deprecated_public

        if missing_in_canonical:
            logger.warning(f"Methods missing in canonical: {missing_in_canonical}")
        if extra_in_canonical:
            logger.warning(f"Extra methods in canonical: {extra_in_canonical}")

        # CRITICAL ASSERTION: Method sets should be identical for compatibility
        # This test MUST FAIL initially if classes have different interfaces
        self.assertEqual(
            canonical_public,
            deprecated_public,
            f"METHOD COMPATIBILITY VIOLATION: DeepAgentState classes have different public interfaces! "
            f"Missing in canonical: {missing_in_canonical}, "
            f"Extra in canonical: {extra_in_canonical}. "
            f"This proves API incompatibility between definitions."
        )


@pytest.mark.unit
class TestDeepAgentStateGoldenPathIndependence(SSotAsyncTestCase):
    """Test Golden Path independence - MUST FAIL initially to prove WebSocket dependency issues."""

    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)
        self.canonical_import_path = "netra_backend.app.schemas.agent_models"
        self.deprecated_import_path = "netra_backend.app.agents.state"
        self.class_name = "DeepAgentState"

    def test_deep_agent_state_websocket_independence_validation(self):
        """
        TEST THAT MUST FAIL: Validate WebSocket independence between definitions.

        EXPECTED FAILURE: Should find WebSocket coupling differences affecting Golden Path.
        This is critical for $500K+ ARR Golden Path reliability.
        """
        logger.info("Testing DeepAgentState WebSocket independence validation...")

        # Import both classes
        canonical_module = importlib.import_module(self.canonical_import_path)
        deprecated_module = importlib.import_module(self.deprecated_import_path)

        canonical_class = getattr(canonical_module, self.class_name)
        deprecated_class = getattr(deprecated_module, self.class_name)

        # Create instances
        test_data = {
            'user_request': 'test_websocket_independence',
            'chat_thread_id': 'websocket_test_123',
            'user_id': 'websocket_user_456',
        }

        canonical_instance = canonical_class(**test_data)
        deprecated_instance = deprecated_class(**test_data)

        # Test for WebSocket-specific dependencies by checking imports
        canonical_module_source = inspect.getsource(canonical_module)
        deprecated_module_source = inspect.getsource(deprecated_module)

        # Check for WebSocket imports (should be consistent)
        websocket_imports = ['websocket', 'WebSocket', 'ws', 'socket']

        canonical_has_websocket = any(ws_term in canonical_module_source for ws_term in websocket_imports)
        deprecated_has_websocket = any(ws_term in deprecated_module_source for ws_term in websocket_imports)

        logger.info(f"Canonical has WebSocket references: {canonical_has_websocket}")
        logger.info(f"Deprecated has WebSocket references: {deprecated_has_websocket}")

        # CRITICAL TEST: WebSocket coupling should be identical for Golden Path consistency
        # This test MUST FAIL initially if coupling is different
        self.assertEqual(
            canonical_has_websocket,
            deprecated_has_websocket,
            f"GOLDEN PATH RISK: DeepAgentState definitions have different WebSocket coupling! "
            f"Canonical coupling: {canonical_has_websocket}, "
            f"Deprecated coupling: {deprecated_has_websocket}. "
            f"This could affect $500K+ ARR WebSocket reliability and Golden Path consistency."
        )

    def test_deep_agent_state_factory_pattern_consistency(self):
        """
        TEST THAT MUST FAIL: Validate factory pattern consistency between definitions.

        EXPECTED FAILURE: Should find factory pattern differences affecting user isolation.
        """
        logger.info("Testing DeepAgentState factory pattern consistency...")

        # Import both classes
        canonical_module = importlib.import_module(self.canonical_import_path)
        deprecated_module = importlib.import_module(self.deprecated_import_path)

        canonical_class = getattr(canonical_module, self.class_name)
        deprecated_class = getattr(deprecated_module, self.class_name)

        # Check if classes have factory methods or class methods
        canonical_class_methods = [name for name, method in inspect.getmembers(canonical_class)
                                 if inspect.ismethod(method) or isinstance(method, classmethod)]
        deprecated_class_methods = [name for name, method in inspect.getmembers(deprecated_class)
                                  if inspect.ismethod(method) or isinstance(method, classmethod)]

        logger.info(f"Canonical class methods: {canonical_class_methods}")
        logger.info(f"Deprecated class methods: {deprecated_class_methods}")

        # Look for factory-pattern methods
        factory_patterns = ['create', 'build', 'from_', 'new', 'factory']

        canonical_factory_methods = [method for method in canonical_class_methods
                                   if any(pattern in method.lower() for pattern in factory_patterns)]
        deprecated_factory_methods = [method for method in deprecated_class_methods
                                    if any(pattern in method.lower() for pattern in factory_patterns)]

        logger.info(f"Canonical factory methods: {canonical_factory_methods}")
        logger.info(f"Deprecated factory methods: {deprecated_factory_methods}")

        # CRITICAL TEST: Factory patterns should be consistent for user isolation
        # This test MUST FAIL initially if patterns are different
        self.assertEqual(
            set(canonical_factory_methods),
            set(deprecated_factory_methods),
            f"FACTORY PATTERN INCONSISTENCY: DeepAgentState definitions have different factory patterns! "
            f"Canonical: {canonical_factory_methods}, "
            f"Deprecated: {deprecated_factory_methods}. "
            f"This could affect user isolation and multi-tenant safety."
        )

    def test_deep_agent_state_thread_safety_consistency(self):
        """
        TEST THAT MUST FAIL: Validate thread safety consistency between definitions.

        EXPECTED FAILURE: Should find thread safety differences affecting concurrent users.
        """
        logger.info("Testing DeepAgentState thread safety consistency...")

        # Import both classes
        canonical_module = importlib.import_module(self.canonical_import_path)
        deprecated_module = importlib.import_module(self.deprecated_import_path)

        canonical_class = getattr(canonical_module, self.class_name)
        deprecated_class = getattr(deprecated_module, self.class_name)

        # Check for class-level attributes (potential shared state issues)
        canonical_class_attrs = [attr for attr in dir(canonical_class)
                               if not attr.startswith('_') and not callable(getattr(canonical_class, attr))]
        deprecated_class_attrs = [attr for attr in dir(deprecated_class)
                                if not attr.startswith('_') and not callable(getattr(deprecated_class, attr))]

        logger.info(f"Canonical class attributes: {canonical_class_attrs}")
        logger.info(f"Deprecated class attributes: {deprecated_class_attrs}")

        # Check for mutable defaults (thread safety risk)
        test_data = {'user_request': 'thread_safety_test'}

        canonical_instance1 = canonical_class(**test_data)
        canonical_instance2 = canonical_class(**test_data)

        deprecated_instance1 = deprecated_class(**test_data)
        deprecated_instance2 = deprecated_class(**test_data)

        # Test for shared mutable state by modifying one instance
        if hasattr(canonical_instance1, 'metadata') and hasattr(canonical_instance1.metadata, 'update'):
            try:
                canonical_instance1.metadata.update({'test_key': 'test_value'})
                canonical_shared_state = hasattr(canonical_instance2.metadata, 'test_key') if hasattr(canonical_instance2, 'metadata') else False
            except:
                canonical_shared_state = False
        else:
            canonical_shared_state = False

        if hasattr(deprecated_instance1, 'metadata') and hasattr(deprecated_instance1.metadata, 'update'):
            try:
                deprecated_instance1.metadata.update({'test_key': 'test_value'})
                deprecated_shared_state = hasattr(deprecated_instance2.metadata, 'test_key') if hasattr(deprecated_instance2, 'metadata') else False
            except:
                deprecated_shared_state = False
        else:
            deprecated_shared_state = False

        logger.info(f"Canonical shared state detected: {canonical_shared_state}")
        logger.info(f"Deprecated shared state detected: {deprecated_shared_state}")

        # CRITICAL TEST: Thread safety behavior should be identical
        # This test MUST FAIL initially if thread safety differs
        self.assertEqual(
            canonical_shared_state,
            deprecated_shared_state,
            f"THREAD SAFETY INCONSISTENCY: DeepAgentState definitions have different thread safety behavior! "
            f"Canonical shared state: {canonical_shared_state}, "
            f"Deprecated shared state: {deprecated_shared_state}. "
            f"This could cause race conditions and data corruption in multi-user scenarios."
        )


if __name__ == "__main__":
    import unittest

    # Run all tests
    unittest.main(verbosity=2)