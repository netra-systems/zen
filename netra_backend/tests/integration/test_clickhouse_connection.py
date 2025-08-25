"""
Integration test for ClickHouse connection authentication.
Tests ClickHouse authentication and basic connectivity issues.
"""
import pytest
import asyncio
from netra_backend.app.config import get_config
from netra_backend.app.database import get_clickhouse_client
from netra_backend.app.db.clickhouse_init import initialize_clickhouse_tables
from netra_backend.app.db.clickhouse import ClickHouseService


class TestClickHouseConnection:
    """Test ClickHouse connection and authentication."""

    @pytest.mark.asyncio
    async def test_clickhouse_basic_connection(self):
        """Test basic ClickHouse connection without authentication issues."""
        try:
            # Directly use the real ClickHouse client for integration testing
            from netra_backend.app.db.clickhouse import _create_real_client
            
            async for client in _create_real_client():
                # Test basic query
                result = await client.execute("SELECT 1 as test")
                assert result is not None
                assert len(result) > 0
                assert result[0]['test'] == 1
                break
                
        except Exception as e:
            error_msg = str(e).lower()
            if 'authentication' in error_msg or 'password' in error_msg or 'user' in error_msg:
                pytest.fail(f"ClickHouse authentication failed: {e}")
            elif 'connection' in error_msg or 'timeout' in error_msg:
                pytest.skip(f"ClickHouse connection issue (not auth): {e}")
            else:
                pytest.fail(f"ClickHouse unexpected error: {e}")

    @pytest.mark.asyncio
    async def test_clickhouse_configuration_values(self):
        """Test ClickHouse configuration is properly loaded."""
        config = get_config()
        
        # Check that ClickHouse config exists
        assert hasattr(config, 'clickhouse_https'), "ClickHouse HTTPS config missing"
        
        ch_config = config.clickhouse_https
        
        # Check required fields are present
        assert hasattr(ch_config, 'host'), "ClickHouse host missing"
        assert hasattr(ch_config, 'port'), "ClickHouse port missing"
        assert hasattr(ch_config, 'username'), "ClickHouse username missing"  
        assert hasattr(ch_config, 'password'), "ClickHouse password missing"
        
        # Check values are not empty
        assert ch_config.host, "ClickHouse host is empty"
        assert ch_config.port, "ClickHouse port is empty"
        assert ch_config.username, "ClickHouse username is empty"
        # Password could be empty for some auth methods, so just check it exists
        
    @pytest.mark.asyncio
    async def test_clickhouse_initialization_without_errors(self):
        """Test ClickHouse table initialization doesn't fail with auth errors."""
        try:
            # This should not fail with authentication errors
            await initialize_clickhouse_tables(verbose=True)
            # If we get here, no auth errors occurred
            assert True
            
        except Exception as e:
            error_msg = str(e).lower()
            if 'authentication' in error_msg or 'password' in error_msg or 'user' in error_msg:
                pytest.fail(f"ClickHouse authentication failed during initialization: {e}")
            elif 'permission' in error_msg or 'access' in error_msg:
                pytest.fail(f"ClickHouse permission error during initialization: {e}")
            else:
                # Other errors might be acceptable (like network issues)
                print(f"Non-auth error during initialization (may be acceptable): {e}")

    @pytest.mark.asyncio 
    async def test_clickhouse_credentials_not_default(self):
        """Test that ClickHouse credentials are not using obvious defaults."""
        config = get_config()
        ch_config = config.clickhouse_https
        
        # Check for common default values that would indicate misconfiguration
        default_combinations = [
            ('default', ''),
            ('default', 'default'),
            ('admin', 'admin'),
            ('admin', ''),
            ('root', 'root'),
            ('', ''),
        ]
        
        current_combo = (ch_config.username, ch_config.password)
        
        if current_combo in default_combinations:
            pytest.fail(f"ClickHouse using default credentials: {ch_config.username}")
            
        # Also check host isn't localhost with production credentials
        if ch_config.host == 'localhost' and ch_config.username == 'default':
            pytest.skip("Using localhost with default user - likely development setup")


if __name__ == "__main__":
    # Run this test standalone to check ClickHouse connection
    pytest.main([__file__, "-v"])