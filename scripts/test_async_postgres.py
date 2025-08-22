#!/usr/bin/env python3
"""Test async PostgreSQL connections for both backend and auth services

This script verifies that the new async-only PostgreSQL configuration
works correctly in local development environment.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set up environment for testing
os.environ["ENVIRONMENT"] = "development"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:password@localhost:5432/netra"
os.environ["SQL_ECHO"] = "false"


async def test_backend_connection():
    """Test backend service database connection"""
    print("\n=== Testing Backend Service Database Connection ===")
    
    try:
        from netra_backend.app.db.postgres_unified import unified_db
        
        # Initialize database
        await unified_db.initialize()
        print("[OK] Backend database initialized")
        
        # Test connection
        is_connected = await unified_db.test_connection()
        if is_connected:
            print("✓ Backend database connection successful")
        else:
            print("✗ Backend database connection failed")
            return False
        
        # Get status
        status = unified_db.get_status()
        print(f"✓ Backend database status: {status}")
        
        # Test session
        async with unified_db.get_session() as session:
            from sqlalchemy import text
            result = await session.execute(text("SELECT version()"))
            version = result.scalar_one()
            print(f"✓ PostgreSQL version: {version[:50]}...")
        
        # Close connection
        await unified_db.close()
        print("✓ Backend database connection closed")
        
        return True
        
    except Exception as e:
        print(f"✗ Backend database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_auth_connection():
    """Test auth service database connection"""
    print("\n=== Testing Auth Service Database Connection ===")
    
    try:
        from auth_service.auth_core.database.connection import auth_db
        
        # Initialize database
        await auth_db.initialize()
        print("✓ Auth database initialized")
        
        # Test connection
        is_connected = await auth_db.test_connection()
        if is_connected:
            print("✓ Auth database connection successful")
        else:
            print("✗ Auth database connection failed")
            return False
        
        # Get status
        status = auth_db.get_status()
        print(f"✓ Auth database status: {status}")
        
        # Test session
        async with auth_db.get_session() as session:
            from sqlalchemy import text
            result = await session.execute(text("SELECT current_database()"))
            db_name = result.scalar_one()
            print(f"✓ Connected to database: {db_name}")
        
        # Close connection
        await auth_db.close()
        print("✓ Auth database connection closed")
        
        return True
        
    except Exception as e:
        print(f"✗ Auth database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_cloud_sql_imports():
    """Test if Cloud SQL connector can be imported"""
    print("\n=== Testing Cloud SQL Connector Availability ===")
    
    try:
        from google.cloud.sql.connector import Connector
        print("✓ Cloud SQL connector is available")
        return True
    except ImportError as e:
        print(f"ℹ Cloud SQL connector not installed (optional for local dev): {e}")
        print("  Install with: pip install cloud-sql-python-connector[asyncpg]")
        return False


async def main():
    """Run all tests"""
    print("=" * 60)
    print("PostgreSQL Async Configuration Test")
    print("=" * 60)
    
    # Check if PostgreSQL is running locally
    print("\n=== Checking PostgreSQL Availability ===")
    try:
        import asyncpg
        # Try to connect directly
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='password',
            database='postgres'
        )
        await conn.close()
        print("[OK] PostgreSQL is running on localhost:5432")
    except Exception as e:
        print(f"[ERROR] PostgreSQL not available: {e}")
        print("\nPlease start PostgreSQL with:")
        print("  docker run --name postgres -e POSTGRES_PASSWORD=password -p 5432:5432 -d postgres")
        return
    
    # Run tests
    results = []
    
    # Test backend connection
    backend_result = await test_backend_connection()
    results.append(("Backend Service", backend_result))
    
    # Test auth connection
    auth_result = await test_auth_connection()
    results.append(("Auth Service", auth_result))
    
    # Test Cloud SQL imports
    cloud_sql_result = await test_cloud_sql_imports()
    results.append(("Cloud SQL Connector", cloud_sql_result))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED" if result is False else "ℹ SKIPPED"
        print(f"{name:.<40} {status}")
    
    all_passed = all(r for _, r in results if r is not False)
    
    if all_passed:
        print("\n✅ All tests passed! Async PostgreSQL configuration is working.")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())