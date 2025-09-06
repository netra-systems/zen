"""Test alembic.ini path configuration to expose issues."""

import sys
from pathlib import Path
from test_framework.database.test_database_manager import TestDatabaseManager
from shared.isolated_environment import IsolatedEnvironment

import pytest

from netra_backend.app.db.migration_utils import (
_get_alembic_ini_path,
create_alembic_config)

# Define project root paths
project_root = Path(__file__).parent.parent.parent.parent  # Go up to netra-core-generation-1
correct_project_root = project_root  # Same for this case

class TestAlembicIniPath:
    """Test suite to expose alembic.ini path configuration issues."""
    
    def test_expected_alembic_ini_path_should_exist(self):
        """Test that the expected alembic.ini path exists in the correct location."""
        # Get the path that the code expects
        expected_path = _get_alembic_ini_path()
        
        # The code now correctly expects: config/alembic.ini (at project root)
        assert expected_path.endswith("config\\alembic.ini") or \
        expected_path.endswith("config/alembic.ini"), \
        f"Unexpected path: {expected_path}"
        
        # This should now pass because the file exists at this location
        assert Path(expected_path).exists(), \
        f"alembic.ini not found at expected path: {expected_path}"
    
        def test_single_alembic_ini_location(self):
            """Test that only one alembic.ini exists in the correct location."""
        
        # Should NOT exist at root (removed duplicate)
            root_alembic = project_root / "alembic.ini"
            assert not root_alembic.exists(), f"Duplicate alembic.ini should not exist at root: {root_alembic}"
        
        # Should exist at config/alembic.ini
            config_alembic = project_root / "config" / "alembic.ini"
            assert config_alembic.exists(), f"Config alembic.ini not found at: {config_alembic}"
        
        # Should NOT exist at netra_backend/config/alembic.ini (incorrect location)
            incorrect_path = project_root / "netra_backend" / "config" / "alembic.ini"
            assert not incorrect_path.exists(), \
            f"Unexpected alembic.ini found at: {incorrect_path}"
    
            def test_create_alembic_config_succeeds_with_fixed_path(self):
                """Test that create_alembic_config succeeds with fixed path calculation."""
        # This should succeed now that path is fixed
                cfg = create_alembic_config("postgresql://test:test@localhost/test")
        
        # Verify it's a valid config object
                assert cfg is not None
                assert hasattr(cfg, 'get_main_option')
                assert cfg.get_main_option('sqlalchemy.url') == "postgresql://test:test@localhost/test"
    
                def test_correct_path_calculation_for_alembic_ini(self):
                    """Test what the correct path calculation should be."""
                    pass
        # The file should exist at the project root config directory
                    config_path = project_root / "config" / "alembic.ini"
        
                    assert Path(config_path).exists(), \
                    f"File should exist at config path: {config_path}"
    
    # Mock: Component isolation for testing without external dependencies
                    def test_startup_module_fails_with_wrong_path(self, mock_path):
                        """Test that startup module fails when looking for alembic.ini in wrong location."""
        # Mock the path to simulate the incorrect behavior
        # Mock: Generic component isolation for controlled unit testing
                        mock_path_instance = MagicNone  # TODO: Use real service instance
                        mock_path_instance.exists.return_value = False
                        mock_path.return_value = mock_path_instance
        
        # This simulates what happens in startup_module when it can't find alembic.ini
                        with pytest.raises(FileNotFoundError) as exc_info:
                            create_alembic_config("postgresql://test:test@localhost/test")
        
                            assert "Alembic configuration file not found" in str(exc_info.value)
                            pass