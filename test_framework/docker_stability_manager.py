#!/usr/bin/env python3
"""
Docker Stability Manager - Ensures Docker daemon reliability during test execution

SCIENTIFIC ANALYSIS:
- Problem: Docker Desktop on macOS intermittently shuts down during test runs
- Root Cause: System resource pressure, daemon timeouts, auto-sleep behavior
- Solution: Proactive monitoring, auto-restart, container restoration

This module provides permanent fixes for Docker instability issues.
"""
import subprocess
import time
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import os
import signal
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class DockerHealth:
    """Docker daemon health status"""
    daemon_running: bool
    daemon_responsive: bool
    containers_present: bool
    error_message: Optional[str] = None

class DockerStabilityManager:
    """
    Manages Docker daemon stability and container persistence for reliable testing.
    
    Key Features:
    - Docker daemon health monitoring
    - Automatic daemon restart on failure
    - Container restoration after daemon restart
    - Graceful degradation when Docker is unavailable
    """
    
    def __init__(self, required_containers: Optional[List[str]] = None):
        # Dynamically determine the project prefix
        self.project_prefix = self._get_project_prefix()
        self.required_containers = required_containers or [
            f'{self.project_prefix}-test-backend-1',
            f'{self.project_prefix}-test-auth-1', 
            f'{self.project_prefix}-test-postgres-1',
            f'{self.project_prefix}-test-redis-1',
            f'{self.project_prefix}-test-clickhouse-1'
        ]
        # Dynamically find compose file relative to current working directory
        self.compose_file = self._find_compose_file()
        self.max_restart_attempts = 3
        self.restart_delay = 10  # seconds
    
    def _get_project_prefix(self) -> str:
        """
        Get the project prefix for Docker container names.
        
        Returns:
            Project prefix (e.g., 'netra-apex')
        """
        # Dynamically determine project prefix from directory or existing containers
        try:
            # Try to get project name from Git repo root directory name
            import git
            repo = git.Repo(search_parent_directories=True)
            project_name = Path(repo.working_dir).name
            return project_name
        except Exception:
            pass
        
        # Fall back to current directory name
        try:
            current_dir = Path.cwd()
            # Find the root project directory by looking for docker-compose files
            for parent in [current_dir] + list(current_dir.parents)[:3]:
                if (parent / 'docker-compose.test.yml').exists():
                    return parent.name
            # If no compose file found, use current directory name
            return current_dir.name
        except Exception:
            pass
        
        # Final fallback to detect from existing containers
        try:
            result = subprocess.run(
                ['docker', 'ps', '--format', '{{.Names}}'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                container_names = result.stdout.strip().split('\n')
                for name in container_names:
                    if '-test-' in name:
                        # Extract project prefix (everything before -test-)
                        return name.split('-test-')[0]
        except Exception:
            pass
            
        # Ultimate fallback
        return 'netra-apex'
    
    def _find_compose_file(self) -> str:
        """
        Find the docker-compose.test.yml file relative to current directory.
        
        Returns:
            Path to the compose file
        """
        # Try to find git root first
        try:
            import git
            repo = git.Repo(search_parent_directories=True)
            compose_path = Path(repo.working_dir) / 'docker-compose.test.yml'
            if compose_path.exists():
                return str(compose_path)
        except Exception:
            pass
        
        # Fall back to searching from current directory
        current_path = Path.cwd()
        
        # Check current directory
        if (current_path / 'docker-compose.test.yml').exists():
            return str(current_path / 'docker-compose.test.yml')
        
        # Check parent directories (up to 3 levels)
        for parent in [current_path.parent, current_path.parent.parent, current_path.parent.parent.parent]:
            compose_path = parent / 'docker-compose.test.yml'
            if compose_path.exists():
                return str(compose_path)
        
        # Default fallback
        return 'docker-compose.test.yml'
        
    def check_docker_health(self, timeout: float = 5.0) -> DockerHealth:
        """
        Comprehensive Docker daemon health check.
        
        Args:
            timeout: Maximum time to wait for Docker commands
            
        Returns:
            DockerHealth object with detailed status
        """
        try:
            # Test daemon connectivity
            result = subprocess.run(
                ['docker', 'version', '--format', '{{.Server.Version}}'],
                capture_output=True, text=True, timeout=timeout
            )
            
            daemon_running = result.returncode == 0
            if not daemon_running:
                return DockerHealth(
                    daemon_running=False,
                    daemon_responsive=False,
                    containers_present=False,
                    error_message=f"Docker daemon not running: {result.stderr}"
                )
            
            # Test daemon responsiveness
            result = subprocess.run(
                ['docker', 'ps', '-q'],
                capture_output=True, text=True, timeout=timeout
            )
            
            daemon_responsive = result.returncode == 0
            if not daemon_responsive:
                return DockerHealth(
                    daemon_running=True,
                    daemon_responsive=False, 
                    containers_present=False,
                    error_message=f"Docker daemon unresponsive: {result.stderr}"
                )
            
            # Check for required containers
            missing_containers = self._check_container_presence()
            containers_present = len(missing_containers) == 0
            
            return DockerHealth(
                daemon_running=True,
                daemon_responsive=True,
                containers_present=containers_present,
                error_message=f"Missing containers: {missing_containers}" if missing_containers else None
            )
            
        except subprocess.TimeoutExpired:
            return DockerHealth(
                daemon_running=False,
                daemon_responsive=False,
                containers_present=False,
                error_message="Docker command timed out"
            )
        except Exception as e:
            return DockerHealth(
                daemon_running=False,
                daemon_responsive=False,
                containers_present=False,
                error_message=f"Docker health check failed: {e}"
            )
    
    def _check_container_presence(self) -> List[str]:
        """Check which required containers are missing"""
        missing = []
        
        try:
            result = subprocess.run(
                ['docker', 'ps', '--format', '{{.Names}}'],
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode == 0:
                running_containers = result.stdout.strip().split('\n')
                for required in self.required_containers:
                    if required not in running_containers:
                        missing.append(required)
        except Exception as e:
            logger.warning(f"Container presence check failed: {e}")
            missing = self.required_containers.copy()
            
        return missing
    
    def restart_docker_desktop(self) -> bool:
        """
        Restart Docker Desktop application on macOS.
        
        Returns:
            True if restart was successful, False otherwise
        """
        try:
            logger.info("🔄 Restarting Docker Desktop...")
            
            # Kill existing Docker processes
            subprocess.run(['pkill', '-f', 'Docker'], capture_output=True)
            time.sleep(3)
            
            # Start Docker Desktop
            subprocess.run(['open', '/Applications/Docker.app'], capture_output=True)
            
            # Wait for Docker to fully start
            max_wait = 60  # seconds
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                health = self.check_docker_health(timeout=3)
                if health.daemon_running and health.daemon_responsive:
                    logger.info("✅ Docker Desktop restarted successfully")
                    return True
                time.sleep(2)
            
            logger.error("❌ Docker Desktop restart timed out")
            return False
            
        except Exception as e:
            logger.error(f"Docker Desktop restart failed: {e}")
            return False
    
    def restore_containers(self) -> bool:
        """
        Restore required containers using docker-compose.
        
        Returns:
            True if containers were restored successfully
        """
        try:
            logger.info("🔧 Restoring containers...")
            
            # Use docker-compose to restore containers
            result = subprocess.run([
                'docker-compose', '-f', self.compose_file, 'up', '-d'
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                logger.error(f"Container restoration failed: {result.stderr}")
                return False
            
            # Wait for containers to be healthy
            max_wait = 60
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                health = self.check_docker_health()
                if health.containers_present:
                    logger.info("✅ Containers restored successfully")
                    return True
                time.sleep(3)
            
            logger.error("❌ Container restoration timed out")
            return False
            
        except Exception as e:
            logger.error(f"Container restoration failed: {e}")
            return False
    
    def ensure_docker_stability(self) -> Tuple[bool, str]:
        """
        Ensure Docker daemon and containers are stable and ready for testing.
        
        This is the main entry point for ensuring Docker stability.
        
        Returns:
            Tuple of (success, message)
        """
        for attempt in range(self.max_restart_attempts):
            logger.info(f"🔍 Docker stability check (attempt {attempt + 1}/{self.max_restart_attempts})")
            
            health = self.check_docker_health()
            
            if health.daemon_running and health.daemon_responsive and health.containers_present:
                return True, "Docker is stable and ready"
            
            logger.warning(f"Docker issues detected: {health.error_message}")
            
            # Try to fix the issues
            if not health.daemon_running or not health.daemon_responsive:
                logger.info("Docker daemon issues - attempting restart...")
                if not self.restart_docker_desktop():
                    if attempt == self.max_restart_attempts - 1:
                        return False, "Failed to restart Docker daemon"
                    time.sleep(self.restart_delay)
                    continue
            
            if not health.containers_present:
                logger.info("Container issues - attempting restoration...")
                if not self.restore_containers():
                    if attempt == self.max_restart_attempts - 1:
                        return False, "Failed to restore containers"
                    time.sleep(self.restart_delay)
                    continue
            
            # Small delay before next attempt
            time.sleep(2)
        
        return False, f"Docker stability could not be ensured after {self.max_restart_attempts} attempts"
    
    def monitor_during_testing(self, check_interval: int = 30) -> None:
        """
        Background monitoring of Docker stability during test execution.
        
        Args:
            check_interval: Seconds between health checks
        """
        logger.info(f"🔍 Starting Docker stability monitoring (interval: {check_interval}s)")
        
        while True:
            try:
                health = self.check_docker_health()
                
                if not (health.daemon_running and health.daemon_responsive):
                    logger.error("Docker daemon became unhealthy during testing!")
                    success, message = self.ensure_docker_stability()
                    if success:
                        logger.info("Docker stability restored")
                    else:
                        logger.error(f"Failed to restore Docker stability: {message}")
                
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                logger.info("Docker stability monitoring stopped")
                break
            except Exception as e:
                logger.error(f"Docker monitoring error: {e}")
                time.sleep(check_interval)

def ensure_docker_for_testing() -> bool:
    """
    Convenience function to ensure Docker is ready for testing.
    
    Returns:
        True if Docker is stable and ready
    """
    manager = DockerStabilityManager()
    success, message = manager.ensure_docker_stability()
    
    if success:
        logger.info("🐳 Docker is ready for testing")
    else:
        logger.error(f"🚨 Docker stability check failed: {message}")
        
    return success

if __name__ == "__main__":
    # Enable debug logging
    logging.basicConfig(level=logging.INFO)
    
    # Test Docker stability
    if ensure_docker_for_testing():
        print("✅ Docker is ready for testing")
    else:
        print("❌ Docker stability issues detected")
        exit(1)