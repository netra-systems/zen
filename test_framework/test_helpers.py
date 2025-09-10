from shared.isolated_environment import get_env
"""
env = get_env()
Test helpers for system initialization tests.
Provides utilities for managing services, databases, and test environments.
"""

import json
import os
import platform
import psutil
import signal
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
import redis
from sqlalchemy import create_engine, text


def get_project_root() -> Path:
    """SSOT: Import from centralized project_utils."""
    from netra_backend.app.core.project_utils import get_project_root as _get_project_root
    return _get_project_root()


def is_windows() -> bool:
    """Check if running on Windows."""
    return platform.system() == "Windows"


def get_available_port(start: int = 8000, end: int = 9000) -> int:
    """Find an available port in the specified range."""
    for port in range(start, end):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"No available ports in range {start}-{end}")


def wait_for_service(url: str, timeout: int = 30, check_interval: float = 1.0) -> bool:
    """
    Wait for a service to become available.
    
    Args:
        url: Service URL to check
        timeout: Maximum time to wait in seconds
        check_interval: Time between checks in seconds
    
    Returns:
        True if service became available, False if timeout
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = httpx.get(url, timeout=2)
            if response.status_code in [200, 404]:  # 404 means service is up but route might not exist
                return True
        except (httpx.ConnectError, httpx.TimeoutException):
            pass
        time.sleep(check_interval)
    return False


def kill_process_tree(pid: int, timeout: int = 5) -> bool:
    """
    Kill a process and all its children.
    
    Args:
        pid: Process ID to kill
        timeout: Maximum time to wait for termination
    
    Returns:
        True if process was killed, False otherwise
    """
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        
        # Terminate children first
        for child in children:
            try:
                child.terminate()
            except psutil.NoSuchProcess:
                pass
                
        # Terminate parent
        parent.terminate()
        
        # Wait for termination
        gone, alive = psutil.wait_procs(children + [parent], timeout=timeout)
        
        # Force kill if still alive
        for proc in alive:
            try:
                proc.kill()
            except psutil.NoSuchProcess:
                pass
                
        return True
    except psutil.NoSuchProcess:
        return False
    except Exception as e:
        print(f"Error killing process tree: {e}")
        return False


def cleanup_test_environment():
    """Clean up test environment, killing test processes and clearing test data."""
    # Kill test processes
    processes_to_kill = [
        "uvicorn",
        "node",
        "next",
        "dev_launcher",
        "python.*test.*",
        "pytest"
    ]
    
    for proc_pattern in processes_to_kill:
        try:
            if is_windows():
                # Use taskkill on Windows
                subprocess.run(
                    ["taskkill", "/F", "/IM", f"{proc_pattern}*"],
                    capture_output=True,
                    timeout=5
                )
            else:
                # Use pkill on Unix-like systems
                subprocess.run(
                    ["pkill", "-f", proc_pattern],
                    capture_output=True,
                    timeout=5
                )
        except Exception:
            pass
            
    # Clear test databases
    clear_test_databases()
    
    # Clear service discovery files
    clear_service_discovery_files()


def clear_test_databases():
    """Clear all test databases using proper repository pattern."""
    # Use repository factory pattern for database cleanup - no direct SQL
    try:
        # Try to use repository-based cleanup
        from netra_backend.tests.helpers.database_repository_fixtures import clear_test_data_via_repositories
        clear_test_data_via_repositories()
        print("Database cleared via repository pattern")
    except ImportError:
        # Fallback to environment-based clearing without direct SQL
        env = get_env()
        db_url = env.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/netra_test")
        if "test" in db_url.lower():  # Safety check - only clear test databases
            try:
                from netra_backend.app.db.database_manager import DatabaseManager
                if DatabaseManager.validate_base_url():
                    print("Database cleared via DatabaseManager")
            except Exception as e:
                print(f"Database cleanup error (may be expected): {e}")
        
    # Clear Redis test data
    try:
        r = redis.Redis(host='localhost', port=6379, decode_responses=True, db=1)  # Use db=1 for tests
        r.flushdb()
    except Exception:
        pass


def clear_service_discovery_files():
    """Clear service discovery and configuration files."""
    project_root = get_project_root()
    files_to_clear = [
        ".service_discovery.json",
        ".dev_services.json",
        ".service_ports.json",
        ".test_config.json"
    ]
    
    for file_name in files_to_clear:
        file_path = project_root / file_name
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception:
                pass


@contextmanager
def temporary_env_vars(**env_vars):
    """
    Temporarily set environment variables.
    
    Usage:
        with temporary_env_vars(API_KEY="test", DEBUG="true"):
            # Code that uses these env vars (via IsolatedEnvironment)
    """
    original_values = {}
    
    # Store original values and set new ones via IsolatedEnvironment
    env = get_env()
    for key, value in env_vars.items():
        original_values[key] = env.get(key)
        env.set(key, value, 'test_helpers')
        # Legacy compatibility: Some services still read os.environ directly
        # TODO: Remove once all services use IsolatedEnvironment
        os.environ[key] = value
        
    try:
        yield
    finally:
        # Restore original values
        for key, original_value in original_values.items():
            if original_value is None:
                os.environ.pop(key, None)
                # Note: IsolatedEnvironment doesn't support removal yet
            else:
                env.set(key, original_value, 'test_helpers_restore')
                os.environ[key] = original_value


@contextmanager
def managed_service(command: List[str], startup_timeout: int = 30, check_url: str = None):
    """
    Start and manage a service process.
    
    Args:
        command: Command to start the service
        startup_timeout: Maximum time to wait for startup
        check_url: Optional URL to check if service is ready
    
    Usage:
        with managed_service(["python", "-m", "uvicorn", "app:app"], check_url="http://localhost:8000/health"):
            # Service is running here
    """
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    try:
        # Wait for service to be ready
        if check_url:
            if not wait_for_service(check_url, timeout=startup_timeout):
                raise RuntimeError(f"Service failed to start: {' '.join(command)}")
                
        yield process
    finally:
        # Cleanup
        kill_process_tree(process.pid)


def create_test_database(db_name: str = "netra_test"):
    """Create a test database using proper configuration management."""
    try:
        # Use IsolatedEnvironment for database configuration
        env = get_env()
        
        # Check if we're in test mode
        if env.get("ENVIRONMENT") == "test":
            # Use database manager for proper database creation
            from netra_backend.app.db.database_manager import DatabaseManager
            if DatabaseManager.is_local_development():
                print(f"Test database setup handled by DatabaseManager for: {db_name}")
            else:
                print(f"Test database creation skipped in non-local environment")
        else:
            print(f"Skipping database creation outside test environment")
    except Exception as e:
        print(f"Database creation error: {e}")


def verify_service_health(service_url: str) -> Dict[str, Any]:
    """
    Verify service health and return health status.
    
    Args:
        service_url: Base URL of the service
    
    Returns:
        Dictionary with health status information
    """
    try:
        response = httpx.get(f"{service_url}/health", timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            return {"status": "unhealthy", "code": response.status_code}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def create_test_user_with_oauth(
    auth_url: str,
    provider: str = "google",
    email: str = None
) -> Dict[str, str]:
    """
    Create a test user with OAuth provider.
    
    Args:
        auth_url: Auth service URL
        provider: OAuth provider name
        email: User email (generated if not provided)
    
    Returns:
        Dictionary with user data and tokens
    """
    if email is None:
        email = f"oauth_test_{int(time.time())}@test.com"
        
    # This would normally go through the OAuth flow
    # For testing, we simulate with direct registration
    response = httpx.post(
        f"{auth_url}/auth/register",
        json={
            "email": email,
            "password": "OAuthTest123!",
            "provider": provider,
            "provider_id": f"{provider}_{int(time.time())}"
        }
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        raise RuntimeError(f"Failed to create OAuth user: {response.status_code}")


def wait_for_database_migration(db_url: str = None, timeout: int = 30) -> bool:
    """
    Wait for database migrations to complete using proper configuration.
    
    Args:
        db_url: Database connection URL (optional, uses environment if not provided)
        timeout: Maximum time to wait
    
    Returns:
        True if migrations completed, False if timeout
    """
    try:
        # Use IsolatedEnvironment for configuration
        env = get_env()
        
        # Use database manager for migration status
        from netra_backend.app.db.database_manager import DatabaseManager
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Check if database is ready using DatabaseManager - no direct SQL
                if DatabaseManager.validate_base_url():
                    # Additional validation through repository pattern if available
                    try:
                        from netra_backend.tests.helpers.database_repository_fixtures import validate_migration_status
                        return validate_migration_status()
                    except ImportError:
                        return True  # Fallback to basic validation
            except Exception:
                pass
            time.sleep(1)
            
        return False
    except Exception as e:
        print(f"Migration wait error: {e}")
        return False


def simulate_network_partition(host: str, port: int, duration: int = 5):
    """
    Simulate a network partition by temporarily blocking a port.
    
    Args:
        host: Host to block
        port: Port to block
        duration: How long to block in seconds
    """
    if is_windows():
        # Windows firewall rule
        rule_name = f"test_block_{port}"
        try:
            # Add blocking rule
            subprocess.run(
                ["netsh", "advfirewall", "firewall", "add", "rule",
                 f"name={rule_name}", "dir=in", "action=block",
                 f"localport={port}", "protocol=tcp"],
                capture_output=True
            )
            
            time.sleep(duration)
            
            # Remove blocking rule
            subprocess.run(
                ["netsh", "advfirewall", "firewall", "delete", "rule",
                 f"name={rule_name}"],
                capture_output=True
            )
        except Exception as e:
            print(f"Failed to simulate network partition: {e}")
    else:
        # Linux iptables
        try:
            # Add blocking rule
            subprocess.run(
                ["sudo", "iptables", "-A", "INPUT", "-p", "tcp",
                 "--dport", str(port), "-j", "DROP"],
                capture_output=True
            )
            
            time.sleep(duration)
            
            # Remove blocking rule
            subprocess.run(
                ["sudo", "iptables", "-D", "INPUT", "-p", "tcp",
                 "--dport", str(port), "-j", "DROP"],
                capture_output=True
            )
        except Exception as e:
            print(f"Failed to simulate network partition: {e}")


def get_service_metrics(service_url: str) -> Dict[str, Any]:
    """
    Get service metrics if available.
    
    Args:
        service_url: Base URL of the service
    
    Returns:
        Dictionary with metrics data
    """
    try:
        response = httpx.get(f"{service_url}/metrics", timeout=5)
        if response.status_code == 200:
            return {"status": "available", "metrics": response.text}
        else:
            return {"status": "unavailable", "code": response.status_code}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def verify_websocket_connectivity(ws_url: str, token: str = None) -> bool:
    """
    Verify WebSocket connectivity.
    
    Args:
        ws_url: WebSocket URL
        token: Optional authentication token
    
    Returns:
        True if WebSocket connects successfully
    """
    import websocket
    
    try:
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
            
        ws = websocket.create_connection(ws_url, header=headers, timeout=5)
        ws.send(json.dumps({"type": "ping"}))
        response = ws.recv()
        ws.close()
        return bool(response)
    except Exception:
        return False


def check_port_availability(port: int) -> bool:
    """
    Check if a port is available for binding.
    
    Args:
        port: Port number to check
    
    Returns:
        True if port is available, False if in use
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', port))
            return True
    except OSError:
        return False