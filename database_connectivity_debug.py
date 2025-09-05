#!/usr/bin/env python3
"""
Database Connectivity Debug Tool
Tests actual database connectivity to debug configuration issues
"""

import sys
import socket
from shared.isolated_environment import IsolatedEnvironment, get_env

def test_port_connectivity(host, port, service_name):
    """Test if we can connect to a specific host:port"""
    print(f"\n=== Testing {service_name} at {host}:{port} ===")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, int(port)))
        sock.close()
        
        if result == 0:
            print(f"[OK] {service_name} is REACHABLE at {host}:{port}")
            return True
        else:
            print(f"[FAIL] {service_name} is NOT REACHABLE at {host}:{port}")
            print(f"   Connection result: {result}")
            return False
            
    except Exception as e:
        print(f"[ERROR] {service_name} CONNECTION ERROR: {e}")
        return False

def main():
    print("DATABASE CONNECTIVITY DEBUGGING")
    print("==================================")
    
    # Initialize environment
    env = get_env()
    
    print(f"\nEnvironment Variables:")
    print(f"TESTING: {env.get('TESTING', 'not set')}")
    print(f"NETRA_ENV: {env.get('NETRA_ENV', 'not set')}")
    print(f"ENVIRONMENT: {env.get('ENVIRONMENT', 'not set')}")
    
    # Test expected configurations
    configs_to_test = [
        # ClickHouse configurations from different sources
        ("ClickHouse Test Port 8125", "localhost", "8125"),
        ("ClickHouse Test Port 8126", "localhost", "8126"),  
        ("ClickHouse Default", "localhost", "8123"),
        
        # PostgreSQL configurations
        ("PostgreSQL Dev", "localhost", "5433"),
        ("PostgreSQL Test", "localhost", "5434"), 
        ("PostgreSQL Default", "localhost", "5432"),
        
        # Redis configurations  
        ("Redis Dev", "localhost", "6379"),
        ("Redis Test", "localhost", "6381"),
    ]
    
    results = []
    for name, host, port in configs_to_test:
        result = test_port_connectivity(host, port, name)
        results.append((name, result))
    
    print(f"\n{'='*50}")
    print("CONNECTIVITY SUMMARY")
    print(f"{'='*50}")
    
    reachable = []
    unreachable = []
    
    for name, result in results:
        if result:
            reachable.append(name)
            print(f"[OK] {name}")
        else:
            unreachable.append(name)
            print(f"[FAIL] {name}")
    
    print(f"\nREACHABLE SERVICES: {len(reachable)}")
    print(f"UNREACHABLE SERVICES: {len(unreachable)}")
    
    if unreachable:
        print(f"\nCRITICAL: {len(unreachable)} services are not reachable!")
        print("   This explains why database tests are failing.")
        print("\nNEXT STEPS:")
        print("   1. Start Docker services with appropriate ports")
        print("   2. Check Docker compose configuration alignment")  
        print("   3. Verify port conflicts")
        return 1
    else:
        print(f"\nAll services are reachable!")
        return 0

if __name__ == "__main__":
    sys.exit(main())