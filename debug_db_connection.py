#!/usr/bin/env python3
"""Debug Database Connection Script

Tests the database connection with detailed error reporting to diagnose
the PostgreSQL authentication issue.
"""

import asyncio
import os
import sys
import logging
from urllib.parse import urlparse
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Set up logging to see detailed errors
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_database_connection():
    """Test the database connection with current credentials."""
    
    # Get the current database URL from the secret
    database_url = "postgresql://postgres:qNdlZRHu%28Mlc%23%296K8LHm-lYi%5B7sc%7D25K@/postgres?host=/cloudsql/netra-staging:us-central1:staging-shared-postgres"
    
    logger.info(f"Testing connection with URL: {database_url}")
    
    # Parse the URL to see components
    parsed = urlparse(database_url)
    logger.info(f"URL components:")
    logger.info(f"  Scheme: {parsed.scheme}")
    logger.info(f"  Username: {parsed.username}")
    logger.info(f"  Password: {'*' * len(parsed.password) if parsed.password else 'None'}")
    logger.info(f"  Hostname: {parsed.hostname}")
    logger.info(f"  Port: {parsed.port}")
    logger.info(f"  Path: {parsed.path}")
    logger.info(f"  Query: {parsed.query}")
    
    # Convert to asyncpg format
    async_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
    logger.info(f"Async URL: {async_url}")
    
    try:
        # Create engine with minimal configuration
        engine = create_async_engine(
            async_url,
            echo=True,  # Show SQL queries
            pool_pre_ping=True,
            pool_size=1,
            max_overflow=0,
        )
        
        logger.info("Engine created successfully, attempting connection...")
        
        # Test the connection
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT current_user, current_database(), version()"))
            row = result.fetchone()
            logger.info(f"Connection successful!")
            logger.info(f"Current user: {row[0]}")
            logger.info(f"Current database: {row[1]}")
            logger.info(f"PostgreSQL version: {row[2]}")
            
        await engine.dispose()
        return True
        
    except Exception as e:
        logger.error(f"Connection failed with error: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        
        # Try to get more specific error information
        if hasattr(e, 'args') and e.args:
            logger.error(f"Error args: {e.args}")
        
        # Check for common authentication error patterns
        error_str = str(e).lower()
        if "password authentication failed" in error_str:
            logger.error("AUTHENTICATION ERROR: Password authentication failed")
            logger.error("This indicates the password in the secret is incorrect")
        elif "connection refused" in error_str:
            logger.error("CONNECTION ERROR: Connection refused")
            logger.error("This indicates the database server is not accessible")
        elif "timeout" in error_str:
            logger.error("TIMEOUT ERROR: Connection timed out")
            logger.error("This indicates network connectivity issues")
        
        return False

async def test_direct_postgres_user():
    """Test connection with just the postgres user and URL-decoded password."""
    
    # URL-decode the password
    import urllib.parse
    encoded_password = "qNdlZRHu%28Mlc%23%296K8LHm-lYi%5B7sc%7D25K"
    decoded_password = urllib.parse.unquote(encoded_password)
    
    logger.info(f"Testing with decoded password: {decoded_password}")
    
    # Create URL with decoded password
    test_url = f"postgresql+asyncpg://postgres:{encoded_password}@/postgres?host=/cloudsql/netra-staging:us-central1:staging-shared-postgres"
    
    logger.info(f"Test URL: {test_url}")
    
    try:
        engine = create_async_engine(
            test_url,
            echo=True,
            pool_size=1,
            max_overflow=0,
        )
        
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            logger.info("Direct postgres connection successful!")
            
        await engine.dispose()
        return True
        
    except Exception as e:
        logger.error(f"Direct postgres connection failed: {e}")
        return False

def main():
    """Run all connection tests."""
    logger.info("Starting database connection debugging...")
    
    async def run_tests():
        logger.info("=" * 50)
        logger.info("Test 1: Current database URL")
        success1 = await test_database_connection()
        
        logger.info("=" * 50)
        logger.info("Test 2: Direct postgres user test")
        success2 = await test_direct_postgres_user()
        
        logger.info("=" * 50)
        logger.info("SUMMARY:")
        logger.info(f"  Current URL test: {'SUCCESS' if success1 else 'FAILED'}")
        logger.info(f"  Direct postgres test: {'SUCCESS' if success2 else 'FAILED'}")
        
        if not success1 and not success2:
            logger.error("All tests failed - this indicates a credential or connectivity issue")
        elif success1:
            logger.info("Connection is working - the issue may be environmental")
        else:
            logger.info("Need to investigate further")
    
    asyncio.run(run_tests())

if __name__ == "__main__":
    main()