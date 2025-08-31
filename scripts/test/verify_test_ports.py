#!/usr/bin/env python3
"""Verify test service port configuration is correct."""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from test_framework.real_services import ServiceConfig, RealServicesManager

def main():
    """Verify test port configuration."""
    print("=" * 60)
    print("TEST SERVICE PORT CONFIGURATION VERIFICATION")
    print("=" * 60)
    
    # Load configuration from environment
    manager = RealServicesManager()
    config = manager.config
    
    # Expected port mappings from docker-compose.yml
    expected = {
        "PostgreSQL": {"port": 5434, "actual": config.postgres_port},
        "Redis": {"port": 6381, "actual": config.redis_port},
        "ClickHouse TCP": {"port": 9000, "actual": config.clickhouse_port},
        "Auth Service": {"url": "http://localhost:8082", "actual": config.auth_service_url},
        "Backend Service": {"url": "http://localhost:8001", "actual": config.backend_service_url},
    }
    
    # Also check default values in ServiceConfig
    default_config = ServiceConfig()
    defaults = {
        "PostgreSQL (default)": {"port": 5434, "actual": default_config.postgres_port},
        "Redis (default)": {"port": 6381, "actual": default_config.redis_port},
        "ClickHouse TCP (default)": {"port": 9000, "actual": default_config.clickhouse_port},
    }
    
    print("\nConfiguration from environment:")
    all_correct = True
    for service, check in expected.items():
        if "port" in check:
            is_correct = check["port"] == check["actual"]
            status = "OK" if is_correct else "FAIL"
            print(f"  {status} {service}: {check['actual']} (expected: {check['port']})")
        else:
            is_correct = check["url"] == check["actual"]
            status = "OK" if is_correct else "FAIL"
            print(f"  {status} {service}: {check['actual']} (expected: {check['url']})")
        
        if not is_correct:
            all_correct = False
    
    print("\nDefault configuration values:")
    for service, check in defaults.items():
        is_correct = check["port"] == check["actual"]
        status = "OK" if is_correct else "FAIL"
        print(f"  {status} {service}: {check['actual']} (expected: {check['port']})")
        
        if not is_correct:
            all_correct = False
    
    print("\nCredentials check:")
    print(f"  PostgreSQL: user={config.postgres_user}, password={config.postgres_password}")
    print(f"  ClickHouse: user={config.clickhouse_user}, password={config.clickhouse_password}")
    
    # Check .env.test file if it exists
    env_test_path = project_root / ".env.test"
    if env_test_path.exists():
        print("\n.env.test file values:")
        with open(env_test_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if any(key in line for key in ["PORT", "USER", "PASSWORD"]):
                        print(f"  {line}")
    
    print("\n" + "=" * 60)
    if all_correct:
        print("SUCCESS: All port configurations are CORRECT!")
    else:
        print("ERROR: Some port configurations are INCORRECT!")
        print("\nTo fix:")
        print("1. Ensure Docker Desktop is running")
        print("2. Run: docker compose --profile test up -d")
        print("3. Wait for services to be healthy")
        print("4. Run tests again")
    print("=" * 60)
    
    return 0 if all_correct else 1

if __name__ == "__main__":
    sys.exit(main())