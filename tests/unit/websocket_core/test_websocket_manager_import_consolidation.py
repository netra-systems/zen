#!/usr/bin/env python
"""WebSocket Manager Import Consolidation Test - SSOT CRITICAL

PURPOSE: Validate only 1-2 canonical import paths exist for WebSocket management
EXPECTED BEHAVIOR: Test should FAIL initially, proving multiple import paths exist
SUCCESS CRITERIA: After SSOT consolidation, only single canonical import path remains

BUSINESS VALUE: Prevents configuration chaos and ensures Golden Path stability
FAILURE CONSEQUENCE: Multiple import paths cause race conditions and system instability

This test is designed to FAIL initially, proving the need for WebSocket SSOT consolidation.
After consolidation is complete, this test should PASS with a single canonical import path.

Test Categories:
1. Import Path Discovery - Find all WebSocket manager import paths
2. Import Path Validation - Verify imports work and return same type
3. Import Path Consolidation - Validate only 1-2 canonical paths exist
4. SSOT Compliance - Ensure all imports use the same underlying implementation

Expected Failure Modes (Before SSOT):
- Multiple working import paths detected (6+ paths)
- Different types returned from different import paths
- Import path inconsistencies across services
- Legacy factory patterns still accessible

Expected Success Criteria (After SSOT):
- Only 1 canonical import path exists
- All imports return identical WebSocketManager type
- No factory pattern imports available
- Consistent behavior across all import paths
"""

import asyncio
import importlib
import inspect
import sys
import os
from typing import List, Dict, Any, Set, Optional, Tuple
from unittest.mock import patch, AsyncMock
import pytest

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import test framework
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment
from shared.logging.unified_logging_ssot import get_logger

# Import types for validation
from shared.types.core_types import UserID, ensure_user_id, ensure_thread_id
from netra_backend.app.services.user_execution_context import UserExecutionContext

logger = get_logger(__name__)


class TestWebSocketManagerImportConsolidation(SSotAsyncTestCase):
    """
    SSOT Critical Test: WebSocket Manager Import Consolidation Validation

    This test validates that WebSocket manager imports are consolidated to a single
    source of truth, eliminating the fragmentation that causes Golden Path issues.

    EXPECTED TO FAIL INITIALLY: This test should fail before SSOT consolidation,
    proving that multiple import paths exist and cause system fragmentation.
    """

    def setup_method(self, method):
        """Setup test environment for WebSocket import validation."""
        super().setup_method(method)

        # Set environment for SSOT validation
        self.set_env_var("TESTING_SSOT_WEBSOCKET", "true")
        self.set_env_var("WEBSOCKET_IMPORT_VALIDATION", "strict")

        # Track discovered import paths
        self.discovered_import_paths = []
        self.working_import_paths = []
        self.failed_import_paths = []
        self.import_type_map = {}

        logger.info(f"🔍 SSOT TEST: {method.__name__ if method else 'unknown'}")
        logger.info("📍 PURPOSE: Validate WebSocket manager import consolidation")

    def test_websocket_manager_import_path_discovery(self):
        """
        CRITICAL: Discover all possible WebSocket manager import paths.

        This test scans the codebase for all possible ways to import WebSocket
        manager functionality. It should FAIL initially by finding multiple paths.

        EXPECTED TO FAIL: 6+ import paths currently exist (proving fragmentation)
        AFTER CONSOLIDATION: Should find only 1-2 canonical paths
        """
        logger.info("🔍 PHASE 1: Discovering WebSocket manager import paths")

        # Define all known WebSocket manager import patterns
        potential_import_paths = [
            # Primary SSOT candidates
            ("netra_backend.app.websocket_core.websocket_manager", "get_websocket_manager"),
            ("netra_backend.app.websocket_core.websocket_manager", "WebSocketManager"),

            # Unified manager paths
            ("netra_backend.app.websocket_core.unified_manager", "_UnifiedWebSocketManagerImplementation"),
            ("netra_backend.app.websocket_core.unified_manager", "UnifiedWebSocketManager"),

            # Factory patterns (should be deprecated)
            ("netra_backend.app.websocket_core.websocket_manager_factory", "get_websocket_manager_factory"),
            ("netra_backend.app.websocket_core.websocket_manager_factory", "WebSocketManagerFactory"),
            ("netra_backend.app.websocket_core.websocket_manager_factory", "create_websocket_manager"),

            # Legacy manager patterns
            ("netra_backend.app.websocket_core.manager", "WebSocketManager"),
            ("netra_backend.app.websocket_core.manager", "UnifiedWebSocketManager"),

            # Service-level imports
            ("netra_backend.app.websocket_core", "get_websocket_manager"),
            ("netra_backend.app.websocket_core", "WebSocketManager"),

            # __init__ level imports
            ("netra_backend.app.websocket_core.__init__", "get_websocket_manager"),

            # Potential compatibility imports
            ("netra_backend.app.core.websocket_manager", "get_websocket_manager"),
            ("netra_backend.app.services.websocket_manager", "WebSocketManager"),
        ]

        logger.info(f"🔍 Testing {len(potential_import_paths)} potential import paths")

        # Test each potential import path
        for module_path, attribute_name in potential_import_paths:
            try:
                logger.debug(f"📍 Testing: {module_path}.{attribute_name}")

                # Try to import the module
                module = importlib.import_module(module_path)

                # Check if the attribute exists
                if hasattr(module, attribute_name):
                    attribute = getattr(module, attribute_name)

                    # Record successful import
                    import_info = {
                        "module_path": module_path,
                        "attribute_name": attribute_name,
                        "attribute_type": type(attribute).__name__,
                        "is_callable": callable(attribute),
                        "is_class": inspect.isclass(attribute),
                        "is_function": inspect.isfunction(attribute),
                        "module_file": getattr(module, '__file__', 'Unknown')
                    }

                    self.discovered_import_paths.append(f"{module_path}.{attribute_name}")
                    self.working_import_paths.append(import_info)
                    self.import_type_map[f"{module_path}.{attribute_name}"] = type(attribute)

                    logger.info(f"✅ FOUND: {module_path}.{attribute_name} -> {type(attribute).__name__}")

                else:
                    self.failed_import_paths.append(f"{module_path}.{attribute_name} (attribute not found)")

            except ImportError as e:
                self.failed_import_paths.append(f"{module_path}.{attribute_name} (import failed: {e})")
                logger.debug(f"❌ Import failed: {module_path}.{attribute_name} - {e}")
            except Exception as e:
                self.failed_import_paths.append(f"{module_path}.{attribute_name} (error: {e})")
                logger.warning(f"⚠️ Error testing: {module_path}.{attribute_name} - {e}")

        # Log discovery results
        logger.info(f"📊 DISCOVERY RESULTS:")
        logger.info(f"   Working imports: {len(self.working_import_paths)}")
        logger.info(f"   Failed imports: {len(self.failed_import_paths)}")
        logger.info(f"   Total tested: {len(potential_import_paths)}")

        # Validate import path consolidation - THIS SHOULD FAIL INITIALLY
        max_allowed_paths = 2  # Allow for 1 main + 1 compatibility layer

        if len(self.working_import_paths) > max_allowed_paths:
            failure_message = (
                f"❌ WEBSOCKET SSOT VIOLATION: Too many working import paths found!\n"
                f"   Found: {len(self.working_import_paths)} working imports\n"
                f"   Maximum allowed: {max_allowed_paths}\n"
                f"   Working paths: {[info['module_path'] + '.' + info['attribute_name'] for info in self.working_import_paths]}\n"
                f"\n🚨 THIS PROVES WEBSOCKET FRAGMENTATION - SSOT CONSOLIDATION REQUIRED!"
            )

            # Log all working imports for analysis
            logger.error(failure_message)
            for import_info in self.working_import_paths:
                logger.error(f"   - {import_info['module_path']}.{import_info['attribute_name']} ({import_info['attribute_type']})")

            # This assertion should FAIL before SSOT consolidation
            self.fail(failure_message)

        else:
            # If we get here, SSOT consolidation was successful
            logger.info("✅ SSOT SUCCESS: WebSocket imports are properly consolidated")
            logger.info(f"   Found {len(self.working_import_paths)} import paths (within limit)")

            # Validate that remaining imports are canonical
            canonical_patterns = [
                "netra_backend.app.websocket_core.websocket_manager.get_websocket_manager",
                "netra_backend.app.websocket_core.websocket_manager.WebSocketManager"
            ]

            for import_info in self.working_import_paths:
                full_path = f"{import_info['module_path']}.{import_info['attribute_name']}"
                self.assertIn(
                    full_path,
                    canonical_patterns,
                    f"Non-canonical import path found: {full_path}"
                )

    async def test_websocket_manager_import_consistency(self):
        """
        CRITICAL: Validate that all working imports return consistent types.

        This test ensures that different import paths don't return different
        WebSocket manager implementations, which would cause runtime errors.

        EXPECTED TO FAIL: Different imports return different types (proving fragmentation)
        AFTER CONSOLIDATION: All imports return same underlying implementation
        """
        logger.info("🔍 PHASE 2: Validating WebSocket manager import consistency")

        # First discover imports (reuse logic from previous test)
        if not self.working_import_paths:
            self.test_websocket_manager_import_path_discovery()

        if len(self.working_import_paths) < 2:
            logger.warning("⚠️ Less than 2 working imports found - cannot test consistency")
            return

        # Test consistency across all working imports
        manager_instances = {}
        manager_types = set()

        # Create test user context for manager creation
        user_context = UserExecutionContext(
            user_id=ensure_user_id("ssot_test_user"),
            thread_id=ensure_thread_id("ssot_test_thread"),
            session_id="ssot_test_session"
        )

        for import_info in self.working_import_paths:
            module_path = import_info['module_path']
            attribute_name = import_info['attribute_name']

            try:
                # Import the module and get the attribute
                module = importlib.import_module(module_path)
                attribute = getattr(module, attribute_name)

                # Handle different types of imports
                manager_instance = None

                if import_info['is_function'] and 'get_websocket_manager' in attribute_name:
                    # Function that returns manager
                    if asyncio.iscoroutinefunction(attribute):
                        manager_instance = await attribute(user_context=user_context)
                    else:
                        manager_instance = attribute(user_context=user_context)

                elif import_info['is_class'] and 'Manager' in attribute_name:
                    # Manager class - try to instantiate
                    if 'Factory' not in attribute_name:
                        try:
                            # Try with user context
                            manager_instance = attribute(user_context=user_context)
                        except TypeError:
                            # Try without parameters
                            manager_instance = attribute()
                    else:
                        # Factory class - skip for now
                        logger.warning(f"⚠️ Skipping factory class: {module_path}.{attribute_name}")
                        continue

                if manager_instance is not None:
                    import_path = f"{module_path}.{attribute_name}"
                    manager_instances[import_path] = manager_instance
                    manager_types.add(type(manager_instance).__name__)

                    logger.info(f"✅ Created manager from: {import_path} -> {type(manager_instance).__name__}")

            except Exception as e:
                logger.warning(f"⚠️ Failed to create manager from {module_path}.{attribute_name}: {e}")

        # Validate consistency - THIS SHOULD FAIL INITIALLY
        if len(manager_types) > 1:
            failure_message = (
                f"❌ WEBSOCKET TYPE INCONSISTENCY: Different imports return different types!\n"
                f"   Types found: {list(manager_types)}\n"
                f"   Import paths and their types:\n"
            )

            for import_path, instance in manager_instances.items():
                failure_message += f"     - {import_path} -> {type(instance).__name__}\n"

            failure_message += f"\n🚨 THIS PROVES WEBSOCKET TYPE FRAGMENTATION - SSOT CONSOLIDATION REQUIRED!"

            logger.error(failure_message)

            # This assertion should FAIL before SSOT consolidation
            self.fail(failure_message)

        elif len(manager_types) == 1:
            # Success case - all imports return same type
            manager_type = list(manager_types)[0]
            logger.info(f"✅ CONSISTENCY SUCCESS: All imports return {manager_type}")

            # Validate that the type is the expected SSOT type
            expected_ssot_types = [
                "UnifiedWebSocketManager",
                "_UnifiedWebSocketManagerImplementation",
                "WebSocketManager"
            ]

            self.assertIn(
                manager_type,
                expected_ssot_types,
                f"Manager type {manager_type} is not an expected SSOT type"
            )

        else:
            logger.warning("⚠️ No manager instances could be created - cannot test consistency")

    def test_websocket_manager_factory_deprecation(self):
        """
        CRITICAL: Validate that factory patterns are properly deprecated.

        Factory patterns were the source of user isolation issues and should
        be eliminated in favor of direct manager instantiation.

        EXPECTED TO FAIL: Factory imports still accessible (proving legacy patterns exist)
        AFTER CONSOLIDATION: Factory patterns should be deprecated or removed
        """
        logger.info("🔍 PHASE 3: Validating factory pattern deprecation")

        # Factory patterns that should be deprecated
        deprecated_factory_patterns = [
            "netra_backend.app.websocket_core.websocket_manager_factory.get_websocket_manager_factory",
            "netra_backend.app.websocket_core.websocket_manager_factory.WebSocketManagerFactory",
            "netra_backend.app.websocket_core.websocket_manager_factory.create_websocket_manager",
        ]

        active_factory_patterns = []
        deprecated_factory_patterns_found = []

        for factory_pattern in deprecated_factory_patterns:
            try:
                module_path, attribute_name = factory_pattern.rsplit('.', 1)
                module = importlib.import_module(module_path)

                if hasattr(module, attribute_name):
                    attribute = getattr(module, attribute_name)

                    # Check if properly deprecated
                    is_deprecated = (
                        hasattr(attribute, '__deprecated__') and attribute.__deprecated__ or
                        hasattr(attribute, '__doc__') and attribute.__doc__ and 'DEPRECATED' in attribute.__doc__
                    )

                    if is_deprecated:
                        deprecated_factory_patterns_found.append(factory_pattern)
                        logger.info(f"✅ DEPRECATED: {factory_pattern}")
                    else:
                        active_factory_patterns.append(factory_pattern)
                        logger.warning(f"⚠️ ACTIVE FACTORY: {factory_pattern}")

            except ImportError:
                # Factory doesn't exist - this is good for SSOT
                logger.info(f"✅ REMOVED: {factory_pattern} (import failed)")
            except Exception as e:
                logger.warning(f"⚠️ Error checking {factory_pattern}: {e}")

        # Validate factory deprecation - THIS MAY FAIL INITIALLY
        if active_factory_patterns:
            failure_message = (
                f"❌ WEBSOCKET FACTORY DEPRECATION FAILURE: Active factory patterns found!\n"
                f"   Active factories: {active_factory_patterns}\n"
                f"   These patterns should be deprecated or removed for SSOT compliance.\n"
                f"\n🚨 THIS PROVES LEGACY FACTORY PATTERNS STILL ACTIVE - DEPRECATION REQUIRED!"
            )

            logger.error(failure_message)

            # This assertion should FAIL if factories are still active
            self.fail(failure_message)

        else:
            logger.info("✅ FACTORY DEPRECATION SUCCESS: No active factory patterns found")
            if deprecated_factory_patterns_found:
                logger.info(f"   Properly deprecated: {deprecated_factory_patterns_found}")

    def test_websocket_manager_ssot_canonical_path(self):
        """
        CRITICAL: Validate that a single canonical import path is established.

        After SSOT consolidation, there should be one primary import path that
        all other imports delegate to or import from.

        EXPECTED AFTER CONSOLIDATION: Single canonical path exists and works
        """
        logger.info("🔍 PHASE 4: Validating canonical SSOT import path")

        # The canonical SSOT import path (after consolidation)
        canonical_path = "netra_backend.app.websocket_core.websocket_manager.get_websocket_manager"

        try:
            # Import the canonical path
            module = importlib.import_module("netra_backend.app.websocket_core.websocket_manager")
            get_manager_func = getattr(module, "get_websocket_manager")

            # Validate it's the correct type
            self.assertTrue(callable(get_manager_func), "Canonical get_websocket_manager must be callable")
            self.assertTrue(asyncio.iscoroutinefunction(get_manager_func), "Canonical function must be async")

            # Test that it works
            user_context = UserExecutionContext(
                user_id=ensure_user_id("canonical_test_user"),
                thread_id=ensure_thread_id("canonical_test_thread"),
                session_id="canonical_test_session"
            )

            manager = await get_manager_func(user_context=user_context)
            self.assertIsNotNone(manager, "Canonical path must return valid manager")

            # Validate manager type
            manager_type = type(manager).__name__
            expected_types = ["UnifiedWebSocketManager", "_UnifiedWebSocketManagerImplementation", "WebSocketManager"]
            self.assertIn(manager_type, expected_types, f"Manager type {manager_type} not expected SSOT type")

            logger.info(f"✅ CANONICAL PATH SUCCESS: {canonical_path} -> {manager_type}")

        except ImportError as e:
            self.fail(f"❌ CANONICAL PATH FAILURE: Cannot import {canonical_path}: {e}")
        except Exception as e:
            self.fail(f"❌ CANONICAL PATH ERROR: {canonical_path} failed: {e}")

    def teardown_method(self, method):
        """Teardown with comprehensive reporting."""
        try:
            # Log final test results
            logger.info("📊 WEBSOCKET IMPORT CONSOLIDATION TEST RESULTS:")
            logger.info(f"   Total import paths discovered: {len(self.discovered_import_paths)}")
            logger.info(f"   Working import paths: {len(self.working_import_paths)}")
            logger.info(f"   Failed import paths: {len(self.failed_import_paths)}")
            logger.info(f"   Unique manager types: {len(set(self.import_type_map.values()))}")

            # Record metrics
            self.record_metric("import_paths_discovered", len(self.discovered_import_paths))
            self.record_metric("working_import_paths", len(self.working_import_paths))
            self.record_metric("failed_import_paths", len(self.failed_import_paths))
            self.record_metric("manager_types_found", len(set(self.import_type_map.values())))

            if len(self.working_import_paths) <= 2:
                logger.info("✅ SSOT CONSOLIDATION SUCCESS: Import paths properly consolidated")
                self.record_metric("ssot_consolidation_status", "SUCCESS")
            else:
                logger.error("❌ SSOT CONSOLIDATION NEEDED: Too many import paths found")
                self.record_metric("ssot_consolidation_status", "CONSOLIDATION_REQUIRED")

        except Exception as e:
            logger.error(f"❌ TEARDOWN ERROR: {str(e)}")

        finally:
            super().teardown_method(method)


if __name__ == "__main__":
    """Run WebSocket manager import consolidation test directly."""
    import pytest

    logger.info("🚨 RUNNING WEBSOCKET MANAGER IMPORT CONSOLIDATION TEST")
    logger.info("📍 PURPOSE: Validate SSOT consolidation and detect import fragmentation")

    # Run the test
    pytest.main([__file__, "-v", "-s"])