#!/usr/bin/env python3
"""
Fix script for ClickHouse Cloud authentication issues.

This script verifies and fixes ClickHouse Cloud connectivity issues
by ensuring proper authentication credentials are used.
"""

import os
import sys
import asyncio
from urllib.parse import urlparse, parse_qs

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def test_clickhouse_connection():
    """Test ClickHouse connection with proper authentication."""
    
    # Import after path setup
    from shared.isolated_environment import get_env
    from netra_backend.app.logging_config import central_logger as logger
    
    env = get_env()
    
    # Get ClickHouse URL
    clickhouse_url = env.get("CLICKHOUSE_URL")
    if not clickhouse_url:
        logger.error("CLICKHOUSE_URL not set in environment")
        return False
    
    logger.info(f"Testing ClickHouse URL: {clickhouse_url[:50]}...")
    
    # Parse the URL
    parsed = urlparse(clickhouse_url)
    
    # Check if password is embedded in URL or needs to be loaded separately
    if not parsed.password or parsed.password == "":
        # Need to load password from environment or secrets
        password = env.get("CLICKHOUSE_PASSWORD", "")
        
        if not password:
            logger.warning("CLICKHOUSE_PASSWORD not found in environment")
            logger.info("Attempting to load from GCP Secret Manager...")
            
            try:
                from netra_backend.app.core.configuration.secrets import SecretManager
                secret_manager = SecretManager()
                password = secret_manager.get_secret("CLICKHOUSE_PASSWORD")
                if password:
                    logger.info("Successfully loaded CLICKHOUSE_PASSWORD from GCP Secret Manager")
                else:
                    logger.error("CLICKHOUSE_PASSWORD not found in GCP Secret Manager")
            except Exception as e:
                logger.error(f"Failed to load password from GCP Secret Manager: {e}")
                return False
        
        # Rebuild URL with password
        if password:
            # Insert password into URL
            netloc = f"{parsed.username or 'default'}:{password}@{parsed.hostname}"
            if parsed.port:
                netloc += f":{parsed.port}"
            
            clickhouse_url = urlunparse((
                parsed.scheme,
                netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))
            
            # Update environment with authenticated URL
            os.environ["CLICKHOUSE_URL"] = clickhouse_url
            logger.info("Updated CLICKHOUSE_URL with authentication credentials")
    
    # Now test the connection
    logger.info("Testing ClickHouse connection...")
    
    try:
        import clickhouse_connect
        
        # Parse connection parameters
        parsed = urlparse(clickhouse_url)
        
        # Extract query parameters
        query_params = parse_qs(parsed.query)
        secure = query_params.get('secure', ['0'])[0] == '1'
        
        # Create client
        client = clickhouse_connect.get_client(
            host=parsed.hostname,
            port=parsed.port or (8443 if secure else 8123),
            username=parsed.username or 'default',
            password=parsed.password or '',
            database=parsed.path.lstrip('/') or 'default',
            secure=secure
        )
        
        # Test query
        result = client.query("SELECT 1 as test")
        if result:
            logger.info("✅ ClickHouse connection successful!")
            logger.info(f"Result: {result.result_rows}")
            
            # Test database access
            tables = client.query("SHOW TABLES")
            logger.info(f"Found {len(tables.result_rows)} tables in database")
            
            return True
        else:
            logger.error("ClickHouse query returned empty result")
            return False
            
    except Exception as e:
        logger.error(f"❌ ClickHouse connection failed: {e}")
        
        # Provide detailed error analysis
        error_str = str(e).lower()
        if "authentication" in error_str or "password" in error_str:
            logger.error("This appears to be an authentication issue.")
            logger.error("Ensure CLICKHOUSE_PASSWORD is set correctly.")
        elif "connection refused" in error_str:
            logger.error("Connection refused - ClickHouse may not be running.")
        elif "timeout" in error_str:
            logger.error("Connection timeout - check network/firewall settings.")
        elif "unknown table" in error_str or "doesn't exist" in error_str:
            logger.error("Table does not exist - database may need initialization.")
        
        return False


async def fix_clickhouse_config():
    """Fix ClickHouse configuration issues."""
    from netra_backend.app.logging_config import central_logger as logger
    
    logger.info("=" * 80)
    logger.info("CLICKHOUSE AUTHENTICATION FIX SCRIPT")
    logger.info("=" * 80)
    
    # Test current configuration
    success = await test_clickhouse_connection()
    
    if success:
        logger.info("=" * 80)
        logger.info("✅ ClickHouse authentication is working correctly!")
        logger.info("=" * 80)
    else:
        logger.error("=" * 80)
        logger.error("❌ ClickHouse authentication failed!")
        logger.error("=" * 80)
        logger.error("Required actions:")
        logger.error("1. Set CLICKHOUSE_PASSWORD environment variable")
        logger.error("2. Or ensure it's available in GCP Secret Manager")
        logger.error("3. Verify ClickHouse Cloud instance is running")
        logger.error("4. Check firewall rules allow connection")
        logger.error("=" * 80)
        
        # Provide the correct URL format
        logger.info("\nCorrect CLICKHOUSE_URL format:")
        logger.info("clickhouse://username:password@host:port/database?secure=1")
        logger.info("\nFor ClickHouse Cloud:")
        logger.info("clickhouse://default:YOUR_PASSWORD@xedvrr4c3r.us-central1.gcp.clickhouse.cloud:8443/default?secure=1")
        
    return success


if __name__ == "__main__":
    # Run the fix
    success = asyncio.run(fix_clickhouse_config())
    sys.exit(0 if success else 1)