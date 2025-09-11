"""
Unit Test for GitHub Issue #272: Missing 'staging_compatible' pytest marker

PURPOSE: Reproduce the exact error when pytest encounters the undefined marker
EXPECTED: Test collection should fail with 'staging_compatible' not found in markers configuration
"""

import pytest
import subprocess
import sys
from pathlib import Path


class TestPytestMarkerValidationIssue272:
    """Test suite to reproduce missing staging_compatible marker issue"""
    
    def test_staging_compatible_marker_not_configured(self):
        """
        PROOF TEST: Verify staging_compatible marker causes collection failure
        
        This test creates a minimal file with the problematic marker and
        attempts collection to reproduce the exact error reported in issue #272
        """
        # Create a temporary test file with the problematic marker
        temp_test_content = '''
import pytest

@pytest.mark.staging_compatible
def test_example_with_staging_compatible():
    """Example test using the undefined marker"""
    assert True
'''
        
        temp_test_file = Path("temp_staging_marker_test.py")
        try:
            # Write temporary test file
            temp_test_file.write_text(temp_test_content)
            
            # Attempt pytest collection with strict marker checking
            result = subprocess.run([
                sys.executable, "-m", "pytest",
                "--collect-only",
                "--strict-markers",
                str(temp_test_file)
            ], capture_output=True, text=True, cwd=Path.cwd())
            
            # Verify the specific error occurs
            assert result.returncode != 0, "Expected collection to fail with strict markers"
            # The error appears in stdout, not stderr for pytest collection errors
            full_output = result.stdout + result.stderr
            assert "'staging_compatible' not found in" in full_output, \
                f"Expected marker error not found. Full output: {full_output}"
            
        finally:
            # Clean up temporary file
            if temp_test_file.exists():
                temp_test_file.unlink()
    
    def test_pytest_config_lacks_staging_compatible_marker(self):
        """
        Verify that pytest.ini or pyproject.toml doesn't define staging_compatible marker
        """
        # Check pytest.ini
        pytest_ini = Path("pytest.ini")
        if pytest_ini.exists():
            config_content = pytest_ini.read_text()
            assert "staging_compatible" not in config_content, \
                "staging_compatible should not be defined in pytest.ini yet"
        
        # Check pyproject.toml
        pyproject_toml = Path("pyproject.toml")
        if pyproject_toml.exists():
            config_content = pyproject_toml.read_text()
            assert "staging_compatible" not in config_content, \
                "staging_compatible should not be defined in pyproject.toml yet"
    
    def test_affected_e2e_files_use_staging_compatible_marker(self):
        """
        Verify that the 6 affected E2E files actually use the staging_compatible marker
        """
        affected_files = [
            "tests/e2e/test_complete_authenticated_chat_workflow_e2e.py",
            "tests/e2e/test_authenticated_multi_agent_chat_flow_e2e.py", 
            "tests/e2e/test_business_value_chat_recovery_e2e.py",
            "tests/e2e/test_agent_state_sync_integration_helpers.py",
            "tests/e2e/test_websocket_notifier_complete_e2e.py",
            "tests/e2e/test_workflow_orchestrator_golden_path.py"
        ]
        
        files_with_marker = []
        for file_path in affected_files:
            full_path = Path(file_path)
            if full_path.exists():
                try:
                    content = full_path.read_text(encoding='utf-8')
                    if "staging_compatible" in content:
                        files_with_marker.append(file_path)
                except UnicodeDecodeError:
                    # Try with different encoding
                    try:
                        content = full_path.read_text(encoding='latin-1')
                        if "staging_compatible" in content:
                            files_with_marker.append(file_path)
                    except Exception as e:
                        print(f"Could not read {file_path}: {e}")
        
        assert len(files_with_marker) > 0, \
            f"Expected to find staging_compatible marker in E2E files, but found none. Checked: {affected_files}"
        
        print(f"Found staging_compatible marker in {len(files_with_marker)} files: {files_with_marker}")