#!/usr/bin/env python3
"""
Container Manual Control Script - Supports Docker and Podman
For manual container operations when needed outside of the test framework.

This script provides a simple CLI interface to the unified container management system.
All operations use the central UnifiedDockerManager from test_framework, with added
Podman compatibility detection.

Usage:
    python scripts/docker_manual.py start       # Start test environment
    python scripts/docker_manual.py stop        # Stop all containers
    python scripts/docker_manual.py restart     # Restart services
    python scripts/docker_manual.py status      # Check status
    python scripts/docker_manual.py clean       # Clean up everything
    python scripts/docker_manual.py test        # Run tests with containers
    python scripts/docker_manual.py --runtime podman start  # Force Podman
"""

import sys
import os
import subprocess
import time
import logging
import shutil
import platform
from pathlib import Path
from typing import Optional, List, Tuple
import argparse

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from test_framework.unified_docker_manager import (
    UnifiedDockerManager,
    get_default_manager,
    restart_service,
    wait_for_services,
    EnvironmentType
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class ContainerManualControl:
    """Manual control interface for container operations supporting Docker and Podman"""
    
    def __init__(self, runtime: Optional[str] = None):
        """Initialize with optional runtime specification.
        
        Args:
            runtime: Force 'docker' or 'podman', or None for auto-detect
        """
        # Detect container runtime
        self.runtime, self.compose_cmd = self._detect_runtime(runtime)
        logger.info(f"Using container runtime: {self.runtime}")
        
        # Use the central unified Docker manager (works with both Docker and Podman)
        self.manager = get_default_manager()
        self.project_root = project_root
    
    def _detect_runtime(self, preferred: Optional[str] = None) -> Tuple[str, str]:
        """Detect available container runtime.
        
        Returns:
            Tuple of (runtime_command, compose_command)
        """
        # Windows: Prefer Podman if available for better performance
        if platform.system() == 'Windows' and not preferred:
            if shutil.which("podman"):
                logger.info("🐧 Windows detected - preferring Podman for better performance")
                if shutil.which("podman-compose"):
                    return "podman", "podman-compose"
                elif shutil.which("docker-compose"):
                    logger.info("Using docker-compose with Podman backend")
                    return "podman", "docker-compose"
        
        if preferred:
            if preferred == "docker" and shutil.which("docker"):
                if shutil.which("docker-compose"):
                    return "docker", "docker-compose"
                elif subprocess.run(["docker", "compose", "version"], capture_output=True).returncode == 0:
                    return "docker", "docker compose"
            elif preferred == "podman" and shutil.which("podman"):
                if shutil.which("podman-compose"):
                    return "podman", "podman-compose"
                else:
                    logger.warning("podman-compose not found. Install with: pip install podman-compose")
                    if shutil.which("docker-compose"):
                        logger.info("Falling back to docker-compose with Podman backend")
                        return "podman", "docker-compose"
        
        # Auto-detect (non-Windows or no Podman)
        if shutil.which("docker"):
            if shutil.which("docker-compose"):
                return "docker", "docker-compose"
            elif subprocess.run(["docker", "compose", "version"], capture_output=True).returncode == 0:
                return "docker", "docker compose"
        
        if shutil.which("podman"):
            if shutil.which("podman-compose"):
                return "podman", "podman-compose"
            elif shutil.which("docker-compose"):
                logger.info("Using docker-compose with Podman backend")
                return "podman", "docker-compose"
        
        raise RuntimeError(
            "No container runtime found! Please install Docker or Podman:\n"
            "Docker: https://docs.docker.com/get-docker/\n"
            "Podman: https://podman.io/getting-started/installation"
        )
        
    def start(self, environment: str = "test") -> bool:
        """Start container services using central manager"""
        logger.info(f"🚀 Starting {environment} environment with {self.runtime}...")
        
        # Ensure container runtime is available
        if not self._is_runtime_available():
            logger.info(f"{self.runtime.title()} is not running. Starting {self.runtime}...")
            if not self._start_runtime_daemon():
                logger.error(f"Failed to start {self.runtime}")
                return False
        
        # Acquire environment from central manager
        try:
            env_name, ports = self.manager.acquire_environment()
            logger.info(f"✅ Environment '{env_name}' started successfully")
            logger.info(f"Available ports: {ports}")
            
            # Wait for services to be healthy
            if not self.manager.wait_for_services(timeout=60):
                logger.error("Services failed health checks")
                return False
                
            logger.info("✅ All services are healthy")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start environment: {e}")
            return False
    
    def stop(self) -> bool:
        """Stop all container services using central manager"""
        logger.info(f"🛑 Stopping all {self.runtime} services...")
        
        # Get current environment name
        env_name = self.manager._get_environment_name()
        
        # Release environment
        self.manager.release_environment(env_name)
        
        logger.info("✅ All services stopped")
        return True
    
    def restart(self, services: Optional[List[str]] = None) -> bool:
        """Restart container services using central manager"""
        if services:
            logger.info(f"🔄 Restarting {self.runtime} services: {', '.join(services)}")
            success = True
            for service in services:
                if not restart_service(service):
                    logger.error(f"Failed to restart {service}")
                    success = False
            return success
        else:
            logger.info("🔄 Restarting all services...")
            self.stop()
            time.sleep(2)
            return self.start()
    
    def clean(self) -> bool:
        """Clean up everything using central manager"""
        logger.info("🧹 Cleaning up everything...")
        
        # Stop all services first
        self.stop()
        
        # Clean up orphaned containers
        self.manager.cleanup_orphaned_containers()
        
        # Clean up old environments
        self.manager.cleanup_old_environments(max_age_hours=0)  # Clean all
        
        logger.info("✅ Cleanup complete")
        return True
    
    def test(self, test_args: List[str] = None) -> bool:
        """Run tests with container services"""
        logger.info(f"🧪 Running tests with {self.runtime}...")
        
        # Check if services are already running
        if not self._is_runtime_available():
            logger.info(f"{self.runtime.title()} not running, starting services...")
            if not self.start("test"):
                return False
        elif not wait_for_services(timeout=10):
            logger.info("Services not healthy, restarting...")
            if not self.start("test"):
                return False
        else:
            logger.info("✅ Using existing Docker services")
        
        # Run tests
        test_cmd = [
            sys.executable,
            str(self.project_root / "tests" / "unified_test_runner.py"),
            "--real-services"
        ]
        
        if test_args:
            test_cmd.extend(test_args)
        else:
            test_cmd.extend(["--categories", "unit", "integration", "--fast-fail"])
        
        logger.info(f"Running: {' '.join(test_cmd)}")
        result = subprocess.run(test_cmd)
        
        return result.returncode == 0
    
    def status(self) -> bool:
        """Check status of all services using central manager"""
        logger.info(f"📊 Checking {self.runtime} service status...")
        
        # Check if runtime is available
        if not self._is_runtime_available():
            logger.error(f"❌ {self.runtime.title()} is not running")
            return False
        
        # Get container status from central manager
        container_info = self.manager.get_enhanced_container_status()
        
        if container_info:
            logger.info("\nRunning containers:")
            for name, info in container_info.items():
                status = "✅ Healthy" if info.health == "healthy" else f"⚠️ {info.health or 'Unknown'}"
                logger.info(f"  {name}: {status} - {info.state.value}")
        else:
            logger.info("No Netra containers are running")
        
        # Show health report
        logger.info("\nHealth Report:")
        print(self.manager.get_health_report())
        
        return True
    
    def _is_runtime_available(self) -> bool:
        """Check if container runtime is available."""
        try:
            result = subprocess.run(
                [self.runtime, "version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False
    
    def _start_runtime_daemon(self) -> bool:
        """Start container runtime daemon based on platform and runtime type."""
        # Check if runtime is already available
        if self._is_runtime_available():
            return True
        
        logger.info(f"Starting {self.runtime} daemon...")
        
        # Platform-specific runtime startup
        if self.runtime == "docker":
            if sys.platform == "win32":
                # Windows: Start Docker Desktop
                docker_desktop = r"C:\Program Files\Docker\Docker\Docker Desktop.exe"
                if Path(docker_desktop).exists():
                    subprocess.Popen([docker_desktop], shell=True)
                    logger.info("Starting Docker Desktop on Windows...")
                else:
                    logger.error("Docker Desktop not found")
                    return False
                    
            elif sys.platform == "darwin":
                # macOS: Start Docker Desktop
                subprocess.run(["open", "-a", "Docker"], capture_output=True)
                logger.info("Starting Docker Desktop on macOS...")
                
            else:
                # Linux: Start Docker daemon
                subprocess.run(["sudo", "systemctl", "start", "docker"], capture_output=True)
                logger.info("Starting Docker daemon on Linux...")
        
        elif self.runtime == "podman":
            if sys.platform == "win32":
                # Windows: Start Podman machine
                subprocess.run(["podman", "machine", "start"], capture_output=True)
                logger.info("Starting Podman machine on Windows...")
                
            elif sys.platform == "darwin":
                # macOS: Start Podman machine
                subprocess.run(["podman", "machine", "start"], capture_output=True)
                logger.info("Starting Podman machine on macOS...")
                
            else:
                # Linux: Podman runs rootless, no daemon needed
                logger.info("Podman runs rootless on Linux, no daemon to start")
                return True
        
        # Wait for runtime to be ready
        max_wait = 60
        for i in range(max_wait):
            if self._is_runtime_available():
                logger.info(f"✅ {self.runtime.title()} is ready after {i+1} seconds")
                return True
            time.sleep(1)
            if i % 5 == 0:
                logger.info(f"Waiting for {self.runtime}... ({i}/{max_wait}s)")
        
        logger.error(f"❌ {self.runtime.title()} failed to start after {max_wait} seconds")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Manual container control supporting Docker and Podman"
    )
    parser.add_argument(
        "command",
        choices=["start", "stop", "restart", "clean", "test", "status"],
        help="Command to execute"
    )
    parser.add_argument(
        "--runtime",
        choices=["docker", "podman"],
        help="Force specific container runtime (auto-detect by default)"
    )
    parser.add_argument(
        "--services",
        nargs="+",
        help="Specific services to operate on (for restart)"
    )
    parser.add_argument(
        "--env",
        default="test",
        choices=["test", "dev", "prod"],
        help="Environment to use (default: test)"
    )
    parser.add_argument(
        "test_args",
        nargs=argparse.REMAINDER,
        help="Additional arguments for test command"
    )
    
    args = parser.parse_args()
    
    try:
        controller = ContainerManualControl(runtime=args.runtime)
    except RuntimeError as e:
        logger.error(str(e))
        sys.exit(1)
    
    try:
        if args.command == "start":
            success = controller.start(args.env)
        elif args.command == "stop":
            success = controller.stop()
        elif args.command == "restart":
            success = controller.restart(args.services)
        elif args.command == "clean":
            success = controller.clean()
        elif args.command == "test":
            success = controller.test(args.test_args)
        elif args.command == "status":
            success = controller.status()
        else:
            logger.error(f"Unknown command: {args.command}")
            success = False
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        logger.info("\n⚠️ Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()