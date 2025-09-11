"""
Unit Test: WebSocket SSOT Import Path Validation

PURPOSE: Validate that websocket_ssot.py uses correct import paths for agent_websocket_bridge

CRITICAL ISSUE: 
- Lines 732 and 747 in websocket_ssot.py have BROKEN imports:
  from netra_backend.app.agents.agent_websocket_bridge import create_agent_websocket_bridge

- Should be CORRECT imports:
  from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge

This test validates the import paths and demonstrates the failure with broken imports.
Tests should FAIL with current broken imports, PASS after fix.

Business Impact: Golden Path protection - $500K+ ARR depends on WebSocket agent functionality
"""

import sys
import importlib
import logging
from unittest.mock import patch, MagicMock
import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase

logger = logging.getLogger(__name__)


class TestWebSocketSSotImportPathValidation(SSotBaseTestCase):
    """Unit tests validating WebSocket SSOT import paths for agent bridge functionality."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.category = "UNIT"
        self.test_name = "websocket_ssot_import_validation"
    
    def test_broken_import_path_fails_as_expected(self):
        """Test that broken import path fails with ImportError."""
        
        # BROKEN IMPORT PATH - Should fail
        broken_import_path = "netra_backend.app.agents.agent_websocket_bridge"
        
        with pytest.raises(ImportError) as exc_info:
            # This should fail because the module doesn't exist at this path
            importlib.import_module(broken_import_path)
        
        # Verify it's the specific missing module error
        assert "No module named 'netra_backend.app.agents.agent_websocket_bridge'" in str(exc_info.value)
        
        # Log the expected failure for Golden Path protection
        logger.critical(f"EXPECTED FAILURE: Broken import path {broken_import_path} correctly fails")
    
    def test_correct_import_path_succeeds(self):
        """Test that correct import path succeeds."""
        
        # CORRECT IMPORT PATH - Should succeed
        correct_import_path = "netra_backend.app.services.agent_websocket_bridge"
        
        try:
            # This should succeed because the module exists at this path
            module = importlib.import_module(correct_import_path)
            
            # Verify the create_agent_websocket_bridge function exists
            assert hasattr(module, 'create_agent_websocket_bridge'), \
                "create_agent_websocket_bridge function not found in module"
            
            logger.info(f"SUCCESS: Correct import path {correct_import_path} works")
            
        except ImportError as e:
            pytest.fail(f"Correct import path failed unexpectedly: {e}")
    
    def test_websocket_ssot_file_has_broken_imports(self):
        """Test that websocket_ssot.py file currently contains broken import paths."""
        
        import os
        # Get project root by going up from test file location
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
        
        websocket_ssot_path = os.path.join(
            project_root, 
            "netra_backend", "app", "routes", "websocket_ssot.py"
        )
        
        # Verify file exists
        assert os.path.exists(websocket_ssot_path), f"websocket_ssot.py not found at {websocket_ssot_path}"
        
        # Read file content
        with open(websocket_ssot_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for broken import patterns
        broken_import_line = "from netra_backend.app.agents.agent_websocket_bridge import create_agent_websocket_bridge"
        
        if broken_import_line in content:
            # File contains broken imports - this demonstrates the issue
            logger.error(f"BROKEN IMPORT DETECTED in websocket_ssot.py: {broken_import_line}")
            
            # Count occurrences
            import_count = content.count(broken_import_line)
            logger.error(f"Found {import_count} occurrences of broken import")
            
            # This test should fail when broken imports exist
            pytest.fail(f"websocket_ssot.py contains {import_count} broken import statements")
        else:
            # File has been fixed - imports are correct
            correct_import_line = "from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge"
            assert correct_import_line in content, \
                "Neither broken nor correct import found in websocket_ssot.py"
            
            logger.info("SUCCESS: websocket_ssot.py has correct import paths")
    
    def test_websocket_ssot_import_line_numbers(self):
        """Test specific line numbers where broken imports should be fixed."""
        
        import os
        # Get project root by going up from test file location
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
        
        websocket_ssot_path = os.path.join(
            project_root, 
            "netra_backend", "app", "routes", "websocket_ssot.py"
        )
        
        with open(websocket_ssot_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Check specific line numbers mentioned in the issue
        target_lines = [732, 747]  # Lines 732 and 747 have broken imports
        broken_imports_found = []
        
        for line_num in target_lines:
            if line_num <= len(lines):
                line_content = lines[line_num - 1].strip()  # Convert to 0-based index
                
                if "from netra_backend.app.agents.agent_websocket_bridge" in line_content:
                    broken_imports_found.append((line_num, line_content))
                    logger.error(f"BROKEN IMPORT at line {line_num}: {line_content}")
        
        if broken_imports_found:
            # This test should fail when broken imports exist at specific lines
            error_msg = f"Found broken imports at lines: {[line[0] for line in broken_imports_found]}"
            logger.critical(f"GOLDEN PATH FAILURE: {error_msg}")
            pytest.fail(error_msg)
        else:
            logger.info("SUCCESS: No broken imports found at target line numbers")
    
    def test_import_replacement_suggestion(self):
        """Test that provides the exact replacement needed for the fix."""
        
        broken_import = "from netra_backend.app.agents.agent_websocket_bridge import create_agent_websocket_bridge"
        correct_import = "from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge"
        
        # Log the exact fix needed
        logger.info("=== WEBSOCKET SSOT IMPORT FIX REQUIRED ===")
        logger.info(f"REPLACE: {broken_import}")
        logger.info(f"WITH:    {correct_import}")
        logger.info("LOCATIONS: websocket_ssot.py lines 732 and 747")
        logger.info("IMPACT: Golden Path restoration, $500K+ ARR protection")
        
        # Verify the replacement would work
        try:
            # Test that we can import from the correct location
            module = importlib.import_module("netra_backend.app.services.agent_websocket_bridge")
            assert hasattr(module, 'create_agent_websocket_bridge')
            logger.info("VERIFIED: Correct import path is functional")
        except ImportError as e:
            pytest.fail(f"Correct import path validation failed: {e}")

    def tearDown(self):
        """Clean up test environment."""
        super().tearDown()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])