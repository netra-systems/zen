"""Direct test of staging database connection using migrated secrets."""

import asyncio
import sys
from pathlib import Path
from google.cloud import secretmanager
import asyncpg
import psycopg2
from urllib.parse import quote_plus

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

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
        
        # URL-encode the password to handle special characters
        encoded_password = quote_plus(password)
        
        # Build connection URLs
        if "/cloudsql/" in host:
            # Unix socket connection
            print("\n2. Detected Cloud SQL Unix socket connection")
            sync_url = f"postgresql://{user}:{encoded_password}@/{db}?host={host}"
            async_url = f"postgresql+asyncpg://{user}:{encoded_password}@/{db}?host={host}"
            
            # For direct connection testing
            async_dsn = f"postgresql://{user}:{encoded_password}@/{db}?host={host}"
        else:
            # TCP connection
            print("\n2. Using TCP connection")
            sync_url = f"postgresql://{user}:{encoded_password}@{host}:{port}/{db}"
            async_url = f"postgresql+asyncpg://{user}:{encoded_password}@{host}:{port}/{db}"
            async_dsn = async_url.replace("postgresql+asyncpg://", "postgresql://")
        
        print(f"\n3. Testing async connection with asyncpg...")
        print(f"   DSN: {async_dsn[:50]}...")
        
        # Test async connection
        try:
            conn = await asyncpg.connect(async_dsn)
            result = await conn.fetchval("SELECT version()")
            print(f"   SUCCESS! PostgreSQL version: {result[:50]}...")
            await conn.close()
        except Exception as e:
            print(f"   FAILED: {e}")
            return False
        
        print(f"\n4. Testing sync connection with psycopg2...")
        print(f"   URL: {sync_url[:50]}...")
        
        # Test sync connection
        try:
            with psycopg2.connect(sync_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT version()")
                    result = cur.fetchone()[0]
                    print(f"   SUCCESS! PostgreSQL version: {result[:50]}...")
        except Exception as e:
            print(f"   FAILED: {e}")
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