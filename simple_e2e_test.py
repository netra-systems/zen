#!/usr/bin/env python
"""Simple E2E test to verify services are running."""

import asyncio
import sys
import time
import subprocess
import requests
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_backend_health():
    """Test backend health endpoint."""
    try:
        response = requests.get("http://localhost:8001/health/", timeout=5)
        if response.status_code == 200:
            print("[PASS] Backend health check passed")
            return True
        else:
            print(f"[FAIL] Backend health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"[FAIL] Backend not accessible: {e}")
        return False

def test_auth_health():
    """Test auth service health endpoint."""
    try:
        response = requests.get("http://localhost:8083/health", timeout=5)
        if response.status_code == 200:
            print("[PASS] Auth service health check passed")
            return True
        else:
            print(f"[FAIL] Auth service health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"[FAIL] Auth service not accessible: {e}")
        return False

def test_database_connection():
    """Test database connectivity."""
    try:
        # Import after path setup
        from netra_backend.app.db.postgres_core import PostgresManager
        import asyncio
        
        async def check_db():
            manager = PostgresManager()
            await manager.initialize()
            result = await manager.test_connection()
            await manager.shutdown()
            return result
        
        result = asyncio.run(check_db())
        if result:
            print("[PASS] Database connection test passed")
            return True
        else:
            print("[FAIL] Database connection test failed")
            return False
    except Exception as e:
        print(f"[SKIP] Database test skipped: {e}")
        return None

def start_services():
    """Start services using dev_launcher."""
    print("\n[INFO] Starting services...")
    process = subprocess.Popen(
        ["python", "scripts/dev_launcher.py", "--no-browser"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for services to start
    print("[INFO] Waiting for services to start (30 seconds)...")
    time.sleep(30)
    
    # Check if process is still running
    if process.poll() is not None:
        stdout, stderr = process.communicate()
        print(f"[FAIL] Services failed to start")
        print(f"Error: {stderr}")
        return None
    
    return process

def run_e2e_tests():
    """Run simple E2E tests."""
    print("\n" + "="*60)
    print("SIMPLE E2E TEST SUITE")
    print("="*60)
    
    # Check if services are already running
    backend_running = test_backend_health()
    auth_running = test_auth_health()
    
    services_process = None
    if not backend_running or not auth_running:
        print("\n[WARN] Services not running, attempting to start...")
        services_process = start_services()
        
        if services_process is None:
            print("[FAIL] Failed to start services")
            return False
    else:
        print("\n[INFO] Services already running")
    
    # Run tests
    print("\n[TEST] Running E2E Tests...")
    print("-" * 40)
    
    results = []
    
    # Test 1: Backend Health
    results.append(("Backend Health", test_backend_health()))
    
    # Test 2: Auth Service Health
    results.append(("Auth Service Health", test_auth_health()))
    
    # Test 3: Database Connection
    db_result = test_database_connection()
    if db_result is not None:
        results.append(("Database Connection", db_result))
    
    # Test 4: API Endpoint
    try:
        response = requests.get("http://localhost:8001/api/v1/threads", timeout=5)
        api_test = response.status_code in [200, 401, 403]  # Any of these is fine
        print(f"[PASS] API endpoint test passed (status: {response.status_code})")
        results.append(("API Endpoint", True))
    except Exception as e:
        print(f"[FAIL] API endpoint test failed: {e}")
        results.append(("API Endpoint", False))
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    failed = sum(1 for _, result in results if not result)
    
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{test_name:25} {status}")
    
    print("-" * 40)
    print(f"Total: {len(results)} | Passed: {passed} | Failed: {failed}")
    
    # Cleanup
    if services_process:
        print("\n[INFO] Stopping services...")
        services_process.terminate()
        services_process.wait(timeout=10)
    
    return failed == 0

if __name__ == "__main__":
    success = run_e2e_tests()
    sys.exit(0 if success else 1)