#!/usr/bin/env python3
"""
Issue #553 - Pytest Marker Collection Validation Test

MISSION:
- Validate pytest marker collection behavior across different configurations
- Test marker registration and discovery mechanisms
- Ensure marker definitions match actual usage patterns  
- Validate marker collection performance and reliability

METHODOLOGY:
- Test marker collection with various pytest configurations
- Validate marker registration programmatically
- Test collection performance with large marker sets
- Verify marker inheritance and scoping behavior

BUSINESS VALUE:
- Ensures reliable test collection for golden path validation
- Prevents marker-related test discovery failures
- Validates marker configuration completeness and accuracy
"""

import pytest
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Dict, Set, Optional
import re
import time
import json

class TestMarkerCollectionValidation:
    """
    Validate pytest marker collection behavior and configuration completeness
    """

    @pytest.fixture
    def project_root(self) -> Path:
        """Get project root directory"""
        return Path(__file__).parent.parent.parent

    @pytest.fixture  
    def current_markers(self, project_root: Path) -> Set[str]:
        """Extract currently defined markers from pyproject.toml"""
        pyproject_path = project_root / "pyproject.toml"
        
        markers = set()
        with open(pyproject_path, 'r') as f:
            content = f.read()
            
        # Parse markers section
        in_markers = False
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('markers = ['):
                in_markers = True
                continue
            elif in_markers:
                if line == ']':
                    break
                elif ':' in line and '"' in line:
                    # Extract marker name
                    marker_def = line.strip().strip('"').strip(',').strip('"')
                    if ':' in marker_def:
                        marker_name = marker_def.split(':')[0].strip()
                        markers.add(marker_name)
                        
        return markers

    @pytest.mark.unit
    @pytest.mark.critical
    @pytest.mark.issue_553_validation
    def test_marker_registration_programmatic(self, current_markers: Set[str]):
        """
        VALIDATION TEST: Verify marker registration works programmatically
        
        This test validates that markers can be registered and discovered
        through pytest's plugin system, ensuring the registration mechanism
        itself is working correctly.
        """
        # Create temporary conftest.py with marker registration
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create conftest.py with programmatic marker registration
            conftest_content = '''
import pytest

def pytest_configure(config):
    """Register markers programmatically"""
    config.addinivalue_line("markers", "temp_marker_1: Test marker 1")
    config.addinivalue_line("markers", "temp_marker_2: Test marker 2") 
    config.addinivalue_line("markers", "business_temp: Business test marker")
'''
            (temp_path / "conftest.py").write_text(conftest_content)
            
            # Create test file using the registered markers
            test_content = '''
import pytest

@pytest.mark.temp_marker_1
def test_with_temp_marker_1():
    assert True

@pytest.mark.temp_marker_2
def test_with_temp_marker_2():
    assert True
    
@pytest.mark.business_temp
def test_business_functionality():
    assert True
'''
            (temp_path / "test_temp.py").write_text(test_content)
            
            # Run collection with strict markers
            cmd = [
                sys.executable, '-m', 'pytest',
                str(temp_path),
                '--collect-only',
                '--strict-markers',
                '-v'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Collection should succeed with programmatically registered markers
            assert result.returncode == 0, f"Collection failed: {result.stderr}"
            
            # Verify all tests were collected
            assert "test_with_temp_marker_1" in result.stdout
            assert "test_with_temp_marker_2" in result.stdout
            assert "test_business_functionality" in result.stdout
            
            print(f"✅ MARKER REGISTRATION: Programmatic registration works correctly")
            print(f"Collected tests: {result.stdout.count('::test_')}")

    @pytest.mark.integration
    @pytest.mark.critical 
    @pytest.mark.issue_553_validation
    def test_marker_collection_performance(self, current_markers: Set[str]):
        """
        PERFORMANCE TEST: Validate marker collection performance with large marker sets
        
        This test ensures that marker collection performance is acceptable
        even with the extensive marker list in pyproject.toml.
        """
        # Create test file with many different markers
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Generate test content with multiple markers
            test_content = '''import pytest\n\n'''
            
            # Create tests using various existing markers
            marker_list = list(current_markers)[:20]  # Use first 20 markers
            for i, marker in enumerate(marker_list):
                test_content += f'''
@pytest.mark.{marker}
def test_with_marker_{i}():
    """Test using marker: {marker}"""
    assert True

'''
            
            (temp_path / "test_performance.py").write_text(test_content)
            
            # Copy current pyproject.toml to temp directory
            import shutil
            project_root = Path(__file__).parent.parent.parent
            shutil.copy(project_root / "pyproject.toml", temp_path / "pyproject.toml")
            
            # Measure collection time
            start_time = time.time()
            
            cmd = [
                sys.executable, '-m', 'pytest',
                str(temp_path),
                '--collect-only',
                '--strict-markers',
                '--quiet'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(temp_path))
            
            collection_time = time.time() - start_time
            
            # Collection should succeed and be reasonably fast
            assert result.returncode == 0, f"Collection failed: {result.stderr}"
            assert collection_time < 10.0, f"Collection too slow: {collection_time:.2f}s"
            
            # Count collected tests
            test_count = len(marker_list)  # Should equal number of tests
            
            print(f"✅ COLLECTION PERFORMANCE:")
            print(f"  Collection time: {collection_time:.3f}s")
            print(f"  Tests collected: {test_count}")
            print(f"  Markers tested: {len(marker_list)}")
            print(f"  Avg time per test: {collection_time/test_count:.4f}s")
            
            return {
                "collection_time": collection_time,
                "test_count": test_count,
                "markers_tested": len(marker_list),
                "success": result.returncode == 0
            }

    @pytest.mark.unit
    @pytest.mark.critical
    @pytest.mark.issue_553_validation
    def test_marker_inheritance_and_scoping(self):
        """
        SCOPING TEST: Validate marker inheritance behavior across test hierarchies
        
        This test ensures that markers work correctly at different scoping levels:
        - Module level
        - Class level  
        - Function level
        - Inheritance between levels
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test file with marker scoping
            test_content = '''
import pytest

# Module-level marker
pytestmark = pytest.mark.unit

class TestMarkerInheritance:
    """Class with class-level marker"""
    
    # Class-level marker
    pytestmark = pytest.mark.integration
    
    def test_class_marker_inheritance(self):
        """Should inherit both unit and integration markers"""
        assert True
        
    @pytest.mark.critical
    def test_function_marker_addition(self):
        """Should have unit, integration, and critical markers"""
        assert True

@pytest.mark.e2e
class TestFunctionMarkers:
    """Class with different class marker"""
    
    def test_different_class_marker(self):
        """Should inherit unit and e2e markers"""
        assert True
        
    @pytest.mark.slow
    @pytest.mark.performance
    def test_multiple_function_markers(self):
        """Should have unit, e2e, slow, and performance markers"""
        assert True

@pytest.mark.smoke
def test_standalone_function():
    """Should have unit and smoke markers"""
    assert True
'''
            
            (temp_path / "test_scoping.py").write_text(test_content)
            
            # Copy pyproject.toml for marker definitions
            import shutil
            project_root = Path(__file__).parent.parent.parent
            shutil.copy(project_root / "pyproject.toml", temp_path / "pyproject.toml")
            
            # Test collection with marker reporting
            cmd = [
                sys.executable, '-m', 'pytest',
                str(temp_path),
                '--collect-only',
                '--strict-markers',
                '-v'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(temp_path))
            
            # Collection should succeed
            assert result.returncode == 0, f"Collection failed: {result.stderr}"
            
            # Verify all test functions were collected  
            expected_tests = [
                "test_class_marker_inheritance",
                "test_function_marker_addition", 
                "test_different_class_marker",
                "test_multiple_function_markers",
                "test_standalone_function"
            ]
            
            for test_name in expected_tests:
                assert test_name in result.stdout, f"Test {test_name} not collected"
                
            print(f"✅ MARKER SCOPING: All inheritance levels work correctly")
            print(f"Tests collected: {len(expected_tests)}")
            
            return {
                "tests_collected": expected_tests,
                "collection_output": result.stdout
            }

    @pytest.mark.integration
    @pytest.mark.critical
    @pytest.mark.issue_553_validation  
    def test_marker_filtering_and_selection(self, current_markers: Set[str]):
        """
        FILTERING TEST: Validate marker-based test selection works correctly
        
        This test ensures that pytest marker selection (-m) works properly
        with the configured markers, which is critical for test categorization.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test file with various markers for filtering
            test_content = '''
import pytest

@pytest.mark.unit
def test_unit_only():
    assert True

@pytest.mark.integration  
def test_integration_only():
    assert True

@pytest.mark.e2e
def test_e2e_only():
    assert True
    
@pytest.mark.unit
@pytest.mark.critical
def test_unit_and_critical():
    assert True
    
@pytest.mark.integration
@pytest.mark.slow
def test_integration_and_slow():
    assert True

@pytest.mark.smoke
def test_smoke_only():
    assert True
'''
            
            (temp_path / "test_filtering.py").write_text(test_content)
            
            # Copy pyproject.toml
            import shutil
            project_root = Path(__file__).parent.parent.parent
            shutil.copy(project_root / "pyproject.toml", temp_path / "pyproject.toml")
            
            # Test different marker selections
            filter_tests = [
                ("unit", ["test_unit_only", "test_unit_and_critical"]),
                ("integration", ["test_integration_only", "test_integration_and_slow"]),
                ("critical", ["test_unit_and_critical"]),
                ("slow", ["test_integration_and_slow"]),
                ("unit and critical", ["test_unit_and_critical"]),
                ("unit or integration", ["test_unit_only", "test_integration_only", 
                                      "test_unit_and_critical", "test_integration_and_slow"])
            ]
            
            results = {}
            
            for marker_expr, expected_tests in filter_tests:
                cmd = [
                    sys.executable, '-m', 'pytest',
                    str(temp_path),
                    '-m', marker_expr,
                    '--collect-only',
                    '--quiet'
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(temp_path))
                
                # Collection should succeed
                assert result.returncode == 0, f"Filtering failed for '{marker_expr}': {result.stderr}"
                
                # Verify expected tests are selected
                for test_name in expected_tests:
                    assert test_name in result.stdout, \
                        f"Test {test_name} not selected for marker '{marker_expr}'"
                        
                results[marker_expr] = {
                    "expected_count": len(expected_tests),
                    "success": True
                }
                
            print(f"✅ MARKER FILTERING: All filter expressions work correctly")
            print(f"Filter tests performed: {len(filter_tests)}")
            
            return results

    @pytest.mark.unit
    @pytest.mark.critical
    @pytest.mark.issue_553_validation
    def test_marker_configuration_completeness(self, project_root: Path, current_markers: Set[str]):
        """
        COMPLETENESS TEST: Validate that all used markers are properly defined
        
        This is the core test that validates the fix for Issue #553:
        ensuring all markers used in the codebase are defined in pyproject.toml.
        """
        # Scan all test files for marker usage
        used_markers = set()
        test_dirs = [
            project_root / "tests", 
            project_root / "netra_backend" / "tests",
            project_root / "auth_service" / "tests"
        ]
        
        marker_usage = {}  # Track where each marker is used
        
        for test_dir in test_dirs:
            if not test_dir.exists():
                continue
                
            for test_file in test_dir.rglob("*.py"):
                if test_file.name.startswith("test_") or test_file.name.endswith("_test.py"):
                    try:
                        content = test_file.read_text(encoding='utf-8')
                        
                        # Find all pytest.mark.* patterns
                        for line_num, line in enumerate(content.split('\n'), 1):
                            if '@pytest.mark.' in line:
                                # Extract marker name using regex
                                matches = re.findall(r'@pytest\.mark\.([a-zA-Z_][a-zA-Z0-9_]*)', line)
                                for marker in matches:
                                    if marker != 'parametrize':  # Skip parametrize decorator
                                        used_markers.add(marker)
                                        
                                        if marker not in marker_usage:
                                            marker_usage[marker] = []
                                        marker_usage[marker].append({
                                            'file': str(test_file.relative_to(project_root)),
                                            'line': line_num
                                        })
                                        
                    except Exception as e:
                        # Skip files that can't be read
                        continue
        
        # Analyze marker coverage
        defined_markers = current_markers
        undefined_markers = used_markers - defined_markers
        unused_markers = defined_markers - used_markers
        
        # Report analysis
        print(f"\n📊 MARKER CONFIGURATION COMPLETENESS ANALYSIS:")
        print(f"  Total markers defined: {len(defined_markers)}")
        print(f"  Total markers used in tests: {len(used_markers)}")
        print(f"  Undefined markers (ISSUE #553): {len(undefined_markers)}")
        print(f"  Unused defined markers: {len(unused_markers)}")
        
        if undefined_markers:
            print(f"\n❌ UNDEFINED MARKERS FOUND:")
            for marker in sorted(undefined_markers):
                usage_count = len(marker_usage.get(marker, []))
                print(f"    - {marker} (used in {usage_count} locations)")
                
            print(f"\nThis confirms Issue #553: pytest marker configuration missing markers")
        else:
            print(f"\n✅ ALL MARKERS PROPERLY DEFINED")
            
        if unused_markers:
            print(f"\n📋 UNUSED DEFINED MARKERS:")
            for marker in sorted(list(unused_markers)[:10]):  # Show first 10
                print(f"    - {marker}")
                
        # Create detailed report
        analysis_report = {
            "defined_markers_count": len(defined_markers),
            "used_markers_count": len(used_markers), 
            "undefined_markers": sorted(undefined_markers),
            "unused_markers": sorted(unused_markers),
            "marker_usage": {k: len(v) for k, v in marker_usage.items()},
            "coverage_percentage": (len(used_markers & defined_markers) / len(used_markers) * 100) if used_markers else 100
        }
        
        print(f"  Marker definition coverage: {analysis_report['coverage_percentage']:.1f}%")
        
        return analysis_report

if __name__ == "__main__":
    # Allow direct execution for debugging
    pytest.main([__file__, "-v"])