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

# Import Windows encoding SSOT and set up encoding
from shared.windows_encoding import setup_windows_encoding
setup_windows_encoding()

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
        # If preferred is specified, use it first
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
                    # SSOT: No fallbacks - user must install proper compose tool
                    logger.error(" FAIL:  SSOT VIOLATION: podman-compose not found")
                    logger.error("Solution: Install podman-compose with: pip install podman-compose")
                    raise RuntimeError(
                        "SSOT RUNTIME REQUIREMENT: When using Podman, podman-compose must be installed. "
                        "Install with: pip install podman-compose. No docker-compose fallbacks allowed."
                    )
        
        # Windows: Prefer Podman if available for better performance (only if not preferred)
        if platform.system() == 'Windows' and not preferred:
            if shutil.which("podman"):
                logger.info("[U+1F427] Windows detected - preferring Podman for better performance")
                if shutil.which("podman-compose"):
                    return "podman", "podman-compose"
                else:
                    # SSOT: No docker-compose fallback with Podman
                    logger.error(" FAIL:  SSOT VIOLATION: podman-compose required on Windows")
                    logger.error("Solution: Install podman-compose with: pip install podman-compose") 
                    raise RuntimeError(
                        "SSOT WINDOWS REQUIREMENT: Podman on Windows requires podman-compose. "
                        "Install with: pip install podman-compose. No docker-compose fallbacks."
                    )
        
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
        logger.info(f"[U+1F680] Starting {environment} environment with {self.runtime}...")
        
        # Ensure container runtime is available
        if not self._is_runtime_available():
            logger.info(f"{self.runtime.title()} is not running. Starting {self.runtime}...")
            if not self._start_runtime_daemon():
                logger.error(f"Failed to start {self.runtime}")
                return False
        
        # Acquire environment from central manager
        try:
            env_name, ports = self.manager.acquire_environment()
            logger.info(f" PASS:  Environment '{env_name}' started successfully")
            logger.info(f"Available ports: {ports}")
            
            # Wait for services to be healthy
            if not self.manager.wait_for_services(timeout=60):
                logger.error("Services failed health checks")
                return False
                
            logger.info(" PASS:  All services are healthy")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start environment: {e}")
            return False
    
    def stop(self) -> bool:
        """Stop all container services using central manager"""
        logger.info(f"[U+1F6D1] Stopping all {self.runtime} services...")
        
        # Get current environment name
        env_name = self.manager._get_environment_name()
        
        # Release environment
        self.manager.release_environment(env_name)
        
        logger.info(" PASS:  All services stopped")
        return True
    
    def restart(self, services: Optional[List[str]] = None) -> bool:
        """Restart container services using central manager"""
        if services:
            logger.info(f" CYCLE:  Restarting {self.runtime} services: {', '.join(services)}")
            success = True
            for service in services:
                if not restart_service(service):
                    logger.error(f"Failed to restart {service}")
                    success = False
            return success
        else:
            logger.info(" CYCLE:  Restarting all services...")
            self.stop()
            time.sleep(2)
            return self.start()
    
    def clean(self) -> bool:
        """Clean up everything using central manager"""
        logger.info("[U+1F9F9] Cleaning up everything...")
        
        # Stop all services first
        self.stop()
        
        # Clean up orphaned containers
        self.manager.cleanup_orphaned_containers()
        
        # Clean up old environments
        self.manager.cleanup_old_environments(max_age_hours=0)  # Clean all
        
        logger.info(" PASS:  Cleanup complete")
        return True
    
    def test(self, test_args: List[str] = None) -> bool:
        """Run tests with container services"""
        logger.info(f"[U+1F9EA] Running tests with {self.runtime}...")
        
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
            logger.info(" PASS:  Using existing Docker services")
        
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
        logger.info(f" CHART:  Checking {self.runtime} service status...")
        
        # Check if runtime is available
        if not self._is_runtime_available():
            logger.error(f" FAIL:  {self.runtime.title()} is not running")
            return False
        
        # Get container status from central manager
        container_info = self.manager.get_enhanced_container_status()
        
        if container_info:
            logger.info("\nRunning containers:")
            for name, info in container_info.items():
                status = " PASS:  Healthy" if info.health == "healthy" else f" WARNING: [U+FE0F] {info.health or 'Unknown'}"
                logger.info(f"  {name}: {status} - {info.state.value}")
        else:
            logger.info("No Netra containers are running")
        
        # Show health report
        logger.info("\nHealth Report:")
        print(self.manager.get_health_report())
        
        return True
    
    def monitor_resources(self) -> bool:
        """Monitor resource usage of running containers"""
        logger.info(" CHART:  Monitoring container resource usage...")
        
        # Check if runtime is available
        if not self._is_runtime_available():
            logger.error(f" FAIL:  {self.runtime.title()} is not running")
            return False
        
        # Get real-time stats
        try:
            # Docker stats command to show resource usage
            cmd = [self.runtime, "stats", "--no-stream", "--format",
                   "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}"]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                logger.info("\n SEARCH:  Current Resource Usage:")
                print(result.stdout)
                
                # Parse and analyze the output
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:  # Skip header
                    total_mem_percent = 0.0
                    high_usage_containers = []
                    
                    for line in lines[1:]:
                        parts = line.split()
                        if len(parts) >= 4:
                            container = parts[0]
                            try:
                                mem_percent = float(parts[3].rstrip('%'))
                                total_mem_percent += mem_percent
                                
                                # Flag high memory usage
                                if mem_percent > 50:
                                    high_usage_containers.append((container, mem_percent))
                            except (ValueError, IndexError):
                                continue
                    
                    # Summary analysis
                    logger.info(f"\n[U+1F4C8] Resource Analysis:")
                    logger.info(f"  Total Memory Usage: {total_mem_percent:.1f}%")
                    
                    if high_usage_containers:
                        logger.warning("   WARNING: [U+FE0F] High memory usage detected:")
                        for container, usage in high_usage_containers:
                            logger.warning(f"    - {container}: {usage:.1f}%")
                    
                    if total_mem_percent > 80:
                        logger.error("   ALERT:  CRITICAL: Total memory usage exceeds 80%!")
                        logger.info("  Consider stopping unnecessary services or reducing limits")
                
                # Check WSL2 memory if on Windows
                if platform.system() == "Windows":
                    self._check_wsl_memory()
                    
            else:
                logger.error(f"Failed to get stats: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Timeout getting container stats")
            return False
        except Exception as e:
            logger.error(f"Error monitoring resources: {e}")
            return False
        
        return True
    
    def _check_wsl_memory(self):
        """Check WSL2 memory usage on Windows"""
        try:
            # Get WSL2 memory info
            wsl_cmd = ["wsl", "-e", "free", "-h"]
            result = subprocess.run(wsl_cmd, capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                logger.info("\n[U+1F5A5][U+FE0F] WSL2 Memory Status:")
                for line in result.stdout.split('\n'):
                    if line.strip():
                        print(f"  {line}")
        except:
            # WSL might not be available
            pass
    
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
                logger.info(f" PASS:  {self.runtime.title()} is ready after {i+1} seconds")
                return True
            time.sleep(1)
            if i % 5 == 0:
                logger.info(f"Waiting for {self.runtime}... ({i}/{max_wait}s)")
        
        logger.error(f" FAIL:  {self.runtime.title()} failed to start after {max_wait} seconds")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Manual container control supporting Docker and Podman"
    )
    parser.add_argument(
        "command",
        choices=["start", "stop", "restart", "clean", "test", "status", "monitor", "refresh-dev"],
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
        elif args.command == "monitor":
            success = controller.monitor_resources()
        elif args.command == "refresh-dev":
            logger.info(" CYCLE:  Forwarding to refresh_dev command...")
            # Forward to the official refresh_dev script
            import subprocess
            script_path = Path(__file__).parent / "refresh_dev.py"
            cmd = [sys.executable, str(script_path)]
            if args.services:
                cmd.extend(args.services)
            result = subprocess.run(cmd)
            success = result.returncode == 0
        else:
            logger.error(f"Unknown command: {args.command}")
            success = False
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        logger.info("\n WARNING: [U+FE0F] Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f" FAIL:  Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()