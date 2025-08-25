"""Direct test of staging database connection using migrated secrets.

**UPDATED**: Now uses DatabaseURLBuilder for centralized URL construction.
"""

import asyncio
import sys
from pathlib import Path
from google.cloud import secretmanager
import asyncpg
import psycopg2

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.database_url_builder import DatabaseURLBuilder

def fetch_secret(secret_id: str, project: str = "netra-staging") -> str:
    """Fetch a secret from Google Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project}/secrets/{secret_id}/versions/latest"
    try:
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        print(f"Error fetching secret {secret_id}: {e}")
        raise

async def test_connection():
    """Test database connection with individual secrets."""
    print("=" * 60)
    print("TESTING STAGING DATABASE CONNECTION")
    print("=" * 60)
    
    try:
        # Fetch individual secrets
        print("\n1. Fetching individual PostgreSQL secrets...")
        host = fetch_secret("postgres-host-staging")
        port = fetch_secret("postgres-port-staging")
        db = fetch_secret("postgres-db-staging")
        user = fetch_secret("postgres-user-staging")
        password = fetch_secret("postgres-password-staging")
        
        print(f"   Host: {host}")
        print(f"   Port: {port}")
        print(f"   Database: {db}")
        print(f"   User: {user}")
        print(f"   Password: {'*' * len(password)}")
        
        # Build connection URLs using DatabaseURLBuilder
        print("\n2. Building database URLs using DatabaseURLBuilder...")
        
        # Build environment variables dict
        env_vars = {
            "ENVIRONMENT": "staging",
            "POSTGRES_HOST": host,
            "POSTGRES_PORT": port,
            "POSTGRES_DB": db,
            "POSTGRES_USER": user,
            "POSTGRES_PASSWORD": password,
        }
        
        # Create builder
        builder = DatabaseURLBuilder(env_vars)
        
        # Validate configuration
        is_valid, error_msg = builder.validate()
        if not is_valid:
            print(f"   Configuration error: {error_msg}")
            return False
        
        # Get URLs for different purposes
        sync_url = builder.get_url_for_environment(sync=True)
        async_url = builder.get_url_for_environment(sync=False)
        
        # For direct asyncpg connection, we need the base postgresql:// format
        async_dsn = sync_url  # asyncpg uses postgresql:// not postgresql+asyncpg://
        
        debug_info = builder.debug_info()
        print(f"   Connection type: {'Cloud SQL' if debug_info['has_cloud_sql'] else 'TCP'}")
        print(f"   Environment: {debug_info['environment']}")
        print(f"   SSL configured: {debug_info.get('has_ssl', False)}")
        
        print(f"\n3. Testing async connection with asyncpg...")
        masked_dsn = DatabaseURLBuilder.mask_url_for_logging(async_dsn)
        print(f"   DSN: {masked_dsn}")
        
        # Test async connection
        try:
            conn = await asyncpg.connect(async_dsn)
            result = await conn.fetchval("SELECT version()")
            print(f"   SUCCESS! PostgreSQL version: {result[:50]}...")
            await conn.close()
        except Exception as e:
            print(f"   FAILED: {e}")
            import traceback
            print(f"   TRACEBACK: {traceback.format_exc()}")
            return False
        
        print(f"\n4. Testing sync connection with psycopg2...")
        masked_url = DatabaseURLBuilder.mask_url_for_logging(sync_url)
        print(f"   URL: {masked_url}")
        
        # Test sync connection
        try:
            with psycopg2.connect(sync_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT version()")
                    result = cur.fetchone()[0]
                    print(f"   SUCCESS! PostgreSQL version: {result[:50]}...")
        except Exception as e:
            print(f"   FAILED: {e}")
            import traceback
            print(f"   TRACEBACK: {traceback.format_exc()}")
            return False
        
        print("\n" + "=" * 60)
        print("ALL DATABASE CONNECTION TESTS PASSED!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_connection())
    sys.exit(0 if success else 1)