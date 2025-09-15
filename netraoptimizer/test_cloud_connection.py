#!/usr/bin/env python3
"""
Test CloudSQL connection for NetraOptimizer.

This script tests the CloudSQL configuration and database connectivity.
"""

import asyncio
import os
import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from netraoptimizer.cloud_config import cloud_config
from netraoptimizer.database.client import DatabaseClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_cloud_connection():
    """Test CloudSQL connection and configuration."""

    print("=" * 60)
    print("NetraOptimizer CloudSQL Connection Test")
    print("=" * 60)

    # 1. Check configuration
    print("\n1. Configuration Check:")
    print("-" * 40)

    # Validate configuration
    is_valid, error_msg = cloud_config.validate_configuration()
    if not is_valid:
        print(f"❌ Configuration invalid: {error_msg}")
        return False
    else:
        print("✅ Configuration valid")

    # Display configuration info
    debug_info = cloud_config.get_debug_info()
    print(f"\nConfiguration Details:")
    for key, value in debug_info.items():
        # Mask sensitive information
        if key == "gcp_project" and value:
            value = f"{value[:5]}..." if len(value) > 5 else value
        print(f"  {key}: {value}")

    # 2. Test database connection
    print("\n2. Database Connection Test:")
    print("-" * 40)

    # Check if we're using CloudSQL
    db_config = cloud_config.get_database_config()
    if db_config.get('is_cloud_sql'):
        print(f"🌐 Using CloudSQL connection")
        print(f"   Socket: {db_config['socket_path']}")
    else:
        print(f"💻 Using TCP connection")
        print(f"   Host: {db_config['host']}:{db_config['port']}")

    # Create database client
    try:
        client = DatabaseClient(use_cloud_sql=True)
        print("\n✅ Database client created")

        # Initialize the connection pool
        await client.initialize()
        print("✅ Connection pool initialized")

        # Test a simple query
        async with client.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            if result == 1:
                print("✅ Database query successful")
            else:
                print(f"❌ Unexpected query result: {result}")
                return False

        # Check if netra_optimizer database exists
        async with client.acquire() as conn:
            exists = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = 'netra_optimizer'"
            )
            if exists:
                print("✅ netra_optimizer database exists")
            else:
                print("⚠️  netra_optimizer database does not exist")
                print("   Run: python netraoptimizer/database/setup.py")

        # If database exists, check tables
        if exists:
            # Switch to netra_optimizer database
            optimizer_client = DatabaseClient(use_cloud_sql=True)
            await optimizer_client.initialize()

            async with optimizer_client.acquire() as conn:
                # Check for tables
                tables = await conn.fetch("""
                    SELECT tablename
                    FROM pg_tables
                    WHERE schemaname = 'public'
                    ORDER BY tablename
                """)

                if tables:
                    print(f"\n📊 Tables in netra_optimizer:")
                    for table in tables:
                        print(f"   - {table['tablename']}")

                    # Check record count
                    count = await conn.fetchval(
                        "SELECT COUNT(*) FROM command_executions"
                    )
                    print(f"\n📈 Records in command_executions: {count}")
                else:
                    print("\n⚠️  No tables found in netra_optimizer")
                    print("   Run: python netraoptimizer/database/setup.py")

            await optimizer_client.close()

        # Close the connection pool
        await client.close()
        print("\n✅ Connection closed successfully")

        return True

    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point."""
    # Set environment for testing if not set
    if not os.environ.get("ENVIRONMENT"):
        print("ℹ️  ENVIRONMENT not set, using 'development'")
        os.environ["ENVIRONMENT"] = "development"

    # Check if we should use CloudSQL
    use_cloud = os.environ.get("USE_CLOUD_SQL", "").lower() == "true"
    environment = os.environ.get("ENVIRONMENT", "").lower()

    if use_cloud or environment in ["staging", "production"]:
        print(f"🌐 CloudSQL mode enabled (environment: {environment})")
    else:
        print(f"💻 Local mode (environment: {environment})")
        print("\nTo test CloudSQL connection, set:")
        print("  export USE_CLOUD_SQL=true")
        print("  export POSTGRES_HOST=/cloudsql/PROJECT:REGION:INSTANCE")
        print("  export POSTGRES_USER=your_user")
        print("  export POSTGRES_PASSWORD=your_password")
        print("  export GCP_PROJECT_ID=your_project_id")

    # Run the async test
    success = asyncio.run(test_cloud_connection())

    print("\n" + "=" * 60)
    if success:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed")
    print("=" * 60)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())