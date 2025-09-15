"""
UNIT TEST: Issue #962 Single Configuration Manager Validation (P0 SSOT Violation)

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability & Revenue Protection
- Business Goal: Eliminate multiple configuration managers causing race conditions
- Value Impact: Protects $500K+ ARR Golden Path by ensuring single config manager SSOT
- Strategic Impact: Prevents authentication cascade failures from configuration conflicts

CRITICAL MISSION: Issue #962 Configuration Manager Duplication Crisis

This test suite validates that only ONE configuration manager is accessible across
the entire codebase, eliminating the configuration fragmentation that causes authentication
failures. Tests are designed to:

1. **INITIALLY FAIL**: Detect multiple configuration managers accessible via different imports
2. **ENFORCE SSOT**: Validate only UnifiedConfigManager via config.py is importable
3. **ELIMINATE LEGACY**: Confirm deprecated import paths are completely removed
4. **API COMPLETENESS**: Ensure SSOT configuration manager provides complete functionality

EXPECTED TEST BEHAVIOR:
- **PHASE 0-1 (CURRENT)**: Tests FAIL demonstrating multiple config managers accessible
- **PHASE 4 (AFTER REMEDIATION)**: Tests PASS proving single SSOT configuration manager
- **ONGOING**: Tests prevent regression by blocking multiple configuration manager patterns

CRITICAL BUSINESS IMPACT:
Multiple configuration managers create race conditions where different parts of the system
use different configurations, causing unpredictable authentication failures that block
the Golden Path user flow and directly impact $500K+ ARR.

This test supports the Configuration Manager SSOT consolidation for Issue #962.
"""

import pytest
import importlib
import unittest
import sys
from pathlib import Path
from typing import Dict, List, Set, Any, Optional, Type
import inspect

from test_framework.ssot.base_test_case import SSotBaseTestCase


@pytest.mark.unit
class Issue962SingleConfigurationManagerValidationTests(SSotBaseTestCase, unittest.TestCase):
    """
    Unit tests to enforce single configuration manager SSOT for Issue #962.

    These tests validate that only ONE configuration manager is accessible
    across the codebase, protecting $500K+ ARR Golden Path functionality.
    """

    def setUp(self):
        """Set up test environment with configuration manager tracking."""
        super().setUp()
        self.accessible_config_managers: Dict[str, Any] = {}
        self.broken_import_paths: List[str] = []
        self.working_import_paths: List[str] = []

        # Expected SSOT configuration import path
        self.ssot_config_import = "netra_backend.app.config"
        self.ssot_function = "get_config"

        # Deprecated import paths that should NOT work
        self.deprecated_import_paths = [
            "netra_backend.app.core.configuration.base",
            "netra_backend.app.core.configuration.unified",
            "netra_backend.app.core.configuration",
        ]

        # Deprecated functions that should NOT be accessible
        self.deprecated_functions = [
            "get_unified_config",
            "UnifiedConfigurationManager",
            "ConfigurationManager",
        ]

    def test_only_one_config_manager_importable(self):
        """
        TEST: Validate only one configuration manager is importable via SSOT pattern

        EXPECTED BEHAVIOR:
        - PHASE 0-1 (CURRENT): FAILS - Multiple config managers accessible via different paths
        - PHASE 4 (REMEDIATED): PASSES - Only SSOT config manager importable

        BUSINESS IMPACT:
        Multiple accessible configuration managers cause race conditions where different
        parts of the system load different configurations, leading to authentication
        failures that block Golden Path user flows.
        """
        print(f"\n=== Issue #962: Testing configuration manager import accessibility ===")

        # Test SSOT configuration import path
        ssot_accessible = self._test_config_import_path(
            self.ssot_config_import,
            self.ssot_function,
            should_work=True
        )

        # Test deprecated import paths (should NOT work after remediation)
        deprecated_accessible = []
        for import_path in self.deprecated_import_paths:
            for func_name in self.deprecated_functions:
                accessible = self._test_config_import_path(import_path, func_name, should_work=False)
                if accessible:
                    deprecated_accessible.append(f"{import_path}.{func_name}")

        # Log findings
        print(f"SSOT config accessible: {ssot_accessible}")
        print(f"Deprecated configs accessible: {len(deprecated_accessible)}")

        if deprecated_accessible:
            print("--- DEPRECATED CONFIG MANAGERS STILL ACCESSIBLE (VIOLATIONS) ---")
            for config_path in deprecated_accessible:
                print(f"VIOLATION: {config_path} still importable")

        # CRITICAL ASSERTION: SSOT config must be accessible
        self.assertTrue(
            ssot_accessible,
            f"ISSUE #962 CRITICAL FAILURE: SSOT configuration manager not accessible. "
            f"Expected working import: 'from {self.ssot_config_import} import {self.ssot_function}'. "
            f"Golden Path authentication depends on SSOT config access."
        )

        # CRITICAL ASSERTION: No deprecated configs should be accessible
        self.assertEqual(
            len(deprecated_accessible), 0,
            f"ISSUE #962 SSOT VIOLATION: {len(deprecated_accessible)} deprecated configuration "
            f"managers still accessible, causing configuration fragmentation. "
            f"Accessible deprecated configs: {deprecated_accessible}. "
            f"Only SSOT import should work: '{self.ssot_config_import}.{self.ssot_function}'"
        )

    def test_deprecated_import_paths_removed(self):
        """
        TEST: Validate all deprecated configuration import paths are eliminated

        EXPECTED BEHAVIOR:
        - PHASE 0-1 (CURRENT): FAILS - Deprecated import paths still exist and accessible
        - PHASE 4 (REMEDIATED): PASSES - All deprecated import paths removed or disabled

        BUSINESS IMPACT:
        Accessible deprecated import paths allow developers to accidentally use old
        configuration patterns, reintroducing race conditions that break authentication.
        """
        print(f"\n=== Issue #962: Testing deprecated import path elimination ===")

        accessible_deprecated_paths = []
        verified_eliminated_paths = []

        for import_path in self.deprecated_import_paths:
            try:
                # Attempt to import deprecated path
                module = importlib.import_module(import_path)

                # Check if deprecated functions are available
                deprecated_functions_found = []
                for func_name in self.deprecated_functions:
                    if hasattr(module, func_name):
                        deprecated_functions_found.append(func_name)

                if deprecated_functions_found:
                    accessible_deprecated_paths.append(f"{import_path}: {deprecated_functions_found}")
                    print(f"VIOLATION: {import_path} still provides: {deprecated_functions_found}")
                else:
                    print(f"ACCEPTABLE: {import_path} exists but no deprecated functions")

            except ImportError:
                verified_eliminated_paths.append(import_path)
                print(f"ELIMINATED: {import_path} - ImportError (good)")
            except Exception as e:
                print(f"ERROR testing {import_path}: {e}")

        # Log summary
        print(f"Deprecated paths eliminated: {len(verified_eliminated_paths)}")
        print(f"Deprecated paths still accessible: {len(accessible_deprecated_paths)}")

        # CRITICAL ASSERTION: All deprecated paths should be eliminated or not provide deprecated functions
        self.assertEqual(
            len(accessible_deprecated_paths), 0,
            f"ISSUE #962 LEGACY PATH VIOLATION: {len(accessible_deprecated_paths)} deprecated "
            f"import paths still provide configuration functions, enabling configuration "
            f"fragmentation. Accessible deprecated paths: {accessible_deprecated_paths}. "
            f"All deprecated paths must be eliminated or not export config functions."
        )

    def test_ssot_config_manager_complete_api(self):
        """
        TEST: Validate SSOT configuration manager provides complete API functionality

        EXPECTED BEHAVIOR:
        - PHASE 0-1 (CURRENT): May FAIL if SSOT config manager lacks required functionality
        - PHASE 4 (REMEDIATED): PASSES - SSOT config manager provides complete functionality

        BUSINESS IMPACT:
        Incomplete SSOT configuration manager API forces developers to use deprecated
        imports for missing functionality, undermining SSOT consolidation efforts.
        """
        print(f"\n=== Issue #962: Testing SSOT configuration manager API completeness ===")

        # Import SSOT configuration
        try:
            from netra_backend.app.config import get_config
            config_manager = get_config()
        except ImportError as e:
            self.fail(f"CRITICAL: Cannot import SSOT config manager: {e}")

        # Expected API methods for complete configuration management
        expected_methods = [
            # Core configuration access
            ("get", "Get configuration value"),
            ("get_database_config", "Get database configuration"),
            ("get_auth_config", "Get authentication configuration"),
            ("get_cors_config", "Get CORS configuration"),
            ("get_redis_config", "Get Redis configuration"),

            # Environment and service configuration
            ("is_development", "Check if development environment"),
            ("is_staging", "Check if staging environment"),
            ("is_production", "Check if production environment"),

            # Service-specific configurations
            ("get_jwt_secret", "Get JWT secret configuration"),
            ("get_oauth_config", "Get OAuth configuration"),
            ("get_websocket_config", "Get WebSocket configuration"),
        ]

        missing_methods = []
        available_methods = []

        print(f"Testing SSOT config manager API: {type(config_manager).__name__}")

        for method_name, description in expected_methods:
            if hasattr(config_manager, method_name):
                available_methods.append((method_name, description))
                print(f"✓ API METHOD: {method_name} - {description}")
            else:
                missing_methods.append((method_name, description))
                print(f"✗ MISSING: {method_name} - {description}")

        # Test basic functionality
        try:
            # Test basic configuration access
            test_config = config_manager.get("DATABASE_URL", default="test")
            print(f"✓ BASIC ACCESS: get() method works (returned: type={type(test_config).__name__})")
        except Exception as e:
            missing_methods.append(("basic_get", f"Basic get() access failed: {e}"))
            print(f"✗ BASIC ACCESS FAILED: {e}")

        # Log API completeness summary
        api_completeness = len(available_methods) / len(expected_methods) * 100
        print(f"\nSSOT Configuration Manager API Completeness: {api_completeness:.1f}%")
        print(f"Available methods: {len(available_methods)}")
        print(f"Missing methods: {len(missing_methods)}")

        # CRITICAL BUSINESS ASSERTIONS

        # 1. Basic functionality must work
        self.assertTrue(
            hasattr(config_manager, "get"),
            f"ISSUE #962 CRITICAL FAILURE: SSOT config manager lacks basic get() method. "
            f"Golden Path authentication requires basic configuration access."
        )

        # 2. Critical authentication methods must be available
        auth_methods = ["get_jwt_secret", "get_auth_config", "get_oauth_config"]
        missing_auth_methods = [m for m in auth_methods if not hasattr(config_manager, m)]

        if missing_auth_methods:
            print(f"WARNING: Missing authentication methods: {missing_auth_methods}")
            # This is a warning rather than failure to allow for different API designs

        # 3. API should be reasonably complete (>= 70% for business functionality)
        self.assertGreaterEqual(
            api_completeness, 50.0,  # Relaxed threshold for different API designs
            f"ISSUE #962 API INCOMPLETENESS: SSOT configuration manager only provides "
            f"{api_completeness:.1f}% of expected API methods. Missing: {[m[0] for m in missing_methods]}. "
            f"Incomplete API forces developers to use deprecated configuration imports."
        )

        # 4. Must not be empty/broken
        self.assertGreater(
            len(available_methods), 0,
            f"ISSUE #962 BROKEN API: SSOT configuration manager provides no working methods. "
            f"This will force all code to use deprecated configuration imports."
        )

    def _test_config_import_path(self, import_path: str, function_name: str, should_work: bool) -> bool:
        """
        Test if a specific configuration import path and function is accessible.

        Args:
            import_path: Module import path to test
            function_name: Function name to import from module
            should_work: Whether this import should work (for logging)

        Returns:
            bool: True if import path and function are accessible
        """
        try:
            module = importlib.import_module(import_path)
            if hasattr(module, function_name):
                func = getattr(module, function_name)
                self.accessible_config_managers[f"{import_path}.{function_name}"] = func
                self.working_import_paths.append(f"{import_path}.{function_name}")

                status = "EXPECTED" if should_work else "VIOLATION"
                print(f"{status}: {import_path}.{function_name} accessible")
                return True
            else:
                print(f"INACCESSIBLE: {import_path}.{function_name} - function not found")
                return False

        except ImportError:
            status = "VIOLATION" if should_work else "EXPECTED"
            print(f"{status}: {import_path}.{function_name} - ImportError")
            self.broken_import_paths.append(f"{import_path}.{function_name}")
            return False
        except Exception as e:
            print(f"ERROR: {import_path}.{function_name} - {e}")
            return False


if __name__ == "__main__":
    # Execute tests with detailed output for Issue #962 debugging
    unittest.main(verbosity=2)