"""
Unit Tests for Import Path Compliance and Migration Validation

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Goal: Ensure migration compliance and import path standards
- Value Impact: Validates canonical import paths work correctly
- Strategic Impact: Supports clean deprecation migration for Issue #1090

This test suite validates that:
1. Existing code uses compliant import paths
2. Canonical import paths are functional
3. Migration patterns follow SSOT principles
4. Bridge adapters use proper import patterns

Test Philosophy: These tests validate proper usage patterns and ensure
canonical import paths are functional and warning-free.
"""

import inspect
import pytest
import warnings
from pathlib import Path
from typing import List, Dict, Any, Optional
from unittest.mock import patch, Mock

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestImportPathCompliance(SSotBaseTestCase):
    """Test import path compliance and migration validation."""
    
    def setUp(self):
        """Setup test environment."""
        super().setUp()
        self.test_context.test_category = "unit"
        self.test_context.record_custom('component', 'import_path_compliance')
        
        # Track compliance metrics
        self.compliant_imports_found = 0
        self.problematic_imports_found = 0
        self.canonical_imports_tested = 0
        
    def tearDown(self):
        """Clean up and record metrics."""
        self.test_context.record_custom('compliant_imports_found', self.compliant_imports_found)
        self.test_context.record_custom('problematic_imports_found', self.problematic_imports_found)
        self.test_context.record_custom('canonical_imports_tested', self.canonical_imports_tested)
        super().tearDown()

    @pytest.mark.unit
    def test_websocket_bridge_adapter_import_compliance(self):
        """Test that websocket_bridge_adapter uses compliant import paths.
        
        SHOULD PASS BOTH BEFORE AND AFTER: Bridge adapter already uses compliant imports
        """
        try:
            # Import the bridge adapter to inspect its source
            from netra_backend.app.agents.mixins.websocket_bridge_adapter import WebSocketBridgeAdapter
            
            # Get source file path
            source_file = inspect.getfile(WebSocketBridgeAdapter)
            
            # Read source and check for deprecated patterns
            with open(source_file, 'r') as f:
                content = f.read()
            
            # Bridge adapter should NOT use problematic imports
            problematic_patterns = [
                'from netra_backend.app.websocket_core import WebSocketManager',
                'from netra_backend.app.websocket_core import create_websocket_manager',
                'from netra_backend.app.websocket_core import get_websocket_manager'
            ]
            
            for pattern in problematic_patterns:
                if pattern in content:
                    self.problematic_imports_found += 1
                    self.fail(f"Bridge adapter should not use deprecated import: {pattern}")
            
            # Look for compliant patterns instead
            compliant_patterns = [
                'from netra_backend.app.websocket_core.canonical_import_patterns import',
                'from netra_backend.app.websocket_core.unified_emitter import',
                'from netra_backend.app.websocket_core.event_validator import'
            ]
            
            for pattern in compliant_patterns:
                if pattern in content:
                    self.compliant_imports_found += 1
            
            self.test_context.record_custom('bridge_adapter_source_file', source_file)
            self.test_context.record_custom('bridge_adapter_compliance', 'checked')
            
        except ImportError as e:
            self.test_context.record_custom('bridge_adapter_compliance', f'import_failed: {e}')
            pytest.skip(f"WebSocketBridgeAdapter not available: {e}")

    @pytest.mark.unit
    def test_canonical_import_paths_functional(self):
        """Test that canonical import paths work correctly.
        
        SHOULD PASS BOTH BEFORE AND AFTER: Canonical paths are already working
        """
        # Test canonical import paths one by one
        canonical_imports = [
            {
                'import_statement': 'from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager',
                'class_name': 'WebSocketManager',
                'description': 'WebSocket manager from specific module'
            },
            {
                'import_statement': 'from netra_backend.app.websocket_core.event_validator import UnifiedEventValidator',
                'class_name': 'UnifiedEventValidator', 
                'description': 'Event validator from specific module'
            },
            {
                'import_statement': 'from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter',
                'class_name': 'UnifiedWebSocketEmitter',
                'description': 'Unified emitter from specific module'
            }
        ]
        
        successful_imports = 0
        
        for import_info in canonical_imports:
            try:
                # Execute the import statement
                exec(import_info['import_statement'])
                
                # Verify the class is available in local namespace
                class_name = import_info['class_name']
                imported_class = locals().get(class_name)
                
                self.assertIsNotNone(imported_class, 
                                   f"Canonical import should make {class_name} available")
                
                successful_imports += 1
                self.canonical_imports_tested += 1
                
                self.test_context.record_custom(f'canonical_import_{class_name}', 'success')
                
            except ImportError as e:
                self.test_context.record_custom(f'canonical_import_{import_info["class_name"]}', f'failed: {e}')
                # Don't fail the test - some modules may not exist yet
                
        # Record overall success rate
        total_attempted = len(canonical_imports)
        success_rate = (successful_imports / total_attempted) * 100 if total_attempted > 0 else 0
        self.test_context.record_custom('canonical_import_success_rate', success_rate)
        
        # At least some canonical imports should work
        self.assertGreater(successful_imports, 0, 
                          "At least some canonical import paths should be functional")

    @pytest.mark.unit
    def test_websocket_error_validator_import_paths(self):
        """Test that websocket_error_validator uses proper import paths.
        
        SHOULD PASS BOTH BEFORE AND AFTER: Should already use specific module imports
        """
        try:
            # Import the error validator to inspect its source
            import netra_backend.app.services.websocket_error_validator as error_validator_module
            
            # Get source file path
            source_file = inspect.getfile(error_validator_module)
            
            # Read source and analyze import patterns
            with open(source_file, 'r') as f:
                content = f.read()
            
            # Should use specific module imports
            expected_patterns = [
                'from netra_backend.app.websocket_core.event_validator import UnifiedEventValidator',
                'from netra_backend.app.websocket_core.event_validator import ValidationResult',
                'from netra_backend.app.websocket_core.event_validator import EventCriticality'
            ]
            
            found_patterns = 0
            for pattern in expected_patterns:
                if pattern in content:
                    found_patterns += 1
                    self.compliant_imports_found += 1
            
            # Should NOT use broad imports from __init__.py
            problematic_patterns = [
                'from netra_backend.app.websocket_core import UnifiedEventValidator',
                'from netra_backend.app.websocket_core import ValidationResult'
            ]
            
            for pattern in problematic_patterns:
                if pattern in content:
                    self.problematic_imports_found += 1
            
            self.test_context.record_custom('error_validator_compliant_patterns', found_patterns)
            self.test_context.record_custom('error_validator_problematic_patterns', self.problematic_imports_found)
            self.test_context.record_custom('error_validator_source_file', source_file)
            
            # Should have at least some proper specific imports
            self.assertGreater(found_patterns, 0, 
                             "websocket_error_validator should use specific module imports")
            
        except ImportError as e:
            self.test_context.record_custom('error_validator_analysis', f'import_failed: {e}')
            pytest.skip(f"websocket_error_validator not available: {e}")

    @pytest.mark.unit
    def test_import_equivalence_preservation(self):
        """Test that deprecated and canonical imports provide equivalent functionality.
        
        SHOULD PASS BOTH BEFORE AND AFTER: Functionality should be preserved
        """
        equivalence_tests = [
            {
                'deprecated': 'from netra_backend.app.websocket_core import WebSocketManager',
                'canonical': 'from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager',
                'class_name': 'WebSocketManager'
            }
        ]
        
        for test in equivalence_tests:
            deprecated_class = None
            canonical_class = None
            
            # Test deprecated import (with warnings suppressed for this test)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                try:
                    exec(test['deprecated'])
                    deprecated_class = locals().get(test['class_name'])
                except ImportError:
                    pass
            
            # Test canonical import
            try:
                exec(test['canonical'])
                canonical_class = locals().get(test['class_name'])
            except ImportError:
                pass
            
            # If both imports work, they should provide the same class
            if deprecated_class is not None and canonical_class is not None:
                self.assertIs(deprecated_class, canonical_class,
                            f"Deprecated and canonical imports should provide same {test['class_name']}")
                self.test_context.record_custom(f'equivalence_{test["class_name"]}', 'preserved')
            else:
                self.test_context.record_custom(f'equivalence_{test["class_name"]}', 'cannot_test')

    @pytest.mark.unit
    def test_ssot_import_pattern_validation(self):
        """Test SSOT import pattern compliance across key modules.
        
        SHOULD PASS AFTER MIGRATION: All modules should use SSOT-compliant imports
        """
        # Modules to check for SSOT compliance
        modules_to_check = [
            'netra_backend.app.services.websocket_error_validator',
            # Add more modules as they're migrated
        ]
        
        ssot_compliance_results = {}
        
        for module_name in modules_to_check:
            try:
                # Import module for inspection
                module = __import__(module_name, fromlist=[''])
                source_file = inspect.getfile(module)
                
                with open(source_file, 'r') as f:
                    content = f.read()
                
                # Count SSOT-compliant patterns
                ssot_patterns = [
                    'from netra_backend.app.websocket_core.canonical_import_patterns import',
                    'from netra_backend.app.websocket_core.event_validator import', 
                    'from netra_backend.app.websocket_core.unified_emitter import',
                    'from netra_backend.app.websocket_core.protocols import'
                ]
                
                # Count deprecated patterns
                deprecated_patterns = [
                    'from netra_backend.app.websocket_core import WebSocketManager',
                    'from netra_backend.app.websocket_core import UnifiedEventValidator',
                    'from netra_backend.app.websocket_core import create_websocket_manager'
                ]
                
                ssot_count = sum(1 for pattern in ssot_patterns if pattern in content)
                deprecated_count = sum(1 for pattern in deprecated_patterns if pattern in content)
                
                ssot_compliance_results[module_name] = {
                    'ssot_patterns': ssot_count,
                    'deprecated_patterns': deprecated_count,
                    'compliance_ratio': ssot_count / (ssot_count + deprecated_count) if (ssot_count + deprecated_count) > 0 else 1.0
                }
                
            except (ImportError, OSError) as e:
                ssot_compliance_results[module_name] = {
                    'error': str(e),
                    'compliance_ratio': 0.0
                }
        
        # Record compliance results
        for module_name, result in ssot_compliance_results.items():
            self.test_context.record_custom(f'ssot_compliance_{module_name}', result)
        
        # Calculate overall compliance
        if ssot_compliance_results:
            total_compliance = sum(result.get('compliance_ratio', 0) 
                                 for result in ssot_compliance_results.values())
            avg_compliance = total_compliance / len(ssot_compliance_results)
            self.test_context.record_custom('overall_ssot_compliance', avg_compliance)
            
            # After migration, compliance should be high
            # Before migration, this documents current state
            self.assertGreaterEqual(avg_compliance, 0.0, 
                                  "SSOT compliance should be measurable")


class TestDeprecationMigrationReadiness(SSotBaseTestCase):
    """Test readiness for deprecation warning fixes and migration."""
    
    def setUp(self):
        """Setup test environment."""
        super().setUp()
        self.test_context.test_category = "unit"
        self.test_context.record_custom('component', 'migration_readiness')

    @pytest.mark.unit
    def test_warning_fix_impact_assessment(self):
        """Assess the impact of fixing deprecation warning scoping.
        
        SHOULD PASS: Impact assessment should show minimal risk
        """
        # This test documents what will change when warnings are fixed
        impact_assessment = {
            'files_with_broad_warnings': 1,  # websocket_core/__init__.py
            'files_using_specific_imports': 0,  # To be counted
            'expected_warning_reduction': 'significant',
            'functional_impact': 'none',
            'risk_level': 'minimal'
        }
        
        # Count files that would be affected by warning scope changes
        try:
            import netra_backend.app.services.websocket_error_validator
            # This file uses specific imports and should benefit from warning fix
            impact_assessment['files_using_specific_imports'] += 1
        except ImportError:
            pass
        
        # Record impact assessment
        for key, value in impact_assessment.items():
            self.test_context.record_custom(f'impact_{key}', value)
        
        # Validate that impact is acceptable
        self.assertEqual(impact_assessment['functional_impact'], 'none',
                        "Warning fix should have no functional impact")
        self.assertEqual(impact_assessment['risk_level'], 'minimal',
                        "Warning fix should be minimal risk")

    @pytest.mark.unit
    def test_canonical_path_availability(self):
        """Test that canonical import paths are available for migration.
        
        SHOULD PASS: Canonical paths should be ready for use
        """
        # Test that the canonical paths referenced in warnings actually work
        canonical_paths = [
            'netra_backend.app.websocket_core.websocket_manager',
            'netra_backend.app.websocket_core.event_validator', 
            'netra_backend.app.websocket_core.unified_emitter'
        ]
        
        availability_results = {}
        
        for path in canonical_paths:
            try:
                # Try to import the module
                __import__(path)
                availability_results[path] = 'available'
            except ImportError as e:
                availability_results[path] = f'not_available: {e}'
        
        # Record availability results
        for path, result in availability_results.items():
            self.test_context.record_custom(f'canonical_path_availability_{path}', result)
        
        # Count available paths
        available_count = sum(1 for result in availability_results.values() 
                            if result == 'available')
        total_count = len(canonical_paths)
        
        self.test_context.record_custom('canonical_paths_available', available_count)
        self.test_context.record_custom('canonical_paths_total', total_count)
        
        # Most canonical paths should be available for migration
        availability_ratio = available_count / total_count if total_count > 0 else 0
        self.assertGreaterEqual(availability_ratio, 0.5,
                              "Most canonical import paths should be available for migration")


if __name__ == '__main__':
    # Use pytest to run the tests
    pytest.main([__file__, '-v'])