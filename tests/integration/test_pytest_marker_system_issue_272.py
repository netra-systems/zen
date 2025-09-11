"""
Integration Test for GitHub Issue #272: pytest marker system behavior

PURPOSE: Test the actual pytest collection behavior with missing staging_compatible marker
FOCUS: System-level behavior when collecting tests with undefined markers
"""

import pytest
import subprocess
import sys
from pathlib import Path
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestPytestMarkerSystemIssue272(SSotBaseTestCase):
    """Integration tests for pytest marker collection system"""
    
    def test_strict_marker_enforcement_blocks_collection(self):
        """
        SYSTEM TEST: Verify strict marker enforcement prevents collection
        
        Tests that pytest --strict-markers actually enforces marker definitions
        and blocks collection when undefined markers are encountered
        """
        # Create test content with undefined marker
        test_content = '''
import pytest

@pytest.mark.undefined_test_marker_272
def test_with_undefined_marker():
    assert True
'''
        
        temp_file = Path("temp_undefined_marker_test.py")
        try:
            temp_file.write_text(test_content)
            
            # Test strict marker enforcement
            result = subprocess.run([
                sys.executable, "-m", "pytest",
                "--collect-only", 
                "--strict-markers",
                str(temp_file)
            ], capture_output=True, text=True)
            
            # Verify collection fails with strict markers
            assert result.returncode != 0, "Collection should fail with undefined marker"
            full_output = result.stdout + result.stderr
            assert "not found in `markers` configuration option" in full_output, \
                f"Expected marker error message. Full output: {full_output}"
            
        finally:
            if temp_file.exists():
                temp_file.unlink()
    
    def test_affected_e2e_files_collection_behavior(self):
        """
        Test actual collection behavior of the 6 affected E2E files
        
        This test attempts to collect the actual files mentioned in issue #272
        to demonstrate the collection failure in practice
        """
        affected_files = [
            "tests/e2e/test_complete_authenticated_chat_workflow_e2e.py",
            "tests/e2e/test_authenticated_multi_agent_chat_flow_e2e.py",
            "tests/e2e/test_business_value_chat_recovery_e2e.py", 
            "tests/e2e/test_agent_state_sync_integration_helpers.py",
            "tests/e2e/test_websocket_notifier_complete_e2e.py",
            "tests/e2e/test_workflow_orchestrator_golden_path.py"
        ]
        
        collection_failures = []
        
        for file_path in affected_files:
            full_path = Path(file_path)
            if full_path.exists():
                # Attempt collection with strict markers
                result = subprocess.run([
                    sys.executable, "-m", "pytest",
                    "--collect-only",
                    "--strict-markers", 
                    str(full_path)
                ], capture_output=True, text=True)
                
                full_output = result.stdout + result.stderr
                if result.returncode != 0 and "staging_compatible" in full_output:
                    collection_failures.append({
                        'file': file_path,
                        'error': full_output.strip()
                    })
        
        # We expect to find at least some files that fail due to staging_compatible marker
        assert len(collection_failures) > 0, \
            f"Expected to find files failing collection due to staging_compatible marker, but found none"
        
        print(f"Found {len(collection_failures)} files failing collection due to staging_compatible marker:")
        for failure in collection_failures:
            print(f"  - {failure['file']}")
    
    def test_pytest_configuration_analysis(self):
        """
        Analyze current pytest configuration to understand marker definitions
        """
        config_files = ["pytest.ini", "pyproject.toml", "setup.cfg"]
        config_analysis = {}
        
        for config_file in config_files:
            path = Path(config_file)
            if path.exists():
                content = path.read_text()
                config_analysis[config_file] = {
                    'exists': True,
                    'has_markers_section': 'markers' in content.lower(),
                    'has_staging_compatible': 'staging_compatible' in content,
                    'content_sample': content[:500] if len(content) > 500 else content
                }
            else:
                config_analysis[config_file] = {'exists': False}
        
        # Log configuration state for debugging
        print("Pytest configuration analysis:")
        for config_file, analysis in config_analysis.items():
            print(f"  {config_file}: {analysis}")
        
        # At least one config file should exist for pytest configuration
        existing_configs = [f for f, a in config_analysis.items() if a.get('exists')]
        assert len(existing_configs) > 0, "No pytest configuration files found"