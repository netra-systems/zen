#!/usr/bin/env python3
"""
Database Service Infrastructure Testing - Issue #837 Phase 2

This script tests the current status and connectivity of required database services
for integration testing in a NON-DOCKER environment.

Expected Services:
- PostgreSQL (expected port 5433)
- Redis (default port 6379)
- ClickHouse (ports 8123/9000)
"""

import sys
import socket
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from shared.isolated_environment import IsolatedEnvironment

def check_port_availability(host: str, port: int, timeout: float = 3.0) -> bool:
    """Check if a port is available for connection."""
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            return True
    except (socket.error, OSError):
        return False

def check_windows_services() -> List[str]:
    """Check for database-related Windows services."""
    try:
        result = subprocess.run(
            ["sc", "query", "type=", "service", "state=", "all"],
            capture_output=True,
            text=True,
            timeout=10
        )

        services = []
        for line in result.stdout.split('\n'):
            line = line.strip().lower()
            if any(db in line for db in ['postgres', 'redis', 'clickhouse', 'mysql']):
                services.append(line)

        return services
    except Exception as e:
        return [f"Error checking services: {e}"]

def test_python_connectivity() -> Dict[str, Dict[str, str]]:
    """Test database connectivity using Python libraries."""
    results = {}

    # Test PostgreSQL connectivity
    try:
        import psycopg2
        # Try different ports commonly used for PostgreSQL
        postgres_ports = [5432, 5433, 5434]
        postgres_result = {"status": "failed", "error": "No ports accessible"}

        for port in postgres_ports:
            try:
                conn = psycopg2.connect(
                    host="localhost",
                    port=port,
                    user="postgres",
                    password="",
                    database="postgres",
                    connect_timeout=3
                )
                conn.close()
                postgres_result = {"status": "success", "port": str(port)}
                break
            except Exception as e:
                postgres_result["error"] = f"Port {port}: {str(e)}"

        results["postgresql"] = postgres_result
    except ImportError:
        results["postgresql"] = {"status": "failed", "error": "psycopg2 not installed"}
    except Exception as e:
        results["postgresql"] = {"status": "failed", "error": str(e)}

    # Test Redis connectivity
    try:
        import redis
        redis_ports = [6379, 6380, 6381]
        redis_result = {"status": "failed", "error": "No ports accessible"}

        for port in redis_ports:
            try:
                r = redis.Redis(host='localhost', port=port, socket_connect_timeout=3)
                r.ping()
                redis_result = {"status": "success", "port": str(port)}
                break
            except Exception as e:
                redis_result["error"] = f"Port {port}: {str(e)}"

        results["redis"] = redis_result
    except ImportError:
        results["redis"] = {"status": "failed", "error": "redis package not installed"}
    except Exception as e:
        results["redis"] = {"status": "failed", "error": str(e)}

    # Test ClickHouse connectivity
    try:
        import clickhouse_connect
        clickhouse_ports = [8123, 9000]
        clickhouse_result = {"status": "failed", "error": "No ports accessible"}

        for port in clickhouse_ports:
            try:
                client = clickhouse_connect.get_client(
                    host='localhost',
                    port=port,
                    connect_timeout=3
                )
                client.ping()
                clickhouse_result = {"status": "success", "port": str(port)}
                break
            except Exception as e:
                clickhouse_result["error"] = f"Port {port}: {str(e)}"

        results["clickhouse"] = clickhouse_result
    except ImportError:
        results["clickhouse"] = {"status": "failed", "error": "clickhouse-connect not installed"}
    except Exception as e:
        results["clickhouse"] = {"status": "failed", "error": str(e)}

    return results

def get_database_configuration() -> Dict[str, str]:
    """Get current database configuration from environment."""
    env = IsolatedEnvironment()

    config = {
        "DATABASE_URL": env.get("DATABASE_URL", "Not set"),
        "POSTGRES_HOST": env.get("POSTGRES_HOST", "Not set"),
        "POSTGRES_PORT": env.get("POSTGRES_PORT", "Not set"),
        "POSTGRES_USER": env.get("POSTGRES_USER", "Not set"),
        "POSTGRES_DB": env.get("POSTGRES_DB", "Not set"),
        "REDIS_HOST": env.get("REDIS_HOST", "Not set"),
        "REDIS_PORT": env.get("REDIS_PORT", "Not set"),
        "REDIS_URL": env.get("REDIS_URL", "Not set"),
        "CLICKHOUSE_URL": env.get("CLICKHOUSE_URL", "Not set"),
        "ENVIRONMENT": env.get("ENVIRONMENT", "Not set"),
    }

    return config

def check_docker_alternative() -> Dict[str, str]:
    """Check if Docker Desktop is available as alternative."""
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            docker_status = {"available": True, "version": result.stdout.strip()}

            # Check if Docker Desktop is running
            compose_result = subprocess.run(
                ["docker", "ps"],
                capture_output=True,
                text=True,
                timeout=5
            )
            docker_status["running"] = compose_result.returncode == 0

            return docker_status
        else:
            return {"available": False, "error": "Docker command failed"}
    except Exception as e:
        return {"available": False, "error": str(e)}

def main():
    """Main database infrastructure testing."""
    print("=" * 60)
    print("DATABASE SERVICE INFRASTRUCTURE TEST - Issue #837 Phase 2")
    print("=" * 60)
    print()

    print("1. CHECKING PORT AVAILABILITY")
    print("-" * 30)
    database_ports = [
        ("PostgreSQL", "localhost", 5432),
        ("PostgreSQL (test)", "localhost", 5433),
        ("PostgreSQL (alt)", "localhost", 5434),
        ("Redis", "localhost", 6379),
        ("Redis (alt)", "localhost", 6381),
        ("ClickHouse HTTP", "localhost", 8123),
        ("ClickHouse Native", "localhost", 9000),
    ]

    for name, host, port in database_ports:
        available = check_port_availability(host, port)
        status = "AVAILABLE" if available else "NOT AVAILABLE"
        print(f"{name} ({host}:{port}): {status}")

    print()
    print("2. WINDOWS SERVICES CHECK")
    print("-" * 30)
    services = check_windows_services()
    if services:
        for service in services[:10]:  # Limit output
            print(f"Found: {service}")
    else:
        print("No database-related Windows services found")

    print()
    print("3. PYTHON CONNECTIVITY TEST")
    print("-" * 30)
    connectivity_results = test_python_connectivity()
    for db_name, result in connectivity_results.items():
        status = result["status"].upper()
        if status == "SUCCESS":
            port = result.get("port", "unknown")
            print(f"{db_name}: {status} (port {port})")
        else:
            error = result.get("error", "unknown error")
            print(f"{db_name}: {status} - {error}")

    print()
    print("4. CURRENT CONFIGURATION")
    print("-" * 30)
    config = get_database_configuration()
    for key, value in config.items():
        # Mask passwords in URLs
        if "password" in value.lower() or "://" in value:
            if "://" in value and "@" in value:
                parts = value.split("@")
                if len(parts) == 2:
                    prefix = parts[0].split("://")[0] + "://"
                    user_part = parts[0].split("://")[1]
                    if ":" in user_part:
                        user = user_part.split(":")[0]
                        value = f"{prefix}{user}:***@{parts[1]}"
        print(f"{key}: {value}")

    print()
    print("5. DOCKER AVAILABILITY CHECK")
    print("-" * 30)
    docker_status = check_docker_alternative()
    if docker_status.get("available"):
        print(f"Docker: Available ({docker_status.get('version', 'unknown version')})")
        print(f"Docker Running: {'Yes' if docker_status.get('running') else 'No'}")
    else:
        print(f"Docker: Not available - {docker_status.get('error', 'unknown error')}")

    print()
    print("6. RECOMMENDATIONS")
    print("-" * 30)

    # Determine what's working and what needs to be done
    working_services = []
    failed_services = []

    for db_name, result in connectivity_results.items():
        if result["status"] == "success":
            working_services.append(db_name)
        else:
            failed_services.append(db_name)

    if working_services:
        print(f"✓ Working services: {', '.join(working_services)}")

    if failed_services:
        print(f"✗ Failed services: {', '.join(failed_services)}")
        print()
        print("To start database services:")

        if "postgresql" in failed_services:
            print("  PostgreSQL:")
            print("    - Install PostgreSQL from https://www.postgresql.org/download/windows/")
            print("    - Or use Docker: docker run -p 5433:5432 -e POSTGRES_PASSWORD=test postgres")
            print("    - Or check if existing installation needs to be started")

        if "redis" in failed_services:
            print("  Redis:")
            print("    - Install Redis from https://github.com/microsoftarchive/redis/releases")
            print("    - Or use Docker: docker run -p 6379:6379 redis")
            print("    - Or install via Chocolatey: choco install redis-64")

        if "clickhouse" in failed_services:
            print("  ClickHouse:")
            print("    - Install ClickHouse from https://clickhouse.com/docs/en/install")
            print("    - Or use Docker: docker run -p 8123:8123 -p 9000:9000 clickhouse/clickhouse-server")

    if not working_services and not failed_services:
        print("No database connectivity tests could be performed due to missing Python packages.")
        print("Install required packages:")
        print("  pip install psycopg2-binary redis clickhouse-connect")

    print()
    print("NEXT STEPS:")
    print("- If using staging/remote databases, update configuration with remote URLs")
    print("- If using local services, start the required database services")
    print("- Run integration tests after services are available")
    print("- Consider using test framework's docker orchestration if local setup fails")

if __name__ == "__main__":
    main()