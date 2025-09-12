"""
Test for backend startup path issue.
This test exposes the incorrect app directory path configuration.
"""

from test_framework.ssot.base_test_case import SSotAsyncTestCase, SSotBaseTestCase
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment


class TestBackendStartupPath(SSotBaseTestCase):
    """Test that backend server script correctly locates the app directory."""
    
    def setUp(self):
        """Set up test environment."""
        self.project_root = Path(__file__).parent.parent.parent
        self.run_server_script = self.project_root / "scripts" / "run_server.py"
        
    def test_backend_app_directory_path(self):
        """Test that run_server.py looks for app in the correct location."""
        # The app is actually at netra_backend/app, not /app
        correct_app_path = self.project_root / "netra_backend" / "app"
        incorrect_app_path = self.project_root / "app"
        
        # Verify the correct path exists
        self.assertTrue(
            correct_app_path.exists(),
            f"Expected app directory at {correct_app_path} does not exist"
        )
        
        # Verify the incorrect path does NOT exist
        self.assertFalse(
            incorrect_app_path.exists(),
            f"Incorrect app directory at {incorrect_app_path} should not exist"
        )
        
        # Try to run the server script with --help to test path checking
        # This should fail with the current implementation
        result = subprocess.run(
            [sys.executable, str(self.run_server_script), "--help"],
            capture_output=True,
            text=True,
            cwd=str(self.project_root)
        )
        
        # The current implementation will fail because it's looking in the wrong place
        # This assertion will fail initially, proving the bug exists
        self.assertEqual(
            result.returncode, 0,
            f"run_server.py failed to find app directory. Error: {result.stderr}"
        )
        
    def test_uvicorn_import_path(self):
        """Test that the uvicorn import path is correct."""
        # The script uses "app.main:app" but should use "netra_backend.app.main:app"
        with open(self.run_server_script, 'r') as f:
            content = f.read()
            
        # Check for incorrect import path
        self.assertNotIn(
            '"app.main:app"',
            content,
            "Script uses incorrect import path 'app.main:app' instead of 'netra_backend.app.main:app'"
        )
        
        # Check for correct import path
        self.assertIn(
            '"netra_backend.app.main:app"',
            content,
            "Script should use 'netra_backend.app.main:app' import path"
        )


if __name__ == '__main__':
    unittest.main()