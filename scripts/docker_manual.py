#!/usr/bin/env python3
"""
Docker Manual Control Script
For manual Docker operations when needed outside of the test framework.

This script provides a simple CLI interface to the unified Docker management system.
All operations use the central UnifiedDockerManager from test_framework.

Usage:
    python scripts/docker_manual.py start       # Start test environment
    python scripts/docker_manual.py stop        # Stop all containers
    python scripts/docker_manual.py restart     # Restart services
    python scripts/docker_manual.py status      # Check status
    python scripts/docker_manual.py clean       # Clean up everything
    python scripts/docker_manual.py test        # Run tests with Docker
"""

import sys
import os
import subprocess
import time
import logging
from pathlib import Path
from typing import Optional, List
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


class DockerManualControl:
    """Manual control interface for Docker operations using central manager"""
    
    def __init__(self):
        # Use the central unified Docker manager
        self.manager = get_default_manager()
        self.project_root = project_root
        
    def start(self, environment: str = "test") -> bool:
        """Start Docker services using central manager"""
        logger.info(f"🚀 Starting {environment} environment...")
        
        # Ensure Docker is running first
        if not self.manager.is_docker_available():
            logger.info("Docker is not running. Starting Docker...")
            if not self._start_docker_daemon():
                logger.error("Failed to start Docker")
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
        """Stop all Docker services using central manager"""
        logger.info("🛑 Stopping all services...")
        
        # Get current environment name
        env_name = self.manager._get_environment_name()
        
        # Release environment
        self.manager.release_environment(env_name)
        
        logger.info("✅ All services stopped")
        return True
    
    def restart(self, services: Optional[List[str]] = None) -> bool:
        """Restart Docker services using central manager"""
        if services:
            logger.info(f"🔄 Restarting services: {', '.join(services)}")
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
        """Run tests with Docker services"""
        logger.info("🧪 Running tests with Docker...")
        
        # Check if services are already running
        if not self.manager.is_docker_available():
            logger.info("Docker not running, starting services...")
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
        logger.info("📊 Checking service status...")
        
        # Check if Docker is running
        if not self.manager.is_docker_available():
            logger.error("❌ Docker is not running")
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
    
    def _start_docker_daemon(self) -> bool:
        """Start Docker daemon based on platform"""
        # Check if Docker is already running
        if self.manager.is_docker_available():
            return True
        
        logger.info("Starting Docker daemon...")
        
        # Platform-specific Docker startup
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
        
        # Wait for Docker to be ready
        max_wait = 60
        for i in range(max_wait):
            if self.manager.is_docker_available():
                logger.info(f"✅ Docker is ready after {i+1} seconds")
                return True
            time.sleep(1)
            if i % 5 == 0:
                logger.info(f"Waiting for Docker... ({i}/{max_wait}s)")
        
        logger.error(f"❌ Docker failed to start after {max_wait} seconds")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Manual Docker control using central UnifiedDockerManager"
    )
    parser.add_argument(
        "command",
        choices=["start", "stop", "restart", "clean", "test", "status"],
        help="Command to execute"
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
    
    controller = DockerManualControl()
    
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