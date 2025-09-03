"""
Docker Test Utilities for Stress Testing

Provides utilities for managing Docker containers during tests,
monitoring memory usage, and simulating container failures.
"""

import json
import os
import subprocess
import time
from typing import Dict, Optional, Any
import psutil


class DockerContainerManager:
    """Manages Docker containers for testing purposes"""
    
    def __init__(self, container_name: str = "test-container"):
        self.container_name = container_name
        self.container_id = None
        
    def start(self, image: str = "alpine:latest", **kwargs) -> str:
        """Start a Docker container for testing"""
        # For testing purposes, we'll simulate container operations
        # In a real environment, this would use docker-py or subprocess
        self.container_id = f"mock-{self.container_name}-{time.time()}"
        return self.container_id
    
    def stop(self) -> None:
        """Stop the test container"""
        if self.container_id:
            # Simulate container stop
            self.container_id = None
    
    def restart(self) -> None:
        """Restart the test container"""
        old_id = self.container_id
        self.stop()
        self.container_id = f"mock-{self.container_name}-{time.time()}"
    
    def get_logs(self, tail: int = 100) -> str:
        """Get container logs"""
        return f"Mock logs for container {self.container_id}"
    
    def exec_command(self, command: str) -> str:
        """Execute command in container"""
        return f"Mock execution of: {command}"


def get_container_memory_stats(container_id: str = None) -> Dict[str, Any]:
    """
    Get memory statistics for a container or current process
    
    Returns dict with:
    - usage_mb: Current memory usage in MB
    - limit_mb: Memory limit in MB
    - percent: Usage percentage
    - available_mb: Available memory in MB
    """
    # For testing, we'll use the current process's memory stats
    # In production, this would query Docker API
    process = psutil.Process()
    memory_info = process.memory_info()
    system_memory = psutil.virtual_memory()
    
    usage_mb = memory_info.rss / (1024 * 1024)
    limit_mb = system_memory.total / (1024 * 1024)
    available_mb = system_memory.available / (1024 * 1024)
    
    # Check if we're in a Docker container by looking for cgroup limits
    cgroup_limit = _get_cgroup_memory_limit()
    if cgroup_limit:
        limit_mb = cgroup_limit / (1024 * 1024)
    
    percent = (usage_mb / limit_mb) * 100 if limit_mb > 0 else 0
    
    return {
        "usage_mb": round(usage_mb, 2),
        "limit_mb": round(limit_mb, 2),
        "percent": round(percent, 2),
        "available_mb": round(available_mb, 2),
        "container_id": container_id or "current_process"
    }


def wait_for_container_health(container_id: str, timeout: int = 60) -> bool:
    """
    Wait for a container to become healthy
    
    Args:
        container_id: Container to check
        timeout: Maximum time to wait in seconds
        
    Returns:
        True if container is healthy, False if timeout
    """
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        # In production, check actual container health
        # For testing, simulate health check
        stats = get_container_memory_stats(container_id)
        
        # Consider healthy if memory usage is below 90%
        if stats["percent"] < 90:
            return True
        
        time.sleep(1)
    
    return False


def force_container_restart(container_id: str) -> bool:
    """
    Force restart a container
    
    Args:
        container_id: Container to restart
        
    Returns:
        True if restart successful
    """
    try:
        # In production, this would use Docker API
        # For testing, we simulate a restart
        print(f"Simulating restart of container {container_id}")
        time.sleep(0.5)  # Simulate restart time
        return True
    except Exception as e:
        print(f"Failed to restart container: {e}")
        return False


def _get_cgroup_memory_limit() -> Optional[int]:
    """
    Get memory limit from cgroup (when running in Docker)
    
    Returns:
        Memory limit in bytes or None if not in container
    """
    cgroup_files = [
        "/sys/fs/cgroup/memory/memory.limit_in_bytes",  # cgroup v1
        "/sys/fs/cgroup/memory.max"  # cgroup v2
    ]
    
    for cgroup_file in cgroup_files:
        if os.path.exists(cgroup_file):
            try:
                with open(cgroup_file, 'r') as f:
                    limit = f.read().strip()
                    if limit.isdigit():
                        limit_bytes = int(limit)
                        # Check if it's not the "unlimited" value
                        if limit_bytes < 9223372036854775807:  # MAX_INT64
                            return limit_bytes
            except (IOError, ValueError):
                pass
    
    return None


def check_docker_available() -> bool:
    """Check if Docker is available on the system"""
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def get_docker_memory_limit(container_name: str) -> Optional[int]:
    """
    Get the memory limit for a specific Docker container
    
    Args:
        container_name: Name or ID of the container
        
    Returns:
        Memory limit in bytes or None if not found
    """
    if not check_docker_available():
        return None
    
    try:
        result = subprocess.run(
            ["docker", "inspect", container_name],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            if data and len(data) > 0:
                memory_limit = data[0].get("HostConfig", {}).get("Memory", 0)
                if memory_limit > 0:
                    return memory_limit
    except (subprocess.SubprocessError, json.JSONDecodeError, KeyError):
        pass
    
    return None


def simulate_memory_pressure(target_mb: int, duration_seconds: int = 10) -> None:
    """
    Simulate memory pressure by allocating memory
    
    Args:
        target_mb: Amount of memory to allocate in MB
        duration_seconds: How long to hold the memory
    """
    try:
        # Allocate memory in chunks to avoid sudden spike
        chunk_size_mb = min(100, target_mb // 10)
        chunks = []
        
        allocated_mb = 0
        while allocated_mb < target_mb:
            size = min(chunk_size_mb, target_mb - allocated_mb)
            # Create a bytearray to actually allocate memory
            chunk = bytearray(size * 1024 * 1024)
            chunks.append(chunk)
            allocated_mb += size
            time.sleep(0.1)  # Small delay between allocations
        
        print(f"Allocated {allocated_mb}MB of memory")
        time.sleep(duration_seconds)
        
    finally:
        # Memory will be freed when chunks go out of scope
        pass


def monitor_memory_during_test(func):
    """
    Decorator to monitor memory usage during a test
    
    Usage:
        @monitor_memory_during_test
        def test_something():
            ...
    """
    def wrapper(*args, **kwargs):
        initial_stats = get_container_memory_stats()
        print(f"Initial memory: {initial_stats['usage_mb']}MB")
        
        try:
            result = func(*args, **kwargs)
            
            final_stats = get_container_memory_stats()
            print(f"Final memory: {final_stats['usage_mb']}MB")
            print(f"Memory delta: {final_stats['usage_mb'] - initial_stats['usage_mb']}MB")
            
            return result
            
        except Exception as e:
            error_stats = get_container_memory_stats()
            print(f"Memory at error: {error_stats['usage_mb']}MB")
            raise
    
    return wrapper