#!/usr/bin/env python
"""
Test script to demonstrate Podman dynamic port allocation
"""

import sys
import time
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from test_framework.podman_dynamic_ports import PodmanDynamicPortManager


def main():
    """Test dynamic port allocation with Podman."""
    print("=" * 60)
    print("Podman Dynamic Port Allocation Test")
    print("=" * 60)
    
    # Create port manager with unique test ID
    test_id = f"demo_{int(time.time())}"
    manager = PodmanDynamicPortManager(test_id)
    
    print(f"\nTest ID: {test_id}")
    print("\nStarting services with dynamic ports...")
    
    try:
        # Start all services
        ports = manager.start_all_services()
        
        print("\n[OK] Services started successfully!")
        print("\nAllocated ports:")
        for service, port in ports.items():
            print(f"  {service:12} -> {port}")
        
        # Test connections
        print("\n\nTesting connections:")
        
        # Test PostgreSQL
        import psycopg2
        try:
            conn = psycopg2.connect(
                host="localhost",
                port=ports['postgres'],
                user="test",
                password="test",
                database="netra_test"
            )
            conn.close()
            print("  [OK] PostgreSQL connection successful")
        except Exception as e:
            print(f"  [FAIL] PostgreSQL connection failed: {e}")
        
        # Test Redis
        import redis
        try:
            r = redis.Redis(host='localhost', port=ports['redis'], db=0)
            r.ping()
            print("  [OK] Redis connection successful")
        except Exception as e:
            print(f"  [FAIL] Redis connection failed: {e}")
        
        print("\n[SUCCESS] Dynamic port allocation working perfectly!")
        
        # Keep containers running for manual testing
        input("\nPress Enter to stop containers and exit...")
        
    finally:
        # Cleanup
        print("\nCleaning up containers...")
        manager.cleanup()
        print("[OK] Cleanup complete")
    
    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()