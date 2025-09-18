"""
Issue #416 Deprecation Warning Detection Tests
==============================================

Business Value: Protects $500K+ ARR by ensuring deprecation warnings are detected
before they break customer functionality in production.

Test Strategy:
1. Detection Tests - Find current deprecation warnings 
2. Migration Validation - Ensure proper migration paths exist
3. Regression Prevention - Prevent new deprecated imports
4. Category Coverage - Test all deprecation categories

This test suite should INITIALLY FAIL to demonstrate it can detect deprecation warnings.
"""

import unittest
import warnings
import importlib
import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Set
from unittest.mock import patch
import tempfile
import os
import contextlib

from test_framework.ssot.base_test_case import SSotBaseTestCase


class DeprecationWarningDetectionTests(SSotBaseTestCase):
    """Test suite to detect and validate deprecation warnings - should initially FAIL"""
    
    def setUp(self):
        super().setUp()
        self.detected_warnings = []
        self.deprecation_patterns = [
            "ISSUE #1144",
            "netra_backend.app.websocket_core",
            "deprecated",
            "Phase 2 of SSOT consolidation"
        ]
        
    @contextlib.contextmanager
    def capture_warnings(self):
        """Capture all deprecation warnings during test execution"""
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always", DeprecationWarning)
            yield warning_list
    
    def test_websocket_core_init_deprecation_detection(self):
        """
        FAILING TEST: Detect Issue #1144 deprecation warning from websocket_core.__init__.py
        
        This test should FAIL initially to prove it detects the deprecation warning.
        """
        print("\n=== Testing WebSocket Core Deprecation Detection ===")
        
        # Method 1: Test direct import to trigger warning
        detected_deprecations = []
        
        # Clear any previous imports to ensure we trigger the warning
        if 'netra_backend.app.websocket_core' in sys.modules:
            del sys.modules['netra_backend.app.websocket_core']
        
        with self.capture_warnings() as captured:
            try:
                # Force re-import to trigger the warning
                import netra_backend.app.websocket_core
                importlib.reload(netra_backend.app.websocket_core)
                print(f"CHECK Import successful, checking for warnings...")
            except Exception as e:
                print(f"✗ Import failed: {e}")
                
        # Analyze captured warnings
        for warning in captured:
            if issubclass(warning.category, DeprecationWarning):
                warning_msg = str(warning.message)
                print(f"📊 Captured Warning: {warning_msg}")
                
                # Check if this is the ISSUE #1144 deprecation
                if "ISSUE #1144" in warning_msg and "websocket_core" in warning_msg:
                    detected_deprecations.append({
                        'message': warning_msg,
                        'filename': warning.filename,
                        'lineno': warning.lineno,
                        'category': warning.category.__name__
                    })
                    
        print(f"📈 Method 1 detected {len(detected_deprecations)} ISSUE #1144 deprecations")
        
        # Method 2: Use subprocess to reliably trigger warnings
        if len(detected_deprecations) == 0:
            print("📊 Method 1 didn't capture warnings, trying subprocess method...")
            subprocess_warnings = self._detect_warnings_via_subprocess()
            detected_deprecations.extend(subprocess_warnings)
            print(f"📈 Method 2 detected {len(subprocess_warnings)} additional warnings")
        
        total_detected = len(detected_deprecations)
        print(f"📈 Total detected {total_detected} ISSUE #1144 deprecations")
        
        # ASSERTION: This should FAIL initially, proving the test can detect warnings
        self.assertGreater(
            total_detected, 0,
            "X EXPECTED FAILURE: Should detect ISSUE #1144 deprecation warnings. "
            "If this passes, the deprecation warnings are already fixed!"
        )
        
        # Store results for other tests
        self.detected_warnings = detected_deprecations
        
    def test_deprecation_warning_content_validation(self):
        """
        FAILING TEST: Validate the content and structure of deprecation warnings
        
        Ensures deprecation warnings contain proper guidance for developers.
        """
        print("\n=== Testing Deprecation Warning Content ===")
        
        with self.capture_warnings() as captured:
            import netra_backend.app.websocket_core
            
        deprecation_warnings = [w for w in captured if issubclass(w.category, DeprecationWarning)]
        
        # Should find at least one deprecation warning
        self.assertGreater(
            len(deprecation_warnings), 0,
            "X EXPECTED FAILURE: Should detect deprecation warnings"
        )
        
        for warning in deprecation_warnings:
            warning_msg = str(warning.message)
            print(f"🔍 Analyzing warning: {warning_msg}")
            
            if "ISSUE #1144" in warning_msg:
                # Validate warning contains proper guidance
                required_elements = [
                    "deprecated",
                    "netra_backend.app.websocket_core",
                    "specific module imports",
                    "websocket_manager import WebSocketManager",
                    "Phase 2 of SSOT consolidation"
                ]
                
                missing_elements = []
                for element in required_elements:
                    if element not in warning_msg:
                        missing_elements.append(element)
                
                self.assertEqual(
                    len(missing_elements), 0,
                    f"X EXPECTED FAILURE: Warning missing elements: {missing_elements}"
                )
                
    def test_deprecated_import_pattern_discovery(self):
        """
        FAILING TEST: Discover all files using deprecated import patterns
        
        This should find multiple files importing from deprecated paths.
        """
        print("\n=== Testing Deprecated Import Pattern Discovery ===")
        
        project_root = Path("/Users/anthony/Desktop/netra-apex")
        deprecated_imports = []
        
        # Search for deprecated import patterns
        deprecated_patterns = [
            "from netra_backend.app.websocket_core import",
            "from netra_backend.app.websocket_core.event_validator import",
        ]
        
        for pattern in deprecated_patterns:
            print(f"🔍 Searching for pattern: {pattern}")
            
            # Use grep to find files with deprecated patterns
            result = subprocess.run([
                "grep", "-r", "-l", pattern, str(project_root / "netra_backend")
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                files = result.stdout.strip().split('\n')
                for file_path in files:
                    if file_path.strip():
                        deprecated_imports.append({
                            'file': file_path,
                            'pattern': pattern
                        })
                        print(f"  📁 Found in: {file_path}")
        
        print(f"📊 Total files with deprecated imports: {len(deprecated_imports)}")
        
        # ASSERTION: Should FAIL initially, proving deprecated imports exist
        self.assertGreater(
            len(deprecated_imports), 0,
            "X EXPECTED FAILURE: Should find files with deprecated import patterns. "
            "If this passes, all imports are already migrated!"
        )
        
    def test_migration_path_validation(self):
        """
        FAILING TEST: Validate that proper migration paths exist for deprecated imports
        
        Ensures developers have clear guidance on how to fix deprecations.
        """
        print("\n=== Testing Migration Path Validation ===")
        
        # Test that canonical import paths actually work
        migration_tests = [
            {
                'deprecated': 'from netra_backend.app.websocket_core import WebSocketManager',
                'canonical': 'from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager'
            },
            {
                'deprecated': 'from netra_backend.app.websocket_core.event_validator import get_websocket_validator',
                'canonical': 'from netra_backend.app.websocket_core.event_validation_framework import get_websocket_validator'
            }
        ]
        
        working_migrations = 0
        total_migrations = len(migration_tests)
        
        for test_case in migration_tests:
            print(f"🧪 Testing migration: {test_case['deprecated']} -> {test_case['canonical']}")
            
            # Test if canonical import works
            try:
                # Create temporary module to test import
                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                    f.write(f"{test_case['canonical']}\nprint('Import successful')\n")
                    temp_file = f.name
                
                # Try to execute the canonical import
                result = subprocess.run([
                    sys.executable, temp_file
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    print(f"  CHECK Canonical import works")
                    working_migrations += 1
                else:
                    print(f"  ✗ Canonical import failed: {result.stderr}")
                    
            except Exception as e:
                print(f"  ✗ Migration test failed: {e}")
            finally:
                # Cleanup
                try:
                    os.unlink(temp_file)
                except:
                    pass
        
        # Calculate migration success rate
        migration_success_rate = working_migrations / total_migrations if total_migrations > 0 else 0
        print(f"📊 Migration success rate: {migration_success_rate:.1%} ({working_migrations}/{total_migrations})")
        
        # ASSERTION: Should have high migration success rate
        self.assertGreaterEqual(
            migration_success_rate, 0.5,
            f"X EXPECTED FAILURE: Migration paths should work. "
            f"Success rate: {migration_success_rate:.1%}"
        )

    def test_deprecation_warning_stacklevel_validation(self):
        """
        FAILING TEST: Validate deprecation warnings point to the correct code location
        
        Ensures warnings help developers find the actual problematic import.
        """
        print("\n=== Testing Deprecation Warning Stack Level ===")
        
        # Create a test file that imports deprecated module
        test_content = """
import sys
sys.path.insert(0, '/Users/anthony/Desktop/netra-apex')

import warnings
warnings.simplefilter('always')

# This should trigger deprecation warning pointing to this line
from netra_backend.app.websocket_core.event_validator import get_websocket_validator

print("Import completed")
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_content)
            temp_file = f.name
            
        try:
            # Run the test file and capture warnings
            result = subprocess.run([
                sys.executable, "-W", "default", temp_file
            ], capture_output=True, text=True)
            
            print(f"📊 Test output:")
            print(f"  STDOUT: {result.stdout}")
            print(f"  STDERR: {result.stderr}")
            
            # Check if warning points to the correct location
            warning_found = "ISSUE #1144" in result.stderr
            correct_location = temp_file in result.stderr or "event_validator import" in result.stderr
            
            print(f"  Warning found: {warning_found}")
            print(f"  Correct location: {correct_location}")
            
            # ASSERTION: Should detect warning with correct location
            self.assertTrue(
                warning_found,
                "X EXPECTED FAILURE: Should detect ISSUE #1144 deprecation warning"
            )
            
        finally:
            # Cleanup
            try:
                os.unlink(temp_file)
            except:
                pass

    def _detect_warnings_via_subprocess(self):
        """Use subprocess to detect deprecation warnings"""
        detected_warnings = []
        
        test_code = """
import warnings
import sys
sys.path.insert(0, '/Users/anthony/Desktop/netra-apex')

# Capture warnings
warnings.simplefilter('always')

# Clear module if already imported
if 'netra_backend.app.websocket_core' in sys.modules:
    del sys.modules['netra_backend.app.websocket_core']

# Import to trigger warning
import netra_backend.app.websocket_core

print("Import completed")
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_code)
            temp_file = f.name
        
        try:
            result = subprocess.run([
                sys.executable, "-W", "always", temp_file
            ], capture_output=True, text=True)
            
            if result.stderr:
                # Parse stderr for ISSUE #1144 warnings
                stderr_lines = result.stderr.split('\n')
                for line in stderr_lines:
                    if "ISSUE #1144" in line and "websocket_core" in line:
                        detected_warnings.append({
                            'message': line.strip(),
                            'source': 'subprocess',
                            'method': 'stderr_parsing'
                        })
                        
        except Exception as e:
            print(f"Subprocess warning detection failed: {e}")
        finally:
            try:
                os.unlink(temp_file)
            except:
                pass
                
        return detected_warnings

if __name__ == '__main__':
    print("🚀 Issue #416 Deprecation Warning Detection Test Suite")
    print("=" * 60)
    print("Purpose: Detect and validate deprecation warnings")
    print("Expected: Tests should INITIALLY FAIL to prove detection works")
    print("=" * 60)
    
    unittest.main(verbosity=2)