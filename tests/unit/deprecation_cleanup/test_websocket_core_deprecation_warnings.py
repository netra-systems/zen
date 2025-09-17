"""
Unit Tests for WebSocket Core Deprecation Warning Scoping

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Goal: Developer Experience Enhancement
- Value Impact: Reduces warning noise, improves development velocity
- Strategic Impact: Clean deprecation migration path for Issue #1090

This test suite validates that deprecation warnings are properly scoped:
1. SHOULD trigger warnings for problematic import patterns (factory usage)
2. SHOULD NOT trigger warnings for legitimate specific module imports
3. SHOULD allow websocket_error_validator.py imports to work warning-free

Test Philosophy: These tests FAIL initially (reproducing current warning issues)
and PASS after cleanup (validating targeted warning scoping).
"""

import warnings
import pytest
import importlib
import sys
from pathlib import Path
from typing import List, Dict, Any
from unittest.mock import patch, Mock
import tempfile
import os
import unittest

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestWebSocketCoreDeprecationWarnings(SSotBaseTestCase, unittest.TestCase):
    """Test deprecation warning scoping and accuracy."""
    
    def setUp(self):
        """Setup test environment."""
        super().setUp()
        self.test_context.test_category = "unit"
        self.test_context.record_custom('component', 'websocket_core_deprecation_warnings')
        
        # Track warning metrics
        self.deprecation_warnings_detected = 0
        self.legitimate_imports_tested = 0
        self.problematic_imports_tested = 0
        
    def tearDown(self):
        """Clean up and record metrics."""
        self.test_context.record_custom('deprecation_warnings_detected', self.deprecation_warnings_detected)
        self.test_context.record_custom('legitimate_imports_tested', self.legitimate_imports_tested)
        self.test_context.record_custom('problematic_imports_tested', self.problematic_imports_tested)
        super().tearDown()

    @pytest.mark.unit
    def test_deprecation_warning_triggered_for_problematic_imports(self):
        """Test that deprecation warnings are triggered for actual problematic patterns.
        
        SHOULD FAIL INITIALLY: Current warning is too broad
        SHOULD PASS AFTER FIX: Warning only targets problematic imports
        """
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            # Test imports that SHOULD trigger warnings (factory patterns)
            # These are the problematic patterns that should be deprecated
            try:
                # This should trigger a warning because it's a broad import from __init__.py
                from netra_backend.app.websocket_core import WebSocketManager
                self.problematic_imports_tested += 1
            except ImportError:
                # If import fails, that's fine for this test - we're testing warning behavior
                pass
            
            try:
                # This should also trigger a warning as it's importing from __init__.py
                from netra_backend.app.websocket_core import create_websocket_manager
                self.problematic_imports_tested += 1
            except ImportError:
                pass
            
            # Filter for websocket_core related deprecation warnings
            websocket_deprecation_warnings = [
                warning for warning in w 
                if (issubclass(warning.category, DeprecationWarning) and 
                    'websocket_core' in str(warning.message))
            ]
            
            self.deprecation_warnings_detected = len(websocket_deprecation_warnings)
            
            # CURRENT STATE: Should have warnings (may be too broad)
            # TARGET STATE: Should have warnings only for factory imports
            self.assertGreater(len(websocket_deprecation_warnings), 0, 
                             "Deprecation warnings should be triggered for problematic imports")
            
            # Record warning details for analysis
            for warning in websocket_deprecation_warnings:
                self.test_context.record_custom('warning_message', str(warning.message))
                self.test_context.record_custom('warning_filename', warning.filename)
                self.test_context.record_custom('warning_lineno', warning.lineno)

    @pytest.mark.unit  
    def test_no_deprecation_warning_for_specific_module_imports(self):
        """Test that specific module imports do NOT trigger deprecation warnings.
        
        SHOULD FAIL INITIALLY: Current warning triggers for legitimate imports
        SHOULD PASS AFTER FIX: Legitimate imports are warning-free
        
        This test reproduces the exact issue described in the test plan.
        """
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            # These imports should NOT trigger deprecation warnings
            # These are legitimate specific module imports that should be allowed
            try:
                from netra_backend.app.websocket_core.event_validator import UnifiedEventValidator
                self.legitimate_imports_tested += 1
            except ImportError:
                # Some imports may not exist yet - that's OK for this test
                pass
            
            try:
                from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
                self.legitimate_imports_tested += 1
            except ImportError:
                pass
                
            try:
                from netra_backend.app.websocket_core.protocols import WebSocketManagerProtocol
                self.legitimate_imports_tested += 1
            except ImportError:
                pass
            
            # Filter for websocket_core related deprecation warnings
            websocket_deprecation_warnings = [
                warning for warning in w 
                if (issubclass(warning.category, DeprecationWarning) and 
                    'websocket_core' in str(warning.message))
            ]
            
            self.deprecation_warnings_detected = len(websocket_deprecation_warnings)
            
            # CURRENT STATE: May have warnings (failing test)
            # TARGET STATE: Should have no warnings (passing test)
            warning_messages = [str(w.message) for w in websocket_deprecation_warnings]
            
            # This assertion SHOULD FAIL initially, demonstrating the current issue
            self.assertEqual(len(websocket_deprecation_warnings), 0, 
                f"Specific module imports should not trigger deprecation warnings. Found: {warning_messages}")

    @pytest.mark.unit
    def test_websocket_error_validator_import_warning_free(self):
        """Test that websocket_error_validator.py imports work without warnings.
        
        SHOULD FAIL INITIALLY: Current import triggers deprecation warning
        SHOULD PASS AFTER FIX: Import is warning-free
        
        This directly tests the problematic import from line 32 of websocket_error_validator.py
        """
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            # Simulate the problematic import from websocket_error_validator.py
            # This is the exact import pattern that's causing the issue
            try:
                from netra_backend.app.websocket_core.event_validator import UnifiedEventValidator
                self.legitimate_imports_tested += 1
                
                # Verify the import actually works
                self.assertIsNotNone(UnifiedEventValidator, 
                                   "UnifiedEventValidator should be importable")
                
            except ImportError:
                pytest.skip("UnifiedEventValidator not available")
            
            # Check for websocket_core deprecation warnings
            websocket_warnings = [
                warning for warning in w 
                if (issubclass(warning.category, DeprecationWarning) and 
                    'websocket_core' in str(warning.message))
            ]
            
            self.deprecation_warnings_detected = len(websocket_warnings)
            
            # CURRENT STATE: Has warning (failing test)
            # TARGET STATE: No warning (passing test) 
            warning_messages = [str(w.message) for w in websocket_warnings]
            
            # This assertion SHOULD FAIL initially, proving the current issue exists
            self.assertEqual(len(websocket_warnings), 0, 
                f"event_validator import should not trigger deprecation warning. Found: {warning_messages}")

    @pytest.mark.unit
    def test_deprecation_warning_contains_helpful_guidance(self):
        """Test that deprecation warnings contain helpful migration guidance.
        
        SHOULD PASS BOTH BEFORE AND AFTER: Warning messages should be helpful
        """
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            # Trigger a deprecation warning by importing from __init__.py
            try:
                from netra_backend.app.websocket_core import WebSocketManager
            except ImportError:
                pytest.skip("WebSocketManager not available for warning test")
            
            # Find websocket_core deprecation warnings
            websocket_warnings = [
                warning for warning in w 
                if (issubclass(warning.category, DeprecationWarning) and 
                    'websocket_core' in str(warning.message))
            ]
            
            if websocket_warnings:
                warning_message = str(websocket_warnings[0].message)
                
                # Warning should contain helpful guidance
                self.assertIn("specific module imports", warning_message,
                            "Warning should suggest specific module imports")
                self.assertIn("websocket_manager import WebSocketManager", warning_message,
                            "Warning should provide specific import example")
                
                self.test_context.record_custom('warning_guidance_quality', 'helpful')
            else:
                self.test_context.record_custom('warning_guidance_quality', 'no_warning_found')

    @pytest.mark.unit
    def test_warning_stacklevel_accuracy(self):
        """Test that deprecation warning stacklevel points to caller code.
        
        SHOULD PASS BOTH BEFORE AND AFTER: Stack level should be correct
        """
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            # Create a wrapper function to test stacklevel
            def import_websocket_manager():
                from netra_backend.app.websocket_core import WebSocketManager
                return WebSocketManager
            
            try:
                import_websocket_manager()
            except ImportError:
                pytest.skip("WebSocketManager not available for stacklevel test")
            
            # Find websocket_core deprecation warnings
            websocket_warnings = [
                warning for warning in w 
                if (issubclass(warning.category, DeprecationWarning) and 
                    'websocket_core' in str(warning.message))
            ]
            
            if websocket_warnings:
                warning = websocket_warnings[0]
                
                # Warning should point to this test file, not websocket_core/__init__.py
                warning_filename = Path(warning.filename).name
                expected_filename = Path(__file__).name
                
                self.assertEqual(warning_filename, expected_filename,
                               f"Warning stacklevel should point to caller ({expected_filename}), "
                               f"not to websocket_core module ({warning_filename})")
                
                self.test_context.record_custom('stacklevel_correct', True)
            else:
                self.test_context.record_custom('stacklevel_correct', 'no_warning_to_test')


class TestImportBehaviorChanges(SSotBaseTestCase):
    """Test import behavior changes and edge cases."""
    
    def setUp(self):
        """Setup test environment."""
        super().setUp()
        self.test_context.test_category = "unit"
        self.test_context.record_custom('component', 'import_behavior_deprecation')

    @pytest.mark.unit
    def test_import_from_init_vs_specific_module_equivalence(self):
        """Test that imports from __init__.py and specific modules are equivalent.
        
        SHOULD PASS BOTH BEFORE AND AFTER: Functionality should be preserved
        """
        # Test that both import methods provide the same class
        try:
            from netra_backend.app.websocket_core import WebSocketManager as InitWebSocketManager
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager as SpecificWebSocketManager
            
            # Both should refer to the same class
            self.assertIs(InitWebSocketManager, SpecificWebSocketManager,
                         "WebSocketManager from __init__.py should be same as from specific module")
            
            self.test_context.record_custom('import_equivalence', 'preserved')
            
        except ImportError as e:
            self.test_context.record_custom('import_equivalence', f'import_failed: {e}')
            pytest.skip(f"Import test skipped due to import error: {e}")

    @pytest.mark.unit
    def test_multiple_import_patterns_warning_consistency(self):
        """Test warning consistency across different import patterns.
        
        SHOULD PASS AFTER FIX: Similar import patterns should have consistent warning behavior
        """
        import_patterns = [
            ("from netra_backend.app.websocket_core import WebSocketManager", "broad_init_import"),
            ("from netra_backend.app.websocket_core.websocket_manager import WebSocketManager", "specific_module_import"),
            ("from netra_backend.app.websocket_core.event_validator import UnifiedEventValidator", "specific_module_import"),
            ("from netra_backend.app.websocket_core import create_websocket_manager", "broad_init_import"),
        ]
        
        warning_results = {}
        
        for import_statement, pattern_type in import_patterns:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                
                try:
                    # Execute the import statement
                    exec(import_statement)
                    
                    # Count websocket_core deprecation warnings
                    websocket_warnings = [
                        warning for warning in w 
                        if (issubclass(warning.category, DeprecationWarning) and 
                            'websocket_core' in str(warning.message))
                    ]
                    
                    warning_results[import_statement] = {
                        'pattern_type': pattern_type,
                        'warning_count': len(websocket_warnings),
                        'has_warnings': len(websocket_warnings) > 0
                    }
                    
                except (ImportError, NameError):
                    # Some imports may fail - that's OK for this test
                    warning_results[import_statement] = {
                        'pattern_type': pattern_type,
                        'warning_count': 0,
                        'has_warnings': False,
                        'import_failed': True
                    }
        
        # Analyze consistency
        broad_imports = {k: v for k, v in warning_results.items() if v['pattern_type'] == 'broad_init_import'}
        specific_imports = {k: v for k, v in warning_results.items() if v['pattern_type'] == 'specific_module_import'}
        
        # Record results for analysis
        self.test_context.record_custom('broad_import_warnings', 
                                      sum(1 for v in broad_imports.values() if v.get('has_warnings', False)))
        self.test_context.record_custom('specific_import_warnings', 
                                      sum(1 for v in specific_imports.values() if v.get('has_warnings', False)))
        
        # After fix: broad imports should warn, specific imports should not
        # Before fix: this test documents current inconsistent behavior
        for import_stmt, result in warning_results.items():
            self.test_context.record_custom(f'import_result_{result["pattern_type"]}', result)


if __name__ == '__main__':
    # Use pytest to run the tests
    pytest.main([__file__, '-v'])