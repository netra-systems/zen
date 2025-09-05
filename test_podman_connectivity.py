#!/usr/bin/env python3
"""
Test script to verify connectivity to Podman services.
This script tests direct connectivity to the database services running in Podman.
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load test environment
from shared.isolated_environment import get_env

env = get_env()

# Load the test environment configuration
env_file = project_root / ".env.test.podman"
if env_file.exists():
    env.load_from_file(env_file)
    print(f"✓ Loaded environment from {env_file}")
else:
    print(f"✗ Environment file not found: {env_file}")
    sys.exit(1)

def test_postgresql():
    """Test PostgreSQL connection"""
    try:
        import psycopg2
        
        host = env.get("POSTGRES_HOST", "localhost")
        port = int(env.get("POSTGRES_PORT", "5433"))
        user = env.get("POSTGRES_USER", "postgres")
        password = env.get("POSTGRES_PASSWORD", "postgres")
        database = env.get("POSTGRES_DB", "netra_test")
        
        print(f"Testing PostgreSQL connection: {user}@{host}:{port}/{database}")
        
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"✓ PostgreSQL connected successfully: {version[0][:50]}...")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ PostgreSQL connection failed: {e}")
        return False

def test_redis():
    """Test Redis connection"""
    try:
        import redis
        
        host = env.get("REDIS_HOST", "localhost")
        port = int(env.get("REDIS_PORT", "6379"))
        
        print(f"Testing Redis connection: {host}:{port}")
        
        r = redis.Redis(host=host, port=port, db=0)
        ping_result = r.ping()
        info = r.info()
        
        print(f"✓ Redis connected successfully: {info.get('redis_version', 'unknown version')}")
        return True
        
    except Exception as e:
        print(f"✗ Redis connection failed: {e}")
        return False

def test_clickhouse():
    """Test ClickHouse connection"""
    try:
        import requests
        
        host = env.get("CLICKHOUSE_HOST", "localhost")
        http_port = int(env.get("CLICKHOUSE_HTTP_PORT", "8123"))
        
        print(f"Testing ClickHouse HTTP connection: {host}:{http_port}")
        
        response = requests.get(f"http://{host}:{http_port}/ping", timeout=5)
        
        if response.status_code == 200:
            print("✓ ClickHouse HTTP interface accessible")
            return True
        else:
            print(f"✗ ClickHouse returned status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ ClickHouse connection failed: {e}")
        return False

def test_environment_variables():
    """Test that key environment variables are set correctly"""
    print("\nEnvironment Variable Check:")
    
    required_vars = [
        "ENVIRONMENT",
        "POSTGRES_HOST",
        "POSTGRES_PORT", 
        "POSTGRES_USER",
        "POSTGRES_DB",
        "DATABASE_URL",
        "REDIS_HOST",
        "REDIS_PORT",
        "REDIS_URL"
    ]
    
    all_set = True
    for var in required_vars:
        value = env.get(var)
        if value:
            # Mask sensitive values
            if any(sensitive in var.lower() for sensitive in ['password', 'secret', 'key']):
                display_value = value[:3] + "***" if len(value) > 3 else "***"
            else:
                display_value = value
            print(f"  ✓ {var} = {display_value}")
        else:
            print(f"  ✗ {var} = NOT SET")
            all_set = False
    
    return all_set

def main():
    """Run all connectivity tests"""
    print("=" * 60)
    print("PODMAN SERVICE CONNECTIVITY TEST")
    print("=" * 60)
    
    # Test environment variables
    env_ok = test_environment_variables()
    print()
    
    # Test connections
    tests = [
        ("PostgreSQL", test_postgresql),
        ("Redis", test_redis),
        ("ClickHouse", test_clickhouse),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n{name} Test:")
        print("-" * 20)
        success = test_func()
        results.append((name, success))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {name:<15}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total and env_ok:
        print("🎉 All tests passed! Podman services are accessible.")
        return 0
    else:
        print("❌ Some tests failed. Check the configuration above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())