#!/usr/bin/env python3
"""
Test script to diagnose and fix port allocation issues in the test runner.
This simulates what the test runner does when acquiring Docker environment.
"""
import sys
import subprocess
import logging
from test_framework.docker.unified_docker_manager import UnifiedDockerManager
from shared.isolated_environment import IsolatedEnvironment

# Add the project root to path
sys.path.insert(0, '/Users/anthony/Documents/GitHub/netra-apex')

from test_framework.unified_docker_manager import UnifiedDockerManager, EnvironmentType

# Enable debug logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_docker_environment_acquisition():
    """Test the Docker environment acquisition process"""
    
    print("\n=== TESTING DOCKER ENVIRONMENT ACQUISITION ===\n")
    
    # Create manager instance like the test runner does
    manager = UnifiedDockerManager(
        test_id='test-port-fix',
        environment_type=EnvironmentType.TEST,
        use_production_images=True
    )
    
    print("1. Detecting existing containers...")
    containers = manager._detect_existing_dev_containers()
    print(f"   Found {len(containers)} containers:")
    for service, container in containers.items():
        print(f"   - {service}: {container}")
    
    print("\n2. Discovering ports from existing containers...")
    if containers:
        ports = manager._discover_ports_from_existing_containers(containers)
        print(f"   Discovered {len(ports)} port mappings:")
        for service, port in ports.items():
            print(f"   - {service}: {port}")
    else:
        print("   No containers found, would allocate new ports")
        
    print("\n3. Acquiring environment (full process)...")
    try:
        env_name, allocated_ports = manager.acquire_environment()
        print(f"   Environment: {env_name}")
        print(f"   Allocated ports:")
        for service, port in allocated_ports.items():
            print(f"   - {service}: {port}")
            
        # Test connectivity to the allocated ports
        print("\n4. Testing connectivity to allocated ports...")
        import socket
        for service, port in allocated_ports.items():
            if service in ['backend', 'auth', 'postgres', 'redis', 'clickhouse']:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1)
                    result = sock.connect_ex(('localhost', port))
                    sock.close()
                    if result == 0:
                        print(f"    PASS:  {service}: Port {port} is open")
                    else:
                        print(f"    FAIL:  {service}: Port {port} is closed")
                except Exception as e:
                    print(f"    FAIL:  {service}: Error testing port {port}: {e}")
                    
    except Exception as e:
        print(f"   ERROR: Failed to acquire environment: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Clean up
        try:
            manager.release_environment()
            print("\n5. Released environment")
        except:
            pass

if __name__ == "__main__":
    test_docker_environment_acquisition()