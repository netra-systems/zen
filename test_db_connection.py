#!/usr/bin/env python3
"""
Test database connection to verify dev launcher database connectivity.
"""
import asyncio
import sys
import os
from pathlib import Path

# Set UTF-8 encoding for Windows
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dev_launcher.isolated_environment import get_env
from shared.database_url_builder import DatabaseURLBuilder


async def test_connection():
    """Test database connection using same logic as dev launcher."""
    print("=== Database Connection Test ===\n")
    
    # Load environment
    env = get_env()
    env_file = project_root / ".env"
    if env_file.exists():
        loaded, errors = env.load_from_file(env_file, source="test", override_existing=True)
        print(f"[OK] Loaded {loaded} variables from .env")
        if errors:
            print(f"[WARNING] Errors: {errors}")
    
    # Get all environment variables
    env_vars = env.get_all()
    print(f"\n=== Environment Variables ===")
    print(f"ENVIRONMENT: {env_vars.get('ENVIRONMENT', 'not set')}")
    print(f"DATABASE_URL: {DatabaseURLBuilder.mask_url_for_logging(env_vars.get('DATABASE_URL'))}")
    print(f"POSTGRES_HOST: {env_vars.get('POSTGRES_HOST', 'not set')}")
    print(f"POSTGRES_PORT: {env_vars.get('POSTGRES_PORT', 'not set')}")
    print(f"POSTGRES_USER: {env_vars.get('POSTGRES_USER', 'not set')}")
    print(f"POSTGRES_DB: {env_vars.get('POSTGRES_DB', 'not set')}")
    
    # Build database URL
    print(f"\n=== DatabaseURLBuilder Analysis ===")
    builder = DatabaseURLBuilder(env_vars)
    
    # Debug info
    debug_info = builder.debug_info()
    print(f"Environment: {debug_info['environment']}")
    print(f"Has Cloud SQL: {debug_info['has_cloud_sql']}")
    print(f"Has TCP Config: {debug_info['has_tcp_config']}")
    print(f"Available URLs: {debug_info['available_urls']}")
    
    # Get URL for environment
    async_url = builder.get_url_for_environment(sync=False)
    sync_url = builder.get_url_for_environment(sync=True)
    
    print(f"\n=== Generated URLs ===")
    print(f"Async URL: {DatabaseURLBuilder.mask_url_for_logging(async_url)}")
    print(f"Sync URL: {DatabaseURLBuilder.mask_url_for_logging(sync_url)}")
    
    # Show what the dev launcher would use
    print(f"\n=== Dev Launcher Logic ===")
    print(f"1. TCP Config Available: {builder.tcp.has_config}")
    if builder.tcp.has_config:
        print(f"   - Would use TCP async URL: {DatabaseURLBuilder.mask_url_for_logging(builder.tcp.async_url)}")
    print(f"2. DATABASE_URL Available: {bool(builder.database_url)}")
    if builder.database_url:
        print(f"   - Would use DATABASE_URL: {DatabaseURLBuilder.mask_url_for_logging(builder.database_url)}")
    print(f"3. Fallback default URL: {DatabaseURLBuilder.mask_url_for_logging(builder.development.default_url)}")
    
    print(f"\n=== Final URL Selection ===")
    final_url = builder.development.auto_url
    print(f"Development auto_url returns: {DatabaseURLBuilder.mask_url_for_logging(final_url)}")
    
    # Validate configuration
    is_valid, error_msg = builder.validate()
    print(f"\n=== Validation ===")
    print(f"Valid: {is_valid}")
    if error_msg:
        print(f"Error: {error_msg}")
    
    # Now test actual connection
    print(f"\n=== Testing Connection ===")
    print(f"Attempting to connect to: {DatabaseURLBuilder.mask_url_for_logging(final_url)}")
    
    try:
        # Normalize URL for asyncpg (remove driver prefix)
        normalized_url = DatabaseURLBuilder.normalize_postgres_url(final_url)
        print(f"Normalized for asyncpg: {DatabaseURLBuilder.mask_url_for_logging(normalized_url)}")
        
        import asyncpg
        # asyncpg expects plain postgresql:// not postgresql+asyncpg://
        connection_url = normalized_url.replace("postgresql+asyncpg://", "postgresql://")
        print(f"Final connection URL: {DatabaseURLBuilder.mask_url_for_logging(connection_url)}")
        
        # Try to connect
        conn = await asyncpg.connect(connection_url, timeout=5)
        print("[SUCCESS] Connection successful!")
        
        # Test query
        version = await conn.fetchval("SELECT version()")
        print(f"PostgreSQL version: {version[:50]}...")
        
        await conn.close()
        print("[SUCCESS] Connection closed successfully")
        
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        print(f"\nError type: {type(e).__name__}")
        
        # Provide debugging hints
        print("\n=== Debugging Hints ===")
        print("1. Check if PostgreSQL is running on port 5433:")
        print("   docker ps | grep postgres")
        print("2. Check if port 5433 is accessible:")
        print("   netstat -an | grep 5433")
        print("3. Verify credentials in .env file")
        print("4. Try starting PostgreSQL container:")
        print("   docker run -d -p 5433:5432 -e POSTGRES_PASSWORD=DTprdt5KoQXlEG4Gh9lF postgres:13")


if __name__ == "__main__":
    asyncio.run(test_connection())