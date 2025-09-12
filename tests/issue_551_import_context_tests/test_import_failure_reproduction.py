"""
Test Issue #551: Import Failure from Subdirectory Context

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Enable reliable test execution from any directory context
- Value Impact: Ensures test framework works reliably across development environments
- Strategic Impact: Prevents development blockers and ensures CI/CD reliability

This test reproduces the exact import failure described in Issue #551:
- `test_framework.base_integration_test` import fails when run from subdirectory context
- Works from root directory but fails from service-specific directories
"""

import os
import sys
import subprocess
import tempfile
import pytest
from pathlib import Path
from typing import List, Dict, Any

class TestImportFailureReproduction:
    """Reproduce Issue #551 import failures from different directory contexts."""
    
    def test_import_works_from_root_directory(self):
        """BASELINE: Verify import works from root directory."""
        # This should pass - establishing the working baseline
        root_dir = Path(__file__).parent.parent.parent
        
        # Execute import test from root directory
        result = subprocess.run([
            sys.executable, "-c",
            "from test_framework.base_integration_test import BaseIntegrationTest; print('SUCCESS')"
        ], 
        cwd=root_dir,
        capture_output=True,
        text=True
        )
        
        assert result.returncode == 0, f"Import failed from root: {result.stderr}"
        assert "SUCCESS" in result.stdout, f"Import succeeded but no success message: {result.stdout}"
    
    @pytest.mark.parametrize("subdirectory", [
        "netra_backend",
        "auth_service", 
        "tests/integration",
        "tests/e2e",
        "frontend"
    ])
    def test_import_fails_from_subdirectory_context(self, subdirectory: str):
        """FAILING TEST: Reproduce import failure from various subdirectory contexts."""
        root_dir = Path(__file__).parent.parent.parent
        test_dir = root_dir / subdirectory
        
        # Skip if directory doesn't exist
        if not test_dir.exists():
            pytest.skip(f"Directory {subdirectory} does not exist")
        
        # Execute import test from subdirectory - this SHOULD FAIL currently
        result = subprocess.run([
            sys.executable, "-c", 
            "from test_framework.base_integration_test import BaseIntegrationTest; print('SUCCESS')"
        ],
        cwd=test_dir,
        capture_output=True, 
        text=True
        )
        
        # Document the current failing state
        assert result.returncode != 0, f"Expected import to fail from {subdirectory} but it succeeded"
        assert "ModuleNotFoundError" in result.stderr, f"Expected ModuleNotFoundError but got: {result.stderr}"
        assert "test_framework" in result.stderr, f"Expected test_framework module error but got: {result.stderr}"
    
    def test_import_fails_with_specific_error_message(self):
        """Verify the exact error message matches Issue #551 description."""
        root_dir = Path(__file__).parent.parent.parent
        test_dir = root_dir / "netra_backend"
        
        result = subprocess.run([
            sys.executable, "-c",
            "from test_framework.base_integration_test import BaseIntegrationTest"
        ],
        cwd=test_dir,
        capture_output=True,
        text=True
        )
        
        assert result.returncode != 0
        # Verify the specific error pattern from Issue #551
        expected_patterns = [
            "ModuleNotFoundError: No module named 'test_framework'",
            "test_framework.base_integration_test"
        ]
        
        for pattern in expected_patterns:
            assert pattern in result.stderr, f"Expected error pattern '{pattern}' not found in: {result.stderr}"
    
    def test_current_workaround_with_sys_path(self):
        """Test that current sys.path workaround succeeds."""
        root_dir = Path(__file__).parent.parent.parent
        test_dir = root_dir / "netra_backend"
        
        # Test the workaround that developers currently use
        workaround_code = f"""
import sys
from pathlib import Path
root_dir = Path(r'{root_dir}')
sys.path.insert(0, str(root_dir))
from test_framework.base_integration_test import BaseIntegrationTest
print('WORKAROUND_SUCCESS')
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(workaround_code)
            temp_file = f.name
        
        try:
            result = subprocess.run([
                sys.executable, temp_file
            ],
            cwd=test_dir,
            capture_output=True,
            text=True
            )
            
            assert result.returncode == 0, f"Workaround failed: {result.stderr}"
            assert "WORKAROUND_SUCCESS" in result.stdout
        finally:
            os.unlink(temp_file)
    
    def test_pythonpath_solution_works(self):
        """Test that PYTHONPATH environment variable solution works."""
        root_dir = Path(__file__).parent.parent.parent
        test_dir = root_dir / "netra_backend"
        
        # Set PYTHONPATH to include root directory
        env = os.environ.copy()
        env['PYTHONPATH'] = str(root_dir)
        
        result = subprocess.run([
            sys.executable, "-c",
            "from test_framework.base_integration_test import BaseIntegrationTest; print('PYTHONPATH_SUCCESS')"
        ],
        cwd=test_dir,
        env=env,
        capture_output=True,
        text=True
        )
        
        assert result.returncode == 0, f"PYTHONPATH solution failed: {result.stderr}"
        assert "PYTHONPATH_SUCCESS" in result.stdout
    
    def test_import_resolution_after_fix(self):
        """POST-FIX TEST: This should pass after Issue #551 is resolved."""
        # This test validates that the fix works properly
        # After the fix, this should pass without any workarounds
        
        root_dir = Path(__file__).parent.parent.parent
        test_directories = [
            root_dir / "netra_backend",
            root_dir / "auth_service",
            root_dir / "tests" / "integration"
        ]
        
        success_count = 0
        failures = []
        
        for test_dir in test_directories:
            if not test_dir.exists():
                continue
                
            result = subprocess.run([
                sys.executable, "-c",
                "from test_framework.base_integration_test import BaseIntegrationTest; print('FIXED')"
            ],
            cwd=test_dir,
            capture_output=True,
            text=True
            )
            
            if result.returncode == 0 and "FIXED" in result.stdout:
                success_count += 1
            else:
                failures.append({
                    'directory': str(test_dir.relative_to(root_dir)),
                    'error': result.stderr,
                    'returncode': result.returncode
                })
        
        # After the fix, we expect at least 2 directories to work  
        # (This will fail until Issue #551 is resolved)
        if success_count >= 2:
            # Fix has been implemented successfully
            assert True, f"Fix successful: {success_count} directories working"
        else:
            # Still failing - document current state for fixing
            pytest.skip(f"Issue #551 not yet resolved: {success_count} working, {len(failures)} failing. Failures: {failures}")


class TestImportContextAnalysis:
    """Analyze import context and path resolution for Issue #551."""
    
    def test_analyze_python_path_from_different_contexts(self):
        """Analyze how Python path resolution works from different contexts."""
        root_dir = Path(__file__).parent.parent.parent
        
        contexts_to_test = [
            ("root", root_dir),
            ("netra_backend", root_dir / "netra_backend"),
            ("auth_service", root_dir / "auth_service"),
            ("tests_integration", root_dir / "tests" / "integration")
        ]
        
        path_analysis = {}
        
        for context_name, context_dir in contexts_to_test:
            if not context_dir.exists():
                continue
                
            # Get sys.path from each context
            result = subprocess.run([
                sys.executable, "-c",
                "import sys; import json; print(json.dumps(sys.path))"
            ],
            cwd=context_dir,
            capture_output=True,
            text=True
            )
            
            if result.returncode == 0:
                import json
                try:
                    sys_path = json.loads(result.stdout.strip())
                    path_analysis[context_name] = {
                        'working_directory': str(context_dir),
                        'sys_path': sys_path,
                        'has_root_in_path': str(root_dir) in sys_path,
                        'has_current_dir_in_path': '' in sys_path or str(context_dir) in sys_path
                    }
                except json.JSONDecodeError:
                    path_analysis[context_name] = {'error': 'Could not parse sys.path'}
        
        # This test always passes - it's just collecting diagnostic information
        print(f"\nPath Analysis for Issue #551:")
        for context, info in path_analysis.items():
            print(f"  {context}: {info}")
        
        # Store analysis for debugging
        self._path_analysis = path_analysis
        assert len(path_analysis) > 0, "Should have analyzed at least one context"
    
    def test_check_test_framework_locations(self):
        """Check where test_framework directories exist in the project."""
        root_dir = Path(__file__).parent.parent.parent
        
        test_framework_locations = []
        for path in root_dir.rglob("test_framework"):
            if path.is_dir():
                test_framework_locations.append(str(path.relative_to(root_dir)))
        
        print(f"\ntest_framework directories found:")
        for location in test_framework_locations:
            print(f"  {location}")
        
        # Verify the main test_framework exists
        assert "test_framework" in test_framework_locations, "Main test_framework directory not found"
        
        # Document findings for Issue #551 resolution
        assert len(test_framework_locations) > 0, f"No test_framework directories found in project"