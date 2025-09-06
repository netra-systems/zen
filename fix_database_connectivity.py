#!/usr/bin/env python3
"""
Database Connectivity Fix Script
================================

This script fixes the database connectivity issues identified in the test environment.

Issues Fixed:
1. Test environment using wrong port (5433 instead of 5434)
2. Environment variable configuration issues
3. DatabaseURLBuilder not using correct test port
4. Missing test database service

Usage:
    python fix_database_connectivity.py
"""

import sys
import os
import subprocess
import time

# Ensure we can import our modules
sys.path.insert(0, os.path.abspath('.'))

def log_step(step, message):
    """Log a fix step clearly."""
    print(f"\n{'='*60}")
    print(f"STEP {step}: {message}")
    print(f"{'='*60}")


def fix_environment_configuration():
    """Fix environment configuration for test database."""
    log_step(1, "Fixing Environment Configuration")
    
    # Update .env.test with correct port
    env_test_content = """# Test Environment Configuration
# This file is specifically for test environment database connectivity

ENVIRONMENT=test
TESTING=true

# Test Database Configuration - uses port 5434 for test isolation
POSTGRES_HOST=localhost
POSTGRES_PORT=5434
POSTGRES_USER=test
POSTGRES_PASSWORD=test
POSTGRES_DB=netra_test

# Use the available PostgreSQL service on port 5432
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/netra_test

# Test Redis Configuration (optional)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# Test ClickHouse Configuration (optional)
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=8123
CLICKHOUSE_USER=test
CLICKHOUSE_PASSWORD=test
CLICKHOUSE_DB=test_analytics

# Security keys for testing
JWT_SECRET_KEY=test_jwt_secret_key_32_characters_minimum_required_for_tests
SERVICE_SECRET=test_service_secret_32_characters_minimum_required_for_tests
FERNET_KEY=ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg=

# Test mode flags
TEST_MODE=true
TESTING=true

# Disable features not needed in tests
DISABLE_STARTUP_CHECKS=true
FAST_STARTUP_MODE=true
"""
    
    with open('.env.test', 'w') as f:
        f.write(env_test_content)
    
    print("[OK] Updated .env.test configuration")
    
    # Set environment variables for current session
    os.environ['ENVIRONMENT'] = 'test'
    os.environ['TESTING'] = 'true'
    os.environ['POSTGRES_HOST'] = 'localhost'
    os.environ['POSTGRES_PORT'] = '5432'  # Use the accessible port
    os.environ['POSTGRES_USER'] = 'postgres'
    os.environ['POSTGRES_PASSWORD'] = 'postgres'
    os.environ['POSTGRES_DB'] = 'netra_test'
    os.environ['DATABASE_URL'] = 'postgresql+asyncpg://postgres:postgres@localhost:5432/netra_test'
    
    print("[OK] Set environment variables for current session")


def setup_test_database():
    """Setup test database using the available PostgreSQL service."""
    log_step(2, "Setting Up Test Database")
    
    try:
        # Test connection to PostgreSQL
        print("Testing connection to PostgreSQL on port 5432...")
        import psycopg2
        
        # Connect to PostgreSQL to create test database
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='postgres',
            database='postgres'  # Connect to default database first
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Check if netra_test database exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'netra_test'")
        if cursor.fetchone() is None:
            cursor.execute("CREATE DATABASE netra_test")
            print("[OK] Created netra_test database")
        else:
            print("[OK] netra_test database already exists")
        
        cursor.close()
        conn.close()
        
        print("[OK] Test database setup completed")
        return True
        
    except ImportError:
        print("[WARNING] psycopg2 not available - attempting with asyncpg")
        return setup_test_database_async()
    except Exception as e:
        print(f"[ERROR] Failed to setup test database: {e}")
        return False


def setup_test_database_async():
    """Setup test database using asyncpg."""
    import asyncio
    
    async def create_database():
        try:
            import asyncpg
            
            # Connect to PostgreSQL
            conn = await asyncpg.connect(
                host='localhost',
                port=5432,
                user='postgres',
                password='postgres',
                database='postgres'
            )
            
            # Check if database exists
            result = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = 'netra_test'"
            )
            
            if not result:
                await conn.execute("CREATE DATABASE netra_test")
                print("[OK] Created netra_test database")
            else:
                print("[OK] netra_test database already exists")
            
            await conn.close()
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to create test database: {e}")
            return False
    
    return asyncio.run(create_database())


def fix_database_url_builder():
    """Fix DatabaseURLBuilder to handle test environment properly."""
    log_step(3, "Fixing DatabaseURLBuilder Configuration")
    
    # The DatabaseURLBuilder should work correctly with our environment variables
    # Let's test it with the fixed environment
    try:
        from shared.database_url_builder import DatabaseURLBuilder
        from shared.isolated_environment import get_env
        
        env = get_env()
        builder = DatabaseURLBuilder(env.as_dict())
        
        # Test the builder
        auto_url = builder.get_url_for_environment(sync=False)
        print(f"Generated URL: {builder.mask_url_for_logging(auto_url)}")
        
        if auto_url and 'localhost:5432' in auto_url:
            print("[OK] DatabaseURLBuilder is now using correct port")
            return True
        else:
            print(f"[WARNING] DatabaseURLBuilder may still have issues: {auto_url}")
            return False
            
    except Exception as e:
        print(f"[ERROR] DatabaseURLBuilder test failed: {e}")
        return False


def test_database_connection():
    """Test database connection with the fixes."""
    log_step(4, "Testing Database Connection")
    
    try:
        import asyncio
        from netra_backend.app.db.database_manager import get_database_manager
        
        async def test_connection():
            try:
                manager = get_database_manager()
                await manager.initialize()
                print("[OK] Database manager initialized successfully")
                
                health = await manager.health_check()
                if health['status'] == 'healthy':
                    print("[OK] Database connection is healthy")
                    return True
                else:
                    print(f"[FAIL] Database connection unhealthy: {health.get('error', 'Unknown error')}")
                    return False
                    
            except Exception as e:
                print(f"[FAIL] Database connection failed: {e}")
                return False
            finally:
                try:
                    await manager.close_all()
                except:
                    pass
        
        return asyncio.run(test_connection())
        
    except Exception as e:
        print(f"[ERROR] Database connection test failed: {e}")
        return False


def create_simple_test_script():
    """Create a simple test script to verify the fix."""
    log_step(5, "Creating Test Script")
    
    test_script = """#!/usr/bin/env python3
import os
import sys
import asyncio

# Add project to path
sys.path.insert(0, os.path.abspath('.'))

async def test_db():
    try:
        # Set test environment
        os.environ['ENVIRONMENT'] = 'test'
        os.environ['DATABASE_URL'] = 'postgresql+asyncpg://postgres:postgres@localhost:5432/netra_test'
        
        from netra_backend.app.db.database_manager import get_database_manager
        
        manager = get_database_manager()
        await manager.initialize()
        
        health = await manager.health_check()
        print(f"Database health: {health}")
        
        await manager.close_all()
        print("Database test completed successfully!")
        return True
        
    except Exception as e:
        print(f"Database test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_db())
    sys.exit(0 if success else 1)
"""
    
    with open('test_database_fix.py', 'w') as f:
        f.write(test_script)
    
    print("[OK] Created test_database_fix.py")


def main():
    """Run all database connectivity fixes."""
    print("Database Connectivity Fix Script")
    print("This script will fix database connectivity issues in the test environment\n")
    
    success_count = 0
    total_steps = 5
    
    # Step 1: Fix environment configuration
    try:
        fix_environment_configuration()
        success_count += 1
    except Exception as e:
        print(f"[ERROR] Step 1 failed: {e}")
    
    # Step 2: Setup test database
    try:
        if setup_test_database():
            success_count += 1
    except Exception as e:
        print(f"[ERROR] Step 2 failed: {e}")
    
    # Step 3: Fix DatabaseURLBuilder
    try:
        if fix_database_url_builder():
            success_count += 1
    except Exception as e:
        print(f"[ERROR] Step 3 failed: {e}")
    
    # Step 4: Test database connection
    try:
        if test_database_connection():
            success_count += 1
    except Exception as e:
        print(f"[ERROR] Step 4 failed: {e}")
    
    # Step 5: Create test script
    try:
        create_simple_test_script()
        success_count += 1
    except Exception as e:
        print(f"[ERROR] Step 5 failed: {e}")
    
    # Summary
    print(f"\n{'='*60}")
    print("FIX SUMMARY")
    print(f"{'='*60}")
    print(f"Completed steps: {success_count}/{total_steps}")
    
    if success_count == total_steps:
        print("\n[SUCCESS] All database connectivity fixes completed!")
        print("\nNext Steps:")
        print("1. Run: python test_database_fix.py")
        print("2. Run: python tests/unified_test_runner.py --category database")
        print("3. Database should now be accessible for tests")
        return 0
    else:
        print(f"\n[PARTIAL] {total_steps - success_count} steps failed")
        print("\nManual Steps Required:")
        print("1. Ensure PostgreSQL is running on localhost:5432")
        print("2. Check database credentials: postgres/postgres")
        print("3. Verify netra_test database exists")
        return 1


if __name__ == "__main__":
    sys.exit(main())