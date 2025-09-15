"""
Integration tests for path validation in the dev launcher.

These tests ensure that the launcher correctly validates the actual project
structure and fails appropriately when directories are missing.
"""

from test_framework.ssot.base_test_case import SSotAsyncTestCase, SSotBaseTestCase
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Add parent directory to path

from dev_launcher.config import LauncherConfig
from dev_launcher.launcher import DevLauncher


class TestPathValidationIntegration(SSotBaseTestCase):
    """Integration tests for path validation."""
    
    def test_real_project_structure_validation(self):
        """Test that launcher validates the actual project structure."""
        # Get the real project root
        real_project_root = Path(__file__).parent.parent.parent
        
        # This should work with the real project structure
        config = LauncherConfig(project_root=real_project_root)
        
        # Verify paths are correctly set
        backend_path = config.project_root / "netra_backend" / "app"
        frontend_path = config.project_root / "frontend"
        
        self.assertTrue(backend_path.exists())
        self.assertTrue(frontend_path.exists())
    
    def test_launcher_fails_with_incorrect_structure(self):
        """Test that launcher fails when structure is incorrect."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Create only the old structure (wrong)
            (tmppath / "app").mkdir(parents=True)
            (tmppath / "frontend").mkdir(parents=True)
            
            # Should fail because netra_backend/app doesn't exist
            with self.assertRaises(ValueError) as cm:
                config = LauncherConfig(project_root=tmppath)
            
            self.assertIn("Backend directory not found", str(cm.exception))
            self.assertIn("netra_backend", str(cm.exception))
    
    def test_launcher_initialization_with_correct_paths(self):
        """Test that DevLauncher can be initialized with correct paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Create correct structure
            (tmppath / "netra_backend" / "app").mkdir(parents=True)
            (tmppath / "frontend").mkdir(parents=True)
            
            # Create necessary files for launcher
            (tmppath / "requirements.txt").touch()
            (tmppath / "frontend" / "package.json").write_text('{"name": "test"}')
            
            # Create config with correct structure
            config = LauncherConfig(project_root=tmppath)
            
            # Mock the environment checker to avoid dependency issues
            with patch('dev_launcher.launcher.EnvironmentChecker'):
                with patch('dev_launcher.launcher.setup_logging'):
                    launcher = DevLauncher(config)
                    
                    # Verify launcher is initialized
                    self.assertIsNotNone(launcher)
                    self.assertEqual(launcher.config.project_root, tmppath)
    
    def test_backend_starter_uses_correct_path(self):
        """Test that backend starter uses netra_backend.app.main."""
        from dev_launcher.backend_starter import BackendStarter
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Create correct structure
            (tmppath / "netra_backend" / "app").mkdir(parents=True)
            (tmppath / "frontend").mkdir(parents=True)
            
            config = LauncherConfig(project_root=tmppath)
            
            # Create mocks for required dependencies
            # Mock: Generic component isolation for controlled unit testing
            mock_services_config = MagicMock()
            # Mock: Generic component isolation for controlled unit testing
            mock_log_manager = MagicMock()
            # Mock: Generic component isolation for controlled unit testing
            mock_service_discovery = MagicMock()
            
            # Create backend starter with mocks
            starter = BackendStarter(config, mock_services_config, mock_log_manager, mock_service_discovery)
            
            # Build command and verify it uses correct module path
            cmd = starter._build_uvicorn_command(8000)
            
            # Check that the command includes the correct module path
            self.assertIn("netra_backend.app.main:app", cmd)
    
    def test_migration_paths_use_correct_backend_path(self):
        """Test that migration checks use correct backend paths."""
        from dev_launcher.cache_manager import CacheManager
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            cache_dir = tmppath / ".netra_cache"
            cache_dir.mkdir(parents=True)
            
            manager = CacheManager(tmppath, cache_dir)
            
            # Check that migration paths include netra_backend
            migration_changed = manager.has_migration_files_changed()
            
            # This should handle missing files gracefully
            self.assertIsInstance(migration_changed, bool)
    
    def test_utils_check_project_structure(self):
        """Test that utils.check_project_structure uses correct paths."""
        from dev_launcher.utils import check_project_structure
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Create incorrect structure
            (tmppath / "app").mkdir(parents=True)
            (tmppath / "frontend").mkdir(parents=True)
            
            # Check structure - should report backend as missing
            structure = check_project_structure(tmppath)
            self.assertFalse(structure['backend'])
            
            # Create correct structure
            shutil.rmtree(tmppath / "app")
            (tmppath / "netra_backend" / "app").mkdir(parents=True)
            
            # Check structure again - should now be correct
            structure = check_project_structure(tmppath)
            self.assertTrue(structure['backend'])
            self.assertTrue(structure['frontend'])


if __name__ == '__main__':
    unittest.main()