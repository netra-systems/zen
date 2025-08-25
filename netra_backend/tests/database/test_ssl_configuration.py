"""Test SSL/TLS configuration for database connections."""

import pytest
import asyncio
import ssl
from unittest.mock import patch, AsyncMock, MagicMock

from netra_backend.app.core.database_url_builder import DatabaseURLBuilder
from netra_backend.app.core.database import get_database_connection
from test_framework.fixtures import isolated_environment

pytestmark = [
    pytest.mark.database,
    pytest.mark.integration, 
    pytest.mark.ssl_configuration
]

class TestSSLConfiguration:
    """Test SSL/TLS configuration for database connections."""
    
    @pytest.mark.asyncio
    async def test_ssl_cert_validation_fails_with_invalid_cert(self, isolated_environment):
        """Test that SSL certificate validation fails with invalid certificates."""
        # This test should fail initially - expecting proper SSL validation
        url_builder = DatabaseURLBuilder()
        
        # Mock invalid SSL certificate
        with patch('ssl.create_default_context') as mock_ssl:
            mock_context = MagicMock()
            mock_context.check_hostname = True
            mock_context.verify_mode = ssl.CERT_REQUIRED
            mock_ssl.return_value = mock_context
            
            # Should fail with invalid certificate
            with pytest.raises(Exception, match="certificate"):
                connection = await get_database_connection(
                    url_builder.build_url(require_ssl=True),
                    ssl_context=mock_context
                )
                
    @pytest.mark.asyncio
    async def test_tls_version_enforcement(self, isolated_environment):
        """Test that minimum TLS version is enforced."""
        # This should fail initially - no TLS version enforcement
        url_builder = DatabaseURLBuilder()
        
        # Mock TLS context with old version
        with patch('ssl.create_default_context') as mock_ssl:
            mock_context = MagicMock()
            mock_context.minimum_version = ssl.TLSVersion.TLSv1  # Old version
            mock_ssl.return_value = mock_context
            
            # Should fail with old TLS version
            with pytest.raises(Exception, match="TLS"):
                connection = await get_database_connection(
                    url_builder.build_url(require_ssl=True),
                    ssl_context=mock_context
                )
                
    @pytest.mark.asyncio
    async def test_ssl_disabled_in_production_fails(self, isolated_environment):
        """Test that SSL cannot be disabled in production environment."""
        # This should fail initially - no production SSL enforcement
        url_builder = DatabaseURLBuilder()
        
        # Mock production environment
        with patch.dict('os.environ', {'ENVIRONMENT': 'production'}):
            # Should fail when trying to disable SSL in production
            with pytest.raises(Exception, match="production"):
                connection_url = url_builder.build_url(require_ssl=False)
                await get_database_connection(connection_url)