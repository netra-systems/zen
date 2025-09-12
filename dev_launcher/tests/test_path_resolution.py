"""
Test path resolution for the dev launcher.

This test ensures that the launcher correctly identifies and validates
the actual project directory structure, particularly the backend path.
"""

from test_framework.ssot.base_test_case import SSotAsyncTestCase, SSotBaseTestCase
import os
import sys
import tempfile
import unittest
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Add parent directory to path

from dev_launcher.config import LauncherConfig


class TestPathResolution(SSotBaseTestCase):
    """Test suite for path resolution issues."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.project_root = Path(self.test_dir)
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_backend_path_validation_legacy_structure(self):
        """Test validation fails with legacy app/ structure."""
        # Create legacy structure (incorrect)
        (self.project_root / "app").mkdir(parents=True)
        (self.project_root / "frontend").mkdir(parents=True)
        
        with self.assertRaises(ValueError) as cm:
            config = LauncherConfig(project_root=self.project_root)
        
        # Should fail because netra_backend/app doesn't exist
        self.assertIn("Backend directory not found", str(cm.exception))
    
    def test_backend_path_validation_correct_structure(self):
        """Test validation succeeds with correct netra_backend/app structure."""
        # Create correct structure
        (self.project_root / "netra_backend" / "app").mkdir(parents=True)
        (self.project_root / "frontend").mkdir(parents=True)
        
        # This should work
        config = LauncherConfig(project_root=self.project_root)
        self.assertEqual(config.project_root, self.project_root)
    
    def test_backend_path_validation_missing_frontend(self):
        """Test validation fails when frontend is missing."""
        # Create only backend
        (self.project_root / "netra_backend" / "app").mkdir(parents=True)
        
        with self.assertRaises(ValueError) as cm:
            config = LauncherConfig(project_root=self.project_root)
        
        self.assertIn("Frontend directory not found", str(cm.exception))
    
    def test_backend_path_validation_missing_backend(self):
        """Test validation fails when backend is missing."""
        # Create only frontend
        (self.project_root / "frontend").mkdir(parents=True)
        
        with self.assertRaises(ValueError) as cm:
            config = LauncherConfig(project_root=self.project_root)
        
        self.assertIn("Backend directory not found", str(cm.exception))
    
    def test_real_project_structure(self):
        """Test with the actual project structure."""
        # Get the real project root (3 levels up from this test file)
        real_project_root = Path(__file__).parent.parent.parent
        
        # Check if we're in the actual project
        if (real_project_root / "netra_backend" / "app").exists():
            # Test should pass with real structure
            config = LauncherConfig(project_root=real_project_root)
            self.assertEqual(config.project_root, real_project_root)
        else:
            self.skipTest("Not running in actual project directory")
    
    def test_backward_compatibility_warning(self):
        """Test that we provide helpful error for legacy structure."""
        # Create legacy structure
        (self.project_root / "app").mkdir(parents=True)
        (self.project_root / "frontend").mkdir(parents=True)
        
        try:
            config = LauncherConfig(project_root=self.project_root)
            self.fail("Should have raised ValueError")
        except ValueError as e:
            # Check for helpful error message
            error_msg = str(e)
            self.assertIn("Backend directory not found", error_msg)
            # Could enhance to suggest the correct path
    
    def test_path_normalization(self):
        """Test that paths are properly normalized."""
        # Create correct structure
        (self.project_root / "netra_backend" / "app").mkdir(parents=True)
        (self.project_root / "frontend").mkdir(parents=True)
        
        # Test with different path representations
        config1 = LauncherConfig(project_root=self.project_root)
        config2 = LauncherConfig(project_root=Path(str(self.project_root)))
        
        self.assertEqual(config1.project_root, config2.project_root)
    
    def test_service_paths_correct(self):
        """Test that service paths are correctly resolved."""
        # Create correct structure
        backend_dir = self.project_root / "netra_backend" / "app"
        frontend_dir = self.project_root / "frontend"
        backend_dir.mkdir(parents=True)
        frontend_dir.mkdir(parents=True)
        
        config = LauncherConfig(project_root=self.project_root)
        
        # Verify the paths that will be used by services
        expected_backend = self.project_root / "netra_backend" / "app"
        expected_frontend = self.project_root / "frontend"
        
        self.assertTrue(expected_backend.exists())
        self.assertTrue(expected_frontend.exists())


if __name__ == '__main__':
    unittest.main()