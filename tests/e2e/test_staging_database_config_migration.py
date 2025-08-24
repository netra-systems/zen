"""Test to verify DatabaseConfig migration is complete and staging deployment issues.

This test reproduces the staging error:
RuntimeError: Database engine creation failed: name 'DatabaseConfig' is not defined

Root cause: Incomplete migration from DatabaseConfig static attributes to get_unified_config().
"""

import os
import sys
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Optional

# Setup path for imports
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.app.core.configuration.base import get_unified_config


class TestDatabaseConfigMigration:
    """Test suite to verify DatabaseConfig migration and prevent staging deployment failures."""
    
    def test_postgres_core_uses_unified_config(self):
        """Verify postgres_core.py uses get_unified_config instead of DatabaseConfig attributes.
        
        This test catches the staging error where DatabaseConfig was not properly imported
        or referenced, causing deployment failures.
        """
        # Read the postgres_core.py file to check for DatabaseConfig references
        import netra_backend.app.db.postgres_core as postgres_core
        
        # Check that the module imports get_unified_config
        assert hasattr(postgres_core, 'get_unified_config') or 'get_unified_config' in dir(postgres_core)
        
        # Verify critical functions don't reference DatabaseConfig directly
        source_file = postgres_core.__file__.replace('.pyc', '.py')
        with open(source_file, 'r') as f:
            content = f.read()
            
        # These patterns would cause the staging error
        problematic_patterns = [
            'DatabaseConfig.POOL_SIZE',
            'DatabaseConfig.MAX_OVERFLOW',
            'DatabaseConfig.ECHO',
            'DatabaseConfig.ECHO_POOL',
            'DatabaseConfig.POOL_TIMEOUT',
            'DatabaseConfig.POOL_RECYCLE',
            'DatabaseConfig.POOL_PRE_PING'
        ]
        
        for pattern in problematic_patterns:
            assert pattern not in content, f"Found legacy pattern '{pattern}' in postgres_core.py - migration incomplete!"
    
    def test_postgres_core_imports_required_dependencies(self):
        """Test that postgres_core has all required imports for database initialization."""
        import netra_backend.app.db.postgres_core as postgres_core
        
        # Verify critical imports exist
        required_functions = [
            '_create_engine_components',
            '_initialize_engine_with_url',
            '_build_engine_args',
            '_get_base_engine_args',
            '_get_pool_specific_args'
        ]
        
        for func_name in required_functions:
            assert hasattr(postgres_core, func_name), f"Missing required function: {func_name}"
    
    @pytest.mark.asyncio
    async def test_database_initialization_with_unified_config(self):
        """Test database initialization uses unified config properly.
        
        This simulates the staging environment initialization that was failing.
        """
        from netra_backend.app.db.postgres_core import initialize_postgres
        from netra_backend.app.core.configuration.base import get_unified_config
        
        # Mock the database URL to prevent actual connection
        with patch('netra_backend.app.db.postgres_core.DatabaseManager') as mock_db_manager:
            mock_db_manager.get_application_url_async.return_value = "postgresql+asyncpg://test:test@localhost/test"
            
            # Mock the create_async_engine to prevent actual engine creation
            with patch('netra_backend.app.db.postgres_core.create_async_engine') as mock_create_engine:
                mock_engine = AsyncMock()
                mock_create_engine.return_value = mock_engine
                
                # This should not raise "DatabaseConfig is not defined" error
                try:
                    await initialize_postgres()
                    # If we get here, the initialization succeeded without DatabaseConfig errors
                    assert True
                except NameError as e:
                    if "DatabaseConfig" in str(e):
                        pytest.fail(f"DatabaseConfig reference error in staging: {e}")
                    raise
                except Exception:
                    # Other exceptions are acceptable for this test
                    pass
    
    def test_no_direct_database_config_usage_in_core_files(self):
        """Verify core database files don't use DatabaseConfig class attributes directly."""
        core_db_files = [
            'netra_backend/app/db/postgres_core.py',
            'netra_backend/app/db/postgres_events.py',
            'netra_backend/app/db/postgres.py'
        ]
        
        for file_path in core_db_files:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    
                # Check for problematic patterns
                if 'DatabaseConfig.' in content:
                    # Extract lines with DatabaseConfig references
                    lines = content.split('\n')
                    problematic_lines = [
                        (i+1, line.strip()) 
                        for i, line in enumerate(lines) 
                        if 'DatabaseConfig.' in line and not line.strip().startswith('#')
                    ]
                    
                    if problematic_lines:
                        issues = '\n'.join([f"  Line {num}: {line}" for num, line in problematic_lines])
                        pytest.fail(f"Found DatabaseConfig attribute references in {file_path}:\n{issues}")
                        
            except FileNotFoundError:
                # File might not exist in test environment
                pass
    
    def test_unified_config_provides_all_required_attributes(self):
        """Verify get_unified_config() provides all attributes previously in DatabaseConfig."""
        config = get_unified_config()
        
        # Map old DatabaseConfig attributes to new unified config attributes
        required_mappings = {
            'POOL_SIZE': 'db_pool_size',
            'MAX_OVERFLOW': 'db_max_overflow',
            'POOL_TIMEOUT': 'db_pool_timeout',
            'POOL_RECYCLE': 'db_pool_recycle',
            'POOL_PRE_PING': 'db_pool_pre_ping',
            'ECHO': 'db_echo',
            'ECHO_POOL': 'db_echo_pool'
        }
        
        for old_attr, new_attr in required_mappings.items():
            assert hasattr(config, new_attr), f"Unified config missing attribute: {new_attr} (was DatabaseConfig.{old_attr})"
            
            # Verify the attribute has a reasonable value
            value = getattr(config, new_attr)
            assert value is not None, f"Unified config attribute {new_attr} is None"


class TestStagingDeploymentValidation:
    """Tests to validate staging deployment configuration."""
    
    @pytest.mark.asyncio
    async def test_staging_environment_database_config(self):
        """Test database configuration in staging environment.
        
        This test ensures staging deployment has proper configuration.
        """
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}):
            config = get_unified_config()
            
            # Verify staging-specific settings
            assert config.environment in [\'staging\', \'testing\']
            
            # Verify database pool settings are appropriate for Cloud Run
            assert config.db_pool_size >= 5, "Pool size too small for staging"
            assert config.db_pool_size <= 50, "Pool size too large for Cloud Run limits"
            assert config.db_max_overflow >= 10, "Max overflow too small for staging load"
    
    def test_import_resolution_in_deployment(self):
        """Test that all critical imports resolve correctly as they would in deployment."""
        critical_imports = [
            "from netra_backend.app.core.configuration.base import get_unified_config",
            "from netra_backend.app.db.database_manager import DatabaseManager",
            "from sqlalchemy.ext.asyncio import create_async_engine"
        ]
        
        for import_stmt in critical_imports:
            try:
                exec(import_stmt)
            except ImportError as e:
                pytest.fail(f"Critical import failed (would break staging): {import_stmt}\n  Error: {e}")
    
    @pytest.mark.asyncio
    async def test_database_engine_creation_flow(self):
        """Test the complete flow of database engine creation as it happens in staging.
        
        This reproduces the exact sequence that was failing in staging deployment.
        """
        from netra_backend.app.db import postgres_core
        
        # Mock dependencies to isolate the test
        with patch.object(postgres_core, 'DatabaseManager') as mock_db_manager:
            mock_db_manager.get_application_url_async.return_value = "postgresql+asyncpg://test:test@localhost/test"
            
            with patch.object(postgres_core, 'create_async_engine') as mock_create_engine:
                mock_engine = AsyncMock()
                mock_create_engine.return_value = mock_engine
                
                # Simulate the initialization sequence
                try:
                    # 1. Validate database URL
                    db_url = postgres_core._validate_database_url()
                    assert db_url is not None
                    
                    # 2. Create engine components (this was failing in staging)
                    engine_args = postgres_core._create_engine_components(db_url)
                    assert engine_args is not None
                    assert 'poolclass' in engine_args
                    assert 'echo' in engine_args
                    
                    # 3. Build engine args (check for DatabaseConfig reference)
                    pool_class = engine_args['poolclass']
                    final_args = postgres_core._build_engine_args(pool_class)
                    assert final_args is not None
                    
                    # If we get here without NameError, the migration is complete
                    assert True
                    
                except NameError as e:
                    if "DatabaseConfig" in str(e):
                        pytest.fail(f"DatabaseConfig not defined error (staging failure): {e}")
                    raise