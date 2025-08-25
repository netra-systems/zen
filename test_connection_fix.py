#!/usr/bin/env python3
"""Test database connection with updated secrets."""

import asyncio
import subprocess
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from shared.database_url_builder import DatabaseURLBuilder

def get_secret_value(secret_name, project="netra-staging"):
    """Get a secret value from GCP Secret Manager."""
    try:
        result = subprocess.run([
            "gcloud", "secrets", "versions", "access", "latest",
            "--secret", secret_name,
            "--project", project
        ], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error fetching secret {secret_name}: {e}")
        return None

async def test_connection():
    """Test the database connection using the updated secrets."""
    print("Testing PostgreSQL connection with updated secrets...")
    print("=" * 60)
    
    # Fetch individual secrets
    secrets = {}
    secret_names = [
        "postgres-host-staging",
        "postgres-port-staging", 
        "postgres-db-staging",
        "postgres-user-staging",
        "postgres-password-staging"
    ]
    
    for secret_name in secret_names:
        value = get_secret_value(secret_name)
        if value is None:
            print(f"❌ Failed to fetch {secret_name}")
            return False
        secrets[secret_name] = value
        
        # Show value (mask password)
        if "password" in secret_name:
            print(f"[OK] {secret_name}: ***")
        else:
            print(f"[OK] {secret_name}: {value}")
    
    print("\nBuilding database URL...")
    
    # Build environment vars dict
    env_vars = {
        "ENVIRONMENT": "staging",
        "POSTGRES_HOST": secrets["postgres-host-staging"],
        "POSTGRES_PORT": secrets["postgres-port-staging"],
        "POSTGRES_DB": secrets["postgres-db-staging"],
        "POSTGRES_USER": secrets["postgres-user-staging"],
        "POSTGRES_PASSWORD": secrets["postgres-password-staging"],
    }
    
    # Create URL builder
    builder = DatabaseURLBuilder(env_vars)
    
    # Validate configuration
    is_valid, error_msg = builder.validate()
    if not is_valid:
        print(f"[ERROR] Configuration validation failed: {error_msg}")
        return False
    
    print("[OK] Configuration validation passed")
    
    # Get the URL
    url = builder.get_url_for_environment(sync=False)
    if not url:
        print("[ERROR] Failed to generate database URL")
        return False
    
    # Show masked URL
    masked_url = DatabaseURLBuilder.mask_url_for_logging(url)
    print(f"Generated URL: {masked_url}")
    
    print(f"\nTesting connection...")
    
    # Test actual connection
    try:
        import asyncpg
        
        # For Cloud SQL, we need to use the unix socket directly
        # Parse the URL components
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(url)
        
        if "/cloudsql/" in url:
            # Extract host from query parameters
            query_params = parse_qs(parsed.query)
            host_path = query_params.get('host', [''])[0]
            
            # Connect directly using asyncpg with unix socket
            conn = await asyncpg.connect(
                user=parsed.username,
                password=parsed.password,
                database=parsed.path.lstrip('/'),
                host=host_path
            )
            
            # Test query
            result = await conn.fetchrow("SELECT current_user, current_database(), version()")
            
            print("[SUCCESS] Connection successful!")
            print(f"   Current user: {result['current_user']}")
            print(f"   Current database: {result['current_database']}")
            print(f"   PostgreSQL version: {result['version'][:50]}...")
            
            await conn.close()
            return True
        else:
            print("[ERROR] Expected Cloud SQL Unix socket connection")
            return False
            
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        
        error_str = str(e).lower()
        if "password authentication failed" in error_str:
            print("   Authentication issue: Password is incorrect for this user")
            print("   Suggestion: Reset postgres user password or use different user")
        elif "does not exist" in error_str:
            print("   User/database doesn't exist")
            print("   Suggestion: Create the user/database or use existing ones")
        
        return False

if __name__ == "__main__":
    success = asyncio.run(test_connection())
    sys.exit(0 if success else 1)