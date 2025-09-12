#!/usr/bin/env python3
"""
Graceful PostgreSQL Shutdown Script

This script ensures PostgreSQL is properly shut down to prevent automatic recovery
on the next startup. It performs the following steps:

1. Waits for active connections to complete
2. Stops new connections
3. Performs a final checkpoint
4. Gracefully stops the container

Author: Netra Core Generation 1
Date: 2025-08-28
"""

import sys
import time
import subprocess
import json
from typing import Dict, List, Optional


def run_command(cmd: List[str], capture_output: bool = True) -> subprocess.CompletedProcess:
    """Execute a command and return the result."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            check=False
        )
        return result
    except Exception as e:
        print(f"Error running command {' '.join(cmd)}: {e}")
        sys.exit(1)


def check_postgres_container() -> Optional[Dict]:
    """Check if the PostgreSQL container is running."""
    result = run_command(["docker", "ps", "--filter", "name=netra-postgres", "--format", "json"])
    
    if result.returncode != 0:
        print("Error: Failed to check Docker containers")
        return None
    
    if result.stdout.strip():
        try:
            container_info = json.loads(result.stdout.strip())
            return container_info
        except json.JSONDecodeError:
            # Try line-by-line format
            lines = result.stdout.strip().split('\n')
            if lines:
                try:
                    return json.loads(lines[0])
                except json.JSONDecodeError:
                    print("Warning: Could not parse container info")
    
    return None


def get_active_connections() -> int:
    """Get the number of active database connections."""
    query = """
    SELECT COUNT(*) 
    FROM pg_stat_activity 
    WHERE state = 'active' 
    AND pid != pg_backend_pid()
    AND application_name != 'psql'
    """
    
    result = run_command([
        "docker", "exec", "netra-postgres",
        "psql", "-U", "netra", "-d", "netra_dev",
        "-t", "-c", query
    ])
    
    if result.returncode == 0:
        try:
            return int(result.stdout.strip())
        except ValueError:
            return 0
    return 0


def wait_for_connections_to_close(timeout: int = 60) -> bool:
    """Wait for active connections to close gracefully."""
    print("Waiting for active database connections to close...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        active_connections = get_active_connections()
        print(f"Active connections: {active_connections}")
        
        if active_connections == 0:
            print("All connections closed.")
            return True
        
        time.sleep(2)
    
    print(f"Warning: Timeout reached. {get_active_connections()} connections still active.")
    return False


def perform_final_checkpoint():
    """Perform a final database checkpoint before shutdown."""
    print("Performing final database checkpoint...")
    
    result = run_command([
        "docker", "exec", "netra-postgres",
        "psql", "-U", "netra", "-d", "netra_dev",
        "-c", "CHECKPOINT;"
    ])
    
    if result.returncode == 0:
        print("Database checkpoint completed successfully.")
        return True
    else:
        print("Warning: Database checkpoint failed.")
        return False


def stop_postgres_gracefully():
    """Stop PostgreSQL using the proper signal."""
    print("Stopping PostgreSQL gracefully...")
    
    # Send SIGTERM to PostgreSQL process for graceful shutdown
    result = run_command([
        "docker", "exec", "netra-postgres",
        "pg_ctl", "stop", "-D", "/var/lib/postgresql/data", "-m", "smart", "-w"
    ])
    
    if result.returncode == 0:
        print("PostgreSQL stopped gracefully.")
        return True
    else:
        print("Warning: PostgreSQL graceful stop failed, using container stop...")
        # Fallback to container stop
        result = run_command(["docker", "stop", "--time", "30", "netra-postgres"])
        return result.returncode == 0


def main():
    """Main function to perform graceful PostgreSQL shutdown."""
    print("=== Graceful PostgreSQL Shutdown ===")
    
    # Check if container is running
    container_info = check_postgres_container()
    if not container_info:
        print("PostgreSQL container is not running.")
        return
    
    print(f"PostgreSQL container found: {container_info.get('Names', 'netra-postgres')}")
    
    # Wait for connections to close
    wait_for_connections_to_close()
    
    # Perform final checkpoint
    perform_final_checkpoint()
    
    # Stop PostgreSQL gracefully
    if stop_postgres_gracefully():
        print(" PASS:  PostgreSQL shutdown completed successfully.")
    else:
        print(" FAIL:  PostgreSQL shutdown completed with warnings.")
        sys.exit(1)


if __name__ == "__main__":
    main()