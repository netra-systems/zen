"""
Test Cloud SQL URL handling in auth service
Ensures proper handling of Cloud SQL Unix socket format
"""
import os
import pytest
from unittest.mock import patch, MagicMock
from auth_core.database.connection import AuthDatabase


@pytest.mark.asyncio
async def test_cloud_sql_url_format():
    """Test that Cloud SQL Unix socket URLs are handled correctly"""
    # Test URL formats used by Cloud SQL
    test_urls = [
        "postgresql://user:pass@/dbname?host=/cloudsql/project:region:instance",
        "postgresql://user:pass@/dbname?host=/cloudsql/project:region:instance&sslmode=require",
        "postgresql://user:pass@localhost/dbname?host=/cloudsql/project:region:instance"
    ]
    
    for original_url in test_urls:
        with patch.dict(os.environ, {"DATABASE_URL": original_url, "ENVIRONMENT": "staging"}):
            with patch("auth_core.database.connection.create_async_engine") as mock_engine:
                mock_engine.return_value = MagicMock()
                
                db = AuthDatabase()
                await db.initialize()
                
                # Verify the URL was converted to asyncpg format
                mock_engine.assert_called_once()
                call_args = mock_engine.call_args[0][0]
                
                # Should convert postgresql:// to postgresql+asyncpg://
                assert call_args.startswith("postgresql+asyncpg://")
                
                # Should preserve the Cloud SQL socket path
                assert "/cloudsql/" in call_args
                
                # Should preserve the instance identifier
                if "project:region:instance" in original_url:
                    assert "project:region:instance" in call_args


@pytest.mark.asyncio
async def test_regular_postgres_url():
    """Test that regular PostgreSQL URLs are handled correctly"""
    test_url = "postgresql://user:pass@localhost:5432/dbname"
    
    with patch.dict(os.environ, {"DATABASE_URL": test_url, "ENVIRONMENT": "development"}):
        with patch("auth_core.database.connection.create_async_engine") as mock_engine:
            mock_engine.return_value = MagicMock()
            
            db = AuthDatabase()
            await db.initialize()
            
            # Verify the URL was converted to asyncpg format
            mock_engine.assert_called_once()
            call_args = mock_engine.call_args[0][0]
            
            # Should convert postgresql:// to postgresql+asyncpg://
            assert call_args.startswith("postgresql+asyncpg://")
            assert "localhost:5432" in call_args


@pytest.mark.asyncio
async def test_heroku_style_url():
    """Test that Heroku-style postgres:// URLs are handled correctly"""
    test_url = "postgres://user:pass@host.com:5432/dbname"
    
    with patch.dict(os.environ, {"DATABASE_URL": test_url, "ENVIRONMENT": "production"}):
        with patch("auth_core.database.connection.create_async_engine") as mock_engine:
            mock_engine.return_value = MagicMock()
            
            db = AuthDatabase()
            await db.initialize()
            
            # Verify the URL was converted to asyncpg format
            mock_engine.assert_called_once()
            call_args = mock_engine.call_args[0][0]
            
            # Should convert postgres:// to postgresql+asyncpg://
            assert call_args.startswith("postgresql+asyncpg://")
            assert "host.com:5432" in call_args