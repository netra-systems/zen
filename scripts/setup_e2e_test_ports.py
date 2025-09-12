from shared.isolated_environment import get_env
#!/usr/bin/env python3
"""Setup E2E Test Ports for Docker and Local Testing

This script ensures E2E tests use the correct ports based on the execution environment.
It detects whether tests are running locally, in Docker, or in CI and configures
ports accordingly.

BVJ:
- Segment: Platform/Internal
- Business Goal: Ensure reliable test execution
- Value Impact: Prevents port conflicts and test failures
- Strategic Impact: Enables parallel testing and CI/CD reliability
"""

import os
import sys
import json
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.e2e.dynamic_port_manager import DynamicPortManager, TestMode


def detect_docker_compose_mode():
    """Detect if docker-compose test services are running"""
    import subprocess
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=netra-test", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            check=True
        )
        test_containers = result.stdout.strip().split('\n')
        # Check if test containers are running
        expected_containers = ["netra-test-backend", "netra-test-auth", "netra-test-postgres"]
        running_test_services = any(name in test_containers for name in expected_containers)
        return running_test_services
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def main():
    """Main function to setup E2E test ports"""
    parser = argparse.ArgumentParser(description="Setup E2E test ports")
    parser.add_argument("--mode", choices=["local", "docker", "ci", "auto"],
                       default="auto", help="Test execution mode")
    parser.add_argument("--export", action="store_true", 
                       help="Export configuration to environment")
    parser.add_argument("--json", action="store_true",
                       help="Output configuration as JSON")
    parser.add_argument("--wait", action="store_true",
                       help="Wait for services to be available")
    
    args = parser.parse_args()
    
    # Determine mode
    if args.mode == "auto":
        if os.environ.get("CI") == "true":
            mode = TestMode.CI
        elif detect_docker_compose_mode():
            mode = TestMode.DOCKER
        else:
            mode = TestMode.LOCAL
    else:
        mode = TestMode[args.mode.upper()]
    
    # Create port manager
    port_manager = DynamicPortManager(mode)
    
    # Export to environment if requested
    if args.export:
        port_manager.export_to_env()
        print(f"Exported port configuration for {mode.value} mode")
    
    # Output configuration
    config = port_manager.get_config_dict()
    
    if args.json:
        print(json.dumps(config, indent=2))
    else:
        print(f"E2E Test Port Configuration ({mode.value} mode):")
        print(f"  Backend: {config['ports']['backend']}")
        print(f"  Auth: {config['ports']['auth']}")
        print(f"  Frontend: {config['ports']['frontend']}")
        print(f"  PostgreSQL: {config['ports']['postgres']}")
        print(f"  Redis: {config['ports']['redis']}")
        print(f"  ClickHouse: {config['ports']['clickhouse']}")
        print("\nService URLs:")
        for service, url in config['urls'].items():
            print(f"  {service}: {url}")
    
    # Wait for services if requested
    if args.wait:
        print("\nWaiting for services to be available...")
        services_to_check = ["backend", "auth", "postgres", "redis"]
        
        all_available = True
        for service in services_to_check:
            if port_manager.wait_for_service(service, timeout=30):
                print(f"  [U+2713] {service} is available")
            else:
                print(f"  [U+2717] {service} is not available")
                all_available = False
        
        if not all_available:
            print("\nSome services are not available!")
            return 1
        else:
            print("\nAll services are ready!")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
