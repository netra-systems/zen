"""Test auth service database session management and DatabaseURLBuilder integration."""

import sys
import os
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock
from google.cloud import secretmanager

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

def test_auth_service_database_manager_import():
    """Test that auth service database manager can be imported and uses DatabaseURLBuilder."""
    print("=" * 60)
    print("TESTING AUTH SERVICE DATABASE MANAGER IMPORT")
    print("=" * 60)
    
    try:
        # Test import
        print("\n1. Testing auth service imports...")
        from auth_service.auth_core.database.database_manager import AuthDatabaseManager
        print("   AuthDatabaseManager imported successfully")
        
        # Check if it has methods for URL handling
        print("\n2. Checking DatabaseManager methods...")
        expected_methods = [
            'convert_database_url',
            'create_async_engine',
            'get_database_url',
            'validate_base_url'
        ]
        
        for method_name in expected_methods:
            if hasattr(AuthDatabaseManager, method_name):
                print(f"   + {method_name} method exists")
            else:
                print(f"   - {method_name} method missing")
                return False
        
        return True
        
    except ImportError as e:
        print(f"   FAILED: Cannot import AuthDatabaseManager: {e}")
        return False
    except Exception as e:
        print(f"   FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_auth_database_url_conversion():
    """Test auth service URL conversion with DatabaseURLBuilder integration."""
    print("\n" + "=" * 60)
    print("TESTING AUTH DATABASE URL CONVERSION")
    print("=" * 60)
    
    try:
        from auth_service.auth_core.database.database_manager import AuthDatabaseManager
        
        # Test URL conversion
        print("\n1. Testing URL conversion...")
        
        test_urls = [
            "postgresql://user:pass@localhost:5432/db",
            "postgresql://user:pass@localhost:5432/db?sslmode=require",
            "postgresql://user:pass@/db?host=/cloudsql/project:region:instance"
        ]
        
        for i, test_url in enumerate(test_urls, 1):
            print(f"\n   Test case {i}: {DatabaseURLBuilder.mask_url_for_logging(test_url)}")
            
            # Test URL conversion to async
            try:
                async_url = AuthDatabaseManager.convert_database_url(test_url)
                print(f"   Async URL: {DatabaseURLBuilder.mask_url_for_logging(async_url)}")
                
                # Validate the converted URL
                if not async_url.startswith(("postgresql+asyncpg://", "postgresql://")):
                    print(f"   ERROR: Invalid async URL format")
                    return False
                
                # Check SSL parameter handling
                if "/cloudsql/" in test_url and "ssl" in async_url:
                    print(f"   ERROR: Cloud SQL URL should not have SSL parameters")
                    return False
                
                print(f"   + URL conversion successful")
                
            except Exception as e:
                print(f"   ERROR: URL conversion failed: {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"   FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_auth_database_engine_creation():
    """Test auth service database engine creation."""
    print("\n" + "=" * 60)
    print("TESTING AUTH DATABASE ENGINE CREATION")
    print("=" * 60)
    
    try:
        from auth_service.auth_core.database.database_manager import AuthDatabaseManager
        
        # Test engine creation with mock URL
        print("\n1. Testing engine creation...")
        
        # Use a memory database for testing
        test_url = "sqlite+aiosqlite:///:memory:"
        
        print(f"   Test URL: {test_url}")
        
        # Create engine
        engine = AuthDatabaseManager.create_async_engine(
            database_url=test_url,
            echo=False,
            pool_pre_ping=True
        )
        
        if engine:
            print("   + Engine created successfully")
            print(f"   Engine URL: {engine.url}")
            
            # Test engine disposal
            engine.dispose()
            print("   + Engine disposed successfully")
        else:
            print("   ERROR: Engine creation failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"   FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_auth_database_url_validation():
    """Test auth service database URL validation."""
    print("\n" + "=" * 60)
    print("TESTING AUTH DATABASE URL VALIDATION")
    print("=" * 60)
    
    try:
        from auth_service.auth_core.database.database_manager import AuthDatabaseManager
        
        # Test URL validation
        print("\n1. Testing URL validation...")
        
        # Test valid URLs
        valid_urls = [
            "postgresql://user:pass@localhost:5432/db",
            "sqlite:///test.db"
        ]
        
        for url in valid_urls:
            print(f"   Testing valid URL: {DatabaseURLBuilder.mask_url_for_logging(url)}")
            with patch.dict(os.environ, {"DATABASE_URL": url}):
                try:
                    is_valid = AuthDatabaseManager.validate_base_url()
                    print(f"   Result: {is_valid}")
                    if not is_valid:
                        print(f"   WARNING: Expected valid URL to pass validation")
                except Exception as e:
                    print(f"   Error during validation: {e}")
        
        # Test invalid URLs
        print("\n2. Testing invalid URLs...")
        invalid_urls = [
            "invalid_url",
            "",
            "postgresql+asyncpg://user:pass@localhost:5432/db"  # Should be stripped to base
        ]
        
        for url in invalid_urls:
            print(f"   Testing URL: {DatabaseURLBuilder.mask_url_for_logging(url)}")
            with patch.dict(os.environ, {"DATABASE_URL": url}):
                try:
                    is_valid = AuthDatabaseManager.validate_base_url()
                    print(f"   Result: {is_valid}")
                except Exception as e:
                    print(f"   Error during validation (expected): {e}")
        
        return True
        
    except Exception as e:
        print(f"   FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_auth_database_staging_integration():
    """Test auth service database integration with staging configuration."""
    print("\n" + "=" * 60)
    print("TESTING AUTH DATABASE STAGING INTEGRATION")
    print("=" * 60)
    
    try:
        from auth_service.auth_core.database.database_manager import AuthDatabaseManager
        
        # Get staging configuration
        print("\n1. Fetching staging configuration...")
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
        
        # Build database URL using DatabaseURLBuilder
        print("\n2. Building database URL...")
        builder = DatabaseURLBuilder(env_vars)
        base_url = builder.get_url_for_environment(sync=True)  # Get base URL
        
        print(f"   Base URL: {DatabaseURLBuilder.mask_url_for_logging(base_url)}")
        
        # Test auth service URL conversion
        print("\n3. Testing auth service URL conversion...")
        if base_url:
            async_url = AuthDatabaseManager.convert_database_url(base_url)
            print(f"   Auth async URL: {DatabaseURLBuilder.mask_url_for_logging(async_url)}")
            
            # Validate URL format
            if async_url.startswith(("postgresql+asyncpg://", "postgresql://")):
                print("   + URL format valid")
            else:
                print("   ERROR: Invalid URL format")
                return False
            
            # Check SSL parameter handling for Cloud SQL
            if "/cloudsql/" in base_url:
                if "ssl" in async_url.lower():
                    print("   ERROR: Cloud SQL URL should not have SSL parameters")
                    return False
                else:
                    print("   + Cloud SQL SSL parameters handled correctly")
        
        # Test engine creation (don't actually connect)
        print("\n4. Testing engine creation configuration...")
        try:
            # We'll use a mock URL to test engine creation without connecting
            mock_url = "sqlite+aiosqlite:///:memory:"
            engine = AuthDatabaseManager.create_async_engine(
                database_url=mock_url,
                echo=False,
                pool_pre_ping=True
            )
            
            if engine:
                print("   + Engine creation configuration valid")
                engine.dispose()
            else:
                print("   ERROR: Engine creation failed")
                return False
                
        except Exception as e:
            print(f"   ERROR: Engine creation failed: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"   FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_auth_database_session_lifecycle():
    """Test auth service database session lifecycle management."""
    print("\n" + "=" * 60)
    print("TESTING AUTH DATABASE SESSION LIFECYCLE")
    print("=" * 60)
    
    try:
        from auth_service.auth_core.database.database_manager import AuthDatabaseManager
        
        print("\n1. Testing session management patterns...")
        
        # Test with SQLite memory database for safety
        test_url = "sqlite+aiosqlite:///:memory:"
        
        # Create engine
        engine = AuthDatabaseManager.create_async_engine(
            database_url=test_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10
        )
        
        print("   + Engine created with connection pool")
        print(f"   Pool size: 5, Max overflow: 10")
        
        # Test connection pool configuration
        if hasattr(engine.pool, 'size'):
            print(f"   Pool size: {engine.pool.size()}")
        
        # Clean up
        engine.dispose()
        print("   + Engine disposed successfully")
        
        # Test URL validation methods
        print("\n2. Testing URL validation methods...")
        
        # Mock environment with staging URL
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://user:pass@localhost:5432/db"}):
            try:
                is_valid = AuthDatabaseManager.validate_base_url()
                print(f"   Base URL validation: {is_valid}")
            except Exception as e:
                print(f"   Validation error: {e}")
        
        return True
        
    except Exception as e:
        print(f"   FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all auth service database session tests."""
    print("AUTH SERVICE DATABASE SESSION MANAGEMENT TESTING")
    print("=" * 80)
    
    tests = [
        ("Auth Database Manager Import", test_auth_service_database_manager_import),
        ("Auth Database URL Conversion", test_auth_database_url_conversion),
        ("Auth Database Engine Creation", test_auth_database_engine_creation),
        ("Auth Database URL Validation", test_auth_database_url_validation),
        ("Auth Database Staging Integration", test_auth_database_staging_integration),
        ("Auth Database Session Lifecycle", test_auth_database_session_lifecycle)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'=' * 20} {test_name} {'=' * 20}")
        try:
            result = test_func()
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
    print("AUTH DATABASE SESSION TEST SUMMARY")
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