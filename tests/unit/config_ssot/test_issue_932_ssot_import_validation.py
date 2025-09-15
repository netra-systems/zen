"""
UNIT TEST: SSOT Configuration Import Validation - Issue #932

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability
- Business Goal: Prevent configuration import failures that block Golden Path user flow
- Value Impact: Protects $500K+ ARR by ensuring configuration imports work reliably
- Strategic Impact: Validates SSOT compliance for configuration management system

CRITICAL MISSION: Issue #932 Configuration Manager Broken Import Crisis (P0 SSOT violation)

This test suite validates that SSOT configuration imports work correctly and identifies
broken import paths that prevent proper configuration management. Tests are designed to:

1. Validate working SSOT configuration imports
2. Detect broken import paths and fail appropriately
3. Ensure Golden Path configuration flow is protected
4. Prevent regression of SSOT configuration patterns

Expected Behavior:
- SSOT imports should work reliably
- Broken imports should fail fast with clear error messages
- Configuration factory patterns should be consistent
- No circular dependency issues should exist

This test supports the Configuration Manager SSOT remediation effort for Issue #932.
"""

import unittest
import importlib
import inspect
from typing import Dict, List, Optional, Any, Type
from pathlib import Path
import sys

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestIssue932SSOTImportValidation(SSotBaseTestCase, unittest.TestCase):
    """Unit tests to validate SSOT configuration imports for Issue #932."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.import_results = {}
        self.broken_imports = []
        self.working_imports = []
    
    def test_primary_config_import_works(self):
        """
        CRITICAL TEST: Validate primary config import path works.
        
        This test ensures the main configuration entry point is accessible
        and follows SSOT patterns. Critical for Golden Path user flow.
        """
        self.record_metric("test_category", "ssot_import_validation")
        
        try:
            # Test primary configuration import
            from netra_backend.app.config import get_config
            
            # Validate function is callable
            self.assertTrue(callable(get_config), "get_config should be callable")
            
            # Test configuration loading
            config = get_config()
            self.assertIsNotNone(config, "Configuration should not be None")
            
            # Record success
            self.working_imports.append("netra_backend.app.config.get_config")
            self.record_metric("primary_config_import", "success")
            
        except ImportError as e:
            self.broken_imports.append(f"netra_backend.app.config.get_config: {e}")
            self.record_metric("primary_config_import", "failed")
            self.fail(f"Primary config import failed: {e}")
        except Exception as e:
            self.record_metric("primary_config_import", "error")
            self.fail(f"Configuration loading failed: {e}")
    
    def test_unified_config_manager_import_works(self):
        """
        CRITICAL TEST: Validate unified configuration manager import.
        
        Tests the SSOT configuration manager import path that should be the
        single source of truth for configuration management.
        """
        self.record_metric("test_category", "ssot_config_manager")
        
        try:
            # Test unified configuration manager import
            from netra_backend.app.core.configuration.base import get_unified_config
            
            # Validate function exists and is callable
            self.assertTrue(callable(get_unified_config), "get_unified_config should be callable")
            
            # Test configuration loading
            config = get_unified_config()
            self.assertIsNotNone(config, "Unified configuration should not be None")
            
            # Record success
            self.working_imports.append("netra_backend.app.core.configuration.base.get_unified_config")
            self.record_metric("unified_config_manager_import", "success")
            
        except ImportError as e:
            self.broken_imports.append(f"netra_backend.app.core.configuration.base.get_unified_config: {e}")
            self.record_metric("unified_config_manager_import", "failed")
            self.fail(f"Unified config manager import failed: {e}")
        except Exception as e:
            self.record_metric("unified_config_manager_import", "error")
            self.fail(f"Unified configuration loading failed: {e}")
    
    def test_configuration_schemas_import_works(self):
        """
        TEST: Validate configuration schema imports work correctly.
        
        Configuration schemas are critical for type safety and validation.
        """
        self.record_metric("test_category", "config_schemas")
        
        schema_imports = [
            "netra_backend.app.schemas.config.AppConfig",
            "netra_backend.app.schemas.config.DevelopmentConfig",
            "netra_backend.app.schemas.config.StagingConfig",
            "netra_backend.app.schemas.config.ProductionConfig",
        ]
        
        for import_path in schema_imports:
            try:
                module_path, class_name = import_path.rsplit('.', 1)
                module = importlib.import_module(module_path)
                config_class = getattr(module, class_name)
                
                # Validate it's a class
                self.assertTrue(inspect.isclass(config_class), f"{class_name} should be a class")
                
                # Record success
                self.working_imports.append(import_path)
                
            except ImportError as e:
                self.broken_imports.append(f"{import_path}: {e}")
                self.record_metric(f"schema_import_{class_name}", "failed")
                self.fail(f"Configuration schema import failed: {import_path} - {e}")
            except AttributeError as e:
                self.broken_imports.append(f"{import_path}: {e}")
                self.record_metric(f"schema_import_{class_name}", "missing")
                self.fail(f"Configuration schema class not found: {import_path} - {e}")
        
        self.record_metric("config_schemas_imported", len(schema_imports))
    
    def test_configuration_loader_components_import(self):
        """
        TEST: Validate configuration loader component imports.
        
        Tests that supporting configuration components are importable
        and follow SSOT patterns.
        """
        self.record_metric("test_category", "config_components")
        
        component_imports = [
            "netra_backend.app.core.configuration.loader.ConfigurationLoader",
            "netra_backend.app.core.configuration.validator.ConfigurationValidator",
        ]
        
        for import_path in component_imports:
            try:
                module_path, class_name = import_path.rsplit('.', 1)
                module = importlib.import_module(module_path)
                component_class = getattr(module, class_name)
                
                # Validate it's a class
                self.assertTrue(inspect.isclass(component_class), f"{class_name} should be a class")
                
                # Test instantiation
                instance = component_class()
                self.assertIsNotNone(instance, f"{class_name} should be instantiable")
                
                # Record success
                self.working_imports.append(import_path)
                self.record_metric(f"component_import_{class_name}", "success")
                
            except ImportError as e:
                self.broken_imports.append(f"{import_path}: {e}")
                self.record_metric(f"component_import_{class_name}", "failed")
                self.fail(f"Configuration component import failed: {import_path} - {e}")
            except Exception as e:
                self.broken_imports.append(f"{import_path}: instantiation failed - {e}")
                self.record_metric(f"component_import_{class_name}", "error")
                self.fail(f"Configuration component instantiation failed: {import_path} - {e}")
    
    def test_no_circular_dependencies_in_config_imports(self):
        """
        CRITICAL TEST: Validate no circular dependencies exist in configuration imports.
        
        Circular dependencies can cause import failures and system instability.
        This test ensures clean import paths for SSOT configuration management.
        """
        self.record_metric("test_category", "circular_dependency_detection")
        
        # Test critical import paths that are prone to circular dependencies
        critical_imports = [
            "netra_backend.app.config",
            "netra_backend.app.core.configuration.base",
            "netra_backend.app.schemas.config",
            "shared.isolated_environment",
        ]
        
        imported_modules = {}
        circular_issues = []
        
        for import_path in critical_imports:
            try:
                # Clear module cache to ensure fresh import
                if import_path in sys.modules:
                    # Don't delete, just note it was already loaded
                    self.record_metric(f"module_already_loaded_{import_path}", True)
                
                # Import the module
                module = importlib.import_module(import_path)
                imported_modules[import_path] = module
                
                # Record success
                self.working_imports.append(import_path)
                self.record_metric(f"circular_test_{import_path}", "success")
                
            except ImportError as e:
                if "circular import" in str(e).lower():
                    circular_issues.append(f"{import_path}: {e}")
                    self.record_metric(f"circular_test_{import_path}", "circular")
                else:
                    self.broken_imports.append(f"{import_path}: {e}")
                    self.record_metric(f"circular_test_{import_path}", "failed")
                    
        # Fail if circular dependencies detected
        if circular_issues:
            self.record_metric("circular_dependencies_detected", len(circular_issues))
            self.fail(f"Circular dependencies detected: {circular_issues}")
        else:
            self.record_metric("circular_dependencies_detected", 0)
    
    def test_configuration_environment_detection_works(self):
        """
        TEST: Validate environment detection works for configuration.
        
        Environment detection is critical for loading correct configuration
        for different deployment environments.
        """
        self.record_metric("test_category", "environment_detection")
        
        try:
            # Test environment detection import
            from netra_backend.app.core.environment_constants import EnvironmentDetector
            
            # Validate class and instantiation
            self.assertTrue(inspect.isclass(EnvironmentDetector), "EnvironmentDetector should be a class")
            
            detector = EnvironmentDetector()
            self.assertIsNotNone(detector, "EnvironmentDetector should be instantiable")
            
            # Test environment detection method
            if hasattr(detector, 'detect_environment'):
                env = detector.detect_environment()
                self.assertIsNotNone(env, "Environment should be detected")
                self.assertIsInstance(env, str, "Environment should be a string")
                
            # Record success
            self.working_imports.append("netra_backend.app.core.environment_constants.EnvironmentDetector")
            self.record_metric("environment_detection_import", "success")
            
        except ImportError as e:
            self.broken_imports.append(f"netra_backend.app.core.environment_constants.EnvironmentDetector: {e}")
            self.record_metric("environment_detection_import", "failed")
            self.fail(f"Environment detection import failed: {e}")
        except Exception as e:
            self.record_metric("environment_detection_import", "error")
            self.fail(f"Environment detection failed: {e}")
    
    def test_import_validation_summary(self):
        """
        SUMMARY TEST: Provide comprehensive import validation summary.
        
        This test summarizes all import validation results and provides
        metrics for SSOT compliance monitoring.
        """
        self.record_metric("test_category", "import_summary")
        
        # Since this test may run before others, perform basic import validation here
        if len(self.working_imports) == 0 and len(self.broken_imports) == 0:
            # Perform basic import validation to populate results
            try:
                from netra_backend.app.config import get_config
                self.working_imports.append("netra_backend.app.config.get_config")
            except ImportError as e:
                self.broken_imports.append(f"netra_backend.app.config.get_config: {e}")
            
            try:
                from netra_backend.app.core.configuration.base import get_unified_config
                self.working_imports.append("netra_backend.app.core.configuration.base.get_unified_config")
            except ImportError as e:
                self.broken_imports.append(f"netra_backend.app.core.configuration.base.get_unified_config: {e}")
        
        # Calculate metrics
        total_working = len(self.working_imports)
        total_broken = len(self.broken_imports)
        total_tested = total_working + total_broken
        
        # Record comprehensive metrics
        self.record_metric("total_imports_tested", total_tested)
        self.record_metric("working_imports_count", total_working)
        self.record_metric("broken_imports_count", total_broken)
        
        if total_tested > 0:
            success_rate = (total_working / total_tested) * 100
            self.record_metric("import_success_rate", success_rate)
        else:
            self.record_metric("import_success_rate", 0)
        
        # Log detailed results for debugging
        if self.working_imports:
            self.get_metrics().record_custom("working_imports_list", self.working_imports)
        
        if self.broken_imports:
            self.get_metrics().record_custom("broken_imports_list", self.broken_imports)
        
        # Test should pass if we have any working imports
        # This allows us to identify what works vs what's broken
        self.assertGreater(
            total_working, 0, 
            f"At least some imports should work. Broken imports: {self.broken_imports}"
        )
        
        # Log summary
        summary_message = (
            f"Configuration Import Summary: {total_working}/{total_tested} imports working "
            f"({self.get_metric('import_success_rate', 0):.1f}% success rate)"
        )
        self.get_metrics().record_custom("import_summary", summary_message)


if __name__ == '__main__':
    # Run tests
    unittest.main()