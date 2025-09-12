#!/usr/bin/env python3
"""Test Docker service stability and connectivity."""

import time
import requests
import psycopg2
# MIGRATED: from netra_backend.app.services.redis_client import get_redis_client
import sys
from datetime import datetime
from shared.isolated_environment import IsolatedEnvironment

def test_postgres():
    """Test PostgreSQL connectivity."""
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5433,
            user="netra",
            password="netra123",
            database="netra_dev"
        )
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return True, "PostgreSQL is accessible"
    except Exception as e:
        return False, f"PostgreSQL error: {e}"

def test_redis():
    """Test Redis connectivity."""
    try:
        r = await get_redis_client()  # MIGRATED: was redis.Redis(host='localhost', port=6380, db=0)
        r.ping()
        return True, "Redis is accessible"
    except Exception as e:
        return False, f"Redis error: {e}"

def test_auth_service():
    """Test Auth service health."""
    try:
        response = requests.get("http://localhost:8081/health", timeout=5)
        if response.status_code == 200:
            return True, f"Auth service is healthy: {response.json()['status']}"
        else:
            return False, f"Auth service returned status {response.status_code}"
    except Exception as e:
        return False, f"Auth service error: {e}"

def test_clickhouse():
    """Test ClickHouse connectivity."""
    try:
        response = requests.get("http://localhost:8124/ping", timeout=5)
        if response.status_code == 200:
            return True, "ClickHouse is accessible"
        else:
            return False, f"ClickHouse returned status {response.status_code}"
    except Exception as e:
        return False, f"ClickHouse error: {e}"

def monitor_services(duration_seconds=60):
    """Monitor services for specified duration."""
    print(f"\nStarting Docker service stability test for {duration_seconds} seconds...")
    print("=" * 60)
    
    start_time = time.time()
    test_count = 0
    failures = []
    
    while time.time() - start_time < duration_seconds:
        test_count += 1
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        print(f"\n[{timestamp}] Test #{test_count}")
        print("-" * 40)
        
        # Test each service
        services = [
            ("PostgreSQL", test_postgres),
            ("Redis", test_redis),
            ("Auth Service", test_auth_service),
            ("ClickHouse", test_clickhouse),
        ]
        
        for service_name, test_func in services:
            success, message = test_func()
            icon = "OK" if success else "FAIL"
            print(f"{icon} {service_name}: {message}")
            
            if not success:
                failures.append(f"[{timestamp}] {service_name}: {message}")
        
        # Wait before next test
        if time.time() - start_time < duration_seconds:
            time.sleep(10)
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Total tests run: {test_count}")
    print(f"Total failures: {len(failures)}")
    
    if failures:
        print("\nFailures detected:")
        for failure in failures[-5:]:  # Show last 5 failures
            print(f"  - {failure}")
        return False
    else:
        print("\nAll services remained stable during the test period!")
        return True

if __name__ == "__main__":
    # Run stability test for 60 seconds
    success = monitor_services(60)
    sys.exit(0 if success else 1)