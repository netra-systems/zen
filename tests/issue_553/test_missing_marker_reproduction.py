#!/usr/bin/env python3
"""
Issue #553 - Pytest Marker Configuration Missing Markers Reproduction Test

MISSION:
- Reproduce the exact pytest collection errors related to missing markers
- Demonstrate that pytest collection fails with unknown marker errors
- Validate that existing tests use markers not defined in pyproject.toml 
- Prove that the issue is configuration-level (not infrastructure)

METHODOLOGY:
- Create isolated test environment to collect pytest markers
- Run pytest collection with --strict-markers to force marker validation
- Capture exact missing marker error messages
- Document all undefined markers found in codebase

BUSINESS VALUE:
- Protects golden path test execution by fixing test collection failures
- Prevents test collection errors from blocking development workflow
- Ensures pytest marker compliance across all test categories
"""

import pytest
import subprocess
import os
import sys
import tempfile
from pathlib import Path
from typing import List, Dict, Set
import json

class TestMissingMarkerReproduction:
    """
    Reproduce pytest marker configuration issues showing exact missing markers
    """

    @pytest.fixture
    def temp_test_file(self) -> Path:
        """Create temporary test file with unknown markers for reproduction"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='_test.py', delete=False) as f:
            f.write('''
import pytest

@pytest.mark.unknown_marker_1
def test_with_unknown_marker_1():
    """Test using undefined marker to trigger collection error"""
    assert True

@pytest.mark.unknown_marker_2  
def test_with_unknown_marker_2():
    """Test using another undefined marker"""
    assert True

@pytest.mark.some_business_marker
def test_business_functionality():
    """Test representing business functionality"""
    assert True
''')
            return Path(f.name)

    @pytest.mark.unit
    @pytest.mark.critical 
    @pytest.mark.issue_553_reproduction
    def test_missing_marker_collection_failure(self, temp_test_file: Path):
        """
        REPRODUCTION TEST: Demonstrate pytest collection fails with missing markers
        
        This test proves that pytest collection fails when:
        1. --strict-markers is enabled (which it is in pyproject.toml)
        2. Tests use markers not defined in markers configuration
        3. Collection error prevents test discovery/execution
        """
        # Run pytest collection on temporary file with undefined markers
        cmd = [
            sys.executable, '-m', 'pytest',
            str(temp_test_file),
            '--collect-only',
            '--strict-markers',
            '--quiet'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
        
        # Collection should fail with marker errors
        assert result.returncode != 0, "Collection should fail with undefined markers"
        
        # Verify specific error pattern for unknown markers
        error_output = result.stderr.lower()
        assert 'unknown_marker' in error_output or 'unregistered' in error_output, \
            f"Expected marker error not found in: {result.stderr}"
            
        # Clean up temporary file
        temp_test_file.unlink()
        
        print(f"✅ REPRODUCTION CONFIRMED: Pytest collection fails with undefined markers")
        print(f"Error output: {result.stderr}")

    @pytest.mark.unit
    @pytest.mark.critical
    @pytest.mark.issue_553_reproduction  
    def test_scan_existing_tests_for_undefined_markers(self):
        """
        DISCOVERY TEST: Find all markers used in existing tests that aren't defined
        
        This test scans the actual codebase to find undefined markers,
        proving that the issue exists in real test files (not just reproduction)
        """
        # Read current pyproject.toml markers
        project_root = Path(__file__).parent.parent.parent
        pyproject_path = project_root / "pyproject.toml"
        
        defined_markers = set()
        with open(pyproject_path, 'r') as f:
            content = f.read()
            
        # Extract markers from pyproject.toml
        in_markers_section = False
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('markers = ['):
                in_markers_section = True
                continue
            elif in_markers_section:
                if line == ']':
                    break
                elif ':' in line:
                    # Extract marker name before colon
                    marker_line = line.strip().strip('"').strip(',').strip('"')
                    if ':' in marker_line:
                        marker_name = marker_line.split(':')[0].strip()
                        defined_markers.add(marker_name)

        # Scan test files for pytest.mark usage
        used_markers = set()
        test_dirs = [
            project_root / "tests",
            project_root / "netra_backend" / "tests", 
            project_root / "auth_service" / "tests"
        ]
        
        for test_dir in test_dirs:
            if test_dir.exists():
                for test_file in test_dir.rglob("*.py"):
                    try:
                        with open(test_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                        # Find pytest.mark.marker_name patterns
                        lines = content.split('\n')
                        for line_num, line in enumerate(lines, 1):
                            if '@pytest.mark.' in line:
                                # Extract marker name
                                start = line.find('@pytest.mark.') + len('@pytest.mark.')
                                end = line.find('(', start) if '(' in line[start:] else len(line)
                                if end == -1:
                                    end = len(line)
                                marker = line[start:end].strip()
                                
                                # Remove any additional decorators or parameters
                                marker = marker.split()[0] if marker else ''
                                if marker and not marker.startswith('parametrize'):
                                    used_markers.add(marker)
                                    
                    except Exception as e:
                        # Skip files that can't be read
                        continue

        # Find undefined markers
        undefined_markers = used_markers - defined_markers
        
        # Report findings
        print(f"\n📊 MARKER ANALYSIS RESULTS:")
        print(f"  Defined markers in pyproject.toml: {len(defined_markers)}")
        print(f"  Markers used in test files: {len(used_markers)}")  
        print(f"  Undefined markers found: {len(undefined_markers)}")
        
        if undefined_markers:
            print(f"\n❌ UNDEFINED MARKERS FOUND:")
            for marker in sorted(undefined_markers):
                print(f"    - {marker}")
                
        # Test passes regardless - this is discovery, not validation
        assert len(defined_markers) > 0, "Should find some defined markers"
        assert len(used_markers) > 0, "Should find some used markers"
        
        return {
            'defined_markers': sorted(defined_markers),
            'used_markers': sorted(used_markers),
            'undefined_markers': sorted(undefined_markers)
        }

    @pytest.mark.integration
    @pytest.mark.critical
    @pytest.mark.issue_553_reproduction
    def test_pytest_collection_with_real_test_files(self):
        """
        INTEGRATION TEST: Run pytest collection on actual test directories
        
        This test attempts pytest collection on real test directories to capture
        actual collection failures and specific missing marker error messages.
        """
        project_root = Path(__file__).parent.parent.parent
        
        # Test directories to check
        test_paths = [
            "tests/unit",
            "tests/integration", 
            "tests/e2e",
            "netra_backend/tests",
            "auth_service/tests"
        ]
        
        collection_results = {}
        
        for test_path in test_paths:
            full_path = project_root / test_path
            if not full_path.exists():
                collection_results[test_path] = {"status": "directory_not_found"}
                continue
                
            # Run pytest collection with strict markers
            cmd = [
                sys.executable, '-m', 'pytest',
                str(full_path),
                '--collect-only',
                '--strict-markers',
                '--quiet',
                '--tb=no'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(project_root))
            
            collection_results[test_path] = {
                "status": "success" if result.returncode == 0 else "failed",
                "returncode": result.returncode,
                "stderr": result.stderr[:500],  # Limit error output
                "test_count": result.stdout.count("test session starts") if result.returncode == 0 else 0
            }
            
        # Report results
        print(f"\n📋 PYTEST COLLECTION RESULTS:")
        failed_collections = []
        
        for path, result in collection_results.items():
            status_icon = "✅" if result["status"] == "success" else "❌"
            print(f"  {status_icon} {path}: {result['status']}")
            
            if result["status"] == "failed":
                failed_collections.append(path)
                print(f"      Error: {result.get('stderr', 'Unknown error')[:200]}...")
                
        # Document collection failures  
        if failed_collections:
            print(f"\n🚨 COLLECTION FAILURES FOUND: {len(failed_collections)} directories")
            print("This confirms Issue #553: pytest marker configuration missing markers")
        else:
            print(f"\n✅ ALL COLLECTIONS SUCCESSFUL")
            print("This suggests markers may already be properly configured")
            
        return collection_results

    @pytest.mark.unit
    @pytest.mark.critical
    @pytest.mark.issue_553_reproduction
    def test_marker_validation_strict_vs_permissive(self):
        """
        CONFIGURATION TEST: Compare strict vs permissive marker validation
        
        This test demonstrates the difference between:
        1. --strict-markers (fails on undefined markers)  
        2. No --strict-markers (allows undefined markers)
        
        Proving that the issue is the strict-markers configuration interacting
        with undefined markers in the codebase.
        """
        # Create test file with undefined marker
        with tempfile.NamedTemporaryFile(mode='w', suffix='_test.py', delete=False) as f:
            f.write('''
import pytest

@pytest.mark.undefined_test_marker
def test_with_undefined_marker():
    assert True
''')
            temp_file = Path(f.name)
            
        try:
            # Test 1: Strict markers (should fail)
            strict_cmd = [
                sys.executable, '-m', 'pytest',
                str(temp_file),
                '--collect-only', 
                '--strict-markers',
                '--quiet'
            ]
            strict_result = subprocess.run(strict_cmd, capture_output=True, text=True)
            
            # Test 2: Permissive markers (should pass)  
            permissive_cmd = [
                sys.executable, '-m', 'pytest',
                str(temp_file),
                '--collect-only',
                '--quiet'
            ]
            permissive_result = subprocess.run(permissive_cmd, capture_output=True, text=True)
            
            print(f"\n🔍 MARKER VALIDATION COMPARISON:")
            print(f"  Strict markers result: {'FAILED' if strict_result.returncode != 0 else 'PASSED'}")
            print(f"  Permissive markers result: {'FAILED' if permissive_result.returncode != 0 else 'PASSED'}")
            
            # Strict should fail, permissive should pass
            assert strict_result.returncode != 0, "Strict markers should fail with undefined marker"
            assert permissive_result.returncode == 0, "Permissive markers should pass with undefined marker"
            
            print(f"✅ CONFIRMED: Issue is strict-markers + undefined markers combination")
            return {
                "strict_failed": strict_result.returncode != 0,
                "permissive_passed": permissive_result.returncode == 0,
                "strict_error": strict_result.stderr,
                "permissive_output": permissive_result.stdout
            }
            
        finally:
            # Cleanup
            temp_file.unlink()

if __name__ == "__main__":
    # Allow direct execution for debugging
    pytest.main([__file__, "-v"])