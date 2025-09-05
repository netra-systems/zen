"""Test database migrations against staging database."""

import sys
import os
import subprocess
import tempfile
from pathlib import Path
from google.cloud import secretmanager
from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.database_url_builder import DatabaseURLBuilder

env = get_env()
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

def test_migration_url_generation():
    """Test migration URL generation with DatabaseURLBuilder."""
    print("=" * 60)
    print("TESTING MIGRATION URL GENERATION")
    print("=" * 60)
    
    try:
        # Fetch staging database configuration
        print("\n1. Fetching staging database configuration...")
        env_vars = {
            "ENVIRONMENT": "staging",
            "POSTGRES_HOST": fetch_secret("postgres-host-staging"),
            "POSTGRES_PORT": fetch_secret("postgres-port-staging"),
            "POSTGRES_DB": fetch_secret("postgres-db-staging"),
            "POSTGRES_USER": fetch_secret("postgres-user-staging"),
            "POSTGRES_PASSWORD": fetch_secret("postgres-password-staging")
        }
        
        print(f"   Host: {env_vars['POSTGRES_HOST']}")
        print(f"   Port: {env_vars['POSTGRES_PORT']}")
        print(f"   Database: {env_vars['POSTGRES_DB']}")
        print(f"   User: {env_vars['POSTGRES_USER']}")
        
        # Build URLs using DatabaseURLBuilder
        print("\n2. Building migration URLs...")
        builder = DatabaseURLBuilder(env_vars)
        
        # Validate configuration
        is_valid, error_msg = builder.validate()
        print(f"   Configuration valid: {is_valid}")
        if not is_valid:
            print(f"   Error: {error_msg}")
            return False
        
        # Get migration URL (synchronous)
        migration_url = builder.get_url_for_environment(sync=True)
        print(f"   Migration URL: {DatabaseURLBuilder.mask_url_for_logging(migration_url)}")
        
        # Test URL normalization for migrations
        print("\n3. Testing URL normalization for migrations...")
        normalized_url = DatabaseURLBuilder.normalize_postgres_url(migration_url)
        print(f"   Normalized: {DatabaseURLBuilder.mask_url_for_logging(normalized_url)}")
        
        # Format URL for psycopg2 (required for Alembic)
        psycopg2_url = DatabaseURLBuilder.format_url_for_driver(normalized_url, 'psycopg2')
        print(f"   For psycopg2: {DatabaseURLBuilder.mask_url_for_logging(psycopg2_url)}")
        
        # Validate URL for psycopg2
        is_valid_psycopg2, error_msg_psycopg2 = DatabaseURLBuilder.validate_url_for_driver(psycopg2_url, 'psycopg2')
        print(f"   psycopg2 URL valid: {is_valid_psycopg2}")
        if not is_valid_psycopg2:
            print(f"   Error: {error_msg_psycopg2}")
            return False
        
        return migration_url
        
    except Exception as e:
        print(f"   FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_alembic_configuration():
    """Test Alembic configuration with staging database URL."""
    print("\n" + "=" * 60)
    print("TESTING ALEMBIC CONFIGURATION")
    print("=" * 60)
    
    # Get migration URL from previous test
    migration_url = test_migration_url_generation()
    if not migration_url:
        print("   FAILED: Could not generate migration URL")
        return False
    
    # Check if Alembic configuration files exist
    print("\n1. Checking Alembic configuration files...")
    
    # Look for alembic.ini in common locations
    config_locations = [
        "alembic.ini",
        "config/alembic.ini",
        "alembic/alembic.ini",
        "netra_backend/alembic.ini"
    ]
    
    alembic_config = None
    for location in config_locations:
        if os.path.exists(location):
            alembic_config = location
            print(f"   Found Alembic config: {location}")
            break
    
    if not alembic_config:
        print("   No Alembic configuration found")
        print(f"   Searched locations: {config_locations}")
        
        # Check for alembic directory
        alembic_dirs = [
            "alembic",
            "netra_backend/alembic", 
            "database_scripts"
        ]
        
        for alembic_dir in alembic_dirs:
            if os.path.exists(alembic_dir):
                print(f"   Found potential migration directory: {alembic_dir}")
        
        return False
    
    # Test Alembic dry run with staging URL
    print("\n2. Testing Alembic dry run...")
    
    try:
        # Create temporary environment with staging URL
        env = env.get_all()
        env["DATABASE_URL"] = migration_url
        
        # Run alembic current to check connection
        print("   Running 'alembic current'...")
        result = subprocess.run(
            ["python", "-m", "alembic", "-c", alembic_config, "current"],
            env=env,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("   SUCCESS: Alembic can connect to staging database")
            print(f"   Current revision: {result.stdout.strip() or 'No migrations'}")
        else:
            print("   FAILED: Alembic connection failed")
            print(f"   STDOUT: {result.stdout}")
            print(f"   STDERR: {result.stderr}")
            return False
        
        return True
        
    except subprocess.TimeoutExpired:
        print("   TIMEOUT: Alembic command timed out")
        return False
    except FileNotFoundError:
        print("   ERROR: Alembic not found (not installed?)")
        return False
    except Exception as e:
        print(f"   ERROR: {e}")
        return False

def test_migration_safety():
    """Test migration safety checks."""
    print("\n" + "=" * 60)
    print("TESTING MIGRATION SAFETY CHECKS")
    print("=" * 60)
    
    print("\n1. Environment safety checks...")
    
    # Check environment detection
    env_vars = {
        "ENVIRONMENT": "staging",
        "POSTGRES_HOST": "/cloudsql/netra-staging:us-central1:staging-shared-postgres"
    }
    
    builder = DatabaseURLBuilder(env_vars)
    print(f"   Detected environment: {builder.environment}")
    print(f"   Is Cloud SQL: {builder.cloud_sql.is_cloud_sql}")
    
    # Test migration URL safety
    print("\n2. Migration URL safety...")
    
    # Mock migration URL for testing (don't use real for safety)
    mock_migration_url = "postgresql://user:pass@localhost:5432/test_db"
    
    # Test URL validation
    normalized = DatabaseURLBuilder.normalize_postgres_url(mock_migration_url)
    psycopg2_url = DatabaseURLBuilder.format_url_for_driver(normalized, 'psycopg2')
    
    print(f"   Original: {DatabaseURLBuilder.mask_url_for_logging(mock_migration_url)}")
    print(f"   For migrations: {DatabaseURLBuilder.mask_url_for_logging(psycopg2_url)}")
    
    # Validate the migration URL format
    is_valid, error_msg = DatabaseURLBuilder.validate_url_for_driver(psycopg2_url, 'psycopg2')
    print(f"   Migration URL valid: {is_valid}")
    if not is_valid:
        print(f"   Error: {error_msg}")
        return False
    
    return True

def test_database_migration_commands():
    """Test database migration command preparation."""
    print("\n" + "=" * 60)
    print("TESTING DATABASE MIGRATION COMMANDS")
    print("=" * 60)
    
    try:
        # Get staging configuration
        print("\n1. Preparing migration environment...")
        env_vars = {
            "ENVIRONMENT": "staging",
            "POSTGRES_HOST": fetch_secret("postgres-host-staging"),
            "POSTGRES_PORT": fetch_secret("postgres-port-staging"),
            "POSTGRES_DB": fetch_secret("postgres-db-staging"),
            "POSTGRES_USER": fetch_secret("postgres-user-staging"),
            "POSTGRES_PASSWORD": fetch_secret("postgres-password-staging")
        }
        
        builder = DatabaseURLBuilder(env_vars)
        migration_url = builder.get_url_for_environment(sync=True)
        
        # Format URL properly for migrations (psycopg2)
        normalized_url = DatabaseURLBuilder.normalize_postgres_url(migration_url)
        psycopg2_url = DatabaseURLBuilder.format_url_for_driver(normalized_url, 'psycopg2')
        
        print(f"   Migration URL: {DatabaseURLBuilder.mask_url_for_logging(psycopg2_url)}")
        
        # Test command preparation
        print("\n2. Testing migration commands...")
        
        # Common migration commands that would be used
        commands = [
            ["python", "-m", "alembic", "current"],
            ["python", "-m", "alembic", "history", "--verbose"],
            ["python", "-m", "alembic", "check"]  # Dry run check
        ]
        
        for i, cmd in enumerate(commands, 1):
            cmd_str = " ".join(cmd)
            print(f"   Command {i}: {cmd_str}")
            print(f"      Environment: DATABASE_URL={DatabaseURLBuilder.mask_url_for_logging(psycopg2_url)}")
        
        print("\n3. Safety considerations...")
        print("   - Commands are DRY RUN only (no actual migration)")
        print("   - Using psycopg2 driver for Alembic compatibility")
        print("   - SSL parameters handled automatically")
        print("   - Cloud SQL Unix socket connection (secure)")
        
        # Note: We don't actually run migrations on staging in tests
        print("\nNOTE: Actual migration execution skipped for safety")
        print("      Use deployment pipeline for real migrations")
        
        return True
        
    except Exception as e:
        print(f"   FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all database migration tests."""
    print("DATABASE MIGRATION TESTING FOR STAGING")
    print("=" * 80)
    
    tests = [
        ("Migration URL Generation", test_migration_url_generation),
        ("Alembic Configuration", test_alembic_configuration),
        ("Migration Safety Checks", test_migration_safety),
        ("Database Migration Commands", test_database_migration_commands)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'=' * 20} {test_name} {'=' * 20}")
        try:
            result = test_func()
            # Handle case where test_func returns a URL instead of boolean
            if isinstance(result, str):
                result = True
            results.append((test_name, result, None))
            status = "PASSED" if result else "FAILED"
            print(f"\n{test_name}: {status}")
        except Exception as e:
            results.append((test_name, False, str(e)))
            print(f"\n{test_name}: FAILED WITH EXCEPTION")
            print(f"Exception: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 80)
    print("MIGRATION TEST SUMMARY")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for test_name, result, error in results:
        status = "PASSED" if result else "FAILED"
        print(f"{status}: {test_name}")
        if error:
            print(f"    Error: {error}")
        
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\nTotal: {len(results)} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    overall_success = failed == 0
    print(f"\nOverall Result: {'ALL TESTS PASSED' if overall_success else 'SOME TESTS FAILED'}")
    
    return overall_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)